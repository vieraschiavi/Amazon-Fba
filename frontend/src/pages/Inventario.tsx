import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import type { ItemRestock, PanelRestock } from "../api/tipos";
import { Alerta, Badge, Boton, CampoNumero, Card, FilaKpis, Kpi, Seccion, Selector, Spinner, Tabla, num, usd } from "../components/ui";
import { useT } from "../i18n";

// Reabastecimiento (restock) estilo Sellerboard: con la velocidad de venta real
// (de las ventas registradas) y el stock que carga el usuario, dice cuando se
// agota, hasta cuando puede esperar para pedir y cuanto reponer. Sin ventas o
// sin stock, lo dice honestamente y no estima nada.

const TONO: Record<string, string> = {
  rojo: "rojo", amarillo: "amarillo", verde: "verde",
  sin_stock: "navy", sin_ventas: "navy",
};
const ETIQUETA: Record<string, string> = {
  rojo: "rs.est_rojo", amarillo: "rs.est_amarillo", verde: "rs.est_verde",
  sin_stock: "rs.est_sin_stock", sin_ventas: "rs.est_sin_ventas",
};

export function Inventario() {
  const t = useT();
  const [panel, setPanel] = useState<PanelRestock | null>(null);
  const [pid, setPid] = useState<number | null>(null);
  const [stock, setStock] = useState(0);
  const [lead, setLead] = useState(60);
  const [guardando, setGuardando] = useState(false);

  const cargar = () => {
    api.get<PanelRestock>("/api/inventario/panel").then((d) => {
      setPanel(d);
      if (pid === null && d.items.length) setPid(d.items[0].id);
    }).catch(() => {});
  };
  useEffect(cargar, []); // eslint-disable-line react-hooks/exhaustive-deps

  // al elegir producto, precargar su stock/lead actuales
  useEffect(() => {
    const it = panel?.items.find((i) => i.id === pid);
    if (it) { setStock(it.stock ?? 0); setLead(it.lead_time_dias || 60); }
  }, [pid, panel]);

  const guardar = async () => {
    if (pid === null) return;
    setGuardando(true);
    await api.post(`/api/inventario/stock/${pid}`, { stock, lead_time_dias: lead }).catch(() => {});
    setGuardando(false);
    cargar();
  };

  const r = panel?.resumen;
  return (
    <>
      <Seccion titulo={t("rs_titulo")} sub={t("rs_sub")} />

      <Card className="mb-4">
        <h3 className="font-bold text-[14px] text-navy-deep mb-2">{t("rs_form_titulo")}</h3>
        {panel && panel.items.length === 0 ? (
          <p className="text-muted text-[13px]">{t("rs_sin_productos")}</p>
        ) : (
          <div className="flex gap-3 items-end flex-wrap">
            <Selector label={t("rs.producto")} value={pid ?? ""}
                      onChange={(e) => setPid(e.target.value ? parseInt(e.target.value, 10) : null)}
                      className="max-w-[280px]">
              {(panel?.items || []).map((i) => (
                <option key={i.id} value={i.id}>{i.nombre}</option>
              ))}
            </Selector>
            <CampoNumero label={t("rs.stock_actual_u")} value={stock} onValor={(v) => setStock(Math.max(0, Math.round(v)))} className="w-32" />
            <CampoNumero label={t("rs.lead_time_dias")} value={lead} onValor={(v) => setLead(Math.max(1, Math.round(v)))} className="w-32" />
            <Boton onClick={() => void guardar()} disabled={guardando || pid === null}>{t("rs_form_btn")}</Boton>
          </div>
        )}
      </Card>

      {!panel ? <Spinner texto={t("comun.cargando")} /> : (
        <>
          <FilaKpis>
            <Kpi label={t("rs_kpi_reponer")} valor={num(r!.n_reponer)}
                 sub={`de ${num(r!.n_productos)} productos`} hero />
            <Kpi label={t("rs_kpi_capital")} valor={usd(r!.capital_reposicion_total, 0)} tono="warn" />
            <Kpi label={t("rs_kpi_sin_stock")} valor={num(r!.n_sin_stock)} />
            <Kpi label={t("rs_kpi_sin_ventas")} valor={num(r!.n_sin_ventas)} />
          </FilaKpis>
          <Alerta tipo="info">{t("rs_nota")}</Alerta>
          <Card>
            <Tabla
              cabeceras={[t("rs.producto"), t("rs.stock"), t("rs.vel_dia"), t("rs.se_agota"), t("rs.pedir_antes"), t("rs.reponer"), t("rs.capital"), t("rs.estado")]}
              filas={panel.items.map((i: ItemRestock) => [
                i.nombre,
                i.stock ?? "s/d",
                i.velocidad_diaria,
                i.fecha_quiebre ? `${i.fecha_quiebre} (${i.dias_cobertura}d)` : "—",
                i.fecha_pedir || "—",
                i.cantidad_sugerida != null ? num(i.cantidad_sugerida) : "—",
                i.capital_reposicion != null ? usd(i.capital_reposicion, 0) : "—",
                <Badge key="e" texto={ETIQUETA[i.estado] ? t(ETIQUETA[i.estado]) : i.estado} tono={TONO[i.estado] || "navy"} />,
              ])}
            />
            <p className="text-muted text-[12px] mt-2">{t("rs_pie")}</p>
          </Card>
        </>
      )}
    </>
  );
}
