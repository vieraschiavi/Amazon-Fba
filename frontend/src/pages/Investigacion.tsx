import { useEffect, useState } from "react";
import { api, qs } from "../api/cliente";
import type { KeywordMotor } from "../api/tipos";
import { Alerta, Badge, Boton, Campo, Card, FilaKpis, Kpi, Seccion, Selector, Spinner, Tabla, num } from "../components/ui";
import { useT } from "../i18n";
import { useApp } from "../stores/app";

interface ResMotor {
  ok: boolean; fuente: string; seed: string; requests: number;
  keywords: KeywordMotor[];
  nichos: { nicho: string; keywords: string[]; interes_max: number }[];
  mensaje: string; nota_honesta: string;
}
interface Listing { titulo: string; bullets: string[]; descripcion: string; _motor?: string }
interface ResCerebro {
  nicho: { ok: boolean; demanda_mensual: number; competidores: number;
           oportunidad_valor: number; score_nicho: number; veredicto: string;
           comentario: string };
  listing?: Listing;
}
interface Mkt { codigo: string; nombre: string }

export function Investigacion() {
  const t = useT();
  const modoDemo = useApp((s) => s.modoDemo);
  const [fuente, setFuente] = useState<"motor" | "csv">("motor");
  const [keyword, setKeyword] = useState("bamboo kitchen utensils");
  const [mkt, setMkt] = useState("US");
  const [mkts, setMkts] = useState<Mkt[]>([]);
  const [csvPath, setCsvPath] = useState("");
  const [csvNombre, setCsvNombre] = useState("");
  const [resMotor, setResMotor] = useState<ResMotor | null>(null);
  const [listing, setListing] = useState<Listing | null>(null);
  const [resCerebro, setResCerebro] = useState<ResCerebro | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    api.get<{ marketplaces: Mkt[] }>("/api/marketplaces")
      .then((d) => setMkts(d.marketplaces)).catch(() => {});
  }, []);

  const subirCsv = async (archivo: File) => {
    const d = await api.subir<{ ok: boolean; csv_path: string; nombre: string }>(
      "/api/archivos/cerebro", archivo);
    if (d.ok) { setCsvPath(d.csv_path); setCsvNombre(d.nombre); }
  };

  const investigar = async () => {
    setOcupado(true);
    setResMotor(null); setListing(null); setResCerebro(null);
    try {
      if (fuente === "motor") {
        const d = await api.post<{ motor: ResMotor; listing: Listing }>(
          "/api/investigacion/listing",
          { keyword, marketplace: mkt, demo: modoDemo }, 120000);
        setResMotor(d.motor);
        setListing(d.listing);
      } else {
        const d = await api.post<ResCerebro>("/api/investigacion", {
          keyword, marketplace: mkt, demo: modoDemo, csv_path: csvPath || null,
        }, 120000);
        setResCerebro(d);
        setListing(d.listing ?? null);
      }
    } catch { /* mantiene lo anterior */ }
    setOcupado(false);
  };

  return (
    <>
      <Seccion titulo={t("inv_titulo")} sub={t("inv_sub")} />
      <Card className="mb-4">
        <div className="flex gap-2 mb-3">
          {(["motor", "csv"] as const).map((f) => (
            <button key={f} onClick={() => setFuente(f)}
              className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-bold ${
                fuente === f ? "bg-navy text-white" : "bg-navy-soft text-navy"}`}>
              {f === "motor" ? "Motor propio (gratis)" : "CSV de Helium 10 Cerebro"}
            </button>
          ))}
        </div>
        <div className="flex gap-3 items-end flex-wrap">
          <Campo label={t("inv.nicho_keyword")} value={keyword}
                 onChange={(e) => setKeyword(e.target.value)} className="w-72" />
          <Selector label={t("inv.marketplace")} value={mkt} onChange={(e) => setMkt(e.target.value)}>
            {mkts.map((m) => <option key={m.codigo} value={m.codigo}>{m.codigo} — {m.nombre}</option>)}
          </Selector>
          {fuente === "csv" && (
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-bold uppercase text-muted">CSV Cerebro</span>
              <input type="file" accept=".csv" className="text-[12.5px]"
                     onChange={(e) => e.target.files?.[0] && void subirCsv(e.target.files[0])} />
              {csvNombre && <span className="text-[11px] text-green-ink">{csvNombre} ✓</span>}
            </label>
          )}
          <Boton onClick={() => void investigar()} disabled={ocupado}>{t("inv_btn")}</Boton>
        </div>
        {ocupado && <Spinner texto={t("comun.cargando")} />}
      </Card>

      {resMotor && (resMotor.ok ? (
        <>
          <FilaKpis>
            <Kpi label={t("inv.keywords_reales")} valor={num(resMotor.keywords.length)}
                 sub={`${resMotor.requests} consultas gratis`} hero />
            <Kpi label={t("inv.nichos_candidatos")} valor={num(resMotor.nichos.length)} sub={t("inv.modificador_long_tail")} />
            <Kpi label={t("inv.interes_maximo")}
                 valor={resMotor.keywords[0] ? `${resMotor.keywords[0].interes}/100` : "0"}
                 sub={t("inv.proxy_autocompletado")} />
            <Kpi label={t("inv.costo")} valor="US$0" sub={t("inv.apis_pagas")} tono="good" />
          </FilaKpis>
          <Alerta tipo="warn">{resMotor.nota_honesta}</Alerta>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <Card>
              <h3 className="font-bold text-[14px] mb-2 text-navy-deep">Top keywords</h3>
              <Tabla cabeceras={[t("inv.keyword"), t("inv.interes"), t("inv.rank"), t("inv.apar")]}
                filas={resMotor.keywords.slice(0, 20).map((k) => [
                  k.keyword, `${k.interes}/100`, k.mejor_rank, k.apariciones])} />
            </Card>
            <Card>
              <h3 className="font-bold text-[14px] mb-2 text-navy-deep">Nichos candidatos</h3>
              <Tabla cabeceras={[t("inv.nicho"), t("inv.keywords"), t("inv.interes_max")]}
                filas={resMotor.nichos.slice(0, 12).map((n) => [
                  n.nicho, n.keywords.length, n.interes_max])} />
            </Card>
          </div>
        </>
      ) : <Alerta tipo="info">{resMotor.mensaje}</Alerta>)}

      {resCerebro && resCerebro.nicho.ok && (
        <>
          <FilaKpis>
            <Kpi label={t("inv.demanda_mes")} valor={num(resCerebro.nicho.demanda_mensual)} sub={t("inv.unidades_estimadas")} />
            <Kpi label={t("inv.competidores")} valor={num(resCerebro.nicho.competidores)} sub={t("inv.menos_es_mejor")} />
            <Kpi label={t("inv.oportunidad")} valor={`${resCerebro.nicho.oportunidad_valor}/100`} sub={t("inv.hueco_valor")} />
            <Kpi label={t("inv.score_nicho")} valor={`${resCerebro.nicho.score_nicho}/100`} sub={t("inv.ganabilidad")} hero />
          </FilaKpis>
          <div className="mb-4 flex items-center gap-3">
            <Badge texto={resCerebro.nicho.veredicto} tono={resCerebro.nicho.veredicto.toLowerCase()} />
            <span className="text-[13px] text-muted">{resCerebro.nicho.comentario}</span>
          </div>
        </>
      )}
      {resCerebro && !resCerebro.nicho.ok && (
        <Alerta tipo="info">{(resCerebro.nicho as unknown as { comentario: string }).comentario}</Alerta>
      )}

      {listing && (
        <Card>
          <h3 className="font-bold text-[14px] mb-2 text-navy-deep">Listing sugerido</h3>
          <p className="text-[13.5px] font-semibold mb-2">{listing.titulo}</p>
          <ol className="list-decimal ml-5 text-[13px] flex flex-col gap-1 mb-3">
            {listing.bullets.map((b, i) => <li key={i}>{b}</li>)}
          </ol>
          <p className="text-[13px] text-muted whitespace-pre-wrap">{listing.descripcion}</p>
          {listing._motor && <p className="text-[11px] text-muted mt-2">Motor: {listing._motor}</p>}
        </Card>
      )}
    </>
  );
}
