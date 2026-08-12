import { useState } from "react";
import { api, mensajeError } from "../api/cliente";
import { GraficoLineas } from "../components/Graficos";
import { Alerta, Boton, CampoNumero, Card, FilaKpis, Kpi, Seccion, usd, num, pct } from "../components/ui";
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
  // Antes ninguna de las dos llamadas de abajo tenia try/catch: si la API
  // rechazaba un valor (ej. capital negativo, comision > 100%), la promesa
  // quedaba rechazada sin capturar -- ni un aviso en pantalla, ni siquiera
  // "no paso nada" limpio, un error de React en la consola que el usuario
  // nunca ve. Ahora se captura y se muestra que fue lo que no sirvio.
  const [errorEsc, setErrorEsc] = useState("");
  const [errorRet, setErrorRet] = useState("");

  const simular = async () => {
    const base = { capital_propio: capProp, techo, precio, net_unit: neto,
                   landed, capital_inversor: capInv, pct_facturacion: pctFact };
    try {
      const [a, b] = await Promise.all([
        api.post<Escenario>("/api/inversores/escenario", { ...base, n_productos: 1 }),
        api.post<Escenario>("/api/inversores/escenario", { ...base, n_productos: 2 }),
      ]);
      setEsc1(a); setEsc2(b); setErrorEsc("");
    } catch (e) { setErrorEsc(mensajeError(e)); }
  };

  const trayectoria = async () => {
    try {
      const d = await api.post<Retorno>("/api/inversores/retorno", {
        ticket, pct_facturacion: pctFact, techo, precio, landed, meses,
      });
      setRetorno(d); setErrorRet("");
    } catch (e) { setErrorRet(mensajeError(e)); }
  };

  const pitchUrl = `/api/plan/pitch?ticket=${ticket}&pct=${pctFact}&techo=${techo}&precio=${precio}&landed=${landed}&meses=${meses}`;

  const tarjeta = (titulo: string, e: Escenario) => (
    <Card>
      <h3 className="font-bold text-[14px] mb-2 text-navy-deep">{titulo}</h3>
      <div className="grid grid-cols-2 gap-3">
        <Kpi label={t("iv.sueldo")} valor={usd(e.sueldo_martin, 0)} hero />
        <Kpi label={t("iv.comision_inversor")} valor={usd(e.comision_inversor, 0)}
             sub={`retorno ${pct(e.retorno_inversor_mes_pct)}/mes`} />
        <Kpi label={t("iv.inversor")} valor={usd(e.sueldo_sin_inversor, 0)}
             sub={`delta ${usd(e.delta, 0)}`} tono={e.delta >= 0 ? "good" : "bad"} />
        <Kpi label={t("iv.cuello_botella")} valor={e.cuello} sub={`${num(e.unidades_mes)} unid/mes`} />
      </div>
    </Card>
  );

  return (
    <>
      <Seccion titulo={t("iv_titulo")} sub={t("iv_sub")} />
      <Card className="mb-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <CampoNumero label={t("iv.capital_propio")} value={capProp} step={500} onValor={setCapProp} />
          <CampoNumero label={t("iv.capital_inversor")} value={capInv} step={500} onValor={setCapInv} />
          <CampoNumero label={t("iv.comision_facturacion")} value={pctFact} step={1} onValor={setPctFact} />
          <CampoNumero label={t("iv.techo_demanda")} value={techo} onValor={(v) => setTecho(Math.round(v))} />
          <CampoNumero label={t("iv.precio")} value={precio} step={0.5} onValor={setPrecio} />
          <CampoNumero label={t("iv.neto_unidad")} value={neto} step={0.1} onValor={setNeto} />
          <CampoNumero label={t("iv.landed")} value={landed} step={0.1} onValor={setLanded} />
        </div>
        <div className="mt-3"><Boton onClick={() => void simular()}>{t("iv.simular")}</Boton></div>
        {errorEsc && <Alerta tipo="error">{errorEsc}</Alerta>}
      </Card>

      {esc1 && esc2 && (
        <div className="grid md:grid-cols-2 gap-4 mb-5">
          {tarjeta("1 producto", esc1)}
          {tarjeta("2 productos", esc2)}
        </div>
      )}

      <Seccion titulo={t("iv.trayectoria_inversor")} sub={t("iv.comision_reinvertida_techo_honesto")} />
      <Card>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <CampoNumero label={t("iv.ticket")} value={ticket} step={250} onValor={setTicket} />
          <CampoNumero label={t("iv.horizonte_meses")} value={meses} onValor={(v) => setMeses(Math.round(v))} />
        </div>
        <div className="mt-3 flex gap-3">
          <Boton onClick={() => void trayectoria()}>{t("iv.calcular")}</Boton>
          <a href={pitchUrl} target="_blank" rel="noopener"
             className="px-4 py-2 rounded-lg font-bold text-[13.5px] border border-line text-navy hover:bg-navy-soft">
            {t("comun.descargar")} pitch HTML
          </a>
        </div>
        {errorRet && <Alerta tipo="error">{errorRet}</Alerta>}
        {retorno && (
          <div className="mt-4">
            <FilaKpis>
              <Kpi label={t("iv.comision_inicial")} valor={usd(retorno.resumen.comision_inicial, 0)} sub={t("iv.mes")} />
              <Kpi label={t("iv.comision_meseta")} valor={usd(retorno.resumen.comision_meseta, 0)} sub={t("iv.mes")} hero />
              <Kpi label={t("iv.mes_saturacion")} valor={num(retorno.resumen.mes_saturacion)} sub={t("iv.techo_alcanzado")} />
              <Kpi label={t("iv.capital_final")} valor={usd(retorno.resumen.capital_final, 0)}
                   sub={`x${retorno.resumen.multiplicador}`} tono="good" />
            </FilaKpis>
            <GraficoLineas datos={retorno.filas} x="mes"
              series={[{ campo: "comision_mes", nombre: t("iv.serie_comision_mes") }, { campo: "capital", nombre: t("iv.serie_capital") }]} />
          </div>
        )}
      </Card>
    </>
  );
}
