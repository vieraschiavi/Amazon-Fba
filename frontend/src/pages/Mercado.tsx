import { useState } from "react";
import { api, qs } from "../api/cliente";
import type { ProductoEstrella } from "../api/tipos";
import { ComparadorNichos } from "../components/ComparadorNichos";
import { Alerta, Badge, Boton, Campo, CampoNumero, Card, FilaKpis, Kpi, Seccion, Spinner, Tabla, usd, num, pct } from "../components/ui";
import { useT } from "../i18n";
import { useApp } from "../stores/app";

interface Competencia {
  ok: boolean; n_competidores: number; rating_promedio: number | null;
  resenas_mediana: number; precio_min: number; precio_max: number;
  precio_mediana: number; ventas_estim_total: number;
}
interface ResMercado {
  ok: boolean; fuente: string; productos: ProductoEstrella[];
  links_amazon: { nombre: string; url: string }[];
  competencia: Competencia; mensaje: string;
  proveedores: { plataforma: string; prioridad: number; url: string; nota: string }[];
}
interface Evaluacion {
  probabilidad: number; veredicto: string; comentario: string;
  factores: Record<string, { valor: number; detalle: string }>;
  recomendaciones: string[]; caveat: string;
}
interface Demanda {
  ok: boolean; keyword: string; amplitud: number; demanda_score: number;
  nivel: string; n_nichos: number; requests: number; nota_honesta: string;
  mensaje?: string;
}

export function Mercado() {
  const t = useT();
  const modoDemo = useApp((s) => s.modoDemo);
  const [kw, setKw] = useState("bamboo kitchen utensils");
  const [min, setMin] = useState(10);
  const [max, setMax] = useState(50);
  const [res, setRes] = useState<ResMercado | null>(null);
  const [precioObj, setPrecioObj] = useState(24);
  const [margen, setMargen] = useState(0);
  const [ev, setEv] = useState<{ evaluacion: Evaluacion; narrativa?: { texto: string; modo: string } } | null>(null);
  const [demanda, setDemanda] = useState<Demanda | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [midiendoDemanda, setMidiendoDemanda] = useState(false);
  const [evaluando, setEvaluando] = useState(false);

  const explorar = async () => {
    setOcupado(true); setEv(null);
    try {
      const d = await api.get<ResMercado>(
        `/mercado/estrellas${qs({ keyword: kw, precio_min: min, precio_max: max, demo: modoDemo })}`,
        90000);
      setRes(d);
    } catch { /* mantiene */ }
    setOcupado(false);
  };

  const medirDemanda = async () => {
    setMidiendoDemanda(true); setDemanda(null);
    try {
      const d = await api.get<Demanda>(
        `/api/demanda${qs({ keyword: kw, demo: modoDemo })}`, 90000);
      setDemanda(d);
    } catch { /* mantiene */ }
    setMidiendoDemanda(false);
  };


  const evaluar = async () => {
    setEvaluando(true);
    try {
      const d = await api.get<{ evaluacion: Evaluacion; narrativa?: { texto: string; modo: string } }>(
        `/api/exito${qs({ keyword: kw, precio: precioObj, margen_pct: margen || undefined, demo: modoDemo, con_narrativa: true })}`,
        120000);
      setEv(d);
    } catch { /* mantiene */ }
    setEvaluando(false);
  };

  const comp = res?.competencia;
  return (
    <>
      <Seccion titulo={t("mk_titulo")} sub={t("mk_sub")} />
      <Card className="mb-4">
        <div className="flex gap-3 items-end flex-wrap">
          <Campo label="Producto / keyword" value={kw} onChange={(e) => setKw(e.target.value)} className="w-72" />
          <CampoNumero label="Precio min" value={min} onValor={setMin} className="w-24" />
          <CampoNumero label="Precio max" value={max} onValor={setMax} className="w-24" />
          <Boton onClick={() => void explorar()} disabled={ocupado}>{t("mk_btn")}</Boton>
        </div>
        {ocupado && <Spinner texto={t("comun.cargando")} />}
      </Card>

      {/* Demanda GRATIS sin Keepa — señal relativa por autocompletado de Amazon */}
      <Card className="mb-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h3 className="font-bold text-[14px] text-navy-deep">Demanda del nicho — gratis, sin Keepa</h3>
            <p className="text-[12px] text-muted">Señal relativa por amplitud de autocompletado de Amazon (US$0)</p>
          </div>
          <Boton tipo="fantasma" onClick={() => void medirDemanda()} disabled={midiendoDemanda}>
            Medir demanda
          </Boton>
        </div>
        {midiendoDemanda && <Spinner texto="Consultando el autocompletado de Amazon (gratis)…" />}
        {demanda && (demanda.ok ? (
          <div className="mt-3">
            <FilaKpis>
              <Kpi label="Demanda relativa" valor={`${demanda.demanda_score}/100`}
                   sub={demanda.nivel} hero
                   tono={demanda.demanda_score >= 65 ? "good" : demanda.demanda_score >= 40 ? "warn" : "bad"} />
              <Kpi label="Amplitud long-tail" valor={num(demanda.amplitud)}
                   sub="variantes reales que busca la gente" />
              <Kpi label="Nichos candidatos" valor={num(demanda.n_nichos)} sub="sub-nichos detectados" />
              <Kpi label="Costo" valor="US$0" sub={`${demanda.requests} consultas gratis`} tono="good" />
            </FilaKpis>
            <p className="text-[11.5px] text-muted mt-1">{demanda.nota_honesta}</p>
          </div>
        ) : (
          <Alerta tipo="info">{demanda.mensaje || "Sin señal de demanda para ese término."}</Alerta>
        ))}

        {/* Comparador de nichos: metés varios y los rankea por demanda, gratis */}
        <div className="mt-4 pt-4 border-t border-line">
          <h4 className="font-bold text-[13px] text-navy-deep mb-2">
            Comparar varios nichos (gratis)
          </h4>
          <ComparadorNichos />
        </div>
      </Card>

      {res && (res.ok ? (
        <>
          {comp?.ok && (
            <FilaKpis>
              <Kpi label="Competidores" valor={num(comp.n_competidores)}
                   sub={`${usd(comp.precio_min, 0)}–${usd(comp.precio_max, 0)}`} />
              <Kpi label="Ventas estimadas" valor={`${num(comp.ventas_estim_total)}/mes`}
                   sub="suma de líderes (curva BSR)" hero />
              <Kpi label="Calidad promedio" valor={comp.rating_promedio ? `${comp.rating_promedio}/5` : "s/d"}
                   sub="rating de la competencia"
                   tono={(comp.rating_promedio ?? 5) < 4.3 ? "warn" : "navy"} />
              <Kpi label="Reseñas (mediana)" valor={num(comp.resenas_mediana)} sub="barrera de entrada"
                   tono={comp.resenas_mediana > 1000 ? "bad" : comp.resenas_mediana < 300 ? "good" : "warn"} />
            </FilaKpis>
          )}
          <Card className="mb-4">
            <p className="text-[12px] text-muted mb-2">Fuente: {res.fuente} · {res.mensaje}</p>
            <Tabla
              cabeceras={["Producto", "ASIN", "Precio", "BSR", "Ventas/mes", "Rating", "Reseñas", ""]}
              filas={res.productos.map((p) => [
                p.titulo.slice(0, 55), p.asin, usd(p.precio), num(p.bsr),
                num(p.ventas_estim), p.rating ?? "—", num(p.resenas),
                <a key="l" href={p.link} target="_blank" rel="noopener" className="text-navy underline">ver</a>,
              ])}
            />
          </Card>
        </>
      ) : (
        <Card className="mb-4">
          <Alerta tipo="warn">{res.mensaje}</Alerta>
          {res.links_amazon?.map((l) => (
            <a key={l.url} href={l.url} target="_blank" rel="noopener"
               className="block text-navy underline text-[13px] py-0.5">{l.nombre}</a>
          ))}
        </Card>
      ))}

      {res && (
        <Card className="mb-4">
          <h3 className="font-bold text-[14px] mb-2 text-navy-deep">Proveedores mejor rankeados</h3>
          {res.proveedores.map((pv) => (
            <p key={pv.plataforma} className="text-[13px] py-1">
              <b>{pv.prioridad}. <a href={pv.url} target="_blank" rel="noopener" className="text-navy underline">{pv.plataforma}</a></b>
              <span className="text-muted"> — {pv.nota}</span>
            </p>
          ))}
        </Card>
      )}

      {res && (
        <Card>
          <h3 className="font-bold text-[14px] mb-3 text-navy-deep">Asesor de probabilidad de éxito</h3>
          <div className="flex gap-3 items-end flex-wrap">
            <CampoNumero label="Tu precio objetivo (USD)" value={precioObj} step={0.5} onValor={setPrecioObj} className="w-32" />
            <CampoNumero label="Margen calculado % (0 = sin)" value={margen} step={0.5} onValor={setMargen} className="w-32" />
            <Boton onClick={() => void evaluar()} disabled={evaluando}>{t("mk_ex_btn")}</Boton>
          </div>
          {evaluando && <Spinner texto={t("comun.cargando")} />}
          {ev && (
            <div className="mt-4">
              <div className="flex items-center gap-3 mb-3">
                <Kpi label="Probabilidad de éxito" valor={`${ev.evaluacion.probabilidad}/100`} hero />
                <Badge texto={ev.evaluacion.veredicto} tono={ev.evaluacion.veredicto.toLowerCase()} />
                <span className="text-[13px] text-muted">{ev.evaluacion.comentario}</span>
              </div>
              {Object.entries(ev.evaluacion.factores).map(([k, f]) => (
                <div key={k} className="flex items-center gap-2 py-1 text-[13px]">
                  <span className="w-24 font-bold">{k}</span>
                  <div className="flex-1 h-2 bg-line rounded-full overflow-hidden">
                    <div className="h-full bg-navy" style={{ width: `${f.valor * 100}%` }} />
                  </div>
                  <span className="w-10 text-right tabular">{pct(f.valor * 100, 0)}</span>
                  <span className="text-muted flex-[2] text-[12px]">{f.detalle}</span>
                </div>
              ))}
              {ev.narrativa && (
                <Alerta tipo="info">
                  <span className="whitespace-pre-wrap">{ev.narrativa.texto}</span>
                </Alerta>
              )}
              <p className="text-[11.5px] text-muted mt-2">{ev.evaluacion.caveat}</p>
            </div>
          )}
        </Card>
      )}
    </>
  );
}
