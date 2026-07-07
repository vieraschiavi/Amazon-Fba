import { useEffect, useState } from "react";
import { api } from "../api/cliente";
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
    } catch { /* mantiene el resultado anterior */ }
    setOcupado(false);
  };

  const r = proy?.resumen;
  return (
    <>
      <Seccion titulo={t("cj_titulo")} sub={t("cj_sub")} />
      <Card className="mb-4">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <CampoNumero label="Capital (USD)" value={budget} step={500} onValor={setBudget} />
          <CampoNumero label="Landed / unidad (USD)" value={landed} step={0.1} onValor={setLanded} />
          <CampoNumero label="Precio venta (USD)" value={precio} step={0.5} onValor={setPrecio} />
          <CampoNumero label="Neto / unidad (USD)" value={neto} step={0.1} onValor={setNeto} />
          <CampoNumero label="Techo demanda (unid/mes)" value={techo} onValor={(v) => setTecho(Math.round(v))} />
          <CampoNumero label="Meses" value={meses} onValor={(v) => setMeses(Math.round(v))} />
        </div>
        <div className="mt-3">
          <Boton onClick={() => void proyectar()} disabled={ocupado}>Proyectar</Boton>
        </div>
      </Card>

      {proy && r && (
        <>
          <FilaKpis>
            <Kpi label="Sueldo en meseta" valor={usd(r.sueldo_meseta, 0)} sub="neto sostenido por mes" hero />
            <Kpi label="Caja mínima" valor={usd(r.caja_minima, 0)} sub="colchón de efectivo"
                 tono={r.caja_minima < budget * 0.05 ? "warn" : "navy"} />
            <Kpi label="Primer cobro" valor={`mes ${num(r.mes_primer_cobro)}`} sub="lead time + DD+7" />
            <Kpi label="Capital invertido" valor={usd(r.inversion, 0)}
                 sub={`${num(r.unidades_compra)} unidades`} />
          </FilaKpis>
          {r.alerta && r.alerta !== "ok" && <Alerta tipo="warn">{r.alerta}</Alerta>}
          <Card className="mb-4">
            <GraficoLineas datos={proy.filas} x="mes"
              series={[{ campo: "caja", nombre: "Caja" }, { campo: "sueldo", nombre: "Sueldo" }]} />
          </Card>
          <Card>
            <Tabla
              cabeceras={["Mes", "Vendidas", "Cobrado", "Sueldo", "Caja", "Capital atado"]}
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
