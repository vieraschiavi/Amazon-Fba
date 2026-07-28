import { useState } from "react";
import { api, qs } from "../api/cliente";
import { GraficoLineas } from "../components/Graficos";
import { Alerta, Boton, CampoNumero, Card, FilaKpis, Kpi, Seccion, Selector, Tabla, usd, num } from "../components/ui";
import { useT } from "../i18n";

interface PlanRes {
  ok: boolean; alcanzado: boolean; objetivo: number; n_productos: number;
  ingreso_final: number; mes_objetivo: number | null;
  capital_propio_usado: number; capital_inversores: number;
  plan: { producto: number; fuente: string; capital: number; capital_inversor: number;
          sueldo_aporta: number; mes_meseta: number; ingreso_acumulado: number }[];
  advertencia?: string;
}
interface Dedicacion {
  horas_semana_min: number; horas_semana_max: number;
  desglose: Record<string, unknown>[] | Record<string, unknown>;
  automatizado_por_el_sistema: string[] | Record<string, unknown>;
  caveat: string;
}
interface Compuesto {
  filas: Record<string, number>[];
  resumen: { capital_final: number; total_aportado: number; ganancia: number;
             multiplicador: number; capital_ocioso_final: number };
}

export function Plan() {
  const t = useT();
  const [objetivo, setObjetivo] = useState(2500);
  const [capital, setCapital] = useState(10000);
  const [plan, setPlan] = useState<PlanRes | null>(null);
  const [nProd, setNProd] = useState(1);
  const [lanzando, setLanzando] = useState(false);
  const [dedic, setDedic] = useState<Dedicacion | null>(null);
  const [aporteIni, setAporteIni] = useState(5000);
  const [aportePer, setAportePer] = useState(200);
  const [tasa, setTasa] = useState(60);
  const [anios, setAnios] = useState(5);
  const [techoCap, setTechoCap] = useState(0);
  const [comp, setComp] = useState<Compuesto | null>(null);

  const calcularPlan = async () => {
    setPlan(await api.post<PlanRes>("/api/plan/portafolio",
      { objetivo_mensual: objetivo, capital_propio: capital }));
  };
  const calcularDedicacion = async () => {
    setDedic(await api.get<Dedicacion>(
      `/dedicacion${qs({ productos: nProd, lanzando })}`));
  };
  const calcularCompuesto = async () => {
    setComp(await api.post<Compuesto>("/api/plan/interes-compuesto", {
      aporte_inicial: aporteIni, aporte_periodico: aportePer,
      tasa_anual_pct: tasa, anios, techo_capital: techoCap,
    }));
  };

  return (
    <>
      <Seccion titulo={t("pl_titulo")} sub={t("pl_sub")} />
      <Card className="mb-5">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <CampoNumero label={t("pl.objetivo_ingreso_mes")} value={objetivo} step={100} onValor={setObjetivo} />
          <CampoNumero label={t("pl.capital_propio")} value={capital} step={500} onValor={setCapital} />
        </div>
        <div className="mt-3"><Boton onClick={() => void calcularPlan()}>Calcular plan</Boton></div>
        {plan && (
          <div className="mt-4">
            <FilaKpis>
              <Kpi label={t("pl.productos_necesarios")} valor={num(plan.n_productos)} hero />
              <Kpi label={t("pl.mes_objetivo")} valor={plan.mes_objetivo ? `mes ${plan.mes_objetivo}` : "no alcanzado"}
                   tono={plan.alcanzado ? "good" : "warn"} />
              <Kpi label={t("pl.capital_propio_usado")} valor={usd(plan.capital_propio_usado, 0)} />
              <Kpi label={t("pl.ingreso_final")} valor={usd(plan.ingreso_final, 0)} sub={t("pl.mes_meseta")} />
            </FilaKpis>
            {plan.advertencia && <Alerta tipo="warn">{plan.advertencia}</Alerta>}
            <Tabla
              cabeceras={["#", "Fuente", "Capital", "Sueldo que aporta", "Mes meseta", "Acumulado"]}
              filas={plan.plan.map((p) => [
                p.producto, p.fuente, usd(p.capital, 0), usd(p.sueldo_aporta, 0),
                p.mes_meseta, usd(p.ingreso_acumulado, 0),
              ])}
            />
          </div>
        )}
      </Card>

      <Seccion titulo={t("pl.cuantas_horas_semana_necesito")} sub={t("pl.desglosado_tarea_lo_sistema")} />
      <Card className="mb-5">
        <div className="flex gap-3 items-end flex-wrap">
          <CampoNumero label={t("pl.productos_operacion")} value={nProd} onValor={(v) => setNProd(Math.max(1, Math.round(v)))} className="w-36" />
          <Selector label={t("pl.lanzando_producto")} value={lanzando ? "1" : "0"}
                    onChange={(e) => setLanzando(e.target.value === "1")}>
            <option value="0">No</option><option value="1">Sí</option>
          </Selector>
          <Boton onClick={() => void calcularDedicacion()}>{t("pl.estimar")}</Boton>
        </div>
        {dedic && (
          <div className="mt-4">
            <Kpi label={t("pl.horas_semana")} valor={`${dedic.horas_semana_min}–${dedic.horas_semana_max} h`} hero />
            <p className="text-muted text-[12px] mt-2">{dedic.caveat}</p>
          </div>
        )}
      </Card>

      <Seccion titulo={t("pl.reinversion_compuesta")} sub={t("pl.techo_capital_productivo_excedente")} />
      <Card>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <CampoNumero label={t("pl.aporte_inicial")} value={aporteIni} step={500} onValor={setAporteIni} />
          <CampoNumero label={t("pl.aporte_mensual")} value={aportePer} step={50} onValor={setAportePer} />
          <CampoNumero label={t("pl.tasa_anual")} value={tasa} step={5} onValor={setTasa} />
          <CampoNumero label={t("pl.anos")} value={anios} onValor={(v) => setAnios(Math.round(v))} />
          <CampoNumero label={t("pl.techo_capital_0")} value={techoCap} step={1000} onValor={setTechoCap} />
        </div>
        <div className="mt-3"><Boton onClick={() => void calcularCompuesto()}>{t("pl.calcular")}</Boton></div>
        {comp && (
          <div className="mt-4">
            <FilaKpis>
              <Kpi label={t("pl.capital_final")} valor={usd(comp.resumen.capital_final, 0)} hero />
              <Kpi label={t("pl.total_aportado")} valor={usd(comp.resumen.total_aportado, 0)} />
              <Kpi label={t("pl.ganancia")} valor={usd(comp.resumen.ganancia, 0)} tono="good"
                   sub={`x${comp.resumen.multiplicador}`} />
              <Kpi label={t("pl.capital_ocioso")} valor={usd(comp.resumen.capital_ocioso_final, 0)}
                   tono={comp.resumen.capital_ocioso_final > 0 ? "warn" : "navy"} />
            </FilaKpis>
            <GraficoLineas datos={comp.filas} x="mes"
              series={[{ campo: "capital", nombre: t("pl.serie_capital") }, { campo: "aportado", nombre: t("pl.serie_aportado") }]} />
          </div>
        )}
      </Card>
    </>
  );
}
