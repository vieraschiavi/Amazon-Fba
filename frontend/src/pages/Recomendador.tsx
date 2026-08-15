// © 2026 Martín Viera. Todos los derechos reservados.
import { useEffect, useState } from "react";
import { api, mensajeError } from "../api/cliente";
import type { Oportunidad } from "../api/tipos";
import { ComparadorNichos } from "../components/ComparadorNichos";
import { Alerta, Badge, Boton, CampoNumero, Card, FilaKpis, Kpi, Seccion, Selector, Spinner, Tabla, usd, num } from "../components/ui";
import { useT } from "../i18n";
import { useApp } from "../stores/app";

interface Resultado {
  ok: boolean; fuente: string; oportunidades: Oportunidad[];
  seeds_usadas: string[]; n_candidatos_evaluados: number;
  precio_min: number; precio_max: number; marketplace: string;
  mensaje: string; nota_honesta: string;
  narrativa_ia?: { texto: string; modo: string };
}
interface Mkt { codigo: string; nombre: string }

export function Recomendador() {
  const t = useT();
  const modoDemo = useApp((s) => s.modoDemo);
  const [min, setMin] = useState(15);
  const [max, setMax] = useState(45);
  const [mkt, setMkt] = useState("US");
  const [mkts, setMkts] = useState<Mkt[]>([]);
  const [res, setRes] = useState<Resultado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<{ marketplaces: Mkt[] }>("/api/marketplaces")
      .then((d) => setMkts(d.marketplaces)).catch(() => {});
  }, []);

  const escanear = async () => {
    setOcupado(true);
    try {
      const d = await api.post<Resultado>("/api/recomendador/escanear", {
        precio_min: min, precio_max: max, marketplace: mkt, demo: modoDemo,
      }, 180000);
      setRes(d); setError("");
    } catch (e) { setError(mensajeError(e)); }
    setOcupado(false);
  };

  return (
    <>
      <Seccion titulo={t("rec_titulo")} sub={t("rec_sub")} />
      <Card className="mb-4">
        <div className="flex gap-3 items-end flex-wrap">
          <CampoNumero label={t("rec.precio_min")} value={min} onValor={setMin} className="w-28" />
          <CampoNumero label={t("rec.precio_max")} value={max} onValor={setMax} className="w-28" />
          <Selector label={t("rec.marketplace")} value={mkt} onChange={(e) => setMkt(e.target.value)}>
            {mkts.map((m) => <option key={m.codigo} value={m.codigo}>{m.codigo} — {m.nombre}</option>)}
          </Selector>
          <Boton onClick={() => void escanear()} disabled={ocupado}>{t("rec_btn")}</Boton>
        </div>
        {ocupado && <Spinner texto={t("rec.escaneando_categorias_motor_propio")} />}
        {error && <Alerta tipo="error">{error}</Alerta>}
      </Card>

      {res && (res.ok ? (
        <>
          <FilaKpis>
            <Kpi label={t("rec.oportunidades")} valor={num(res.oportunidades.length)}
                 sub={`de ${res.n_candidatos_evaluados} candidatos`} hero />
            <Kpi label={t("rec.mejor_potencial")}
                 valor={res.oportunidades[0] ? `${res.oportunidades[0].potencial}/100` : "—"}
                 sub={res.oportunidades[0]?.nicho.slice(0, 26)} />
            <Kpi label={t("rec.rango_precio")} valor={`${usd(res.precio_min, 0)}–${usd(res.precio_max, 0)}`}
                 sub={res.marketplace} />
            <Kpi label={t("rec.costo")} valor="US$0"
                 sub={res.fuente.includes("Keepa") ? "+ Keepa conectado" : "sin APIs pagas"} tono="good" />
          </FilaKpis>
          <Alerta tipo="warn">{res.nota_honesta}</Alerta>
          {res.narrativa_ia && (
            <Card>
              <h3 className="font-bold text-[14px] text-navy-deep mb-2">{t("rec.narrativa_titulo")}</h3>
              <Alerta tipo="info">
                <span className="whitespace-pre-wrap">{res.narrativa_ia.texto}</span>
              </Alerta>
            </Card>
          )}
          <Card>
            <Tabla
              cabeceras={[t("rec.nicho"), t("rec.potencial"), t("rec.veredicto"), t("rec.interes"), t("rec.competidores"), t("rec.ventas_mes"), t("rec.precio_med")]}
              filas={res.oportunidades.map((o) => [
                o.nicho, `${o.potencial}/100`,
                <Badge key="v" texto={o.veredicto} tono={o.veredicto.toLowerCase()} />,
                o.interes_proxy,
                o.n_competidores ?? "s/d",
                o.ventas_estim_total ? num(o.ventas_estim_total) : "s/d",
                o.precio_mediana ? usd(o.precio_mediana) : "s/d",
              ])}
            />
            <p className="text-muted text-[12px] mt-2">
              Copiá el nicho que te interese y pegalo en Investigación (keywords/listing)
              o Mercado (competidores y éxito) para profundizar.
            </p>
          </Card>
        </>
      ) : (
        <Alerta tipo="info">{res.mensaje}</Alerta>
      ))}

      {/* Comparador cara a cara: precargado con los mejores nichos del escaneo */}
      <Card className="mt-4">
        <h3 className="font-bold text-[14px] text-navy-deep">{t("rec.comparar_titulo")}</h3>
        <p className="text-[12px] text-muted mb-3">
          Medí la demanda relativa de varios candidatos lado a lado — los del escaneo
          vienen precargados, o escribí los tuyos.
        </p>
        <ComparadorNichos
          key={res?.ok ? res.oportunidades.map((o) => o.nicho).join("|") : "vacio"}
          inicial={res?.ok
            ? res.oportunidades.slice(0, 4).map((o) => o.nicho).join(", ")
            : ""}
        />
      </Card>
    </>
  );
}
