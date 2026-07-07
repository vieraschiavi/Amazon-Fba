import { useState } from "react";
import { api } from "../api/cliente";
import { GraficoLineas } from "../components/Graficos";
import { Boton, CampoNumero, Card, FilaKpis, Kpi, Seccion, usd, num, pct } from "../components/ui";
import { useT } from "../i18n";
import { useProductoActivo } from "../stores/productoActivo";

interface Escenario {
  n_productos: number; unidades_mes: number; facturacion: number;
  net_total: number; comision_inversor: number; sueldo_martin: number;
  sueldo_sin_inversor: number; delta: number; cuello: string;
  inv_share_pct: number; retorno_inversor_mes_pct: number;
}
interface Retorno {
  filas: Record<string, number>[];
  resumen: {
    ticket: number; capital_final: number; comision_inicial: number;
    comision_meseta: number; mes_saturacion: number;
    capital_ocioso_final: number; multiplicador: number;
  };
}

export function Inversores() {
  const t = useT();
  const { A } = useProductoActivo();
  const [capProp, setCapProp] = useState(10000);
  const [capInv, setCapInv] = useState(5000);
  const [pctFact, setPctFact] = useState(10);
  const [techo, setTecho] = useState(() => A("techo_demanda", 290));
  const [precio, setPrecio] = useState(() => A("precio", 24.0));
  const [neto, setNeto] = useState(() => A("neto", 6.9));
  const [landed, setLanded] = useState(() => A("landed", 5.5));
  const [esc1, setEsc1] = useState<Escenario | null>(null);
  const [esc2, setEsc2] = useState<Escenario | null>(null);
  const [ticket, setTicket] = useState(1000);
  const [meses, setMeses] = useState(24);
  const [retorno, setRetorno] = useState<Retorno | null>(null);

  const simular = async () => {
    const base = { capital_propio: capProp, techo, precio, net_unit: neto,
                   landed, capital_inversor: capInv, pct_facturacion: pctFact };
    const [a, b] = await Promise.all([
      api.post<Escenario>("/api/inversores/escenario", { ...base, n_productos: 1 }),
      api.post<Escenario>("/api/inversores/escenario", { ...base, n_productos: 2 }),
    ]);
    setEsc1(a); setEsc2(b);
  };

  const trayectoria = async () => {
    const d = await api.post<Retorno>("/api/inversores/retorno", {
      ticket, pct_facturacion: pctFact, techo, precio, landed, meses,
    });
    setRetorno(d);
  };

  const pitchUrl = `/api/plan/pitch?ticket=${ticket}&pct=${pctFact}&techo=${techo}&precio=${precio}&landed=${landed}&meses=${meses}`;

  const tarjeta = (titulo: string, e: Escenario) => (
    <Card>
      <h3 className="font-bold text-[14px] mb-2 text-navy-deep">{titulo}</h3>
      <div className="grid grid-cols-2 gap-3">
        <Kpi label="Tu sueldo" valor={usd(e.sueldo_martin, 0)} hero />
        <Kpi label="Comisión inversor" valor={usd(e.comision_inversor, 0)}
             sub={`retorno ${pct(e.retorno_inversor_mes_pct)}/mes`} />
        <Kpi label="Sin inversor" valor={usd(e.sueldo_sin_inversor, 0)}
             sub={`delta ${usd(e.delta, 0)}`} tono={e.delta >= 0 ? "good" : "bad"} />
        <Kpi label="Cuello de botella" valor={e.cuello} sub={`${num(e.unidades_mes)} unid/mes`} />
      </div>
    </Card>
  );

  return (
    <>
      <Seccion titulo={t("iv_titulo")} sub={t("iv_sub")} />
      <Card className="mb-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <CampoNumero label="Capital propio (USD)" value={capProp} step={500} onValor={setCapProp} />
          <CampoNumero label="Capital inversor (USD)" value={capInv} step={500} onValor={setCapInv} />
          <CampoNumero label="Comisión (% facturación)" value={pctFact} step={1} onValor={setPctFact} />
          <CampoNumero label="Techo demanda" value={techo} onValor={(v) => setTecho(Math.round(v))} />
          <CampoNumero label="Precio (USD)" value={precio} step={0.5} onValor={setPrecio} />
          <CampoNumero label="Neto/unidad (USD)" value={neto} step={0.1} onValor={setNeto} />
          <CampoNumero label="Landed (USD)" value={landed} step={0.1} onValor={setLanded} />
        </div>
        <div className="mt-3"><Boton onClick={() => void simular()}>Simular</Boton></div>
      </Card>

      {esc1 && esc2 && (
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          {tarjeta("1 producto", esc1)}
          {tarjeta("2 productos", esc2)}
        </div>
      )}

      <Seccion titulo="Trayectoria del inversor" sub="Comisión reinvertida con techo honesto — pitch descargable" />
      <Card>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <CampoNumero label="Ticket (USD)" value={ticket} step={250} onValor={setTicket} />
          <CampoNumero label="Horizonte (meses)" value={meses} onValor={(v) => setMeses(Math.round(v))} />
        </div>
        <div className="mt-3 flex gap-3">
          <Boton onClick={() => void trayectoria()}>Calcular</Boton>
          <a href={pitchUrl} target="_blank" rel="noopener"
             className="px-4 py-2 rounded-lg font-bold text-[13.5px] border border-line text-navy hover:bg-navy-soft">
            {t("comun.descargar")} pitch HTML
          </a>
        </div>
        {retorno && (
          <div className="mt-4">
            <FilaKpis>
              <Kpi label="Comisión inicial" valor={usd(retorno.resumen.comision_inicial, 0)} sub="/mes" />
              <Kpi label="Comisión en meseta" valor={usd(retorno.resumen.comision_meseta, 0)} sub="/mes" hero />
              <Kpi label="Mes de saturación" valor={num(retorno.resumen.mes_saturacion)} sub="techo alcanzado" />
              <Kpi label="Capital final" valor={usd(retorno.resumen.capital_final, 0)}
                   sub={`x${retorno.resumen.multiplicador}`} tono="good" />
            </FilaKpis>
            <GraficoLineas datos={retorno.filas} x="mes"
              series={[{ campo: "comision_mes", nombre: "Comisión/mes" }, { campo: "capital", nombre: "Capital" }]} />
          </div>
        )}
      </Card>
    </>
  );
}
