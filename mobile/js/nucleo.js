/* nucleo.js — Motor de negocio de MV FBA IA, portado a JavaScript para
   que la app Android funcione 100% en el telefono, SIN depender de la PC.

   Es un port FIEL de los modulos Python (agents/pricing, ganancias, exito,
   dedicacion, capital_planner). Cada formula se valida contra la salida de
   Python en test/verificar_nucleo.js (deben dar identico, hasta el centavo y
   la redaccion). Por eso se replican aca dos detalles de Python:
     - round() de Python es "banker's rounding" (mitad al par) -> pyRound;
     - f"{n:,}" agrupa miles con coma -> fmtMiles.

   Todo esto corre offline. Las partes que necesitan internet (Keepa, keywords
   de Amazon, asistente Claude) NO estan aca: usan el internet del celular via
   el puente nativo (ver js/app.js + MainActivity). */

const MV = (function () {
  // --- Config (mismos defaults que config.py) ---
  const CFG = {
    REFERRAL_PCT: 15, ACOS_PCT: 10, TARGET_MARGIN: 25, FBA_FEE_DEFAULT: 3.65,
    UMBRAL_VERDE: 25, UMBRAL_AMARILLO: 12,
  };

  // round() de Python: mitad al par (banker's rounding), no mitad-arriba como
  // Math.round. Sin esto, las unidades vendidas y los sueldos divergen del original.
  function pyRound(x, nd) {
    if (nd === undefined) nd = 0;
    const m = Math.pow(10, nd);
    const y = x * m;
    const f = Math.floor(y);
    const diff = y - f;
    let r;
    if (diff > 0.5) r = f + 1;
    else if (diff < 0.5) r = f;
    else r = f % 2 === 0 ? f : f + 1; // exactamente .5 -> al par
    return r / m;
  }
  // a // b de Python para floats: NO es Math.floor(a/b). CPython lo calcula via
  // fmod, y por error de punto flotante puede dar 1 menos (ej: 1036.46 // 3.574
  // = 289, aunque 1036.46/3.574 == 290.0). Replicarlo exacto es lo que hace que
  // las reposiciones de stock coincidan con el original.
  function pyFloorDiv(a, b) {
    let mod = a % b; // el % de JS equivale a fmod de C
    let div = (a - mod) / b;
    if (mod) {
      if ((b < 0) !== (mod < 0)) { mod += b; div -= 1.0; }
    }
    let floordiv = 0.0;
    if (div) {
      floordiv = Math.floor(div);
      if (div - floordiv > 0.5) floordiv += 1.0;
    }
    return floordiv;
  }
  const r2 = (x) => pyRound(x, 2);
  const r1 = (x) => pyRound(x, 1);
  const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, v));
  // f"{n:,}" / f"{n:,.0f}" de Python: agrupa miles con coma.
  const fmtMiles = (n) =>
    Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  // ============================ PRICING ============================
  function landedCost(costo, flete, arancelPct, prep) {
    return costo + flete + ((costo + flete) * arancelPct) / 100 + prep;
  }
  function semaforo(margenPct) {
    if (margenPct >= CFG.UMBRAL_VERDE) return "verde";
    if (margenPct >= CFG.UMBRAL_AMARILLO) return "amarillo";
    return "rojo";
  }
  function metricas(precio, landed, fbaFee, referralPct, acosPct) {
    const referral = (precio * referralPct) / 100;
    const ads = (precio * acosPct) / 100;
    const neto = precio - referral - fbaFee - ads - landed;
    const margen = precio > 0 ? (neto / precio) * 100 : 0;
    const roi = landed > 0 ? (neto / landed) * 100 : 0;
    return {
      precio: r2(precio), referral: r2(referral), fba_fee: r2(fbaFee),
      ads: r2(ads), landed: r2(landed), neto: r2(neto),
      margen_pct: r1(margen), roi_pct: r1(roi),
    };
  }
  function precioObjetivo(landed, fbaFee, margenObj, referralPct, acosPct) {
    const denom = 1 - referralPct / 100 - acosPct / 100 - margenObj / 100;
    return denom <= 0 ? null : (fbaFee + landed) / denom;
  }
  function breakEven(landed, fbaFee, referralPct, acosPct) {
    const denom = 1 - referralPct / 100 - acosPct / 100;
    return denom <= 0 ? null : (fbaFee + landed) / denom;
  }
  function evaluarPrecio(prod, fbaFee, precioCompetencia, margenObj) {
    fbaFee = fbaFee == null ? CFG.FBA_FEE_DEFAULT : fbaFee;
    margenObj = margenObj == null ? CFG.TARGET_MARGIN : margenObj;
    const ref = CFG.REFERRAL_PCT, acos = CFG.ACOS_PCT;
    const landed = landedCost(prod.costo || 0, prod.flete || 0, prod.arancel_pct || 0, prod.prep || 0);
    const pObj = precioObjetivo(landed, fbaFee, margenObj, ref, acos);
    const be = breakEven(landed, fbaFee, ref, acos);
    let estrategia = "objetivo";
    let precio = pObj ? pObj : be || landed * 2;
    if (precioCompetencia && precioCompetencia > 0) {
      const pComp = precioCompetencia * 0.95;
      const mComp = metricas(pComp, landed, fbaFee, ref, acos);
      if (mComp.margen_pct >= CFG.UMBRAL_AMARILLO) {
        precio = pComp;
        estrategia = "competitivo (-5% vs lider)";
      }
    }
    const m = metricas(precio, landed, fbaFee, ref, acos);
    m.semaforo = semaforo(m.margen_pct);
    m.estrategia = estrategia;
    m.precio_objetivo = pObj ? r2(pObj) : null;
    m.break_even = be ? r2(be) : null;
    m.precio_competencia = precioCompetencia || null;
    m.margen_objetivo = margenObj;
    return m;
  }

  // ============================ CAJA (capital_planner) ============================
  function proyeccionRealista(budget, landed, precio, netUnit, opt) {
    opt = opt || {};
    const sellThrough = opt.sell_through != null ? opt.sell_through : 0.5;
    const dev = opt.devoluciones != null ? opt.devoluciones : 0.05;
    const leadTime = opt.lead_time_meses != null ? opt.lead_time_meses : 2;
    const payout = opt.payout_delay_meses != null ? opt.payout_delay_meses : 1;
    const techo = opt.techo_demanda != null ? opt.techo_demanda : 290;
    const meses = opt.meses != null ? opt.meses : 12;
    const feesUnit = Math.max(0, precio - netUnit - landed);
    const unidadesCompra = landed > 0 ? pyFloorDiv(budget, landed) : 0;
    const inversion = unidadesCompra * landed;
    let caja = budget - inversion;
    let transito = [[leadTime, unidadesCompra]];
    let disponible = 0;
    const cobros = {};
    const filas = [];
    let cajaMinima = caja;
    for (let mes = 1; mes <= meses; mes++) {
      let llegadas = 0;
      transito.forEach(([m, u]) => { if (m === mes) llegadas += u; });
      disponible += llegadas;
      transito = transito.filter(([m]) => m !== mes);
      const vendidas = Math.min(pyRound(disponible * sellThrough), disponible, techo);
      disponible -= vendidas;
      const netas = vendidas * (1 - dev);
      const ingreso = netas * precio;
      const mc = mes + payout;
      if (!cobros[mc]) cobros[mc] = { ingreso: 0, unidades: 0 };
      cobros[mc].ingreso += ingreso;
      cobros[mc].unidades += vendidas;
      const cob = cobros[mes] || { ingreso: 0, unidades: 0 };
      delete cobros[mes];
      caja += cob.ingreso;
      const gastoRepos = Math.min(caja, cob.unidades * landed);
      const unidadesRepuestas = landed > 0 ? pyFloorDiv(gastoRepos, landed) : 0;
      caja -= unidadesRepuestas * landed;
      if (unidadesRepuestas > 0) transito.push([mes + leadTime, unidadesRepuestas]);
      const fees = cob.unidades * (1 - dev) * feesUnit;
      caja -= fees;
      const sueldo = Math.max(0, cob.ingreso - unidadesRepuestas * landed - fees);
      caja -= sueldo;
      cajaMinima = Math.min(cajaMinima, caja);
      let atado = disponible;
      transito.forEach(([, u]) => (atado += u));
      filas.push({
        mes, llegan: llegadas, vendidas, ingreso: r2(ingreso), cobrado: r2(cob.ingreso),
        repuso_unid: unidadesRepuestas, sueldo: r2(sueldo), caja: r2(caja),
        capital_atado: r2(atado * landed), disponible,
      });
    }
    const primer = (filas.find((f) => f.cobrado > 0) || {}).mes || null;
    const estables = filas.filter((f) => f.sueldo > 0).map((f) => f.sueldo).slice(-4);
    const meseta = estables.length ? r2(estables.reduce((a, b) => a + b, 0) / estables.length) : 0;
    return {
      filas,
      resumen: {
        unidades_compra: unidadesCompra, inversion: r2(inversion),
        caja_minima: r2(cajaMinima), sueldo_meseta: meseta,
        sueldo_ultimo: filas.length ? filas[filas.length - 1].sueldo : 0,
        mes_primer_cobro: primer,
        caja_final: filas.length ? filas[filas.length - 1].caja : 0,
        techo_demanda: techo,
        alerta: cajaMinima < 0 ? "CAJA NEGATIVA: te quedas sin efectivo" : "ok",
      },
    };
  }

  // ============================ GANANCIAS ============================
  function simularGanancias(o) {
    const fbaFee = o.fba_fee == null ? CFG.FBA_FEE_DEFAULT : o.fba_fee;
    const costo = o.costo || 0, flete = o.flete || 0;
    const arancelPct = o.arancel_pct || 0, prep = o.prep || 0;
    const dev = o.devoluciones != null ? o.devoluciones : 0.05;
    const techo = o.techo_demanda != null ? o.techo_demanda : 290;
    const meses = o.meses != null ? o.meses : 12;
    const landed = landedCost(costo, flete, arancelPct, prep);
    if (landed <= 0) return { ok: false, mensaje: "Cargar costos: el landed cost dio 0." };
    const m = evaluarPrecio(
      { costo: costo, flete: flete, arancel_pct: arancelPct, prep: prep },
      fbaFee, o.precio_competencia);
    const precioV = o.precio && o.precio > 0 ? o.precio : m.precio;
    const referralU = (precioV * CFG.REFERRAL_PCT) / 100;
    const adsU = (precioV * CFG.ACOS_PCT) / 100;
    const netoU = precioV - referralU - fbaFee - adsU - landed;
    let unidades, inversionUsada, entrada;
    if (o.unidades && o.unidades > 0) {
      unidades = Math.trunc(o.unidades);
      inversionUsada = r2(unidades * landed);
      entrada = `${unidades} unidades`;
    } else if (o.inversion && o.inversion > 0) {
      unidades = pyFloorDiv(o.inversion, landed);
      inversionUsada = r2(unidades * landed);
      entrada = `USD ${fmtMiles(o.inversion)} de inversion`;
    } else {
      return { ok: false, mensaje: "Indica cuanta plata invertis (USD) o cuantas unidades." };
    }
    if (unidades <= 0) {
      return { ok: false, mensaje: `Con USD ${fmtMiles(o.inversion)} no llegas a 1 unidad (landed USD ${landed.toFixed(2)}).` };
    }
    const vendibles = unidades * (1 - dev);
    const ingresoBruto = vendibles * precioV;
    const costos = {
      producto: r2(unidades * costo),
      flete: r2(unidades * flete),
      arancel: r2((unidades * (costo + flete) * arancelPct) / 100),
      prep: r2(unidades * prep),
      comision_amazon_referral: r2(vendibles * referralU),
      fba_fee: r2(vendibles * fbaFee),
      publicidad_acos: r2(vendibles * adsU),
    };
    const totalCostos = r2(Object.values(costos).reduce((a, b) => a + b, 0));
    const gananciaNeta = r2(ingresoBruto - totalCostos);
    const mesesVenta = techo ? Math.ceil(unidades / techo) : null;
    const lote = {
      unidades_compradas: unidades,
      inversion_usada: inversionUsada,
      unidades_vendidas_netas: r1(vendibles),
      devoluciones_pct: dev * 100,
      ingreso_bruto: r2(ingresoBruto),
      costos, total_costos: totalCostos,
      ganancia_neta: gananciaNeta,
      ganancia_por_unidad: r2(netoU),
      margen_pct: ingresoBruto ? r1((gananciaNeta / ingresoBruto) * 100) : 0,
      roi_inversion_pct: inversionUsada ? r1((gananciaNeta / inversionUsada) * 100) : 0,
      meses_para_venderlo: mesesVenta,
      ganancia_por_mes_promedio: mesesVenta ? r2(gananciaNeta / mesesVenta) : null,
    };
    const proy = proyeccionRealista(inversionUsada, landed, precioV, netoU,
      { devoluciones: dev, techo_demanda: Math.trunc(techo), meses: meses });
    const rp = proy.resumen;
    const unitSem = (netoU / precioV) * 100 >= CFG.UMBRAL_VERDE ? "verde"
      : (netoU / precioV) * 100 >= CFG.UMBRAL_AMARILLO ? "amarillo" : "rojo";
    return {
      ok: true, entrada,
      unit_economics: {
        landed: r2(landed), precio_venta: r2(precioV),
        precio_es_sugerido: !(o.precio && o.precio > 0),
        referral_unidad: r2(referralU), fba_fee: r2(fbaFee),
        publicidad_unidad: r2(adsU), neto_unidad: r2(netoU),
        semaforo: !(o.precio && o.precio > 0) ? m.semaforo : unitSem,
      },
      lote,
      reciclado: {
        sueldo_meseta_mensual: rp.sueldo_meseta,
        ganancia_12m_estimada: r2(proy.filas.reduce((a, f) => a + f.sueldo, 0)),
        caja_minima: rp.caja_minima,
        mes_primer_cobro: rp.mes_primer_cobro,
        alerta: rp.alerta,
        filas: proy.filas,
      },
      caveat: "Proyeccion, no promesa: asume que vendes al precio indicado y "
        + "al ritmo del techo de demanda; el resultado real depende del "
        + "ranking, el PPC y la calidad del producto. Si la ganancia por "
        + "unidad es negativa, NO compres: estarias pagando por vender.",
    };
  }

  // ============================ EXITO ============================
  const PESOS = { demanda: 0.30, entrada: 0.25, calidad_gap: 0.20, precio: 0.15, margen: 0.10 };
  function evaluarExito(keyword, competencia, interesKw, precioObjetivo, margenPct) {
    const c = competencia || {};
    const factores = {}, faltantes = [];
    let demanda, detD;
    if (c.ventas_estim_total) {
      demanda = clamp(c.ventas_estim_total / 3000);
      detD = `~${fmtMiles(c.ventas_estim_total)} ventas/mes estimadas entre los lideres`;
    } else if (interesKw != null) {
      demanda = clamp(interesKw / 100) * 0.8;
      detD = `proxy de interes del motor propio (${interesKw}/100), sin ventas`;
      faltantes.push("ventas estimadas (conecta Keepa)");
    } else { demanda = 0.4; detD = "sin dato de demanda: se asume neutral-bajo"; faltantes.push("demanda (motor propio o Keepa)"); }
    factores.demanda = { valor: r2(demanda), detalle: detD };

    let entrada, detE;
    if (c.n_competidores) {
      const med = c.resenas_mediana || 0;
      entrada = clamp(1 - med / 1500);
      detE = `mediana de ${fmtMiles(med)} reseñas entre ${c.n_competidores} competidores`
        + (med > 1000 ? " — nicho muy defendido" : med < 300 ? " — entrada viable" : "");
    } else { entrada = 0.5; detE = "sin datos de competidores: se asume neutral"; faltantes.push("competidores (Productos estrella)"); }
    factores.entrada = { valor: r2(entrada), detalle: detE };

    let gap, detC;
    if (c.rating_promedio) {
      const rp = c.rating_promedio;
      gap = clamp((4.6 - rp) / 1.2);
      detC = `rating promedio ${rp}/5 de la competencia`
        + (rp < 4.3 ? " — hay espacio para un producto mejor" : " — competencia muy bien calificada, diferenciarse cuesta");
    } else { gap = 0.5; detC = "sin ratings: se asume neutral"; faltantes.push("calidad de competidores"); }
    factores.calidad_gap = { valor: r2(gap), detalle: detC };

    const pp = precioObjetivo || c.precio_mediana;
    let fp, detP;
    if (pp) {
      if (pp >= 15 && pp <= 45) { fp = 1.0; detP = `USD ${pp.toFixed(2)} en el sweet spot FBA (15-45)`; }
      else if ((pp >= 10 && pp < 15) || (pp > 45 && pp <= 70)) { fp = 0.6; detP = `USD ${pp.toFixed(2)} en el borde del sweet spot`; }
      else { fp = 0.25; detP = `USD ${pp.toFixed(2)} fuera del sweet spot: margen absoluto chico o territorio de marcas establecidas`; }
    } else { fp = 0.5; detP = "sin precio de referencia"; faltantes.push("precio objetivo"); }
    factores.precio = { valor: r2(fp), detalle: detP };

    let fm, detM;
    if (margenPct != null) { fm = clamp(margenPct / 30); detM = `margen calculado ${margenPct.toFixed(1)}% (verde >= 25%)`; }
    else { fm = 0.5; detM = "sin pricing cargado: se asume neutral"; faltantes.push("margen (pestana Pricing)"); }
    factores.margen = { valor: r2(fm), detalle: detM };

    const prob = pyRound(Object.keys(PESOS).reduce((a, k) => a + PESOS[k] * factores[k].valor, 0) * 100);
    let veredicto, comentario;
    if (prob >= 65) { veredicto = "VERDE"; comentario = "Candidato fuerte: avanzar a muestra y orden de prueba."; }
    else if (prob >= 45) { veredicto = "AMARILLO"; comentario = "Marginal: solo avanzar con una diferenciacion clara (mejor producto, bundle, nicho mas fino)."; }
    else { veredicto = "ROJO"; comentario = "Desfavorable: no invertir capital aca."; }

    const recomendaciones = [];
    if (factores.entrada.valor < 0.4) recomendaciones.push("Nicho defendido por reseñas: apunta a un sub-nicho long-tail (del motor propio) en vez del head keyword.");
    if (factores.calidad_gap.valor > 0.6) recomendaciones.push("La competencia tiene ratings flojos: lee sus reseñas de 1-3 estrellas (link en Productos estrella) y arregla ESO en tu producto; pegalas al Asistente IA para el resumen.");
    if (factores.demanda.valor < 0.35) recomendaciones.push("Demanda debil o sin medir: valida con Keepa antes de gastar en muestras.");
    if (factores.margen.valor < 0.5 && margenPct != null) recomendaciones.push("El margen no llega al verde: renegocia costo/flete o sube el precio objetivo antes de avanzar.");
    if (!recomendaciones.length) recomendaciones.push("Pedi muestras a 3 proveedores verificados y valida con la orden de prueba antes de escalar.");

    return {
      ok: true, keyword, probabilidad: prob, veredicto, comentario, factores, pesos: PESOS,
      datos_faltantes: faltantes, recomendaciones,
      caveat: "Estimacion para ordenar candidatos, NO una garantia: el exito "
        + "real depende del proveedor, el listing y la ejecucion. Ninguna "
        + "probabilidad reemplaza la orden de prueba (USD 1.000-2.000).",
    };
  }

  // ============================ DEDICACION ============================
  const TAREAS_LANZ = [
    ["Investigar nicho y keywords (motor propio / Cerebro)", 3, 5, "una vez"],
    ["Evaluar y contactar proveedores + RFQ + negociar + pedir muestra", 4, 6, "una vez"],
    ["Armar listing + coordinar/organizar las 7 fotos", 3, 4, "una vez"],
    ["Configurar Seller Central + primer envio a Amazon (FBA)", 2, 3, "una vez"],
    ["Monitorear PPC y precio la primera semana tras lanzar", 2, 3, "por semana, primer mes"],
  ];
  const TAREAS_OP = [
    ["Revisar PPC, precio y stock", 0.5, 1.0],
    ["Atender casos que el bot deriva (no son FAQ)", 0.5, 1.0],
    ["Seguimiento de reposicion con el proveedor", 0.25, 0.5],
    ["Leer KPIs y alertas (ya automatizadas)", 0.25, 0.25],
  ];
  const AUTOMATIZADO = [
    "Clasificar y responder consultas FAQ (envio, garantia, estado de pedido...)",
    "Registrar ventas, calcular KPIs y margen global",
    "Enviar alertas por email de cada venta/consulta",
    "Calcular pricing, proyeccion de caja y semaforo de margen",
    "Investigar keywords con el motor propio (corre solo, vos revisas el resultado)",
  ];
  function estimarDedicacion(nOp, lanzando, semanasDesdeLanzamiento) {
    if (nOp == null) nOp = 1;
    const semanas = semanasDesdeLanzamiento || 0;
    const filas = []; let tMin = 0, tMax = 0;
    if (lanzando) {
      TAREAS_LANZ.forEach(([t, mn, mx, cuando]) => {
        let a, b;
        if (cuando === "una vez") { a = mn / 3; b = mx / 3; }
        else if (semanas <= 4) { a = mn; b = mx; }
        else return;
        filas.push({ tarea: t, horas_min: r1(a), horas_max: r1(b), frecuencia: cuando, fase: "lanzamiento" });
        tMin += a; tMax += b;
      });
    }
    TAREAS_OP.forEach(([t, mn, mx]) => {
      const a = mn * nOp, b = mx * nOp;
      if (a === 0 && b === 0) return;
      filas.push({ tarea: `${t} (x${nOp} producto/s)`, horas_min: r1(a), horas_max: r1(b), frecuencia: "por semana", fase: "operacion" });
      tMin += a; tMax += b;
    });
    return {
      n_productos_operacion: nOp, lanzando_producto: lanzando,
      horas_semana_min: r1(tMin), horas_semana_max: r1(tMax), desglose: filas,
      automatizado_por_el_sistema: AUTOMATIZADO,
      caveat: "Rangos de referencia. Un producto con problemas de calidad, "
        + "reclamos o guerra de precios exige mas horas que estas; un "
        + "producto sano con proveedor solido puede exigir menos.",
    };
  }

  return {
    CFG, landedCost, evaluarPrecio, proyeccionRealista, simularGanancias,
    evaluarExito, estimarDedicacion,
  };
})();

if (typeof module !== "undefined" && module.exports) module.exports = MV;
