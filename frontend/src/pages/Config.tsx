// © 2026 Martín Viera. Todos los derechos reservados.
import { useEffect, useState } from "react";
import { api, mensajeError, qs } from "../api/cliente";
import type { ConfigEstado, ProveedorIA } from "../api/tipos";
import { Alerta, Badge, Boton, Campo, Card, Seccion, Selector, Spinner } from "../components/ui";
import { useT } from "../i18n";

interface ResConexion { servicio?: string; ok?: boolean; mensaje?: string; [k: string]: unknown }
interface ResModelo { proveedor: string; nombre?: string; ok: boolean; mensaje: string }

export function Config() {
  const t = useT();
  const [estado, setEstado] = useState<ConfigEstado | null>(null);
  const [claves, setClaves] = useState<Record<string, string>>({});
  const [proveedor, setProveedor] = useState("claude");
  // Modelo elegido por proveedor (ANTHROPIC_MODEL, OPENAI_MODEL, ...). Es lo
  // que de verdad regula el gasto: un modelo chico cuesta una fraccion del
  // grande. Arranca con lo que ya tiene guardado el backend.
  const [modelos, setModelos] = useState<Record<string, string>>({});
  const [asin, setAsin] = useState("");
  const [conexiones, setConexiones] = useState<ResConexion[] | null>(null);
  const [probando, setProbando] = useState(false);
  const [actualizando, setActualizando] = useState(false);
  const [resModelos, setResModelos] = useState<ResModelo[] | null>(null);
  const [guardado, setGuardado] = useState("");
  const [error, setError] = useState("");

  const provs: ProveedorIA[] = estado?.proveedores_ia ?? [];
  const opciones: Record<string, string[]> = estado?.modelos_ia ?? {};

  const cargar = () => {
    api.get<ConfigEstado>("/api/config").then((d) => {
      setEstado(d);
      setProveedor(d.ia_provider || "claude");
      const m: Record<string, string> = {};
      for (const p of d.proveedores_ia ?? []) m[p.modelo_env] = p.modelo;
      setModelos(m);
    }).catch((e) => setError(mensajeError(e)));
  };
  useEffect(cargar, []);

  const guardar = async () => {
    const pares: Record<string, string> = { IA_PROVIDER: proveedor, ...modelos };
    for (const [k, v] of Object.entries(claves)) if (v.trim()) pares[k] = v.trim();
    try {
      await api.post("/api/config", pares);
      setClaves({});
      setError("");
      setGuardado("ok");
      cargar();
      setTimeout(() => setGuardado(""), 2500);
    } catch (e) { setError(mensajeError(e)); }
  };

  // Le pregunta a cada proveedor con clave cargada que modelos ofrece HOY, con
  // la clave del propio usuario: asi la lista sigue al dia sola cuando sacan
  // versiones nuevas, sin esperar una actualizacion del programa.
  const actualizarModelos = async () => {
    setActualizando(true);
    setResModelos(null);
    try {
      const d = await api.post<{ resultados: ResModelo[]; modelos: Record<string, string[]> }>(
        "/api/config/modelos", {}, 60000);
      setResModelos(d.resultados);
      setEstado((prev) => (prev ? { ...prev, modelos_ia: d.modelos } : prev));
      setError("");
    } catch (e) { setError(mensajeError(e)); }
    setActualizando(false);
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

  // El backend ya devuelve "(vacia)" con parentesis cuando no hay clave: no
  // hay que envolverlo otra vez o queda "Clave ((vacia))".
  const campoClave = (nombre: string, etiqueta: string) => {
    const actual = estado?.claves?.[nombre] || "";
    const sufijo = !actual ? "" : actual.startsWith("(") ? ` ${actual}` : ` (${actual})`;
    return (
    <Campo
      key={nombre}
      label={`${etiqueta}${sufijo}`}
      type="password"
      value={claves[nombre] || ""}
      placeholder={t("cfg.pegar_clave_nueva")}
      onChange={(e) => setClaves({ ...claves, [nombre]: e.target.value })}
    />
    );
  };

  return (
    <>
      <Seccion titulo={t("cfg_titulo")} sub={t("cfg_sub")} />

      <Card className="mb-5">
        <h3 className="font-bold text-[14px] mb-2 text-navy-deep">{t("cfg_test_btn")}</h3>
        <div className="flex gap-3 items-end flex-wrap">
          <Campo label={t("cfg.asin_keepa_opcional_gasta")} value={asin}
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

      <Card className="mb-5">
        <h3 className="font-bold text-[14px] mb-1 text-navy-deep">Fuentes de datos de mercado</h3>
        <p className="text-[12px] text-muted mb-3">
          El sistema funciona 100% gratis con el motor propio. Estas fuentes premium
          son OPCIONALES — si ya pagás alguna, la app la usa para potenciar los datos.
        </p>
        <div className="flex flex-col gap-2.5">
          <div className="flex items-start gap-3 border border-line rounded-xl p-3">
            <Badge texto={t("cfg.gratis")} tono="verde" />
            <div className="text-[13px]">
              <b>Motor propio + demanda nativa</b> — keywords y demanda relativa por el
              autocompletado de Amazon. Incluido, sin límite, US$0. Ya activo.
            </div>
          </div>
          <div className="flex items-start gap-3 border border-line rounded-xl p-3">
            <Badge texto="API" tono="navy" />
            <div className="text-[13px]">
              <b>Keepa (~19 €/mes)</b> — ventas estimadas reales (BSR→ventas) y precio
              histórico, automático. Pegá tu <b>KEEPA_API_KEY</b> abajo y se conecta solo.
              El plan API (~19 €) es más barato que el plan Data (~49 US$).
            </div>
          </div>
          <div className="flex items-start gap-3 border border-line rounded-xl p-3">
            <Badge texto="API" tono="navy" />
            <div className="text-[13px]">
              <b>Jungle Scout (API, BYOK)</b> — a diferencia de Helium 10, SÍ tiene API:
              volumen de búsqueda REAL de keywords, búsqueda de productos y ventas por
              ASIN, automático. Generá la clave en la app Jungle Scout (<b>Developer →
              Generate Key</b>) y pegá abajo el <b>nombre</b> y la <b>clave</b>.
            </div>
          </div>
          <div className="flex items-start gap-3 border border-line rounded-xl p-3">
            <Badge texto="CSV" tono="amarillo" />
            <div className="text-[13px]">
              <b>Helium 10 (Cerebro)</b> — volúmenes de búsqueda reales. Helium 10 no
              expone API para tu plan, así que el camino es exportar el CSV (botón
              «Export Data») y subirlo en la pestaña <b>Investigación</b>. La app también
              acepta el CSV de Jungle Scout (Keyword Scout) si preferís no usar su API.
            </div>
          </div>
        </div>
      </Card>

      <Card className="mb-5">
        <h3 className="font-bold text-[14px] mb-1 text-navy-deep">Inteligencia artificial (tu propia clave)</h3>
        <p className="text-[12px] text-muted mb-3">
          Pegá la clave del proveedor que ya pagues y elegí el modelo. <b>El modelo
          es lo que decide cuánto gastás</b>: uno chico (Haiku, gpt-4o-mini, Flash)
          cuesta una fracción de uno grande y para la mayoría de las preguntas
          alcanza. Tocá «Actualizar modelos» para que la lista traiga las últimas
          versiones que ofrece tu cuenta hoy.
        </p>

        <div className="flex gap-3 items-end flex-wrap mb-3">
          <Selector label={t("cfg.proveedor_ia")} value={proveedor}
                    onChange={(e) => setProveedor(e.target.value)}>
            {provs.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {p.nombre}{p.codigo === "claude" ? " — recomendada" : ""}
                {p.tiene_clave ? "" : " (sin clave)"}
              </option>
            ))}
          </Selector>
          <Boton tipo="fantasma" onClick={() => void actualizarModelos()} disabled={actualizando}>
            Actualizar modelos
          </Boton>
        </div>
        {actualizando && <Spinner texto="Preguntándole a cada proveedor…" />}
        {resModelos && (
          <div className="mb-3 flex flex-col gap-1.5">
            {resModelos.map((r) => (
              <div key={r.proveedor} className="flex items-center gap-2 text-[13px]">
                <Badge texto={r.ok ? "OK" : "—"} tono={r.ok ? "verde" : "navy"} />
                <b>{r.nombre ?? r.proveedor}</b>
                <span className="text-muted">{r.mensaje}</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-col gap-2.5">
          {provs.map((p) => (
            <div key={p.codigo} className="border border-line rounded-xl p-3">
              <div className="flex items-center gap-2 mb-2">
                <Badge texto={p.tiene_clave ? "conectado" : "sin clave"}
                       tono={p.tiene_clave ? "verde" : "navy"} />
                <b className="text-[13px] text-navy-deep">{p.nombre}</b>
              </div>
              <div className="grid md:grid-cols-2 gap-3">
                {campoClave(p.clave_env, "Clave")}
                <Selector label="Modelo (define el gasto)"
                          value={modelos[p.modelo_env] ?? p.modelo}
                          onChange={(e) => setModelos({ ...modelos, [p.modelo_env]: e.target.value })}>
                  {(opciones[p.codigo] ?? [p.modelo]).map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </Selector>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Boton onClick={() => void guardar()}>{t("cfg_save_btn")}</Boton>
          {guardado && <Badge texto={t("cfg.guardado_env")} tono="verde" />}
        </div>
        {error && <Alerta tipo="error">{error}</Alerta>}
      </Card>

      <Card>
        <h3 className="font-bold text-[14px] mb-3 text-navy-deep">Otras claves y alertas</h3>
        <div className="grid md:grid-cols-2 gap-3">
          {campoClave("KEEPA_API_KEY", "Clave Keepa")}
          {campoClave("JUNGLE_SCOUT_KEY_NAME", "Jungle Scout — nombre de clave")}
          {campoClave("JUNGLE_SCOUT_API_KEY", "Jungle Scout — clave API")}
          {campoClave("SMTP_USER", "SMTP usuario")}
          {campoClave("SMTP_PASS", "SMTP contraseña")}
          {campoClave("ALERT_TO", "Email para alertas")}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Boton onClick={() => void guardar()}>{t("cfg_save_btn")}</Boton>
          {guardado && <Badge texto={t("cfg.guardado_env")} tono="verde" />}
        </div>
        <Alerta tipo="info">
          Las claves se guardan LOCALMENTE en tu archivo .env — nunca salen de tu
          máquina ni van a ningún servidor nuestro.
        </Alerta>
      </Card>
    </>
  );
}
