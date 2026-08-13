// © 2026 Martín Viera. Todos los derechos reservados.
// api/_email_creditos.js — Email post-compra con el saldo de creditos de IA:
// "tenes N creditos, asi se usan". Best-effort sobre api/_email.js (Resend):
// sin RESEND_API_KEY configurada es un no-op, y un fallo de envio NUNCA
// bloquea la emision de la licencia (el llamador lo envuelve en try/catch).
// Compartido por api/licencia.js (MercadoPago) y api/paypal-retorno.js para
// no duplicar el texto del email entre los dos flujos de pago.
import { enviarEmail, emailConfigurado } from "./_email.js";

export async function avisarCreditosPorEmail({ email, bonoNuevo, pack, saldo }) {
  if (!emailConfigurado() || !email || !(saldo > 0)) return null;
  const motivo = pack
    ? `Tu recarga de <b>${pack.creditos.toLocaleString("es-UY")} créditos</b> ya está acreditada.`
    : `Te regalamos <b>${saldo.toLocaleString("es-UY")} créditos de bienvenida</b> por activar tu licencia.`;
  const html = `
  <div style="font-family:system-ui,sans-serif;max-width:520px;margin:0 auto;color:#152a63">
    <h2 style="margin:18px 0 6px">Tus créditos de IA están listos</h2>
    <p>${motivo}</p>
    <p style="font-size:22px;font-weight:800;margin:14px 0">Saldo actual: ${Math.floor(saldo).toLocaleString("es-UY")} créditos</p>
    <p><b>¿Cómo se usan?</b> Abrí la pestaña <b>Asistente IA</b> (en la PC o en el celular)
       y preguntá sobre tus números, tu portafolio o tu estrategia — cada respuesta descuenta
       según lo que consuma, y los créditos <b>no vencen</b>.</p>
    <p>Si preferís usar tu propia clave de IA (Claude/OpenAI/Gemini), configurala en
       <b>Config</b> y no gastás créditos.</p>
    <p style="margin-top:18px"><a href="https://mvfbaia.com/#precios"
       style="color:#152a63">Recargar créditos cuando los necesites →</a></p>
    <p style="color:#8a94ad;font-size:12px;margin-top:22px">MV FBA IA — tu negocio en Amazon, bajo control.</p>
  </div>`;
  return enviarEmail({
    to: email,
    subject: bonoNuevo && !pack
      ? "Te regalamos créditos de IA — MV FBA IA"
      : "Tu recarga de créditos está acreditada — MV FBA IA",
    html,
  });
}
