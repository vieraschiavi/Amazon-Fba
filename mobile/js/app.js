// app.js — MV Amazon FBA IA (mobile). Vanilla JS, sin build ni dependencias:
// una unica pagina, navegacion por pestanas, fetch directo a la API FastAPI
// ya existente (app.py). Todo el estado vive en localStorage (URL de la API,
// modo demo, historial de chat de la sesion).

const LS_KEY_URL = "mvfba_api_url";
const $ = (sel, root = document) => root.querySelector(sel);
const $all = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function apiUrl() {
  return (localStorage.getItem(LS_KEY_URL) || "http://localhost:8000").replace(/\/+$/, "");
}

function fmtMoney(x) {
  const n = Number(x) || 0;
  return "$" + n.toLocaleString("es-AR", { maximumFractionDigits: 0 });
}
function fmtPct(x, dec = 1) {
  const n = Number(x) || 0;
  return n.toFixed(dec) + "%";
}
function tonoSemaforo(s) {
  return { verde: "verde", amarillo: "amarillo", rojo: "rojo" }[s] || "navy";
}

function mostrarToast(texto) {
  let t = $("#toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "toast";
    t.className = "toast";
    document.body.appendChild(t);
  }
  t.textContent = texto;
  t.classList.add("mostrar");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("mostrar"), 3200);
}

async function apiGet(path) {
  const r = await fetch(apiUrl() + path, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}
async function apiPost(path, body) {
  const r = await fetch(apiUrl() + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

// ---------------------------------------------------------------- Navegacion
function irAVista(nombre) {
  $all(".view").forEach((v) => v.classList.toggle("activa", v.id === "view-" + nombre));
  $all(".nav-btn").forEach((b) => b.classList.toggle("activa", b.dataset.vista === nombre));
  if (nombre === "inicio") cargarInicio();
  if (nombre === "portafolio") cargarPortafolio();
}

$all(".nav-btn").forEach((b) => b.addEventListener("click", () => irAVista(b.dataset.vista)));
$all("[data-ir]").forEach((b) => b.addEventListener("click", () => irAVista(b.dataset.ir)));

// ---------------------------------------------------------------- Estado / salud
async function verificarEstado() {
  const dot = $("#btn-estado");
  try {
    await apiGet("/health");
    dot.classList.remove("mal");
    dot.classList.add("ok");
    return true;
  } catch (e) {
    dot.classList.remove("ok");
    dot.classList.add("mal");
    return false;
  }
}
$("#btn-estado").addEventListener("click", () => irAVista("config"));

// ---------------------------------------------------------------- Inicio
function kpiHtml(lab, val, sub, tone, hero) {
  const cls = ["kpi"];
  if (hero) cls.push("hero");
  else if (tone) cls.push(tone);
  return `<div class="${cls.join(" ")}"><div class="lab">${lab}</div>
          <div class="val">${val}</div><div class="sub">${sub || ""}</div></div>`;
}

async function cargarInicio() {
  const cont = $("#inicio-kpis");
  const contPf = $("#inicio-portafolio");
  try {
    const [dash, pf] = await Promise.all([apiGet("/dashboard"), apiGet("/portfolio")]);
    cont.innerHTML =
      kpiHtml("Facturacion", fmtMoney(dash.facturacion), "acumulada", null, true) +
      kpiHtml("Neto", fmtMoney(dash.neto), "despues de costos") +
      kpiHtml("Margen global", fmtPct(dash.margen_global_pct), "neto / facturacion",
        dash.margen_global_pct >= 25 ? "good" : dash.margen_global_pct >= 12 ? "warn" : "bad") +
      kpiHtml("Ordenes", (dash.ordenes || 0).toLocaleString("es-AR"),
        (dash.unidades || 0).toLocaleString("es-AR") + " unidades");

    if (pf.n_productos) {
      const sem = pf.semaforos || {};
      contPf.className = "";
      contPf.innerHTML = `
        <div class="grid-kpi">
          ${kpiHtml("Sueldo meseta proyectado", fmtMoney(pf.sueldo_meseta_proyectado), "portafolio completo", null, true)}
          ${kpiHtml("Productos", pf.n_productos, `${sem.verde || 0} verde · ${sem.amarillo || 0} amarillo · ${sem.rojo || 0} rojo`)}
          ${kpiHtml("Capital en pipeline", fmtMoney(pf.capital_pipeline_total), "~4 meses de stock")}
          ${kpiHtml("Ventas reales", fmtMoney(pf.ingreso_real), "neto " + fmtMoney(pf.neto_real), pf.neto_real > 0 ? "good" : null)}
        </div>`;
    } else {
      contPf.className = "card lista-vacia";
      contPf.textContent = pf.mensaje || "Portafolio vacio.";
    }
  } catch (e) {
    cont.innerHTML = `<div class="card lista-vacia">No se pudo conectar con la API. Revisa la URL en Config.</div>`;
    contPf.className = "card lista-vacia";
    contPf.textContent = "";
  }
}

// ---------------------------------------------------------------- Portafolio
async function cargarPortafolio() {
  const kpisEl = $("#portafolio-kpis");
  const listaEl = $("#portafolio-lista");
  listaEl.innerHTML = `<div class="card lista-vacia">Cargando…</div>`;
  try {
    const pf = await apiGet("/portfolio");
    if (!pf.n_productos) {
      kpisEl.innerHTML = "";
      listaEl.innerHTML = `<div class="card lista-vacia">${pf.mensaje || "Portafolio vacio."}</div>`;
      return;
    }
    kpisEl.innerHTML =
      kpiHtml("Sueldo meseta", fmtMoney(pf.sueldo_meseta_proyectado), "proyectado", null, true) +
      kpiHtml("Margen promedio", fmtPct(pf.margen_promedio_pct), "de todo el portafolio");
    listaEl.innerHTML = pf.productos.map((p) => `
      <div class="producto-card">
        <div class="fila-top">
          <div class="nombre">${p.nombre}</div>
          <span class="badge ${tonoSemaforo(p.semaforo)}"><span class="dot"></span>${(p.semaforo || "").toUpperCase()}</span>
        </div>
        <div class="metricas">
          <span>Precio <b>${fmtMoney(p.precio)}</b></span>
          <span>Margen <b>${fmtPct(p.margen)}</b></span>
          <span>ROI <b>${fmtPct(p.roi)}</b></span>
          <span>Ventas <b>${fmtMoney(p.ventas_ingreso)}</b></span>
        </div>
      </div>`).join("");
  } catch (e) {
    kpisEl.innerHTML = "";
    listaEl.innerHTML = `<div class="card lista-vacia">No se pudo conectar con la API.</div>`;
  }
}

// ---------------------------------------------------------------- Ganancias
$all('input[name="modo_g"]').forEach((r) =>
  r.addEventListener("change", () => {
    const esInversion = $('input[name="modo_g"]:checked').value === "inversion";
    $("#g_inversion").disabled = !esInversion;
    $("#g_unidades").disabled = esInversion;
  })
);

$("#form-ganancias").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const esInversion = $('input[name="modo_g"]:checked').value === "inversion";
  const body = {
    inversion: esInversion ? Number($("#g_inversion").value) : null,
    unidades: esInversion ? null : Number($("#g_unidades").value),
    costo: Number($("#g_costo").value),
    flete: Number($("#g_flete").value),
    arancel_pct: Number($("#g_arancel").value),
    prep: Number($("#g_prep").value),
    precio: Number($("#g_precio").value) || null,
    techo_demanda: Number($("#g_techo").value),
  };
  const cont = $("#ganancias-resultado");
  cont.innerHTML = `<div class="card lista-vacia">Calculando…</div>`;
  try {
    const r = await apiPost("/ganancias", body);
    if (!r.ok) {
      cont.innerHTML = `<div class="card lista-vacia">${r.mensaje}</div>`;
      return;
    }
    const lo = r.lote, ue = r.unit_economics, re = r.reciclado;
    const etiquetas = {
      producto: "Producto (fabrica)", flete: "Flete", arancel: "Arancel", prep: "Prep",
      comision_amazon_referral: "Comision Amazon", fba_fee: "FBA fee", publicidad_acos: "Publicidad",
    };
    const filas = Object.entries(lo.costos)
      .map(([k, v]) => `<tr><td>${etiquetas[k] || k}</td><td>-${fmtMoney(v)}</td></tr>`)
      .join("");
    const tonoG = lo.ganancia_neta > 0 ? "good" : "bad";
    cont.innerHTML = `
      <div class="grid-kpi">
        ${kpiHtml("Ganancia neta", fmtMoney(lo.ganancia_neta), r.entrada, tonoG, true)}
        ${kpiHtml("ROI inversion", fmtPct(lo.roi_inversion_pct), fmtMoney(lo.inversion_usada), tonoG)}
        ${kpiHtml("Ganancia/unidad", fmtMoney(lo.ganancia_por_unidad), "precio " + fmtMoney(ue.precio_venta), tonoSemaforo(ue.semaforo))}
        ${kpiHtml("Sueldo en meseta", fmtMoney(re.sueldo_meseta_mensual), "reciclando capital 12m")}
      </div>
      <div class="card" style="margin-top:12px">
        <table class="tabla-costos">
          <tr class="ingreso"><td>Ingreso bruto</td><td>${fmtMoney(lo.ingreso_bruto)}</td></tr>
          ${filas}
          <tr class="total"><td>GANANCIA NETA</td><td>${fmtMoney(lo.ganancia_neta)}</td></tr>
        </table>
      </div>
      <p class="ayuda-config">${r.caveat}</p>`;
  } catch (e) {
    cont.innerHTML = `<div class="card lista-vacia">No se pudo calcular: revisa la conexion con la API.</div>`;
  }
});

// ---------------------------------------------------------------- Mercado
$("#form-mercado").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const keyword = $("#m_keyword").value.trim();
  const min = Number($("#m_min").value);
  const max = Number($("#m_max").value);
  const demo = $("#m_demo").checked;
  const cont = $("#mercado-resultado");
  cont.innerHTML = `<div class="card lista-vacia">Buscando productos estrella…</div>`;
  try {
    const q = `?keyword=${encodeURIComponent(keyword)}&precio_min=${min}&precio_max=${max}&demo=${demo}`;
    const r = await apiGet("/mercado/estrellas" + q);
    let html = "";
    if (!r.ok) {
      html += `<div class="card lista-vacia">${r.mensaje}</div>`;
      if (r.links_amazon && r.links_amazon.length) {
        html += r.links_amazon.map((l) =>
          `<a class="acceso" href="${l.url}" target="_blank" rel="noopener">${l.nombre}</a>`
        ).join("");
      }
    } else {
      html += `<div class="lista-productos">` + r.productos.map((p) => `
        <div class="producto-card">
          <div class="fila-top">
            <div class="nombre">${p.titulo}</div>
          </div>
          <div class="metricas">
            <span>Precio <b>${fmtMoney(p.precio)}</b></span>
            <span>Ventas <b>~${(p.ventas_estim || 0).toLocaleString("es-AR")}/mes</b></span>
            <span>Rating <b>${p.rating || "s/d"}</b></span>
            <span>Reseñas <b>${(p.resenas || 0).toLocaleString("es-AR")}</b></span>
          </div>
        </div>`).join("") + `</div>`;
    }
    cont.innerHTML = html;

    // Asesor de exito con el mismo keyword/rango, en paralelo
    try {
      const qe = `?keyword=${encodeURIComponent(keyword)}&precio=${max}&demo=${demo}`;
      const ev2 = await apiGet("/exito" + qe);
      const tono = tonoSemaforo({ VERDE: "verde", AMARILLO: "amarillo", ROJO: "rojo" }[ev2.veredicto]);
      cont.innerHTML += `
        <h2 class="titulo-seccion">Probabilidad de exito</h2>
        <div class="card">
          <span class="badge ${tono}"><span class="dot"></span>${ev2.veredicto} — ${ev2.probabilidad}/100</span>
          <p style="font-size:13px;color:var(--slate);margin-top:8px">${ev2.comentario}</p>
        </div>`;
    } catch (e) { /* opcional, no bloquea el resultado principal */ }
  } catch (e) {
    cont.innerHTML = `<div class="card lista-vacia">No se pudo conectar con la API.</div>`;
  }
});

// ---------------------------------------------------------------- Asistente
let chatHistorial = [];
function formatearMensaje(texto) {
  // Escapar HTML primero (nunca confiar en el texto del asistente como marcado),
  // despues renderizar SOLO **negrita** (lo unico que usa el glosario/asistente).
  const seguro = texto.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return seguro.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
}
function pintarChat() {
  const cont = $("#chat-historial");
  cont.innerHTML = chatHistorial.map((m) =>
    `<div class="msg ${m.role}">${formatearMensaje(m.content)}</div>`
  ).join("");
  cont.scrollTop = cont.scrollHeight;
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
  try {
    const r = await apiPost("/assistant", { pregunta: texto, historial: chatHistorial.slice(0, -2) });
    chatHistorial[chatHistorial.length - 1] = { role: "assistant", content: r.texto };
  } catch (e) {
    chatHistorial[chatHistorial.length - 1] = {
      role: "assistant",
      content: "No pude conectar con la API. Revisa la URL en Config.",
    };
  }
  pintarChat();
});

// ---------------------------------------------------------------- Config
$("#cfg-url").value = apiUrl();
$("#form-config").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const url = $("#cfg-url").value.trim().replace(/\/+$/, "");
  localStorage.setItem(LS_KEY_URL, url || "http://localhost:8000");
  const estadoEl = $("#config-estado");
  estadoEl.textContent = "Probando conexion…";
  const ok = await verificarEstado();
  estadoEl.textContent = ok ? "Conectado correctamente." : "No se pudo conectar. Revisa la IP/puerto y la red WiFi.";
  estadoEl.className = "card " + (ok ? "" : "lista-vacia");
  mostrarToast(ok ? "Conectado" : "Sin conexion");
});

// ---------------------------------------------------------------- Arranque
verificarEstado().then((ok) => { if (ok) cargarInicio(); });

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("service-worker.js").catch(() => {});
  });
}
