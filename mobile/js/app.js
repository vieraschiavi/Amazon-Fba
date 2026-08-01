// app.js — MV FBA IA (app Android NATIVA, sin depender de la PC).
//
// TODO el negocio corre EN EL TELEFONO:
//   - la matematica (pricing, ganancias, exito, caja, dedicacion) la hace
//     js/nucleo.js, port fiel del motor Python (validado campo a campo);
//   - los datos (productos, ventas, claves) viven en localStorage del telefono.
//
// Lo unico que necesita internet (keywords reales de Amazon, asistente Claude)
// usa el internet del CELULAR: si esta el puente nativo (MainActivity) lo usa
// para evitar el bloqueo CORS del origen file://; si no, intenta fetch directo.
// Si no hay internet, todo el nucleo sigue funcionando y el asistente responde
// localmente. La app NUNCA queda vacia ni "esperando a la PC".

const $ = (sel, root = document) => root.querySelector(sel);
const $all = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ============================ ESTADO (localStorage) ============================
const LS_ESTADO = "mvfba_estado_v1";
const LS_VISTO = "mvfba_bienvenida_v2";

function estadoDefault() {
  return { productos: [], ventas: [],
    claves: { keepa: "", claude: "", openai: "", gemini: "", ia_prov: "claude" } };
}
function cargarEstado() {
  try {
    const raw = localStorage.getItem(LS_ESTADO);
    if (!raw) return estadoDefault();
    const e = JSON.parse(raw);
    return { ...estadoDefault(), ...e, claves: { ...estadoDefault().claves, ...(e.claves || {}) } };
  } catch (_) { return estadoDefault(); }
}
function guardarEstado(e) { localStorage.setItem(LS_ESTADO, JSON.stringify(e)); }
let estado = cargarEstado();

function nuevoId() {
  // sin depender de crypto: contador + tiempo, unico para el telefono
  return "p" + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36);
}

// ============================ FORMATO ============================
function fmtMoney(x) {
  const n = Number(x) || 0;
  return "$" + n.toLocaleString("es-AR", { maximumFractionDigits: 0 });
}
function fmtMoney2(x) {
  const n = Number(x) || 0;
  return "$" + n.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtPct(x, dec = 1) { return (Number(x) || 0).toFixed(dec) + "%"; }
function fmtNum(x) { return (Number(x) || 0).toLocaleString("es-AR"); }
function tonoSemaforo(s) { return { verde: "verde", amarillo: "amarillo", rojo: "rojo" }[s] || "navy"; }
function tonoMargen(m) { return m >= 25 ? "good" : m >= 12 ? "warn" : "bad"; }

function mostrarToast(texto) {
  let t = $("#toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.className = "toast"; document.body.appendChild(t); }
  t.textContent = texto;
  t.classList.add("mostrar");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("mostrar"), 3000);
}

// ============================ PUENTE DE RED (celular) ============================
// El puente nativo evita el CORS del origen file://. Sin el (ej. en el navegador
// durante desarrollo) se cae a fetch directo.
window.__puentePend = {};
let __reqSeq = 0;
window.__puenteResolver = function (id, resp) {
  const p = window.__puentePend[id];
  if (!p) return;
  delete window.__puentePend[id];
  try { p(typeof resp === "string" ? JSON.parse(resp) : resp); } catch (e) { p({ error: String(e) }); }
};
function hayPuente() {
  return typeof PuenteNativo !== "undefined" && PuenteNativo && typeof PuenteNativo.httpRequest === "function";
}
function httpPorPuente(metodo, url, cuerpo, cabeceras) {
  return new Promise((resolve, reject) => {
    const id = "r" + (++__reqSeq);
    window.__puentePend[id] = (r) => {
      if (!r || r.error) return reject(new Error((r && r.error) || "sin respuesta"));
      if (r.status >= 200 && r.status < 300) return resolve(r.body);
      reject(new Error("HTTP " + r.status));
    };
    PuenteNativo.httpRequest(id, metodo, url, cuerpo || "", JSON.stringify(cabeceras || {}));
  });
}
async function pedirHTTP(metodo, url, cuerpo, cabeceras) {
  if (hayPuente()) return httpPorPuente(metodo, url, cuerpo, cabeceras);
  const opt = { method: metodo, headers: cabeceras || {} };
  if (cuerpo) opt.body = cuerpo;
  const r = await fetch(url, opt);
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.text();
}
function estadoConexion() {
  const dot = $("#btn-estado");
  const online = hayPuente() || (typeof navigator !== "undefined" && navigator.onLine);
  dot.classList.toggle("ok", true); // el nucleo SIEMPRE esta operativo
  dot.title = online ? "Motor local activo · internet disponible" : "Motor local activo · sin internet (funciones online limitadas)";
  return online;
}

// ============================ NAVEGACION ============================
function irAVista(nombre) {
  $all(".view").forEach((v) => v.classList.toggle("activa", v.id === "view-" + nombre));
  $all(".nav-btn").forEach((b) => b.classList.toggle("activa", b.dataset.vista === nombre));
  if (nombre === "inicio") cargarInicio();
  if (nombre === "portafolio") cargarPortafolio();
  if (nombre === "asistente") { pintarChat(); void refrescarSaldoChat(); }   // bienvenida + saldo al entrar
  window.scrollTo(0, 0);
}
$all(".nav-btn").forEach((b) => b.addEventListener("click", () => irAVista(b.dataset.vista)));
$all("[data-ir]").forEach((b) => b.addEventListener("click", () => irAVista(b.dataset.ir)));
$("#btn-estado").addEventListener("click", () => irAVista("config"));

// ============================ CALCULOS DE PORTAFOLIO ============================
// Cada producto se evalua con el motor local; las metricas se derivan al vuelo.
function analizarProducto(p) {
  const prod = { costo: +p.costo || 0, flete: +p.flete || 0, arancel_pct: +p.arancel_pct || 0, prep: +p.prep || 0 };
  const pricing = MV.evaluarPrecio(prod, null, +p.precio_competencia || null);
  const landed = MV.landedCost(prod.costo, prod.flete, prod.arancel_pct, prod.prep);
  const precio = +p.precio > 0 ? +p.precio : pricing.precio;
  const referral = precio * MV.CFG.REFERRAL_PCT / 100;
  const ads = precio * MV.CFG.ACOS_PCT / 100;
  const netoU = precio - referral - MV.CFG.FBA_FEE_DEFAULT - ads - landed;
  const margen = precio > 0 ? netoU / precio * 100 : 0;
  const roi = landed > 0 ? netoU / landed * 100 : 0;
  const techo = +p.techo_demanda || 290;
  const sem = margen >= MV.CFG.UMBRAL_VERDE ? "verde" : margen >= MV.CFG.UMBRAL_AMARILLO ? "amarillo" : "rojo";
  // ventas reales registradas de este producto
  const ventas = estado.ventas.filter((v) => v.producto_id === p.id);
  const unidadesReales = ventas.reduce((a, v) => a + (+v.unidades || 0), 0);
  const ingresoReal = ventas.reduce((a, v) => a + (+v.ingreso || 0), 0);
  const netoReal = unidadesReales * netoU;
  return {
    ...p, landed: MV.evaluarPrecio(prod, null, +p.precio_competencia || null).landed,
    precio, neto_unidad: netoU, margen, roi, semaforo: sem, techo,
    meseta_mensual: netoU * techo,                 // neto mensual a demanda plena
    capital_pipeline: techo * 4 * landed,          // ~4 meses de stock
    unidades_reales: unidadesReales, ingreso_real: ingresoReal, neto_real: netoReal,
  };
}
function resumenPortafolio() {
  const prods = estado.productos.map(analizarProducto);
  const n = prods.length;
  const sem = { verde: 0, amarillo: 0, rojo: 0 };
  prods.forEach((p) => { sem[p.semaforo] = (sem[p.semaforo] || 0) + 1; });
  const meseta = prods.reduce((a, p) => a + p.meseta_mensual, 0);
  const pipeline = prods.reduce((a, p) => a + p.capital_pipeline, 0);
  const margenProm = n ? prods.reduce((a, p) => a + p.margen, 0) / n : 0;
  const ingresoReal = prods.reduce((a, p) => a + p.ingreso_real, 0);
  const netoReal = prods.reduce((a, p) => a + p.neto_real, 0);
  return { n, prods, semaforos: sem, sueldo_meseta_proyectado: meseta,
    capital_pipeline_total: pipeline, margen_promedio_pct: margenProm,
    ingreso_real: ingresoReal, neto_real: netoReal };
}

// ============================ INFO (que es / valor objetivo / desvio) ============================
// Fuente unica de verdad: mismos umbrales que config.py (UMBRAL_VERDE=25, UMBRAL_AMARILLO=12)
// y agents/glosario.py, para no contradecir al panel de PC.
const INFO_METRICAS = {
  margen: {
    que: "Lo que te queda del precio de venta despues de TODOS los costos (producto, flete, arancel, comision Amazon, FBA fee, publicidad).",
    objetivo: "Bien (verde): 25% o mas.",
    desvio: "Alerta: 12–25% es ajustado (amarillo); menos de 12% no conviene (rojo).",
  },
  roi: {
    que: "Return on Investment: tu ganancia neta dividida por lo que invertiste (landed cost). Mide cuanto rinde tu plata, no cuanto factura el producto.",
    objetivo: "Bien: 30% o mas por ciclo de venta.",
    desvio: "Alerta: menos de 15% — tu plata rinde poco frente al riesgo de inmovilizarla en stock.",
  },
  ganancia_neta: {
    que: "Lo que te queda en el bolsillo despues de TODOS los costos: producto, flete, arancel, prep, comision Amazon, FBA fee y publicidad.",
    objetivo: "Bien: positiva y con margen de 25% o mas sobre el ingreso.",
    desvio: "Alerta: cercana a cero o negativa — estas perdiendo plata en cada lote.",
  },
  sueldo_meseta: {
    que: "El ingreso mensual SOSTENIDO cuando reciclas capital: el landed repone stock y el neto se retira.",
    objetivo: "Se estabiliza en ~techo de demanda x neto por unidad — es tu 'sueldo' real, no un pico.",
    desvio: "Alerta: sin techo de demanda el numero 'explota' y miente — desconfia de sueldos que crecen sin limite.",
  },
  capital_pipeline: {
    que: "La plata inmovilizada en stock: en produccion, en transito y ya en los depositos de Amazon.",
    objetivo: "Bien: cubre ~4 meses de reposicion al techo de demanda, sin mas.",
    desvio: "Alerta: si supera largamente eso, tenes mas plata parada de la que el nicho puede vender.",
  },
  exito: {
    que: "Probabilidad de exito del nicho: formula auditable con demanda (30%), barrera de entrada (25%), hueco de calidad (20%), precio (15%) y margen (10%).",
    objetivo: "Bien (verde): 70/100 o mas.",
    desvio: "Alerta: menos de 40/100 — demanda floja, mucha competencia o poco margen.",
  },
  landed: {
    que: "Costo desembarcado: lo que te cuesta poner UNA unidad lista para vender = producto + flete + arancel + prep.",
    objetivo: "Cuanto mas bajo frente al precio de venta, mejor: es la base del margen.",
    desvio: "Alerta: si supera ~50–60% del precio de venta, casi no queda margen para Amazon + publicidad.",
  },
};
function _iconoInfo(clave) {
  return `<button type="button" class="info-ic" data-info="${clave}" aria-label="Que es esta metrica">i</button>`;
}
function _mostrarInfo(clave, x, y) {
  const d = INFO_METRICAS[clave];
  if (!d) return;
  let pop = document.getElementById("info-pop-global");
  if (!pop) {
    pop = document.createElement("div");
    pop.id = "info-pop-global";
    pop.className = "info-pop oculto";
    document.body.appendChild(pop);
  }
  pop.innerHTML = `
    <div class="info-fila"><b>Que es:</b> ${d.que}</div>
    <div class="info-fila"><b>Valor objetivo:</b> ${d.objetivo}</div>
    <div class="info-fila"><b>Desvio / alerta:</b> ${d.desvio}</div>
    <button type="button" class="info-cerrar">Entendido</button>`;
  pop.classList.remove("oculto");
  const vw = window.innerWidth, vh = window.innerHeight;
  const w = Math.min(300, vw - 32);
  const left = Math.min(Math.max(8, x - w / 2), vw - w - 8);
  const top = Math.min(y + 8, vh - 210);
  pop.style.left = left + "px"; pop.style.top = top + "px";
  pop.querySelector(".info-cerrar").addEventListener("click", () => pop.classList.add("oculto"));
}
document.addEventListener("click", (ev) => {
  const btn = ev.target.closest(".info-ic");
  if (btn) {
    const r = btn.getBoundingClientRect();
    _mostrarInfo(btn.dataset.info, r.left + r.width / 2, r.bottom);
    return;
  }
  const pop = document.getElementById("info-pop-global");
  if (pop && !pop.classList.contains("oculto") && !ev.target.closest("#info-pop-global")) {
    pop.classList.add("oculto");
  }
});

// ============================ INICIO ============================
function kpiHtml(lab, val, sub, tone, hero, infoKey) {
  const cls = ["kpi"];
  if (hero) cls.push("hero"); else if (tone) cls.push(tone);
  return `<div class="${cls.join(" ")}"><div class="lab">${lab}${infoKey ? _iconoInfo(infoKey) : ""}</div>
          <div class="val">${val}</div><div class="sub">${sub || ""}</div></div>`;
}
function cargarInicio() {
  const cont = $("#inicio-kpis");
  const contPf = $("#inicio-portafolio");
  const r = resumenPortafolio();
  const facturacion = r.ingreso_real;
  const neto = r.neto_real;
  const margenGlobal = facturacion > 0 ? neto / facturacion * 100 : r.margen_promedio_pct;
  const unidades = r.prods.reduce((a, p) => a + p.unidades_reales, 0);
  const ordenes = estado.ventas.length;
  cont.innerHTML =
    kpiHtml("Facturacion", fmtMoney(facturacion), "ventas registradas", null, true) +
    kpiHtml("Neto", fmtMoney(neto), "despues de costos", neto > 0 ? "good" : null) +
    kpiHtml("Margen", fmtPct(margenGlobal), facturacion > 0 ? "real" : "proyectado del portafolio", tonoMargen(margenGlobal), false, "margen") +
    kpiHtml("Sueldo meseta", fmtMoney(r.sueldo_meseta_proyectado), "proyectado/mes", null, false, "sueldo_meseta");

  if (r.n) {
    const s = r.semaforos;
    contPf.className = "";
    contPf.innerHTML = `
      <div class="grid-kpi">
        ${kpiHtml("Productos", r.n, `${s.verde || 0} verde · ${s.amarillo || 0} amarillo · ${s.rojo || 0} rojo`, null, true)}
        ${kpiHtml("Capital en pipeline", fmtMoney(r.capital_pipeline_total), "~4 meses de stock", null, false, "capital_pipeline")}
        ${kpiHtml("Margen promedio", fmtPct(r.margen_promedio_pct), "de todo el portafolio", tonoMargen(r.margen_promedio_pct), false, "margen")}
        ${kpiHtml("Ordenes", fmtNum(ordenes), fmtNum(unidades) + " unidades")}
      </div>`;
  } else {
    contPf.className = "card lista-vacia";
    contPf.innerHTML = `Todavia no cargaste productos.
      <br><button class="btn-primario" data-ir="portafolio" style="margin-top:10px">Cargar mi primer producto</button>`;
    $("[data-ir]", contPf).addEventListener("click", () => irAVista("portafolio"));
  }
  pintarNudgeDemo();
}

// ============================ PORTAFOLIO ============================
function cargarPortafolio() {
  const kpisEl = $("#portafolio-kpis");
  const listaEl = $("#portafolio-lista");
  const r = resumenPortafolio();
  if (!r.n) {
    kpisEl.innerHTML = "";
    listaEl.innerHTML = `<div class="card lista-vacia">Portafolio vacio. Agregá un producto con el boton de abajo.</div>`;
    return;
  }
  kpisEl.innerHTML =
    kpiHtml("Sueldo meseta", fmtMoney(r.sueldo_meseta_proyectado), "proyectado/mes", null, true, "sueldo_meseta") +
    kpiHtml("Margen promedio", fmtPct(r.margen_promedio_pct), "de todo el portafolio", tonoMargen(r.margen_promedio_pct), false, "margen");
  listaEl.innerHTML = r.prods.map((p) => `
    <div class="producto-card">
      <div class="fila-top">
        <div class="nombre">${escapar(p.nombre)}</div>
        <span class="badge ${tonoSemaforo(p.semaforo)}"><span class="dot"></span>${p.semaforo.toUpperCase()}</span>
      </div>
      <div class="metricas">
        <span>Precio <b>${fmtMoney2(p.precio)}</b></span>
        <span>Margen <b>${fmtPct(p.margen)}</b>${_iconoInfo("margen")}</span>
        <span>ROI <b>${fmtPct(p.roi)}</b>${_iconoInfo("roi")}</span>
        <span>Neto/u <b>${fmtMoney2(p.neto_unidad)}</b></span>
      </div>
      <div class="metricas">
        <span>Ventas reales <b>${fmtMoney(p.ingreso_real)}</b></span>
        <span>Unid. <b>${fmtNum(p.unidades_reales)}</b></span>
      </div>
      <div class="acciones-prod">
        <button class="mini" data-venta="${p.id}">+ Registrar venta</button>
        <button class="mini" data-editar="${p.id}">Editar</button>
        <button class="mini peligro" data-borrar="${p.id}">Borrar</button>
      </div>
    </div>`).join("");
  $all("[data-venta]", listaEl).forEach((b) => b.addEventListener("click", () => abrirVenta(b.dataset.venta)));
  $all("[data-editar]", listaEl).forEach((b) => b.addEventListener("click", () => abrirProducto(b.dataset.editar)));
  $all("[data-borrar]", listaEl).forEach((b) => b.addEventListener("click", () => borrarProducto(b.dataset.borrar)));
}

// escapar() vive en js/seguro.js (un solo lugar, un solo test de regresion:
// test/verificar_escapar.js). Se carga antes que este archivo en index.html.

// --- modal de alta/edicion de producto ---
function abrirProducto(id) {
  const p = id ? estado.productos.find((x) => x.id === id) : null;
  const d = p || { nombre: "", costo: 2.10, flete: 0.80, arancel_pct: 6, prep: 0.50, precio: 0, precio_competencia: 0, techo_demanda: 290 };
  const html = `
    <h2>${p ? "Editar producto" : "Nuevo producto"}</h2>
    <form id="form-producto" class="formulario">
      <label class="col-2">Nombre<input type="text" id="p_nombre" value="${escapar(d.nombre)}" placeholder="Ej: Set de utensilios de bambu" required></label>
      <div class="grid-form">
        <label>Costo fabrica (USD)<input type="number" id="p_costo" value="${d.costo}" min="0" step="0.01"></label>
        <label>Flete unitario (USD)<input type="number" id="p_flete" value="${d.flete}" min="0" step="0.01"></label>
        <label>Arancel (%)<input type="number" id="p_arancel" value="${d.arancel_pct}" min="0" step="0.1"></label>
        <label>Prep (USD)<input type="number" id="p_prep" value="${d.prep}" min="0" step="0.01"></label>
        <label>Precio venta (0=sugerido)<input type="number" id="p_precio" value="${d.precio}" min="0" step="0.01"></label>
        <label>Precio competencia (USD)<input type="number" id="p_comp" value="${d.precio_competencia}" min="0" step="0.01"></label>
        <label>Techo demanda (u/mes)<input type="number" id="p_techo" value="${d.techo_demanda}" min="10" step="10"></label>
      </div>
      <button type="submit" class="btn-primario">${p ? "Guardar cambios" : "Agregar al portafolio"}</button>
    </form>`;
  abrirModal(html);
  $("#form-producto").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const datos = {
      nombre: $("#p_nombre").value.trim() || "Producto sin nombre",
      costo: +$("#p_costo").value, flete: +$("#p_flete").value,
      arancel_pct: +$("#p_arancel").value, prep: +$("#p_prep").value,
      precio: +$("#p_precio").value, precio_competencia: +$("#p_comp").value,
      techo_demanda: +$("#p_techo").value,
    };
    if (p) { Object.assign(p, datos); mostrarToast("Producto actualizado"); }
    else { estado.productos.push({ id: nuevoId(), ...datos }); mostrarToast("Producto agregado"); }
    guardarEstado(estado);
    cerrarModal();
    cargarPortafolio();
  });
}
function borrarProducto(id) {
  const p = estado.productos.find((x) => x.id === id);
  if (!p) return;
  if (!confirm(`¿Borrar "${p.nombre}" y sus ventas registradas?`)) return;
  estado.productos = estado.productos.filter((x) => x.id !== id);
  estado.ventas = estado.ventas.filter((v) => v.producto_id !== id);
  guardarEstado(estado);
  cargarPortafolio();
  mostrarToast("Producto borrado");
}
function abrirVenta(id) {
  const p = estado.productos.find((x) => x.id === id);
  if (!p) return;
  const a = analizarProducto(p);
  const html = `
    <h2>Registrar venta</h2>
    <p class="sub-vista">${escapar(p.nombre)} — precio ${fmtMoney2(a.precio)}</p>
    <form id="form-venta" class="formulario">
      <div class="grid-form">
        <label>Unidades vendidas<input type="number" id="v_unidades" value="10" min="1" step="1"></label>
        <label>Ingreso total (USD, 0=auto)<input type="number" id="v_ingreso" value="0" min="0" step="0.01"></label>
      </div>
      <button type="submit" class="btn-primario">Guardar venta</button>
    </form>`;
  abrirModal(html);
  $("#form-venta").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const u = Math.max(1, Math.floor(+$("#v_unidades").value));
    let ing = +$("#v_ingreso").value;
    if (!ing || ing <= 0) ing = u * a.precio;
    estado.ventas.push({ id: nuevoId(), producto_id: id, unidades: u, ingreso: ing, fecha: new Date().toISOString().slice(0, 10) });
    guardarEstado(estado);
    cerrarModal();
    cargarPortafolio();
    mostrarToast(`Venta registrada: ${u} u · ${fmtMoney(ing)}`);
  });
}

$("#btn-add-producto").addEventListener("click", () => abrirProducto(null));

// --- modal generico ---
function abrirModal(html) {
  let m = $("#modal");
  if (!m) {
    m = document.createElement("div");
    m.id = "modal";
    m.className = "modal";
    m.innerHTML = `<div class="modal-card"><button class="modal-cerrar" aria-label="Cerrar">×</button><div class="modal-cuerpo"></div></div>`;
    document.body.appendChild(m);
    m.addEventListener("click", (e) => { if (e.target === m) cerrarModal(); });
    $(".modal-cerrar", m).addEventListener("click", cerrarModal);
  }
  $(".modal-cuerpo", m).innerHTML = html;
  m.classList.add("abierto");
}
function cerrarModal() { const m = $("#modal"); if (m) m.classList.remove("abierto"); }

// ============================ GANANCIAS ============================
$all('input[name="modo_g"]').forEach((r) =>
  r.addEventListener("change", () => {
    const esInv = $('input[name="modo_g"]:checked').value === "inversion";
    $("#g_inversion").disabled = !esInv;
    $("#g_unidades").disabled = esInv;
  })
);
$("#form-ganancias").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const esInv = $('input[name="modo_g"]:checked').value === "inversion";
  const r = MV.simularGanancias({
    inversion: esInv ? +$("#g_inversion").value : null,
    unidades: esInv ? null : +$("#g_unidades").value,
    costo: +$("#g_costo").value, flete: +$("#g_flete").value,
    arancel_pct: +$("#g_arancel").value, prep: +$("#g_prep").value,
    precio: +$("#g_precio").value || null, techo_demanda: +$("#g_techo").value,
  });
  const cont = $("#ganancias-resultado");
  if (!r.ok) { cont.innerHTML = `<div class="card lista-vacia">${escapar(r.mensaje)}</div>`; return; }
  const lo = r.lote, ue = r.unit_economics, re = r.reciclado;
  const etiquetas = {
    producto: "Producto (fabrica)", flete: "Flete", arancel: "Arancel", prep: "Prep",
    comision_amazon_referral: "Comision Amazon", fba_fee: "FBA fee", publicidad_acos: "Publicidad",
  };
  const filas = Object.entries(lo.costos)
    .map(([k, v]) => `<tr><td>${etiquetas[k] || k}</td><td>-${fmtMoney(v)}</td></tr>`).join("");
  const tonoG = lo.ganancia_neta > 0 ? "good" : "bad";
  cont.innerHTML = `
    <div class="grid-kpi">
      ${kpiHtml("Ganancia neta", fmtMoney(lo.ganancia_neta), r.entrada, tonoG, true, "ganancia_neta")}
      ${kpiHtml("ROI inversion", fmtPct(lo.roi_inversion_pct), fmtMoney(lo.inversion_usada), tonoG, false, "roi")}
      ${kpiHtml("Ganancia/unidad", fmtMoney2(lo.ganancia_por_unidad), "precio " + fmtMoney2(ue.precio_venta), tonoSemaforo(ue.semaforo), false, "margen")}
      ${kpiHtml("Sueldo en meseta", fmtMoney(re.sueldo_meseta_mensual), "reciclando capital 12m", null, false, "sueldo_meseta")}
    </div>
    <div class="card" style="margin-top:12px">
      <table class="tabla-costos">
        <tr class="ingreso"><td>Ingreso bruto</td><td>${fmtMoney(lo.ingreso_bruto)}</td></tr>
        ${filas}
        <tr class="total"><td>GANANCIA NETA</td><td>${fmtMoney(lo.ganancia_neta)}</td></tr>
      </table>
      <p class="ayuda-config" style="margin-top:8px">Unidades: <b>${fmtNum(lo.unidades_compradas)}</b> ·
        se venden ~<b>${fmtNum(lo.meses_para_venderlo)}</b> mes(es) al techo de demanda ·
        primer cobro Amazon: mes <b>${re.mes_primer_cobro || "—"}</b>.</p>
    </div>
    <p class="ayuda-config">${escapar(r.caveat)}</p>`;
  cont.scrollIntoView({ behavior: "smooth", block: "nearest" });
});

// ============================ MERCADO ============================
// EJEMPLO ilustrativo determinista por keyword (sin clave de datos). NO son
// datos reales de Amazon: se marcan como [EJEMPLO] en pantalla. Los datos
// reales llegan por la API de Keepa (ver mercadoRealKeepa).
function hash(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function competenciaDemo(keyword, min, max) {
  const h = hash(keyword.toLowerCase());
  const rnd = (n, a, b) => a + ((h >> (n * 3)) % 1000) / 1000 * (b - a);
  const precioMed = Math.min(max, Math.max(min, rnd(1, min, max)));
  const nComp = 6 + Math.floor(rnd(2, 0, 12));
  const resenasMed = Math.floor(rnd(3, 120, 1800));
  const rating = +(4.1 + rnd(4, 0, 0.7)).toFixed(1);
  const ventas = Math.floor(rnd(5, 400, 3200));
  const productos = Array.from({ length: 5 }, (_, i) => {
    const pr = +(precioMed * (0.8 + rnd(6 + i, 0, 0.5))).toFixed(2);
    return {
      titulo: `[EJEMPLO] ${keyword} — variante ${i + 1}`,
      precio: Math.min(max + 10, Math.max(min, pr)),
      ventas_estim: Math.floor(ventas * (0.5 + rnd(7 + i, 0, 1)) / 3),
      rating: +(4.0 + rnd(8 + i, 0, 0.8)).toFixed(1),
      resenas: Math.floor(resenasMed * (0.4 + rnd(9 + i, 0, 1.4))),
    };
  });
  return {
    ventas_estim_total: ventas, n_competidores: nComp, resenas_mediana: resenasMed,
    rating_promedio: rating, precio_mediana: +precioMed.toFixed(2), productos,
    real: false,
  };
}
// Agrega una lista de productos REALES (Keepa) al resumen que espera evaluarExito.
function resumenComp(productos) {
  const val = productos.filter((p) => p.precio);
  const precios = val.map((p) => p.precio).sort((a, b) => a - b);
  const resenas = val.map((p) => p.resenas || 0).sort((a, b) => a - b);
  const ratings = val.map((p) => p.rating).filter(Boolean);
  const mediana = (a) => a.length ? a[Math.floor(a.length / 2)] : 0;
  return {
    ventas_estim_total: val.reduce((s, p) => s + (p.ventas_estim || 0), 0),
    n_competidores: val.length,
    resenas_mediana: mediana(resenas),
    rating_promedio: ratings.length ? +(ratings.reduce((s, r) => s + r, 0) / ratings.length).toFixed(1) : null,
    precio_mediana: mediana(precios) || 0,
    productos: val, real: true,
  };
}
// Productos REALES por API de Keepa, vía el proxy serverless /api/mercado
// (la clave de Keepa no puede llamarse directo desde el navegador). Solo hay
// proxy en el demo web; en la app descargada (file://) este fetch falla y se
// cae al EJEMPLO — los datos reales viven en el programa de PC.
async function mercadoRealKeepa(keyword, min, max) {
  const keepa = (estado.claves.keepa || "").trim();
  if (!keepa) return null;
  const resp = await fetch("/api/mercado", {
    method: "POST", headers: { "Content-Type": "application/json", "x-mv-app": "mvfba-web-1" },
    body: JSON.stringify({ keyword, min, max, keepaKey: keepa }),
  });
  if (!resp.ok) return null;
  const data = await resp.json();
  if (!data || !data.ok || !(data.productos || []).length) return null;
  return resumenComp(data.productos);
}
async function keywordsAmazon(seed) {
  // keywords reales via autocomplete publico de Amazon (necesita internet).
  const url = "https://completion.amazon.com/api/2017/suggestions?limit=11&prefix="
    + encodeURIComponent(seed) + "&alias=aps&site-variant=desktop&mid=ATVPDKIKX0DER";
  const txt = await pedirHTTP("GET", url, null, { Accept: "application/json" });
  const data = JSON.parse(txt);
  return (data.suggestions || []).map((s) => s.value).filter(Boolean);
}
$("#form-mercado").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const keyword = $("#m_keyword").value.trim();
  const min = +$("#m_min").value, max = +$("#m_max").value;
  const cont = $("#mercado-resultado");
  if (!keyword) { cont.innerHTML = `<div class="card lista-vacia">Escribí un producto o keyword.</div>`; return; }
  cont.innerHTML = `<div class="card lista-vacia">Analizando el nicho…</div>`;

  // 1) Datos REALES por API (Keepa) si hay clave; 2) si no, EJEMPLO etiquetado.
  let comp = null;
  try { comp = await mercadoRealKeepa(keyword, min, max); } catch (e) { comp = null; }
  if (!comp) comp = competenciaDemo(keyword, min, max);

  const ev2 = MV.evaluarExito(keyword, comp, null, comp.precio_mediana, null);
  const tono = tonoSemaforo({ VERDE: "verde", AMARILLO: "amarillo", ROJO: "rojo" }[ev2.veredicto]);
  const fuenteBadge = comp.real
    ? `<span class="chip" style="background:#e7f6ea;color:#1f7a34">● Datos reales · Keepa (API)</span>`
    : `<span class="chip" style="background:#fdf2e2;color:#8a5407">● Ejemplo ilustrativo — no son datos reales</span>`;
  const notaFuente = comp.real
    ? `<p class="ayuda-config">Productos reales de Amazon traídos por la API de Keepa (precio, ventas estimadas por BSR y reseñas).</p>`
    : `<p class="ayuda-config">Estos productos son un <b>ejemplo</b> para mostrar el análisis. Para ver productos <b>reales</b> de Amazon, cargá tu clave de <b>Keepa</b> en Config (la búsqueda real es por API; ningún modelo de IA da estos datos).</p>`;

  let html = `
    <div style="margin-bottom:8px">${fuenteBadge}</div>
    <h2 class="titulo-seccion">Probabilidad de exito${_iconoInfo("exito")}</h2>
    <div class="card">
      <span class="badge ${tono}"><span class="dot"></span>${ev2.veredicto} — ${ev2.probabilidad}/100</span>
      <p style="font-size:13px;color:var(--slate);margin:8px 0">${escapar(ev2.comentario)}</p>
      <div class="factores">
        ${Object.entries(ev2.factores).map(([k, f]) => `
          <div class="factor"><span>${k.replace("_", " ")}</span>
            <div class="barra"><i style="width:${Math.round(f.valor * 100)}%"></i></div>
            <small>${escapar(f.detalle)}</small></div>`).join("")}
      </div>
    </div>
    <h2 class="titulo-seccion">Productos estrella (rango ${fmtMoney(min)}–${fmtMoney(max)})</h2>
    ${notaFuente}
    <div class="lista-productos">${comp.productos.map((p) => `
      <div class="producto-card">
        <div class="fila-top"><div class="nombre">${escapar(p.titulo)}</div></div>
        <div class="metricas">
          <span>Precio <b>${fmtMoney2(p.precio)}</b></span>
          <span>Ventas <b>~${fmtNum(p.ventas_estim)}/mes</b></span>
          <span>Rating <b>${escapar(p.rating)}</b></span>
          <span>Reseñas <b>${fmtNum(p.resenas)}</b></span>
        </div>
      </div>`).join("")}</div>
    <div class="card" style="margin-top:10px">
      <b>Recomendaciones</b>
      <ul class="reco">${ev2.recomendaciones.map((r) => `<li>${escapar(r)}</li>`).join("")}</ul>
      <p class="ayuda-config">${escapar(ev2.caveat)}</p>
    </div>
    <div id="kw-reales"></div>`;
  cont.innerHTML = html;

  // keywords reales de Amazon: solo si hay internet; nunca bloquea lo de arriba.
  const kwEl = $("#kw-reales");
  kwEl.innerHTML = `<h2 class="titulo-seccion">Keywords reales de Amazon</h2><div class="card lista-vacia">Buscando en Amazon…</div>`;
  try {
    const kws = await keywordsAmazon(keyword);
    if (kws.length) {
      kwEl.innerHTML = `<h2 class="titulo-seccion">Keywords reales de Amazon</h2>
        <div class="card"><div class="chips">${kws.map((k) => `<span class="chip">${escapar(k)}</span>`).join("")}</div>
        <p class="ayuda-config">Del autocompletado publico de Amazon (lo que la gente busca de verdad).</p></div>`;
    } else { kwEl.innerHTML = ""; }
  } catch (e) {
    kwEl.innerHTML = `<h2 class="titulo-seccion">Keywords reales de Amazon</h2>
      <div class="card lista-vacia">Sin internet: mostramos el analisis del motor local. Conectá el celular a datos/WiFi para traer las keywords reales de Amazon.</div>`;
  }
});

// ============================ ASISTENTE ============================
let chatHistorial = [];
// Render de markdown liviano (negrita, código, listas con viñeta y numeradas,
// títulos y párrafos) para que las respuestas de la IA se vean prolijas, como
// en el programa, y no como texto plano con guiones sueltos.
function _inline(t) {
  return escapar(t)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}
function formatearMensaje(texto) {
  const lineas = String(texto == null ? "" : texto).split(/\n/);
  let html = "", ul = false, ol = false;
  const cerrar = () => { if (ul) { html += "</ul>"; ul = false; } if (ol) { html += "</ol>"; ol = false; } };
  for (const raw of lineas) {
    const l = raw.trim();
    if (!l) { cerrar(); continue; }
    let m;
    if ((m = l.match(/^[-•*]\s+(.*)/))) {
      if (!ul) { cerrar(); html += "<ul>"; ul = true; }
      html += "<li>" + _inline(m[1]) + "</li>";
    } else if ((m = l.match(/^\d+[.)]\s+(.*)/))) {
      if (!ol) { cerrar(); html += "<ol>"; ol = true; }
      html += "<li>" + _inline(m[1]) + "</li>";
    } else if ((m = l.match(/^#{1,3}\s+(.*)/))) {
      cerrar(); html += "<h4>" + _inline(m[1]) + "</h4>";
    } else {
      cerrar(); html += "<p>" + _inline(l) + "</p>";
    }
  }
  cerrar();
  return html;
}
function _bienvenidaChat() {
  const r = resumenPortafolio();
  const extra = r.n
    ? `Veo que tenés **${r.n} producto/s** cargados y un sueldo estable proyectado de **${fmtMoney(r.sueldo_meseta_proyectado)}/mes**. `
    : "Cargá un producto (o tocá **Ver con datos de ejemplo** en Config) y te analizo tus números. ";
  return "¡Hola! Soy tu asistente de MV FBA IA. " + extra
    + "Preguntame lo que quieras: márgenes, precios, qué producto conviene, cuánto podés ganar…";
}
function pintarChat() {
  const cont = $("#chat-historial");
  const items = chatHistorial.length
    ? chatHistorial
    : [{ role: "assistant", content: _bienvenidaChat() }];
  cont.innerHTML = items.map((m) => {
    if (m.content === "Pensando…") {
      return '<div class="msg assistant escribiendo"><span></span><span></span><span></span></div>';
    }
    return `<div class="msg ${m.role}">${formatearMensaje(m.content)}</div>`;
  }).join("");
  cont.scrollTop = cont.scrollHeight;
}
// Asistente LOCAL: responde desde tus datos y el conocimiento FBA embebido, sin
// internet. Si hay clave de Claude + internet, delega en Claude para respuestas
// abiertas; si falla, cae de nuevo a lo local.
function responderLocal(preg) {
  const q = preg.toLowerCase();
  const r = resumenPortafolio();
  const dinero = (n) => fmtMoney(n);
  if (/(hola|buenas|ayuda|que.*hac[eé]s|qu[eé] pod[eé]s)/.test(q)) {
    return "Soy tu asistente FBA y funciono **en el telefono, sin internet**. Puedo: calcular **cuanto ganas** con un producto (pestaña Ganancias), evaluar la **probabilidad de exito** de un nicho (Mercado), y responderte sobre tu **portafolio** y metricas. Preguntame, por ejemplo: \"¿cuanto es mi sueldo meseta?\" o \"¿que es el ACOS?\".";
  }
  if (/(sueldo|meseta|ingreso.*mes|cuanto.*gano.*mes)/.test(q)) {
    if (!r.n) return "Todavia no cargaste productos. Cargá uno en **Portafolio** y te proyecto el sueldo meseta mensual.";
    return `Con tu portafolio actual (${r.n} producto/s) el **sueldo meseta proyectado** es **${dinero(r.sueldo_meseta_proyectado)}/mes** a demanda plena, reciclando capital. Margen promedio: **${fmtPct(r.margen_promedio_pct)}**.`;
  }
  if (/(portafolio|productos|cuantos.*producto|mi negocio|resumen)/.test(q)) {
    if (!r.n) return "Tu portafolio esta vacio. Agregá tu primer producto en **Portafolio**.";
    const s = r.semaforos;
    return `Tenes **${r.n} producto/s**: ${s.verde || 0} en verde, ${s.amarillo || 0} en amarillo, ${s.rojo || 0} en rojo. Capital en pipeline: **${dinero(r.capital_pipeline_total)}**. Ventas reales registradas: **${dinero(r.ingreso_real)}** (neto ${dinero(r.neto_real)}).`;
  }
  if (/(margen|rentab)/.test(q)) {
    return "El **margen neto** es la ganancia despues de TODOS los costos (producto, flete, arancel, prep, comision de Amazon 15%, FBA fee y publicidad) dividido el precio. Semaforo: **verde ≥ 25%**, amarillo ≥ 12%, rojo por debajo. Cargá tu producto en Portafolio y te lo calculo.";
  }
  if (/(acos|publicidad|ppc)/.test(q)) {
    return "**ACOS** = gasto en publicidad / ventas generadas por esa publicidad. El sistema asume **10%** por defecto al calcular tu margen. Al lanzar suele ser mas alto (20-40%) y baja cuando el producto rankea organicamente.";
  }
  if (/(roi|retorno)/.test(q)) {
    return "El **ROI** es la ganancia neta por unidad dividida el **landed cost** (costo + flete + arancel + prep). Te dice cuanto rinde cada dolar invertido en producto. Lo ves por producto en Portafolio y en el simulador de Ganancias.";
  }
  if (/(dedicaci|horas|tiempo)/.test(q)) {
    const d = MV.estimarDedicacion(Math.max(1, r.n), r.n === 0);
    return `Estimacion de dedicacion: **${d.horas_semana_min}–${d.horas_semana_max} horas/semana** para ${r.n || 1} producto(s)${r.n === 0 ? " en lanzamiento" : " en operacion"}. El sistema automatiza FAQ, KPIs, alertas y calculos; vos revisas PPC, precio, stock y proveedores.`;
  }
  if (/(exito|nicho|keyword|buscar producto|que vender)/.test(q)) {
    return "Andá a **Mercado**, escribí un producto o keyword y un rango de precios: te doy la **probabilidad de exito** (demanda, barrera de entrada, hueco de calidad, precio y margen), productos estrella y, si tenes internet, las keywords reales de Amazon.";
  }
  if (/(precio|cuanto.*vender|cuanto.*cobrar)/.test(q)) {
    return "El sistema sugiere tu **precio** apuntando a un margen objetivo del 25%, y si cargas el precio de la competencia intenta entrar **5% por debajo del lider** siempre que el margen siga sano. Cargá el producto en Portafolio y te lo calcula.";
  }
  if (/(keepa|helium|jungle|herramienta|api.*39|api.*49|19.*euro|49.*euro|que.*pago|vale la pena)/.test(q)) {
    return "Para **Keepa**: la **web (~19 €/mes)** te da el historial de precio y ranking para "
      + "mirar a mano antes de comprar — **es lo que te conviene para arrancar**. La **API (49 €/mes)** "
      + "solo sirve para que la app traiga esos datos sola (automatizado), y recién vale la pena mas "
      + "adelante. **No pagues la API para investigar.** Alternativa: **Helium 10** tiene plan gratis y "
      + "cubre keywords + productos + competencia; Jungle Scout hace lo mismo pero sin free. Igual, tu "
      + "app ya trae el motor propio gratis, asi que las herramientas son para **validar a mano** el "
      + "candidato. (Mas detalle en la pestaña **Config**.)";
  }
  return "Puedo ayudarte con tu **portafolio**, el **sueldo meseta**, **margen/ROI/ACOS**, la **dedicacion horaria** y como **evaluar un nicho** en Mercado. Para respuestas abiertas fuera de tus datos, cargá una clave de Claude en **Config** y con internet te respondo cualquier cosa. ¿Sobre cual querés que profundice?";
}
// Contexto e historial compartidos por todos los proveedores de IA.
function _contextoIA() {
  const r = resumenPortafolio();
  return `Sos el asistente de MV FBA IA, un cockpit para vender en Amazon FBA. `
    + `Datos del negocio del usuario: ${r.n} productos, `
    + `sueldo meseta proyectado ${fmtMoney(r.sueldo_meseta_proyectado)}/mes, `
    + `margen promedio ${fmtPct(r.margen_promedio_pct)}, ventas reales ${fmtMoney(r.ingreso_real)}. `
    + `Respondé con tono profesional pero amable y cercano, breve y práctico, como un asesor FBA `
    + `de confianza. No prometas retornos garantizados. No inventes datos de productos/ventas de `
    + `Amazon: esos vienen de la API de datos (Keepa), no de vos.`;
}
function _historialIA() {
  return chatHistorial.filter((m) => m.content !== "Pensando…").slice(-6)
    .map((m) => ({ role: m.role, content: m.content }));
}
// --- Claude / Anthropic (recomendada) ---
async function responderClaude(preg, clave) {
  const cuerpo = JSON.stringify({
    model: "claude-opus-4-8", max_tokens: 600, system: _contextoIA(),
    messages: [..._historialIA(), { role: "user", content: preg }],
  });
  const txt = await pedirHTTP("POST", "https://api.anthropic.com/v1/messages", cuerpo, {
    "Content-Type": "application/json",
    "x-api-key": clave,
    "anthropic-version": "2023-06-01",
    "anthropic-dangerous-direct-browser-access": "true",
  });
  const data = JSON.parse(txt);
  const bloque = (data.content || []).find((b) => b.type === "text");
  return bloque ? bloque.text : "No obtuve respuesta del asistente.";
}
// --- OpenAI (ChatGPT) ---
async function responderOpenAI(preg, clave) {
  const resp = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + clave },
    body: JSON.stringify({
      model: "gpt-4o-mini", max_tokens: 600,
      messages: [{ role: "system", content: _contextoIA() },
        ..._historialIA(), { role: "user", content: preg }],
    }),
  });
  if (!resp.ok) throw new Error("openai " + resp.status);
  const data = await resp.json();
  const t = data && data.choices && data.choices[0] && data.choices[0].message;
  return (t && t.content) ? t.content : "No obtuve respuesta del asistente.";
}
// --- Google Gemini ---
async function responderGemini(preg, clave) {
  const contents = [..._historialIA().map((m) => ({
    role: m.role === "assistant" ? "model" : "user", parts: [{ text: m.content }] })),
    { role: "user", parts: [{ text: preg }] }];
  const url = "https://generativelanguage.googleapis.com/v1beta/models/"
    + "gemini-2.0-flash:generateContent?key=" + encodeURIComponent(clave);
  const resp = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: _contextoIA() }] },
      contents, generationConfig: { maxOutputTokens: 600 },
    }),
  });
  if (!resp.ok) throw new Error("gemini " + resp.status);
  const data = await resp.json();
  const c = data && data.candidates && data.candidates[0];
  const t = c && c.content && c.content.parts && c.content.parts.map((p) => p.text || "").join("");
  return t ? t : "No obtuve respuesta del asistente.";
}
// Rutea a la clave propia del proveedor elegido (o al primero que tenga clave).
async function responderBYOK(preg) {
  const c = estado.claves;
  const orden = [c.ia_prov || "claude", "claude", "openai", "gemini"];
  const vistos = new Set();
  for (const prov of orden) {
    if (vistos.has(prov)) continue;
    vistos.add(prov);
    const clave = (c[prov] || "").trim();
    if (!clave) continue;
    if (prov === "claude") return await responderClaude(preg, clave);
    if (prov === "openai") return await responderOpenAI(preg, clave);
    if (prov === "gemini") return await responderGemini(preg, clave);
  }
  throw new Error("sin clave");
}
// Id de dispositivo (no personal, solo para topear el uso gratis del proxy
// de IA por instalacion). Generado una vez, vive en localStorage.
const LS_DISPOSITIVO = "mvfba_dispositivo_id";
function idDispositivo() {
  let id = localStorage.getItem(LS_DISPOSITIVO);
  if (!id) {
    id = "d-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(LS_DISPOSITIVO, id);
  }
  return id;
}
// Proxy de IA del DEMO web / cuentas con saldo de creditos: la clave de
// Claude vive en el servidor (Vercel), no en el cliente. En la app descargada
// (file://) este fetch falla y se cae al local. Si hay una licencia
// activada, se manda email+clave para que el servidor descuente del saldo de
// creditos en vez del tope generico de demo (ver api/ia.js).
async function responderProxy(preg) {
  const r = resumenPortafolio();
  const contexto = `${r.n} productos, sueldo meseta ${fmtMoney(r.sueldo_meseta_proyectado)}/mes, `
    + `margen promedio ${fmtPct(r.margen_promedio_pct)}, ventas reales ${fmtMoney(r.ingreso_real)}.`;
  const idioma = (localStorage.getItem("mvfba_idioma") || (navigator.language || "es").slice(0, 2));
  const cuerpo = { pregunta: preg, contexto, idioma, dispositivo: idDispositivo() };
  const reg = Licencia.obtenerRegistro();
  if (reg && reg.email && reg.claveLicencia) {
    cuerpo.email = reg.email;
    cuerpo.clave = reg.claveLicencia;
  }
  const resp = await fetch("/api/ia", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-mv-app": "mvfba-web-1" },
    body: JSON.stringify(cuerpo),
  });
  if (!resp.ok) {
    // 429 (cuota/tope alcanzado) trae un mensaje amigable: mostrarlo en vez
    // de caer en silencio al asistente local, para que el usuario entienda
    // por que dejo de responder la IA.
    try {
      const err = await resp.json();
      if (err && err.mensaje) return err.mensaje;
    } catch (e) { /* sigue */ }
    return null; // 503 no configurada / 502 upstream -> fallback silencioso
  }
  const data = await resp.json();
  if (!data || !data.texto) return null;
  // El servidor devuelve el saldo restante tras cada respuesta con creditos:
  // el chip del chat se actualiza siempre (con su pulso), y ADEMAS se avisa
  // en el propio mensaje SOLO cuando queda poco, para que la recarga no lo
  // agarre de sorpresa a mitad de una consulta importante.
  if (typeof data.creditos_restantes === "number") {
    pintarSaldoChat(data.creditos_restantes);
    if (data.creditos_restantes < 50) {
      return data.texto + `\n\n_Te quedan ~${data.creditos_restantes} créditos de IA — podés recargar desde Config._`;
    }
  }
  return data.texto;
}
// Chip de saldo del chat: numero vivo que pulsa al cambiar. Se pinta al
// entrar a la vista (consultando /api/creditos) y tras cada respuesta del
// proxy (con el saldo que ya viene en la respuesta, sin llamada extra).
function pintarSaldoChat(n) {
  const chip = $("#chat-saldo");
  if (!chip) return;
  const texto = `⚡ ${fmtNum(Math.floor(n))} créditos`;
  const cambio = chip.textContent && chip.textContent !== texto;
  chip.textContent = texto;
  chip.classList.remove("oculto");
  chip.classList.toggle("bajo", n < 50);
  if (cambio) {
    chip.classList.remove("pulso");
    void chip.offsetWidth; // reinicia la animacion CSS
    chip.classList.add("pulso");
  }
}
async function refrescarSaldoChat() {
  const chip = $("#chat-saldo");
  if (!chip) return;
  const reg = Licencia.obtenerRegistro();
  if (!reg || !reg.email || !reg.claveLicencia) { chip.classList.add("oculto"); return; }
  try {
    const url = `/api/creditos?email=${encodeURIComponent(reg.email)}&clave=${encodeURIComponent(reg.claveLicencia)}`;
    const r = await fetch(url, { headers: { "x-mv-app": "mvfba-web-1" } });
    if (!r.ok) return;
    const d = await r.json();
    if (d.activo) pintarSaldoChat(d.saldo);
    else if (d.motivo === "saldo_agotado") pintarSaldoChat(0);
  } catch (e) { /* sin red: el chip simplemente no se muestra */ }
}
// Orquesta: 1) clave propia del proveedor elegido (Claude/OpenAI/Gemini)
// 2) proxy del demo (IA incluida, Claude del servidor) 3) asistente local.
async function responderIA(texto) {
  const c = estado.claves;
  if ((c.claude || c.openai || c.gemini || "").trim()) {
    try { return await responderBYOK(texto); } catch (e) { /* sigue */ }
  }
  try {
    const p = await responderProxy(texto);
    if (p) return p;
  } catch (e) { /* sigue */ }
  return responderLocal(texto);
}
$("#form-chat").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const input = $("#chat-input");
  const texto = input.value.trim();
  if (!texto) return;
  chatHistorial.push({ role: "user", content: texto });
  pintarChat();
  input.value = "";
  chatHistorial.push({ role: "assistant", content: "Pensando…" });
  pintarChat();
  let respuesta;
  try {
    respuesta = await responderIA(texto);            // clave propia -> proxy demo -> local
  } catch (e) {
    respuesta = responderLocal(texto);               // local, siempre disponible
  }
  chatHistorial[chatHistorial.length - 1] = { role: "assistant", content: respuesta };
  pintarChat();
});

// ============================ CONFIG ============================
function pintarConfig() {
  $("#cfg-keepa").value = estado.claves.keepa || "";
  $("#cfg-claude").value = estado.claves.claude || "";
  if ($("#cfg-openai")) $("#cfg-openai").value = estado.claves.openai || "";
  if ($("#cfg-gemini")) $("#cfg-gemini").value = estado.claves.gemini || "";
  if ($("#cfg-ia-prov")) $("#cfg-ia-prov").value = estado.claves.ia_prov || "claude";
  const r = resumenPortafolio();
  $("#cfg-datos").innerHTML = `Tenes <b>${r.n}</b> producto/s y <b>${estado.ventas.length}</b> venta/s registradas en este telefono.`;
  pintarSaldoIA();
}
// Saldo de creditos de IA compartida (ver api/_creditosia.js): se muestra
// SOLO si hay una licencia activada (no tiene sentido para quien todavia
// esta en la demo de 7 dias sin comprar -- ahi corre el tope generico de
// api/ia.js en vez del saldo por cuenta).
async function pintarSaldoIA() {
  const box = $("#saldo-ia-box");
  if (!box) return;
  const reg = Licencia.obtenerRegistro();
  if (!reg || !reg.email || !reg.claveLicencia) { box.classList.add("oculto"); return; }
  try {
    const url = `/api/creditos?email=${encodeURIComponent(reg.email)}&clave=${encodeURIComponent(reg.claveLicencia)}`;
    const r = await fetch(url, { headers: { "x-mv-app": "mvfba-web-1" } });
    if (!r.ok) { box.classList.add("oculto"); return; }
    const d = await r.json();
    if (d.motivo === "sin_cuenta" || d.motivo === "almacen_no_configurado") { box.classList.add("oculto"); return; }
    box.classList.remove("oculto");
    if (d.activo) {
      $("#saldo-ia-estado").textContent = `Créditos de IA disponibles: ${fmtNum(Math.floor(d.saldo))}`;
    } else {
      $("#saldo-ia-estado").textContent = "Se acabaron tus créditos de IA. Recargá para seguir usando el asistente compartido.";
    }
    // Resumen de consumo de la semana (lo acumula el servidor al descontar).
    const reg2 = d.registro || {};
    if (reg2.semana_preguntas > 0) {
      $("#saldo-ia-estado").textContent +=
        ` · Esta semana: ${fmtNum(Math.ceil(reg2.semana_consumido || 0))} créditos en ${fmtNum(reg2.semana_preguntas)} pregunta(s).`;
    }
  } catch (e) { box.classList.add("oculto"); }
}
$("#form-config").addEventListener("submit", (ev) => {
  ev.preventDefault();
  estado.claves.keepa = $("#cfg-keepa").value.trim();
  estado.claves.claude = $("#cfg-claude").value.trim();
  if ($("#cfg-openai")) estado.claves.openai = $("#cfg-openai").value.trim();
  if ($("#cfg-gemini")) estado.claves.gemini = $("#cfg-gemini").value.trim();
  if ($("#cfg-ia-prov")) estado.claves.ia_prov = $("#cfg-ia-prov").value || "claude";
  guardarEstado(estado);
  mostrarToast("Guardado en el telefono");
});
$("#btn-exportar").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(estado, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "mv-fba-backup.json"; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
});
$("#btn-importar").addEventListener("click", () => $("#file-importar").click());
$("#file-importar").addEventListener("change", (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const e = JSON.parse(rd.result);
      estado = { ...estadoDefault(), ...e, claves: { ...estadoDefault().claves, ...(e.claves || {}) } };
      guardarEstado(estado);
      pintarConfig(); cargarInicio();
      mostrarToast("Datos importados");
    } catch (_) { mostrarToast("Archivo invalido"); }
  };
  rd.readAsText(f);
});
$("#btn-borrar-todo").addEventListener("click", () => {
  if (!confirm("¿Borrar TODOS los productos y ventas de este telefono? No se puede deshacer.")) return;
  estado = estadoDefault();
  guardarEstado(estado);
  pintarConfig(); cargarInicio();
  mostrarToast("Datos borrados");
});
$("#btn-demo").addEventListener("click", () => {
  estado.productos = [
    { id: nuevoId(), nombre: "Set utensilios de bambu", costo: 2.10, flete: 0.80, arancel_pct: 6, prep: 0.50, precio: 0, precio_competencia: 19.99, techo_demanda: 290 },
    { id: nuevoId(), nombre: "Organizador de escritorio", costo: 3.40, flete: 1.10, arancel_pct: 6, prep: 0.60, precio: 0, precio_competencia: 27.99, techo_demanda: 210 },
    { id: nuevoId(), nombre: "Botella termica 750ml", costo: 4.20, flete: 1.60, arancel_pct: 8, prep: 0.70, precio: 0, precio_competencia: 34.99, techo_demanda: 180 },
  ];
  estado.ventas = [
    { id: nuevoId(), producto_id: estado.productos[0].id, unidades: 120, ingreso: 2278, fecha: "2026-05-15" },
    { id: nuevoId(), producto_id: estado.productos[1].id, unidades: 60, ingreso: 1595, fecha: "2026-06-02" },
  ];
  guardarEstado(estado);
  pintarConfig(); cargarInicio();
  mostrarToast("Portafolio de ejemplo cargado");
  irAVista("inicio");
});

// ============================ DEMO / REGISTRO (7 dias, multi-idioma) ============================
const LS_IDIOMA = "mvfba_idioma";
function idiomaActual() {
  const guardado = localStorage.getItem(LS_IDIOMA);
  if (guardado) return guardado;
  const nav = (navigator.language || "es").slice(0, 2).toLowerCase();
  return ["es", "en", "pt"].includes(nav) ? nav : "es";
}
function fijarIdioma(id) { localStorage.setItem(LS_IDIOMA, id); }

function pintarBadgeDemo() {
  const st = Licencia.estado();
  const t = Licencia.TXT[idiomaActual()];
  const badge = $("#demo-badge");
  if (!badge) return;
  if (st.licencia) {
    badge.textContent = t.badge_licencia;
    badge.classList.remove("oculto", "vencido");
  } else if (st.registrado) {
    badge.textContent = t.badge_demo.replace("{n}", st.diasRestantes);
    badge.classList.toggle("vencido", st.diasRestantes <= 1);
    badge.classList.remove("oculto");
  } else {
    badge.classList.add("oculto");
  }
}

// Recordatorio DENTRO de la app durante los 7 dias de demo (no es email/WhatsApp:
// no hay backend que dispare esa secuencia; esto usa el mismo reloj local que ya
// mide diasRestantes y aparece cada vez que se abre Inicio).
// El aviso "quedan2" se dispara con diasRestantes === 2, asi que el texto habla
// de los dias que QUEDAN (no de "dia 2 de N"): sigue siendo correcto aunque
// cambie la duracion de la demo.
const NUDGE_TXT = {
  es: { quedan2: "Te quedan 2 días de demo: cargá TU producto real y mirá cuánto podrías ganar.",
        ultimo: "Último día de tu demo — comprá ahora y seguí sin cortes.", cta: "Ver planes" },
  en: { quedan2: "2 days left in your demo: load YOUR real product and see how much you could earn.",
        ultimo: "Last day of your demo — buy now and keep going without interruption.", cta: "See plans" },
  pt: { quedan2: "Faltam 2 dias da sua demo: carregue SEU produto real e veja quanto poderia ganhar.",
        ultimo: "Último dia da sua demo — compre agora e continue sem interrupções.", cta: "Ver planos" },
};
function pintarNudgeDemo() {
  const el = $("#demo-nudge");
  if (!el) return;
  const st = Licencia.estado();
  if (st.licencia || !st.registrado) { el.classList.add("oculto"); return; }
  const t = NUDGE_TXT[idiomaActual()] || NUDGE_TXT.es;
  const url = "https://mvfbaia.com/#precios";
  if (st.diasRestantes <= 1) {
    el.className = "demo-nudge urgente";
    el.innerHTML = `<span><b>⏳</b>${escapar(t.ultimo)}</span><a href="${url}" target="_blank" rel="noopener">${escapar(t.cta)}</a>`;
  } else if (st.diasRestantes === 2) {
    el.className = "demo-nudge";
    el.innerHTML = `<span><b>👋</b>${escapar(t.quedan2)}</span><a href="${url}" target="_blank" rel="noopener">${escapar(t.cta)}</a>`;
  } else {
    el.classList.add("oculto");
  }
}

function pintarGateDemo() {
  const idioma = idiomaActual();
  $("#demo-idioma").value = idioma;
  const t = Licencia.TXT[idioma];
  const st = Licencia.estado();
  $("#demo-sub").textContent = t.sub;
  $("#demo-lbl-nombre").textContent = t.nombre;
  $("#demo-lbl-email").textContent = t.email;
  $("#demo-btn-empezar").textContent = t.empezar;
  $("#demo-vencido-sub").textContent = t.vencida_sub;
  $("#demo-lbl-email2").textContent = t.email;
  $("#demo-lbl-clave").textContent = t.clave;
  $("#demo-btn-activar").textContent = t.activar;
  $("#demo-contactar").textContent = t.contactar;
  const asunto = encodeURIComponent(`Compra de licencia ${Licencia.DOMINIO}`);
  const cuerpo = encodeURIComponent(`Quiero comprar la licencia. Email de registro: ${st.email || ""}`);
  $("#demo-contactar").href = `mailto:vieraschiavi@gmail.com?subject=${asunto}&body=${cuerpo}`;

  if (!st.registrado) {
    $("#demo-registro").classList.remove("oculto");
    $("#demo-vencido").classList.add("oculto");
  } else {
    $("#demo-registro").classList.add("oculto");
    $("#demo-vencido").classList.remove("oculto");
    $("#demo-email2").value = st.email || "";
  }
}

// Devuelve true si la demo/licencia esta vigente (y oculta el gate); si no,
// muestra el gate (registro o reactivacion de licencia) y devuelve false.
function evaluarDemo() {
  const st = Licencia.estado();
  if (st.vigente) {
    $("#demo-gate").classList.add("oculto");
    pintarBadgeDemo();
    return true;
  }
  pintarGateDemo();
  $("#demo-gate").classList.remove("oculto");
  return false;
}

$("#demo-idioma").addEventListener("change", (ev) => {
  fijarIdioma(ev.target.value);
  pintarGateDemo();
});

$("#form-demo-registro").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const nombre = $("#demo-nombre").value.trim();
  const email = $("#demo-email").value.trim();
  const t = Licencia.TXT[idiomaActual()];
  if (!email.includes("@")) { mostrarToast(t.falta_email); return; }
  Licencia.registrar(nombre, email);
  if (evaluarDemo()) {
    if (!localStorage.getItem(LS_VISTO)) $("#bienvenida").classList.remove("oculto");
  }
});

$("#form-demo-licencia").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const email = $("#demo-email2").value.trim();
  const clave = $("#demo-clave").value.trim();
  const t = Licencia.TXT[idiomaActual()];
  const res = await Licencia.activarLicencia(email, clave);
  if (res.ok) {
    mostrarToast(t.clave_ok);
    evaluarDemo();
  } else if (res.mensaje === "sin_conexion") {
    mostrarToast(t.sin_conexion);
  } else {
    mostrarToast(t.clave_invalida);
  }
});

// ============================ BIENVENIDA (standalone) ============================
$("#bienvenida-empezar").addEventListener("click", () => {
  localStorage.setItem(LS_VISTO, "1");
  $("#bienvenida").classList.add("oculto");
  irAVista("portafolio");
});
$("#bienvenida-demo").addEventListener("click", () => {
  localStorage.setItem(LS_VISTO, "1");
  $("#bienvenida").classList.add("oculto");
  $("#btn-demo").click();
  iniciarTour();
});

// ============================ TOUR DE PRIMER USO (3 pasos) ============================
// Sigue al "Ver con datos de ejemplo": cargar ejemplo -> ver semaforo/KPIs en
// Portafolio -> Asistente. Vive dentro de la app (no un .md tecnico aparte).
const TOUR_PASOS = [
  { vista: "portafolio", texto: "Estos son 3 productos de ejemplo. El semáforo (verde/amarillo/rojo) te dice al instante si el margen conviene — tocá el ⓘ para ver el detalle." },
  { vista: "portafolio", texto: "Arriba tenés el resumen: tu sueldo meseta proyectado y el capital en juego. Es la foto completa de tu negocio, siempre a mano." },
  { vista: "asistente", texto: "Cualquier duda, preguntale al Asistente sobre tus números. ¡Ya podés explorar el resto de la app!" },
];
let _tourPaso = 0;
function _pintarTour() {
  const dotsEl = $("#tour-dots");
  dotsEl.innerHTML = TOUR_PASOS.map((_, i) => `<span class="${i === _tourPaso ? "on" : ""}"></span>`).join("");
  $("#tour-texto").textContent = TOUR_PASOS[_tourPaso].texto;
  $("#tour-siguiente").textContent = _tourPaso === TOUR_PASOS.length - 1 ? "Entendido" : "Siguiente";
  irAVista(TOUR_PASOS[_tourPaso].vista);
}
function iniciarTour() {
  _tourPaso = 0;
  $("#tour-card").classList.remove("oculto");
  _pintarTour();
}
function _cerrarTour() { $("#tour-card").classList.add("oculto"); }
$("#tour-siguiente").addEventListener("click", () => {
  if (_tourPaso >= TOUR_PASOS.length - 1) { _cerrarTour(); return; }
  _tourPaso += 1;
  _pintarTour();
});
$("#tour-saltar").addEventListener("click", _cerrarTour);

// ============================ CONTACTO ============================
const CONTACTO_EMAIL = "vieraschiavi@gmail.com";
$("#form-contacto").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const pregunta = $("#ct-pregunta").value.trim();
  if (!pregunta) { mostrarToast("Escribí tu pregunta antes de enviar"); return; }
  const asunto = $("#ct-asunto").value.trim() || "Consulta desde MV FBA IA";
  const contacto = $("#ct-contacto").value.trim() || "(no indicado)";
  const cuerpo = `${pregunta}\n\nContacto de quien consulta: ${contacto}`;
  const mailto = `mailto:${CONTACTO_EMAIL}?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(cuerpo)}`;
  // La WebView nativa reenvia cualquier link no-file:// al sistema (abre la app de mail).
  window.location.href = mailto;
  mostrarToast("Abriendo tu app de correo…");
});

// ============================ ARRANQUE ============================
(function arranque() {
  estadoConexion();
  pintarConfig();
  cargarInicio();
  if (evaluarDemo() && !localStorage.getItem(LS_VISTO)) {
    $("#bienvenida").classList.remove("oculto");
  }
  window.addEventListener("online", estadoConexion);
  window.addEventListener("offline", estadoConexion);
})();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("service-worker.js").catch(() => {});
  });
}
