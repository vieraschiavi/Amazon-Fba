// © 2026 Martín Viera. Todos los derechos reservados.
// api/demo.js — TODO lo de la demo, en UNA sola funcion serverless.
//
// POR QUE ESTAN JUNTAS DOS COSAS QUE PARECEN DISTINTAS
// ----------------------------------------------------
// El plan Hobby de Vercel permite 12 Serverless Functions por deployment, y
// el proyecto ya estaba en el limite. Al agregar el formulario de demo 1:1
// pasamos a 13 y NINGUN deploy volvio a salir -- ni el de produccion. No es
// un error de codigo: el build entero se rechaza.
//
// Asi que las dos piezas de "demo" comparten funcion. No es un invento nuevo:
// vercel.json ya usaba el mismo criterio con /api/demo-registro -> /api/creditos.
//
//   POST  /api/demo              pedido de demo 1:1 (formulario de la landing)
//                                -> manda el mail al dueño. Publico, con tope
//                                   por IP.
//   GET   /api/demo              recordatorio diario "tu demo vence mañana"
//                                (Vercel Cron, ver vercel.json). Protegido con
//                                   CRON_SECRET por Bearer.
//
// Los dos caminos son independientes: se separan por metodo antes de tocar
// nada. El GET nunca es alcanzable sin el secreto, y el POST nunca lee el
// almacen de demos.

import { listaDemos, marcarRecordatorioEnviado, yaComproPrevio } from "./_demo.js";
import { almacenConfigurado } from "./_almacen.js";
import { aplicarCors, clienteValido, limitarPorIp } from "./_seguridad.js";
import { enviarEmail, emailConfigurado, escaparHtml } from "./_email.js";

const DIA_RECORDATORIO_DESDE_HORAS = 136; // ~dia 6: queda ~1 dia de demo
const DIA_RECORDATORIO_HASTA_HORAS = 160; // no seguir mandando si el cron se salteo un dia

function html(nombre) {
  // nombre viene de POST /api/creditos (registro de demo): CUALQUIERA puede
  // registrar una demo con el email de OTRA persona y un "nombre" que en
  // realidad es HTML/links (ver escaparHtml en _email.js) -- un dia despues,
  // el cron manda ese HTML dentro de un mail real, firmado por el dominio
  // legitimo. Se escapa antes de interpolar.
  const nombreSeguro = escaparHtml(nombre);
  const saludo = nombreSeguro ? `Hola ${nombreSeguro},` : "Hola,";
  return `
    <p>${saludo}</p>
    <p>Tu demo gratis de <b>MV FBA IA</b> vence <b>mañana</b> — todavía no vimos que hayas activado una licencia.</p>
    <p>Si te sirvió, podés comprarla acá y seguir sin cortes: <a href="https://amazon-fba-seven.vercel.app/#precios">amazon-fba-seven.vercel.app/#precios</a></p>
    <p>Si tenés dudas o algo no te convenció, respondé este email y te ayudamos.</p>
    <p>— MV FBA IA</p>
  `;
}

const DESTINO = "vieraschiavi@gmail.com";

// Topes de largo: sin esto, un bot puede mandar 2 MB de basura en "empresa" y
// eso viaja al HTML de un mail que sale FIRMADO por el dominio real.
const CAMPOS = {
  nombre:  { etiqueta: "Nombre completo", min: 2, max: 80 },
  empresa: { etiqueta: "Empresa",         min: 2, max: 80 },
  pais:    { etiqueta: "País",            min: 2, max: 56 },
  email:   { etiqueta: "Email",           min: 5, max: 120 },
};

export default async function handler(req, res) {
  // ---------------------------------------------------------------------
  // POST -> pedido de demo 1:1 (lo llama el formulario de la landing)
  // ---------------------------------------------------------------------
  if (req.method === "POST" || req.method === "OPTIONS") {

  aplicarCors(req, res, "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "method" });
  if (!clienteValido(req)) return res.status(403).json({ error: "cliente_no_reconocido" });

  // 5 por hora y por IP: un pedido de demo es un acto deliberado, no algo que
  // se repita. Sin tope, este endpoint es un formulario de spam que manda
  // mails firmados con la reputacion del dominio propio.
  const limite = await limitarPorIp(req, "demo", 5, 3600);
  if (!limite.permitido) return res.status(429).json({ error: "demasiados_intentos" });

  const cuerpo = req.body && typeof req.body === "object" ? req.body : {};
  const datos = {};
  for (const [clave, regla] of Object.entries(CAMPOS)) {
    const v = String(cuerpo[clave] ?? "").trim();
    if (v.length < regla.min || v.length > regla.max) {
      return res.status(400).json({ error: "campo_invalido", campo: clave });
    }
    datos[clave] = v;
  }
  // Validacion deliberadamente laxa: alcanza para atajar el error de tipeo.
  // La direccion se verifica de verdad cuando se responde el mail.
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(datos.email)) {
    return res.status(400).json({ error: "campo_invalido", campo: "email" });
  }

  // Falla honesta: sin Resend configurado se avisa, no se finge que se envio.
  // El formulario muestra el mail de contacto como salida alternativa.
  if (!emailConfigurado()) return res.status(503).json({ error: "email_no_configurado" });

  // fila() recibe el valor YA escapado, a proposito: asi la proteccion se ve
  // en el punto de interpolacion y no hay que abrir el helper para saber si
  // es segura. Es lo que fija test/verificar_escapar_email_demo.mjs.
  const fila = (etiqueta, valorSeguro) =>
    `<tr><td style="padding:6px 12px 6px 0;color:#64748b">${etiqueta}</td>` +
    `<td style="padding:6px 0;font-weight:700">${valorSeguro}</td></tr>`;

  // El ASUNTO no es HTML: escaparHtml ahi solo dejaria "&amp;" a la vista. El
  // riesgo real en una cabecera es el salto de linea (inyeccion de
  // cabeceras), asi que se aplana a una sola linea y se acota el largo.
  const unaLinea = (v) => String(v ?? "").replace(/[\r\n]+/g, " ").trim().slice(0, 70);

  const html = `
  <div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;color:#152a63">
    <h2 style="margin:18px 0 6px">Pedido de demo 1:1</h2>
    <p style="color:#475569;margin:0 0 14px">Alguien pidió ver el programa. Los datos los cargó
       el visitante, así que tomalos como declarados, no verificados.</p>
    <table style="font-size:14px;border-collapse:collapse">
      ${fila("Nombre", escaparHtml(datos.nombre))}
      ${fila("Empresa", escaparHtml(datos.empresa))}
      ${fila("País", escaparHtml(datos.pais))}
      ${fila("Email", escaparHtml(datos.email))}
    </table>
    <p style="margin:18px 0 0"><a href="mailto:${encodeURIComponent(datos.email)}"
       style="background:#152a63;color:#fff;padding:10px 18px;border-radius:9px;
              text-decoration:none;font-weight:700">Responder y agendar</a></p>
  </div>`;

  try {
    await enviarEmail({
      to: DESTINO,
      subject: `Demo 1:1 — ${unaLinea(datos.nombre)} (${unaLinea(datos.empresa)}, ${unaLinea(datos.pais)})`,
      html,
    });
  } catch (e) {
    // El detalle del proveedor no se expone: solo diria si la clave es valida.
    return res.status(502).json({ error: "envio_fallido" });
  }
  return res.status(200).json({ ok: true });
  }

  // ---------------------------------------------------------------------
  // GET -> cron diario del recordatorio de demo
  // ---------------------------------------------------------------------

  const secreto = process.env.CRON_SECRET;
  if (!secreto || req.headers.authorization !== `Bearer ${secreto}`) {
    return res.status(401).json({ error: "no_autorizado" });
  }
  if (!almacenConfigurado() || !emailConfigurado()) {
    return res.status(200).json({ ok: true, enviados: 0, motivo: "almacen_o_email_no_configurado" });
  }

  const demos = await listaDemos(2000);
  const ahora = Date.now();
  let enviados = 0;
  let saltados = 0;

  for (const d of demos) {
    if (d.recordatorioEnviado) continue;
    const inicio = new Date(d.fechaRegistro).getTime();
    if (Number.isNaN(inicio)) continue;
    const horas = (ahora - inicio) / 3600000;
    if (horas < DIA_RECORDATORIO_DESDE_HORAS || horas > DIA_RECORDATORIO_HASTA_HORAS) continue;

    if (await yaComproPrevio(d.email)) {
      await marcarRecordatorioEnviado(d.email); // ya convirtio: no hace falta recordarle, no volver a evaluarlo
      saltados++;
      continue;
    }

    try {
      await enviarEmail({
        to: d.email,
        subject: "Tu demo de MV FBA IA vence mañana",
        html: html(d.nombre),
      });
      await marcarRecordatorioEnviado(d.email);
      enviados++;
    } catch (e) {
      // no marcar como enviado si Resend fallo: se reintenta en la proxima corrida del cron
    }
  }

  return res.status(200).json({ ok: true, enviados, saltados, evaluados: demos.length });
}
