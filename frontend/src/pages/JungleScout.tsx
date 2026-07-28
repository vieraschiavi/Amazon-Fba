import { useEffect, useState } from "react";
import { api, qs } from "../api/cliente";
import type {
  ConfigEstado, JsVolumenHistorico, JsShareOfVoice, JsVentasHistoricas, JsKeywordsAsin,
} from "../api/tipos";
import { GraficoLineas } from "../components/Graficos";
import { Alerta, Badge, Boton, Campo, CampoNumero, Card, FilaKpis, Kpi, Seccion, Spinner, Tabla, num, usd } from "../components/ui";
import { useT } from "../i18n";

// Insights avanzados de Jungle Scout (BYOK): los casos de uso que muestran las
// capturas de su API — estacionalidad y share of voice por keyword, y ventas +
// precio diarios por ASIN con las keywords que lo indexan. Sin clave conectada,
// no se inventa nada: se explica como conectarla.

export function JungleScout() {
  const t = useT();
  const [conectado, setConectado] = useState<boolean | null>(null);

  useEffect(() => {
    api.get<ConfigEstado>("/api/config")
      .then((c) => setConectado(c.jungle_scout === "conectado"))
      .catch(() => setConectado(false));
  }, []);

  return (
    <>
      <Seccion titulo={t("js_titulo")} sub={t("js_sub")} />
      {conectado === false && (
        <Alerta tipo="info">{t("js_sin_clave")}</Alerta>
      )}
      <ToolKeyword />
      <ToolAsin />
    </>
  );
}

function ToolKeyword() {
  const t = useT();
  const [kw, setKw] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [vol, setVol] = useState<JsVolumenHistorico | null>(null);
  const [sov, setSov] = useState<JsShareOfVoice | null>(null);

  const analizar = async () => {
    if (kw.trim().length < 3) return;
    setOcupado(true);
    const [v, s] = await Promise.all([
      api.get<JsVolumenHistorico>(`/api/jungle/volumen-historico${qs({ keyword: kw, meses: 12 })}`, 60000).catch(() => null),
      api.get<JsShareOfVoice>(`/api/jungle/sov${qs({ keyword: kw })}`, 60000).catch(() => null),
    ]);
    setVol(v); setSov(s);
    setOcupado(false);
  };

  const est = vol?.estacionalidad;
  return (
    <Card className="mt-4">
      <h3 className="font-bold text-[14px] text-navy-deep mb-1">{t("js_kw_titulo")}</h3>
      <p className="text-[12px] text-muted mb-3">{t("js_kw_sub")}</p>
      <div className="flex gap-3 items-end flex-wrap">
        <Campo label={t("js.keyword")} value={kw} onChange={(e) => setKw(e.target.value)}
               className="w-64" placeholder="garlic press" />
        <Boton onClick={() => void analizar()} disabled={ocupado}>{t("js_btn")}</Boton>
      </div>
      {ocupado && <Spinner texto={t("js.consultando_jungle_scout")} />}

      {vol && (vol.ok ? (
        <div className="mt-4">
          {est && (
            <FilaKpis>
              <Kpi label={t("js.mejor_mes")} valor={est.mejor_mes} sub={t("js.mayor_demanda_ano")} hero />
              <Kpi label={t("js.volumen_12m")} valor={num(est.volumen_total)} sub={t("js.busquedas_exactas")} />
              <Kpi label={t("js.prom_semanal")} valor={num(est.volumen_prom_semana)} />
              <Kpi label={t("js.pico_mes")} valor={num(est.volumen_mejor_mes)} tono="good" />
            </FilaKpis>
          )}
          <Card className="mt-2">
            <h4 className="font-bold text-[13px] text-navy-deep mb-2">{t("js.volumen_semanal_titulo")}</h4>
            <GraficoLineas datos={vol.serie} x="fecha"
                           series={[{ campo: "volumen", nombre: t("js.volumen_semanal_serie") }]} />
          </Card>
        </div>
      ) : (
        <Alerta tipo="warn">{vol.mensaje}</Alerta>
      ))}

      {sov && (sov.ok && sov.marcas.length > 0 ? (
        <Card className="mt-3">
          <div className="flex items-center gap-4 flex-wrap mb-2">
            <h4 className="font-bold text-[13px] text-navy-deep">{t("js.sov_titulo")}</h4>
            {sov.ppc_bid != null && <Badge texto={`PPC bid ${usd(sov.ppc_bid)}`} tono="navy" />}
            {sov.volumen_30d ? <Badge texto={`${num(sov.volumen_30d)} búsq./30d`} tono="verde" /> : null}
          </div>
          <Tabla
            cabeceras={[t("js.marca"), t("js.share_voice")]}
            filas={sov.marcas.map((m) => [m.marca, m.sov_pct != null ? `${m.sov_pct}%` : "s/d"])}
          />
        </Card>
      ) : sov && !sov.ok ? (
        <p className="text-[12px] text-muted mt-2">{sov.mensaje}</p>
      ) : null)}
    </Card>
  );
}

function ToolAsin() {
  const t = useT();
  const [asin, setAsin] = useState("");
  const [dias, setDias] = useState(30);
  const [ocupado, setOcupado] = useState(false);
  const [ventas, setVentas] = useState<JsVentasHistoricas | null>(null);
  const [kws, setKws] = useState<JsKeywordsAsin | null>(null);

  const analizar = async () => {
    if (!asin.trim()) return;
    setOcupado(true);
    const [v, k] = await Promise.all([
      api.get<JsVentasHistoricas>(`/api/jungle/ventas-historicas${qs({ asin, dias })}`, 60000).catch(() => null),
      api.get<JsKeywordsAsin>(`/api/jungle/keywords-asin${qs({ asin, max_n: 20 })}`, 60000).catch(() => null),
    ]);
    setVentas(v); setKws(k);
    setOcupado(false);
  };

  const r = ventas?.resumen;
  return (
    <Card className="mt-4">
      <h3 className="font-bold text-[14px] text-navy-deep mb-1">{t("js_asin_titulo")}</h3>
      <p className="text-[12px] text-muted mb-3">{t("js_asin_sub")}</p>
      <div className="flex gap-3 items-end flex-wrap">
        <Campo label="ASIN" value={asin} onChange={(e) => setAsin(e.target.value)}
               className="w-48" placeholder="B0..." />
        <CampoNumero label={t("js.dias")} value={dias} onValor={(v) => setDias(Math.max(7, Math.min(365, Math.round(v))))} className="w-24" />
        <Boton onClick={() => void analizar()} disabled={ocupado}>{t("js_btn")}</Boton>
      </div>
      {ocupado && <Spinner texto={t("js.consultando_jungle_scout")} />}

      {ventas && (ventas.ok ? (
        <div className="mt-4">
          {r && (
            <FilaKpis>
              <Kpi label={t("js.unidades")} valor={num(r.unidades_total)} sub={`${r.unidades_prom_dia}/día`} hero />
              <Kpi label={t("js.precio_prom")} valor={r.precio_prom != null ? usd(r.precio_prom) : "s/d"} />
              <Kpi label={t("js.precio_min")} valor={r.precio_min != null ? usd(r.precio_min) : "s/d"} tono="good" />
              <Kpi label={t("js.precio_max")} valor={r.precio_max != null ? usd(r.precio_max) : "s/d"} tono="warn" />
            </FilaKpis>
          )}
          <Card className="mt-2">
            <h4 className="font-bold text-[13px] text-navy-deep mb-2">{t("js.ventas_precio_titulo")}</h4>
            <GraficoLineas datos={ventas.serie} x="fecha" series={[
              { campo: "unidades", nombre: t("js.serie_unidades") },
              { campo: "precio", nombre: t("js.serie_precio") },
            ]} />
          </Card>
        </div>
      ) : (
        <Alerta tipo="warn">{ventas.mensaje}</Alerta>
      ))}

      {kws && (kws.ok && kws.keywords.length > 0 ? (
        <Card className="mt-3">
          <h4 className="font-bold text-[13px] text-navy-deep mb-2">{t("js.keywords_asin_titulo")}</h4>
          <Tabla
            cabeceras={[t("js.keyword"), t("js.volumen_mes"), t("js.competidores")]}
            filas={kws.keywords.map((k) => [k.keyword, num(k.volumen), num(k.competidores)])}
          />
        </Card>
      ) : kws && !kws.ok ? (
        <p className="text-[12px] text-muted mt-2">{kws.mensaje}</p>
      ) : null)}
    </Card>
  );
}
