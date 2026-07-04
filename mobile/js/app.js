// app.js — MV Amazon FBA IA (app Android NATIVA, sin depender de la PC).
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
  return { productos: [], ventas: [], claves: { keepa: "", claude: "" } };
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

// ============================ INICIO ============================
function kpiHtml(lab, val, sub, tone, hero) {
  const cls = ["kpi"];
  if (hero) cls.push("hero"); else if (tone) cls.push(tone);
  return `<div class="${cls.join(" ")}"><div class="lab">${lab}</div>
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
    kpiHtml("Margen", fmtPct(margenGlobal), facturacion > 0 ? "real" : "proyectado del portafolio", tonoMargen(margenGlobal)) +
    kpiHtml("Sueldo meseta", fmtMoney(r.sueldo_meseta_proyectado), "proyectado/mes");

  if (r.n) {
    const s = r.semaforos;
    contPf.className = "";
    contPf.innerHTML = `
      <div class="grid-kpi">
        ${kpiHtml("Productos", r.n, `${s.verde || 0} verde · ${s.amarillo || 0} amarillo · ${s.rojo || 0} rojo`, null, true)}
        ${kpiHtml("Capital en pipeline", fmtMoney(r.capital_pipeline_total), "~4 meses de stock")}
        ${kpiHtml("Margen promedio", fmtPct(r.margen_promedio_pct), "de todo el portafolio", tonoMargen(r.margen_promedio_pct))}
        ${kpiHtml("Ordenes", fmtNum(ordenes), fmtNum(unidades) + " unidades")}
      </div>`;
  } else {
    contPf.className = "card lista-vacia";
    contPf.innerHTML = `Todavia no cargaste productos.
      <br><button class="btn-primario" data-ir="portafolio" style="margin-top:10px">Cargar mi primer producto</button>`;
    $("[data-ir]", contPf).addEventListener("click", () => irAVista("portafolio"));
  }
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
    kpiHtml("Sueldo meseta", fmtMoney(r.sueldo_meseta_proyectado), "proyectado/mes", null, true) +
    kpiHtml("Margen promedio", fmtPct(r.margen_promedio_pct), "de todo el portafolio", tonoMargen(r.margen_promedio_pct));
  listaEl.innerHTML = r.prods.map((p) => `
    <div class="producto-card">
      <div class="fila-top">
        <div class="nombre">${escapar(p.nombre)}</div>
        <span class="badge ${tonoSemaforo(p.semaforo)}"><span class="dot"></span>${p.semaforo.toUpperCase()}</span>
      </div>
      <div class="metricas">
        <span>Precio <b>${fmtMoney2(p.precio)}</b></span>
        <span>Margen <b>${fmtPct(p.margen)}</b></span>
        <span>ROI <b>${fmtPct(p.roi)}</b></span>
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

function escapar(t) {
  return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

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
      ${kpiHtml("Ganancia neta", fmtMoney(lo.ganancia_neta), r.entrada, tonoG, true)}
      ${kpiHtml("ROI inversion", fmtPct(lo.roi_inversion_pct), fmtMoney(lo.inversion_usada), tonoG)}
      ${kpiHtml("Ganancia/unidad", fmtMoney2(lo.ganancia_por_unidad), "precio " + fmtMoney2(ue.precio_venta), tonoSemaforo(ue.semaforo))}
      ${kpiHtml("Sueldo en meseta", fmtMoney(re.sueldo_meseta_mensual), "reciclando capital 12m")}
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
// Datos pseudo-reales deterministas por keyword (modo demo, 100% offline).
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
      titulo: `${keyword} — variante ${i + 1}`,
      precio: Math.min(max + 10, Math.max(min, pr)),
      ventas_estim: Math.floor(ventas * (0.5 + rnd(7 + i, 0, 1)) / 3),
      rating: +(4.0 + rnd(8 + i, 0, 0.8)).toFixed(1),
      resenas: Math.floor(resenasMed * (0.4 + rnd(9 + i, 0, 1.4))),
    };
  });
  return {
    ventas_estim_total: ventas, n_competidores: nComp, resenas_mediana: resenasMed,
    rating_promedio: rating, precio_mediana: +precioMed.toFixed(2), productos,
  };
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

  const comp = competenciaDemo(keyword, min, max);
  const ev2 = MV.evaluarExito(keyword, comp, null, comp.precio_mediana, null);
  const tono = tonoSemaforo({ VERDE: "verde", AMARILLO: "amarillo", ROJO: "rojo" }[ev2.veredicto]);

  let html = `
    <h2 class="titulo-seccion">Probabilidad de exito</h2>
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
    <div class="lista-productos">${comp.productos.map((p) => `
      <div class="producto-card">
        <div class="fila-top"><div class="nombre">${escapar(p.titulo)}</div></div>
        <div class="metricas">
          <span>Precio <b>${fmtMoney2(p.precio)}</b></span>
          <span>Ventas <b>~${fmtNum(p.ventas_estim)}/mes</b></span>
          <span>Rating <b>${p.rating}</b></span>
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
function formatearMensaje(texto) {
  const seguro = escapar(texto);
  return seguro.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
}
function pintarChat() {
  const cont = $("#chat-historial");
  cont.innerHTML = chatHistorial.map((m) => `<div class="msg ${m.role}">${formatearMensaje(m.content)}</div>`).join("");
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
async function responderClaude(preg) {
  const clave = (estado.claves.claude || "").trim();
  if (!clave) throw new Error("sin clave");
  const r = resumenPortafolio();
  const contexto = `Datos del negocio del usuario (Amazon FBA): ${r.n} productos, `
    + `sueldo meseta proyectado ${fmtMoney(r.sueldo_meseta_proyectado)}/mes, `
    + `margen promedio ${fmtPct(r.margen_promedio_pct)}, ventas reales ${fmtMoney(r.ingreso_real)}. `
    + `Respondé en español rioplatense, breve y practico, como asesor FBA.`;
  const cuerpo = JSON.stringify({
    model: "claude-opus-4-8", max_tokens: 600,
    system: contexto,
    messages: [...chatHistorial.filter((m) => m.content !== "Pensando…").slice(-6).map((m) => ({ role: m.role, content: m.content })),
      { role: "user", content: preg }],
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
    respuesta = await responderClaude(texto);       // abierto (si hay clave+internet)
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
  const r = resumenPortafolio();
  $("#cfg-datos").innerHTML = `Tenes <b>${r.n}</b> producto/s y <b>${estado.ventas.length}</b> venta/s registradas en este telefono.`;
}
$("#form-config").addEventListener("submit", (ev) => {
  ev.preventDefault();
  estado.claves.keepa = $("#cfg-keepa").value.trim();
  estado.claves.claude = $("#cfg-claude").value.trim();
  guardarEstado(estado);
  mostrarToast("Claves guardadas en el telefono");
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
});

// ============================ ARRANQUE ============================
(function arranque() {
  estadoConexion();
  pintarConfig();
  cargarInicio();
  if (!localStorage.getItem(LS_VISTO)) {
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
