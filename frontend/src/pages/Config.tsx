import { useEffect, useState } from "react";
import { api, qs } from "../api/cliente";
import type { ConfigEstado } from "../api/tipos";
import { Alerta, Badge, Boton, Campo, Card, Seccion, Selector, Spinner } from "../components/ui";
import { useT } from "../i18n";

interface ResConexion { servicio?: string; ok?: boolean; mensaje?: string; [k: string]: unknown }

export function Config() {
  const t = useT();
  const [estado, setEstado] = useState<ConfigEstado | null>(null);
  const [claves, setClaves] = useState<Record<string, string>>({});
  const [proveedor, setProveedor] = useState("claude");
  const [asin, setAsin] = useState("");
  const [conexiones, setConexiones] = useState<ResConexion[] | null>(null);
  const [probando, setProbando] = useState(false);
  const [guardado, setGuardado] = useState("");

  const cargar = () => {
    api.get<ConfigEstado>("/api/config").then((d) => {
      setEstado(d);
      setProveedor(d.ia_provider || "claude");
    }).catch(() => {});
  };
  useEffect(cargar, []);

  const guardar = async () => {
    const pares: Record<string, string> = { IA_PROVIDER: proveedor };
    for (const [k, v] of Object.entries(claves)) if (v.trim()) pares[k] = v.trim();
    await api.post("/api/config", pares);
    setClaves({});
    setGuardado("ok");
    cargar();
    setTimeout(() => setGuardado(""), 2500);
  };

  const probar = async () => {
    setProbando(true);
    setConexiones(null);
    try {
      const d = await api.get<{ resultados: ResConexion[] }>(
        `/api/config/conexiones${qs({ asin })}`, 60000);
      setConexiones(d.resultados);
    } catch { setConexiones([{ ok: false, mensaje: t("comun.error") }]); }
    setProbando(false);
  };

  const campoClave = (nombre: string, etiqueta: string) => (
    <Campo
      key={nombre}
      label={`${etiqueta} ${estado?.claves?.[nombre] ? `(${estado.claves[nombre]})` : ""}`}
      type="password"
      value={claves[nombre] || ""}
      placeholder="pegar clave nueva…"
      onChange={(e) => setClaves({ ...claves, [nombre]: e.target.value })}
    />
  );

  return (
    <>
      <Seccion titulo={t("cfg_titulo")} sub={t("cfg_sub")} />

      <Card className="mb-5">
        <h3 className="font-bold text-[14px] mb-2 text-navy-deep">{t("cfg_test_btn")}</h3>
        <div className="flex gap-3 items-end flex-wrap">
          <Campo label="ASIN Keepa (opcional, gasta 1 token)" value={asin}
                 onChange={(e) => setAsin(e.target.value)} className="w-44" />
          <Boton onClick={() => void probar()} disabled={probando}>{t("cfg_test_btn")}</Boton>
        </div>
        {probando && <Spinner texto={t("comun.cargando")} />}
        {conexiones && (
          <div className="mt-3 flex flex-col gap-1.5">
            {conexiones.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-[13px]">
                <Badge texto={c.ok ? "OK" : "FALLO"} tono={c.ok ? "verde" : "rojo"} />
                <b>{String(c.servicio ?? "")}</b>
                <span className="text-muted">{String(c.mensaje ?? "")}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h3 className="font-bold text-[14px] mb-3 text-navy-deep">API keys</h3>
        <div className="grid md:grid-cols-2 gap-3">
          <Selector label="Proveedor de IA" value={proveedor}
                    onChange={(e) => setProveedor(e.target.value)}>
            <option value="claude">Claude / Anthropic — recomendada</option>
            <option value="openai">OpenAI (ChatGPT)</option>
            <option value="gemini">Google Gemini</option>
          </Selector>
          {campoClave("ANTHROPIC_API_KEY", "Clave Anthropic")}
          {campoClave("OPENAI_API_KEY", "Clave OpenAI")}
          {campoClave("GEMINI_API_KEY", "Clave Gemini")}
          {campoClave("KEEPA_API_KEY", "Clave Keepa")}
          {campoClave("SMTP_USER", "SMTP usuario")}
          {campoClave("SMTP_PASS", "SMTP contraseña")}
          {campoClave("ALERT_TO", "Email para alertas")}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Boton onClick={() => void guardar()}>{t("cfg_save_btn")}</Boton>
          {guardado && <Badge texto="Guardado en .env" tono="verde" />}
        </div>
        <Alerta tipo="info">
          Las claves se guardan LOCALMENTE en tu archivo .env — nunca salen de tu
          máquina ni van a ningún servidor nuestro.
        </Alerta>
      </Card>
    </>
  );
}
