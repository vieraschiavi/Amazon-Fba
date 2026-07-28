import { FormEvent, useEffect, useState } from "react";
import { api } from "../api/cliente";
import { GraficoBarras } from "../components/Graficos";
import { Badge, Boton, Campo, CampoNumero, Card, FilaKpis, Kpi, Seccion, Tabla, usd, num, pct } from "../components/ui";
import { useT } from "../i18n";
import { useProductoActivo } from "../stores/productoActivo";

interface Mix extends Record<string, unknown> { k: string; ingreso: number; neto: number; unidades: number }
interface Kpis {
  facturacion: number; neto: number; unidades: number; ordenes: number;
  margen_global_pct: number;
  por_producto: Mix[]; por_pais: Mix[]; por_segmento: Mix[];
}

export function Ventas() {
  const t = useT();
  const { activo, A } = useProductoActivo();
  const [asin, setAsin] = useState("");
  const [unidades, setUnidades] = useState(1);
  const [precio, setPrecio] = useState(24.0);
  const [neto, setNeto] = useState(6.9);
  const [pais, setPais] = useState("US");
  const [segmento, setSegmento] = useState("general");
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [guardado, setGuardado] = useState("");

  const cargar = () => { api.get<Kpis>("/dashboard").then(setKpis).catch(() => {}); };
  useEffect(cargar, []);
  useEffect(() => {
    if (activo) setAsin(activo.asin || "");
    setPrecio(A("precio", 24.0)); setNeto(A("neto", 6.9));
  }, [activo]); // eslint-disable-line react-hooks/exhaustive-deps

  const registrar = async (e: FormEvent) => {
    e.preventDefault();
    if (!asin.trim()) { setGuardado("asin"); return; }
    await api.post("/api/ventas", {
      asin, unidades, precio, neto_unitario: neto, pais, segmento,
      product_id: activo?.id ?? null,
    });
    setGuardado("ok");
    cargar();
    setTimeout(() => setGuardado(""), 2500);
  };

  return (
    <>
      <Seccion titulo={t("vt_titulo")} sub={t("vt_sub")} />
      <Card className="mb-4">
        <form onSubmit={(e) => void registrar(e)} className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <Campo label="ASIN" value={asin} onChange={(e) => setAsin(e.target.value)} />
          <CampoNumero label={t("vt.unidades")} value={unidades} onValor={(v) => setUnidades(Math.max(1, Math.round(v)))} />
          <CampoNumero label={t("vt.precio")} value={precio} step={0.5} onValor={setPrecio} />
          <CampoNumero label={t("vt.neto_unidad")} value={neto} step={0.1} onValor={setNeto} />
          <Campo label={t("vt.pais")} value={pais} onChange={(e) => setPais(e.target.value)} />
          <Campo label={t("vt.segmento")} value={segmento} onChange={(e) => setSegmento(e.target.value)} />
          <div className="col-span-2 lg:col-span-3 flex items-center gap-3">
            <Boton>{t("vt_btn")}</Boton>
            {guardado === "ok" && <Badge texto={t("vt.venta_registrada")} tono="verde" />}
            {guardado === "asin" && <Badge texto={t("vt.falta_asin")} tono="amarillo" />}
          </div>
        </form>
      </Card>

      {kpis && (
        <>
          <FilaKpis>
            <Kpi label={t("vt.facturacion")} valor={usd(kpis.facturacion, 0)} hero />
            <Kpi label={t("vt.neto")} valor={usd(kpis.neto, 0)} tono="good" />
            <Kpi label={t("vt.margen_global")} valor={pct(kpis.margen_global_pct)} />
            <Kpi label={t("vt.ordenes")} valor={num(kpis.ordenes)} sub={`${num(kpis.unidades)} unidades`} />
          </FilaKpis>
          {kpis.por_producto.length > 0 && (
            <Card className="mb-4">
              <h3 className="font-bold text-[14px] mb-2 text-navy-deep">{t("vt.mix_producto")}</h3>
              <GraficoBarras
                datos={kpis.por_producto}
                x="k"
                series={[{ campo: "ingreso", nombre: t("vt.serie_ingreso") }, { campo: "neto", nombre: t("vt.serie_neto") }]}
              />
            </Card>
          )}
          <div className="grid md:grid-cols-2 gap-4">
            {[["Por país", kpis.por_pais], ["Por segmento", kpis.por_segmento]].map(([titulo, mix]) => (
              <Card key={titulo as string}>
                <h3 className="font-bold text-[14px] mb-2 text-navy-deep">{titulo as string}</h3>
                <Tabla
                  cabeceras={["", "Ingreso", "Neto", "Unid."]}
                  filas={(mix as Mix[]).map((m) => [
                    m.k, usd(m.ingreso, 0), usd(m.neto, 0), num(m.unidades),
                  ])}
                />
              </Card>
            ))}
          </div>
        </>
      )}
    </>
  );
}
