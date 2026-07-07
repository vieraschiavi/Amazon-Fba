import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import type { ResultadoPricing } from "../api/tipos";
import { Alerta, Badge, Boton, Campo, CampoNumero, Card, FilaKpis, Kpi, Seccion, Semaforo, usd, pct } from "../components/ui";
import { useT } from "../i18n";
import { useProductoActivo } from "../stores/productoActivo";

export function Pricing() {
  const t = useT();
  const { activo, A, cargar } = useProductoActivo();
  const [costo, setCosto] = useState(2.1);
  const [flete, setFlete] = useState(0.8);
  const [arancel, setArancel] = useState(6.0);
  const [prep, setPrep] = useState(0.5);
  const [fba, setFba] = useState(3.65);
  const [competencia, setCompetencia] = useState(19.99);
  const [res, setRes] = useState<ResultadoPricing | null>(null);
  const [nombre, setNombre] = useState("");
  const [asin, setAsin] = useState("");
  const [techo, setTecho] = useState(290);
  const [guardado, setGuardado] = useState("");

  // precarga desde el producto activo (patron A() del panel historico)
  useEffect(() => {
    setCosto(A("costo", 2.1)); setFlete(A("flete", 0.8));
    setArancel(A("arancel_pct", 6.0)); setPrep(A("prep", 0.5));
    setFba(A("fba_fee", 3.65)); setTecho(A("techo_demanda", 290));
    if (activo) setNombre(activo.nombre);
  }, [activo]); // eslint-disable-line react-hooks/exhaustive-deps

  // recalculo automatico con debounce — el semaforo responde mientras escribis
  useEffect(() => {
    const timer = setTimeout(() => {
      api.post<ResultadoPricing>("/api/pricing", {
        costo, flete, arancel_pct: arancel, prep,
        fba_fee: fba || null, precio_competencia: competencia || null,
      }).then(setRes).catch(() => {});
    }, 350);
    return () => clearTimeout(timer);
  }, [costo, flete, arancel, prep, fba, competencia]);

  const guardar = async () => {
    if (!nombre.trim()) { setGuardado("nombre"); return; }
    const r = await api.post<{ ok: boolean; mensaje: string }>("/portfolio/producto", {
      nombre, asin, costo, flete, arancel_pct: arancel, prep,
      fba_fee: fba || null, precio_competencia: competencia || null,
      techo_demanda: techo,
    });
    setGuardado(r.ok ? "ok" : "error");
    if (r.ok) await cargar();
    setTimeout(() => setGuardado(""), 3000);
  };

  return (
    <>
      <Seccion titulo={t("pr_titulo")} sub={t("pr_sub")} />
      <Card className="mb-4">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <CampoNumero label="Costo unitario (USD)" value={costo} step={0.1} onValor={setCosto} />
          <CampoNumero label="Flete unitario (USD)" value={flete} step={0.1} onValor={setFlete} />
          <CampoNumero label="Arancel (%)" value={arancel} step={0.5} onValor={setArancel} />
          <CampoNumero label="Prep (USD)" value={prep} step={0.1} onValor={setPrep} />
          <CampoNumero label="FBA fee (USD)" value={fba} step={0.05} onValor={setFba} />
          <CampoNumero label="Precio competencia (USD, 0=sin)" value={competencia} step={0.5} onValor={setCompetencia} />
        </div>
      </Card>

      {res && (
        <>
          <FilaKpis>
            <Kpi label="Landed cost" valor={usd(res.landed)} sub="costo desembarcado" />
            <Kpi label="Precio sugerido" valor={usd(res.precio)} sub={res.estrategia} hero />
            <Kpi label="Margen" valor={pct(res.margen_pct)} sub="neto / precio"
                 tono={res.semaforo === "verde" ? "good" : res.semaforo === "amarillo" ? "warn" : "bad"} />
            <Kpi label="ROI" valor={pct(res.roi_pct)} sub="neto / landed" />
          </FilaKpis>
          <div className="flex items-center gap-3 mb-4">
            <Semaforo valor={res.semaforo} />
            <span className="text-[13px] text-muted">
              Break-even {usd(res.break_even)} · Neto/unidad {usd(res.neto)} ·
              Referral {usd(res.referral)} · Ads {usd(res.ads)}
            </span>
          </div>
        </>
      )}

      <Card>
        <h3 className="font-bold text-[14px] mb-3 text-navy-deep">{t("pr_btn")}</h3>
        <div className="grid md:grid-cols-3 gap-3">
          <Campo label="Nombre del producto" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <Campo label="ASIN (opcional)" value={asin} onChange={(e) => setAsin(e.target.value)} />
          <CampoNumero label="Techo demanda (unid/mes)" value={techo} onValor={(v) => setTecho(Math.round(v))} />
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Boton onClick={() => void guardar()}>{t("pr_btn")}</Boton>
          {guardado === "ok" && <Badge texto="Guardado" tono="verde" />}
          {guardado === "nombre" && <Badge texto="Falta el nombre" tono="amarillo" />}
        </div>
        {activo && (
          <Alerta tipo="info">
            Campos precargados de «{activo.nombre}» — podés ajustarlos igual.
          </Alerta>
        )}
      </Card>
    </>
  );
}
