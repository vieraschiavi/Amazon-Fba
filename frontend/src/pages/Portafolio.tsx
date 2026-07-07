import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import type { Producto, ResumenPortafolio, FilaProyeccion } from "../api/tipos";
import { GraficoLineas } from "../components/Graficos";
import { Badge, Boton, Card, FilaKpis, Kpi, Seccion, Selector, Semaforo, Tabla, usd, num, pct } from "../components/ui";
import { useT } from "../i18n";
import { useProductoActivo } from "../stores/productoActivo";

interface Analisis {
  ok: boolean; producto: Producto;
  unit_economics: { landed: number; precio: number; neto: number; margen_pct: number; roi_pct: number; semaforo: string };
  capital_pipeline: number;
  proyeccion: { filas?: FilaProyeccion[]; sueldo_meseta?: number; caja_minima?: number; primer_cobro_mes?: number; [k: string]: unknown } | null;
  ventas_reales: { ingreso: number; neto: number; unidades: number; ordenes: number; ultimas: Record<string, unknown>[] };
}

export function Portafolio() {
  const t = useT();
  const { cargar: recargarActivo } = useProductoActivo();
  const [resumen, setResumen] = useState<ResumenPortafolio | null>(null);
  const [sel, setSel] = useState<number | "">("");
  const [analisis, setAnalisis] = useState<Analisis | null>(null);

  const cargar = () => {
    api.get<ResumenPortafolio>("/portfolio").then(setResumen).catch(() => {});
  };
  useEffect(cargar, []);

  useEffect(() => {
    if (sel === "") { setAnalisis(null); return; }
    api.get<Analisis>(`/portfolio/producto/${sel}`).then(setAnalisis).catch(() => {});
  }, [sel]);

  const quitar = async (pid: number) => {
    await api.del(`/api/productos/${pid}`);
    setSel("");
    cargar();
    await recargarActivo();
  };

  const filasProy = (analisis?.proyeccion?.filas as FilaProyeccion[] | undefined) ?? [];

  return (
    <>
      <Seccion titulo={t("pf_titulo")} sub={t("pf_sub")} />
      {resumen && resumen.n_productos > 0 && (
        <FilaKpis>
          <Kpi label="Productos activos" valor={String(resumen.n_productos)}
               sub={`${resumen.semaforos?.verde ?? 0} verde / ${resumen.semaforos?.amarillo ?? 0} amarillo / ${resumen.semaforos?.rojo ?? 0} rojo`} />
          <Kpi label="Sueldo meseta proyectado" valor={usd(resumen.sueldo_meseta_proyectado, 0)}
               sub="suma de techo × neto" hero />
          <Kpi label="Capital en pipeline" valor={usd(resumen.capital_pipeline_total, 0)}
               sub="~4 meses de stock por producto" />
          <Kpi label="Ventas reales" valor={usd(resumen.ingreso_real, 0)}
               sub={`neto ${usd(resumen.neto_real, 0)}`} tono="good" />
        </FilaKpis>
      )}

      <Card className="mb-4">
        {!resumen || resumen.n_productos === 0 ? (
          <p className="text-muted text-[13px]">
            {resumen?.mensaje || t("comun.sin_datos")} — guardá un producto desde Pricing.
          </p>
        ) : (
          <Tabla
            cabeceras={["Producto", "ASIN", "Landed", "Precio", "Neto/u", "Margen", "ROI", "Semáforo", "Techo u/mes", "Ventas"]}
            filas={resumen.productos.map((p) => [
              p.nombre, p.asin || "—", usd(p.landed), usd(p.precio), usd(p.neto),
              pct(p.margen), pct(p.roi), <Semaforo key="s" valor={p.semaforo} />,
              num(p.techo_demanda), usd(p.ventas_ingreso, 0),
            ])}
          />
        )}
      </Card>

      {resumen && resumen.n_productos > 0 && (
        <Card>
          <h3 className="font-bold text-[14px] mb-3 text-navy-deep">Análisis financiero por producto</h3>
          <div className="flex gap-3 items-end flex-wrap">
            <Selector label="Producto" value={sel}
                      onChange={(e) => setSel(e.target.value ? parseInt(e.target.value, 10) : "")}>
              <option value="">—</option>
              {resumen.productos.map((p) => (
                <option key={p.id} value={p.id}>#{p.id} — {p.nombre}</option>
              ))}
            </Selector>
            {sel !== "" && (
              <Boton tipo="peligro" onClick={() => void quitar(sel as number)}>
                {t("pf_del_btn")}
              </Boton>
            )}
          </div>

          {analisis?.ok && (
            <div className="mt-4">
              <FilaKpis>
                <Kpi label="Precio" valor={usd(analisis.unit_economics.precio)} />
                <Kpi label="Margen" valor={pct(analisis.unit_economics.margen_pct)}
                     tono={analisis.unit_economics.semaforo === "verde" ? "good" : "warn"} />
                <Kpi label="ROI" valor={pct(analisis.unit_economics.roi_pct)} />
                <Kpi label="Capital pipeline" valor={usd(analisis.capital_pipeline, 0)} />
              </FilaKpis>
              {filasProy.length > 0 && (
                <GraficoLineas
                  datos={filasProy}
                  x="mes"
                  series={[{ campo: "caja", nombre: "Caja" }, { campo: "sueldo", nombre: "Sueldo" }]}
                />
              )}
              <div className="mt-3">
                <Badge texto={`Ventas reales: ${num(analisis.ventas_reales.unidades)} unid · ${usd(analisis.ventas_reales.ingreso, 0)}`} tono="navy" />
              </div>
            </div>
          )}
        </Card>
      )}
    </>
  );
}
