import { useState } from "react";
import { api, qs } from "../api/cliente";
import type { OrdenCampo, ProductoEstrella, ResVendedores, VendedorPrincipal } from "../api/tipos";
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
  // Vendedores principales sin API: se pega lo que se ve en Amazon, o se sube
  // un export de productos si el usuario ya paga alguna herramienta.
  const [vendTexto, setVendTexto] = useState("");
  const [vend, setVend] = useState<ResVendedores | null>(null);
  const [rankeando, setRankeando] = useState(false);
  // Orden de la tabla de productos del nicho. El pedido: precio, ranking de
  // ventas, potencial y calificacion, ascendente y descendente.
  const [orden, setOrden] = useState<OrdenCampo>("potencial");
  const [desc, setDesc] = useState(true);

  const rankearVendedores = async () => {
    setRankeando(true);
    try {
      const d = await api.post<ResVendedores>("/api/mercado/vendedores",
                                              { texto: vendTexto });
      setVend(d);
    } catch { /* mantiene */ }
    setRankeando(false);
  };

  const subirVendedoresCsv = async (archivo: File) => {
    setRankeando(true);
    try {
      const d = await api.subir<ResVendedores>("/api/mercado/vendedores-csv", archivo);
      setVend(d);
    } catch { /* mantiene */ }
    setRankeando(false);
  };

  // Ordenar es del lado del cliente: es instantaneo y no vuelve a pegarle al
  // backend cada vez que se cambia de criterio o se invierte el sentido.
  const ordenar = (campo: OrdenCampo) => {
    if (campo === orden) { setDesc(!desc); return; }
    setOrden(campo); setDesc(true);
  };

  const productosOrdenados = (() => {
    if (!vend?.productos) return [];
    const val = (p: VendedorPrincipal): number | null => {
      switch (orden) {
        case "precio": return p.precio;
        case "ventas": return p.ventas_estim;
        case "potencial": return p.potencial ?? null;
        case "rating": return p.rating ?? null;
        case "bsr": return p.bsr;
        default: return null;
      }
    };
    // Los que no tienen dato del criterio van SIEMPRE al final, en los dos
    // sentidos: si no, ordenar ascendente los pondria arriba y parecerian "los
    // mejores" cuando en realidad no se sabe.
    return [...vend.productos].sort((a, b) => {
      const va = val(a), vb = val(b);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      return desc ? vb - va : va - vb;
    });
  })();

  const Cab = ({ campo, children }: { campo: OrdenCampo; children: React.ReactNode }) => (
    <button type="button" onClick={() => ordenar(campo)}
            className="uppercase tracking-wide font-bold text-[11px] text-muted hover:text-navy">
      {children}{orden === campo ? (desc ? " ↓" : " ↑") : ""}
    </button>
  );

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
          <Campo label={t("mk.producto_keyword")} value={kw} onChange={(e) => setKw(e.target.value)} className="w-72" />
          <CampoNumero label={t("mk.precio_min")} value={min} onValor={setMin} className="w-24" />
          <CampoNumero label={t("mk.precio_max")} value={max} onValor={setMax} className="w-24" />
          <Boton onClick={() => void explorar()} disabled={ocupado}>{t("mk_btn")}</Boton>
        </div>
        {ocupado && <Spinner texto={t("comun.cargando")} />}
      </Card>

      {/* Demanda GRATIS sin Keepa — señal relativa por autocompletado de Amazon */}
      <Card className="mb-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h3 className="font-bold text-[14px] text-navy-deep">{t("mk.demanda_nicho_titulo")}</h3>
            <p className="text-[12px] text-muted">{t("mk.demanda_nicho_sub")}</p>
          </div>
          <Boton tipo="fantasma" onClick={() => void medirDemanda()} disabled={midiendoDemanda}>
            Medir demanda
          </Boton>
        </div>
        {midiendoDemanda && <Spinner texto={t("mk.consultando_autocompletado_amazon_grat")} />}
        {demanda && (demanda.ok ? (
          <div className="mt-3">
            <FilaKpis>
              <Kpi label={t("mk.demanda_relativa")} valor={`${demanda.demanda_score}/100`}
                   sub={demanda.nivel} hero
                   tono={demanda.demanda_score >= 65 ? "good" : demanda.demanda_score >= 40 ? "warn" : "bad"} />
              <Kpi label={t("mk.amplitud_long_tail")} valor={num(demanda.amplitud)}
                   sub={t("mk.variantes_reales_busca_gente")} />
              <Kpi label={t("mk.nichos_candidatos")} valor={num(demanda.n_nichos)} sub={t("mk.sub_nichos_detectados")} />
              <Kpi label={t("mk.costo")} valor="US$0" sub={`${demanda.requests} consultas gratis`} tono="good" />
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

      {/* Vendedores principales GRATIS: el BSR es publico en cada ficha de
          Amazon, asi que no hace falta clave de Keepa ni de Jungle Scout. */}
      <Card className="mb-4">
        <h3 className="font-bold text-[14px] text-navy-deep">{t("mk.vend_titulo")}</h3>
        <p className="text-[12px] text-muted mb-2">{t("mk.vend_sub")}</p>
        <textarea
          value={vendTexto}
          onChange={(e) => setVendTexto(e.target.value)}
          rows={4}
          placeholder={t("mk.vend_placeholder")}
          className="w-full text-[12px] border border-line rounded-md px-2 py-1.5 font-mono"
        />
        <div className="flex gap-3 items-center mt-2">
          <Boton tipo="fantasma" onClick={() => void rankearVendedores()} disabled={rankeando}>
            {t("mk.vend_btn")}
          </Boton>
          <span className="text-[11px] text-muted">{t("mk.vend_ayuda")}</span>
        </div>
        {/* Si YA pagás Helium 10 o Jungle Scout, su export evita el pegado a
            mano. Es un atajo opcional, no un requisito. */}
        <div className="mt-2 pt-2 border-t border-line">
          <label className="text-[12px] text-muted">
            {t("mk.vend_csv")}{" "}
            <input type="file" accept=".csv" className="text-[12px]"
                   onChange={(e) => e.target.files?.[0] && void subirVendedoresCsv(e.target.files[0])} />
          </label>
        </div>
        {rankeando && <Spinner texto={t("comun.cargando")} />}
        {vend && (vend.ok ? (
          <div className="mt-3">
            <FilaKpis>
              <Kpi label={t("mk.vend_total")} valor={`${num(vend.ventas_estim_total)}/mes`}
                   sub={t("mk.vend_total_sub")} hero />
              <Kpi label={t("mk.vend_lider")} valor={`${num(vend.ventas_estim_lider)}/mes`}
                   sub={t("mk.vend_lider_sub")} />
            </FilaKpis>
            <p className="text-[11.5px] text-muted mb-1">{t("mk.vend_orden_ayuda")}</p>
            <Tabla
              cabeceras={["ASIN",
                          <Cab key="b" campo="bsr">BSR</Cab>,
                          <Cab key="v" campo="ventas">{t("mk.ventas_mes")}</Cab>,
                          t("mk.vend_cuota"),
                          <Cab key="p" campo="precio">{t("mk.precio")}</Cab>,
                          <Cab key="r" campo="rating">{t("mk.rating")}</Cab>,
                          <Cab key="o" campo="potencial">{t("mk.vend_potencial")}</Cab>,
                          t("mk.vend_ingreso")]}
              filas={productosOrdenados.map((p) => [
                p.asin ?? "—",
                p.bsr != null ? num(p.bsr) : "—",
                p.ventas_estim != null ? num(p.ventas_estim) : t("mk.vend_sin_bsr"),
                p.cuota_pct != null ? pct(p.cuota_pct, 1) : "—",
                p.precio != null ? usd(p.precio) : "—",
                p.rating != null ? `${p.rating}/5` : "—",
                p.potencial != null
                  ? <Badge key="pt" texto={String(p.potencial)}
                           tono={p.potencial >= 65 ? "verde" : p.potencial >= 45 ? "amarillo" : "rojo"} />
                  : "—",
                p.ingreso_estim_mes != null ? usd(p.ingreso_estim_mes, 0) : "—",
              ])}
            />
            <p className="text-[11.5px] text-muted mt-1">{vend.mensaje}</p>
            <p className="text-[11px] text-muted mt-1">{t("mk.vend_potencial_ayuda")}</p>
          </div>
        ) : (
          <Alerta tipo="info">{vend.mensaje}</Alerta>
        ))}
      </Card>

      {res && (res.ok ? (
        <>
          {comp?.ok && (
            <FilaKpis>
              <Kpi label={t("mk.competidores")} valor={num(comp.n_competidores)}
                   sub={`${usd(comp.precio_min, 0)}–${usd(comp.precio_max, 0)}`} />
              <Kpi label={t("mk.ventas_estimadas")} valor={`${num(comp.ventas_estim_total)}/mes`}
                   sub={t("mk.suma_lideres_curva_bsr")} hero />
              <Kpi label={t("mk.calidad_promedio")} valor={comp.rating_promedio ? `${comp.rating_promedio}/5` : "s/d"}
                   sub={t("mk.rating_competencia")}
                   tono={(comp.rating_promedio ?? 5) < 4.3 ? "warn" : "navy"} />
              <Kpi label={t("mk.resenas_mediana")} valor={num(comp.resenas_mediana)} sub={t("mk.barrera_entrada")}
                   tono={comp.resenas_mediana > 1000 ? "bad" : comp.resenas_mediana < 300 ? "good" : "warn"} />
            </FilaKpis>
          )}
          <Card className="mb-4">
            <p className="text-[12px] text-muted mb-2">Fuente: {res.fuente} · {res.mensaje}</p>
            <Tabla
              cabeceras={[t("mk.producto"), "ASIN", t("mk.precio"), "BSR", t("mk.ventas_mes"), t("mk.rating"), t("mk.resenas"), ""]}
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
          <h3 className="font-bold text-[14px] mb-3 text-navy-deep">{t("mk.asesor_exito_titulo")}</h3>
          <div className="flex gap-3 items-end flex-wrap">
            <CampoNumero label={t("mk.precio_objetivo")} value={precioObj} step={0.5} onValor={setPrecioObj} className="w-32" />
            <CampoNumero label={t("mk.margen_calculado_0")} value={margen} step={0.5} onValor={setMargen} className="w-32" />
            <Boton onClick={() => void evaluar()} disabled={evaluando}>{t("mk_ex_btn")}</Boton>
          </div>
          {evaluando && <Spinner texto={t("comun.cargando")} />}
          {ev && (
            <div className="mt-4">
              <div className="flex items-center gap-3 mb-3">
                <Kpi label={t("mk.probabilidad_exito")} valor={`${ev.evaluacion.probabilidad}/100`} hero />
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
