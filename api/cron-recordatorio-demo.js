// © 2026 Martín Viera. Todos los derechos reservados.
// api/cron-recordatorio-demo.js — Corre una vez por dia (Vercel Cron, ver
// vercel.json) y manda un email a quien este en el dia 6 de su demo de 7
// dias (le queda 1 dia) y todavia no compro, para que no se le pase sin
// intentar convertir.
//
// Protegido por CRON_SECRET: Vercel manda ese secreto como Bearer token en
// cada invocacion automatica (lo agrega solo al configurar el cron job);
// asi nadie mas puede disparar el envio de emails pegandole a esta URL.
// Requiere ademas RESEND_API_KEY (api/_email.js) y el almacen (api/_demo.js)
// -- si falta cualquiera de los dos, no manda nada y no rompe el cron.
import { listaDemos, marcarRecordatorioEnviado, yaComproPrevio } from "./_demo.js";
import { enviarEmail, emailConfigurado } from "./_email.js";
import { almacenConfigurado } from "./_almacen.js";

// La demo dura 7 dias (168 h; ver DIAS_DEMO en core/licencia.py y
// mobile/js/licencia.js). La ventana apunta al ultimo dia: entre ~1,3 y ~0,3
// dias restantes, para que el mail diga "vence mañana" y siga siendo cierto.
const DIA_RECORDATORIO_DESDE_HORAS = 136; // ~dia 6: queda ~1 dia de demo
const DIA_RECORDATORIO_HASTA_HORAS = 160; // no seguir mandando si el cron se salteo un dia

function html(nombre) {
  const saludo = nombre ? `Hola ${nombre},` : "Hola,";
  return `
    <p>${saludo}</p>
    <p>Tu demo gratis de <b>MV FBA IA</b> vence <b>mañana</b> — todavía no vimos que hayas activado una licencia.</p>
    <p>Si te sirvió, podés comprarla acá y seguir sin cortes: <a href="https://amazon-fba-seven.vercel.app/#precios">amazon-fba-seven.vercel.app/#precios</a></p>
    <p>Si tenés dudas o algo no te convenció, respondé este email y te ayudamos.</p>
    <p>— MV FBA IA</p>
  `;
}

export default async function handler(req, res) {
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
