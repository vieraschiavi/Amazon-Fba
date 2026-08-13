// © 2026 Martín Viera. Todos los derechos reservados.
import { useEffect, useState } from "react";
import { api, mensajeError } from "../api/cliente";
import type { FilaProyeccion } from "../api/tipos";
import { GraficoLineas } from "../components/Graficos";
import { Alerta, Boton, CampoNumero, Card, FilaKpis, Kpi, Seccion, Tabla, usd, num } from "../components/ui";
import { useT } from "../i18n";
import { useProductoActivo } from "../stores/productoActivo";

interface Proyeccion {
  filas: FilaProyeccion[];
  resumen: {
    unidades_compra: number; inversion: number; caja_minima: number;
    sueldo_meseta: number; mes_primer_cobro: number; alerta: string;
  };
}

export function Caja() {
  const t = useT();
  const { activo, A } = useProductoActivo();
  const [budget, setBudget] = useState(8000);
  const [landed, setLanded] = useState(5.5);
  const [precio, setPrecio] = useState(24.0);
  const [neto, setNeto] = useState(6.9);
  const [techo, setTecho] = useState(290);
  const [meses, setMeses] = useState(12);
  const [proy, setProy] = useState<Proyeccion | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLanded(A("landed", 5.5)); setPrecio(A("precio", 24.0));
    setNeto(A("neto", 6.9)); setTecho(A("techo_demanda", 290));
  }, [activo]); // eslint-disable-line react-hooks/exhaustive-deps

  const proyectar = async () => {
    setOcupado(true);
    try {
      const d = await api.post<Proyeccion>("/api/caja/proyeccion", {
        budget, landed, precio, net_unit: neto, techo_demanda: techo, meses,
      });
      setProy(d);
      setError("");
    } catch (e) {
      // Mantiene el resultado anterior a la vista, pero ahora AVISA que el
      // valor que se acaba de pedir no se pudo calcular (antes quedaba en
      // silencio: se veian numeros viejos sin ninguna pista de que el
      // ultimo cambio no se aplico).
      setError(mensajeError(e));
    }
    setOcupado(false);
  };

  const r = proy?.resumen;
  return (
    <>
      <Seccion titulo={t("cj_titulo")} sub={t("cj_sub")} />
      <Card className="mb-4">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <CampoNumero label={t("cj.capital")} value={budget} step={500} onValor={setBudget} />
          <CampoNumero label={t("cj.landed_unidad")} value={landed} step={0.1} onValor={setLanded} />
          <CampoNumero label={t("cj.precio_venta")} value={precio} step={0.5} onValor={setPrecio} />
          <CampoNumero label={t("cj.neto_unidad")} value={neto} step={0.1} onValor={setNeto} />
          <CampoNumero label={t("cj.techo_demanda_unid_mes")} value={techo} onValor={(v) => setTecho(Math.round(v))} />
          <CampoNumero label={t("cj.meses")} value={meses} onValor={(v) => setMeses(Math.round(v))} />
        </div>
        <div className="mt-3">
          <Boton onClick={() => void proyectar()} disabled={ocupado}>{t("cj.proyectar")}</Boton>
        </div>
      </Card>

      {error && <Alerta tipo="error">{error}</Alerta>}

      {proy && r && (
        <>
          <FilaKpis>
            <Kpi label={t("cj.sueldo_meseta")} valor={usd(r.sueldo_meseta, 0)} sub={t("cj.neto_sostenido_mes")} hero />
            <Kpi label={t("cj.caja_minima")} valor={usd(r.caja_minima, 0)} sub={t("cj.colchon_efectivo")}
                 tono={r.caja_minima < budget * 0.05 ? "warn" : "navy"} />
            <Kpi label={t("cj.primer_cobro")} valor={`mes ${num(r.mes_primer_cobro)}`} sub={t("cj.lead_time_dd_7")} />
            <Kpi label={t("cj.capital_invertido")} valor={usd(r.inversion, 0)}
                 sub={`${num(r.unidades_compra)} unidades`} />
          </FilaKpis>
          {r.alerta && r.alerta !== "ok" && <Alerta tipo="warn">{r.alerta}</Alerta>}
          <Card className="mb-4">
            <GraficoLineas datos={proy.filas} x="mes"
              series={[{ campo: "caja", nombre: t("cj.caja") }, { campo: "sueldo", nombre: t("cj.sueldo") }]} />
          </Card>
          <Card>
            <Tabla
              cabeceras={[t("cj.mes"), t("cj.vendidas"), t("cj.cobrado"), t("cj.sueldo"), t("cj.caja"), t("cj.capital_atado")]}
              filas={proy.filas.map((f) => [
                f.mes, num(f.vendidas), usd(f.cobrado, 0), usd(f.sueldo, 0),
                usd(f.caja, 0), usd(f.capital_atado, 0),
              ])}
            />
          </Card>
        </>
      )}
    </>
  );
}
