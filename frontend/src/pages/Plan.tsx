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
          <CampoNumero label="Objetivo de ingreso (USD/mes)" value={objetivo} step={100} onValor={setObjetivo} />
          <CampoNumero label="Capital propio (USD)" value={capital} step={500} onValor={setCapital} />
        </div>
        <div className="mt-3"><Boton onClick={() => void calcularPlan()}>Calcular plan</Boton></div>
        {plan && (
          <div className="mt-4">
            <FilaKpis>
              <Kpi label="Productos necesarios" valor={num(plan.n_productos)} hero />
              <Kpi label="Mes del objetivo" valor={plan.mes_objetivo ? `mes ${plan.mes_objetivo}` : "no alcanzado"}
                   tono={plan.alcanzado ? "good" : "warn"} />
              <Kpi label="Capital propio usado" valor={usd(plan.capital_propio_usado, 0)} />
              <Kpi label="Ingreso final" valor={usd(plan.ingreso_final, 0)} sub="/mes en meseta" />
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

      <Seccion titulo="¿Cuántas horas por semana necesito?" sub="Desglosado por tarea, con lo que el sistema ya automatiza" />
      <Card className="mb-5">
        <div className="flex gap-3 items-end flex-wrap">
          <CampoNumero label="Productos en operación" value={nProd} onValor={(v) => setNProd(Math.max(1, Math.round(v)))} className="w-36" />
          <Selector label="¿Lanzando producto?" value={lanzando ? "1" : "0"}
                    onChange={(e) => setLanzando(e.target.value === "1")}>
            <option value="0">No</option><option value="1">Sí</option>
          </Selector>
          <Boton onClick={() => void calcularDedicacion()}>Estimar</Boton>
        </div>
        {dedic && (
          <div className="mt-4">
            <Kpi label="Horas / semana" valor={`${dedic.horas_semana_min}–${dedic.horas_semana_max} h`} hero />
            <p className="text-muted text-[12px] mt-2">{dedic.caveat}</p>
          </div>
        )}
      </Card>

      <Seccion titulo="Reinversión compuesta" sub="Con techo de capital productivo — el excedente queda ocioso" />
      <Card>
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <CampoNumero label="Aporte inicial (USD)" value={aporteIni} step={500} onValor={setAporteIni} />
          <CampoNumero label="Aporte mensual (USD)" value={aportePer} step={50} onValor={setAportePer} />
          <CampoNumero label="Tasa anual (%)" value={tasa} step={5} onValor={setTasa} />
          <CampoNumero label="Años" value={anios} onValor={(v) => setAnios(Math.round(v))} />
          <CampoNumero label="Techo capital (0 = sin)" value={techoCap} step={1000} onValor={setTechoCap} />
        </div>
        <div className="mt-3"><Boton onClick={() => void calcularCompuesto()}>Calcular</Boton></div>
        {comp && (
          <div className="mt-4">
            <FilaKpis>
              <Kpi label="Capital final" valor={usd(comp.resumen.capital_final, 0)} hero />
              <Kpi label="Total aportado" valor={usd(comp.resumen.total_aportado, 0)} />
              <Kpi label="Ganancia" valor={usd(comp.resumen.ganancia, 0)} tono="good"
                   sub={`x${comp.resumen.multiplicador}`} />
              <Kpi label="Capital ocioso" valor={usd(comp.resumen.capital_ocioso_final, 0)}
                   tono={comp.resumen.capital_ocioso_final > 0 ? "warn" : "navy"} />
            </FilaKpis>
            <GraficoLineas datos={comp.filas} x="mes"
              series={[{ campo: "capital", nombre: "Capital" }, { campo: "aportado", nombre: "Aportado" }]} />
          </div>
        )}
      </Card>
    </>
  );
}
