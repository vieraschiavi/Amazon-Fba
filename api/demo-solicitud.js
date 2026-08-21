// © 2026 Martín Viera. Todos los derechos reservados.
// api/demo-solicitud.js — Recibe el pedido de demo 1:1 y lo manda por mail al
// dueño. Reemplaza a la demo abierta: antes /api/descarga?demo=1 entregaba el
// .exe y el .zip COMPLETOS a cualquiera, sin pago y sin dejar rastro de quien
// se los llevaba. Ahora la demo se pide, se agenda y se muestra en vivo.
//
// QUE RESUELVE, ADEMAS DE NO REGALAR EL PRODUCTO:
//   - deja rastro: quien pidio acceso, con que mail, de que empresa y pais;
//   - filtra curiosidad de la competencia de un prospecto real;
//   - la reunion sirve para vender mientras se muestra.
//
// El visitante NO recibe ningun artefacto por esta via: el endpoint solo
// notifica. Entregar algo es una decision manual posterior.
import { aplicarCors, clienteValido, limitarPorIp } from "./_seguridad.js";
import { enviarEmail, escaparHtml, emailConfigurado } from "./_email.js";

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

  const fila = (etiqueta, valor) =>
    `<tr><td style="padding:6px 12px 6px 0;color:#64748b">${etiqueta}</td>` +
    `<td style="padding:6px 0;font-weight:700">${escaparHtml(valor)}</td></tr>`;

  const html = `
  <div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;color:#152a63">
    <h2 style="margin:18px 0 6px">Pedido de demo 1:1</h2>
    <p style="color:#475569;margin:0 0 14px">Alguien pidió ver el programa. Los datos los cargó
       el visitante, así que tomalos como declarados, no verificados.</p>
    <table style="font-size:14px;border-collapse:collapse">
      ${fila("Nombre", datos.nombre)}
      ${fila("Empresa", datos.empresa)}
      ${fila("País", datos.pais)}
      ${fila("Email", datos.email)}
    </table>
    <p style="margin:18px 0 0"><a href="mailto:${encodeURIComponent(datos.email)}"
       style="background:#152a63;color:#fff;padding:10px 18px;border-radius:9px;
              text-decoration:none;font-weight:700">Responder y agendar</a></p>
  </div>`;

  try {
    await enviarEmail({
      to: DESTINO,
      subject: `Demo 1:1 — ${datos.nombre} (${datos.empresa}, ${datos.pais})`,
      html,
    });
  } catch (e) {
    // El detalle del proveedor no se expone: solo diria si la clave es valida.
    return res.status(502).json({ error: "envio_fallido" });
  }
  return res.status(200).json({ ok: true });
}
