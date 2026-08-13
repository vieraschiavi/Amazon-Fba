// © 2026 Martín Viera. Todos los derechos reservados.
// Gate de demo/licencia. La verdad vive SERVER-SIDE (SQLite via
// /api/licencia): el countdown usa dias_restantes del server, nunca el reloj
// del cliente, y cerrar/abrir la app no resetea nada.
import { FormEvent, useState } from "react";
import { useApp } from "../stores/app";
import { useT, IDIOMAS, Idioma } from "../i18n";
import { api } from "../api/cliente";
import type { EstadoLicencia } from "../api/tipos";
import { Alerta, Boton, Campo, Selector } from "../components/ui";

const EMAIL_SOPORTE = "vieraschiavi@gmail.com";

export function GateDemo({ estado }: { estado: EstadoLicencia }) {
  const t = useT();
  const { idioma, fijarIdioma, refrescarLicencia } = useApp();
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState(estado.email || "");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const registrar = async (e: FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) { setError(t("gate.falta_email")); return; }
    setOcupado(true);
    try {
      await api.post("/api/licencia/registro", { nombre, email });
      await refrescarLicencia();
    } catch { setError(t("comun.error")); }
    setOcupado(false);
  };

  const activar = async (e: FormEvent) => {
    e.preventDefault();
    setOcupado(true); setError("");
    try {
      const r = await api.post<{ ok: boolean; mensaje: string }>(
        "/api/licencia/activar", { email, clave });
      if (r.ok) await refrescarLicencia();
      else setError(t(r.mensaje === "sin_conexion" ? "gate.sin_conexion" : "gate.clave_invalida"));
    } catch { setError(t("comun.error")); }
    setOcupado(false);
  };

  const mailto = `mailto:${EMAIL_SOPORTE}?subject=${encodeURIComponent(
    "Compra de licencia MV FBA IA")}&body=${encodeURIComponent(
    `Quiero comprar la licencia. Email de registro: ${email}`)}`;

  return (
    <div className="h-full flex items-center justify-center bg-navy-deep">
      <div className="w-full max-w-md bg-card rounded-2xl p-8 shadow-2xl mx-4">
        <div className="flex justify-end mb-2">
          <Selector value={idioma} onChange={(e) => fijarIdioma(e.target.value as Idioma)}>
            {IDIOMAS.map((i) => <option key={i.codigo} value={i.codigo}>{i.nombre}</option>)}
          </Selector>
        </div>
        <div className="flex items-center gap-3 mb-4">
          <img src="./icon.png" alt="" className="w-12 h-12 rounded-xl" />
          <h1 className="text-[20px] font-extrabold text-navy-deep">
            {estado.registrado ? t("gate.vencida") : t("gate.bienvenida")}
          </h1>
        </div>

        {!estado.registrado ? (
          <>
            <Alerta tipo="info">{t("gate.sub")}</Alerta>
            <form onSubmit={(e) => void registrar(e)} className="flex flex-col gap-3">
              <Campo label={t("gate.nombre")} value={nombre}
                     onChange={(e) => setNombre(e.target.value)} />
              <Campo label={t("gate.email")} type="email" value={email}
                     onChange={(e) => setEmail(e.target.value)} />
              <Boton disabled={ocupado} className="mt-1">{t("gate.empezar")}</Boton>
            </form>
          </>
        ) : (
          <>
            <Alerta tipo="warn">{t("gate.vencida_sub")}</Alerta>
            <form onSubmit={(e) => void activar(e)} className="flex flex-col gap-3">
              <Campo label={t("gate.email")} type="email" value={email}
                     onChange={(e) => setEmail(e.target.value)} />
              <Campo label={t("gate.clave")} value={clave}
                     onChange={(e) => setClave(e.target.value)} />
              <Boton disabled={ocupado} className="mt-1">{t("gate.activar")}</Boton>
            </form>
            <a href={mailto} className="block text-center text-[13px] text-navy underline mt-4">
              {t("gate.comprar")}
            </a>
          </>
        )}
        {error && <Alerta tipo="error">{error}</Alerta>}
      </div>
    </div>
  );
}
