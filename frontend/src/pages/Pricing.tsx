import { useEffect, useState } from "react";
import { api, mensajeError } from "../api/cliente";
import type { ResultadoPricing } from "../api/tipos";
import { Alerta, Badge, Boton, Campo, CampoNumero, Card, FilaKpis, Kpi, Seccion, Semaforo, usd, pct } from "../components/ui";
import { useT } from "../i18n";
import { useProductoActivo } from "../stores/productoActivo";

export function Pricing() {
  const t = useT();
  // La estrategia la arma el backend en espanol y tiene solo dos valores;
  // se traduce aca y, ante cualquier otro, se muestra el texto original.
  const estrategiaTxt = (e: string) =>
    e === "objetivo" ? t("pr.estr_objetivo")
    : e.startsWith("competitivo") ? t("pr.estr_competitivo")
    : e;
  const { activo, A, cargar } = useProductoActivo();
  const [costo, setCosto] = useState(2.1);
  const [flete, setFlete] = useState(0.8);
  const [arancel, setArancel] = useState(6.0);
  const [prep, setPrep] = useState(0.5);
  const [fba, setFba] = useState(3.65);
  const [competencia, setCompetencia] = useState(19.99);
  const [res, setRes] = useState<ResultadoPricing | null>(null);
  const [errorCalculo, setErrorCalculo] = useState("");
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
      }).then((r) => { setRes(r); setErrorCalculo(""); })
        // Si el valor no sirve (ej. un costo negativo) la API lo rechaza: se
        // avisa y se deja el ULTIMO resultado valido a la vista (abajo sigue
        // mostrando ese numero, no uno recalculado con el valor invalido).
        .catch((e) => setErrorCalculo(mensajeError(e)));
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
          <CampoNumero label={t("pr.costo_unitario")} value={costo} step={0.1} onValor={setCosto} />
          <CampoNumero label={t("pr.flete_unitario")} value={flete} step={0.1} onValor={setFlete} />
          <CampoNumero label={t("pr.arancel")} value={arancel} step={0.5} onValor={setArancel} />
          <CampoNumero label={t("pr.prep")} value={prep} step={0.1} onValor={setPrep} />
          <CampoNumero label={t("pr.fba_fee")} value={fba} step={0.05} onValor={setFba} />
          <CampoNumero label={t("pr.precio_competencia_0")} value={competencia} step={0.5} onValor={setCompetencia} />
        </div>
      </Card>

      {errorCalculo && <Alerta tipo="error">{errorCalculo}</Alerta>}

      {res && (
        <>
          <FilaKpis>
            <Kpi label={t("pr.landed_cost")} valor={usd(res.landed)} sub={t("pr.costo_desembarcado")} />
            <Kpi label={t("pr.precio_sugerido")} valor={usd(res.precio)} sub={estrategiaTxt(res.estrategia)} hero />
            <Kpi label={t("pr.margen")} valor={pct(res.margen_pct)} sub={t("pr.neto_precio")}
                 tono={res.semaforo === "verde" ? "good" : res.semaforo === "amarillo" ? "warn" : "bad"} />
            <Kpi label="ROI" valor={pct(res.roi_pct)} sub={t("pr.neto_landed")} />
          </FilaKpis>
          <div className="flex items-center gap-3 mb-4">
            <Semaforo valor={res.semaforo} />
            <span className="text-[13px] text-muted">
              {t("pr.break_even")} {usd(res.break_even)} · {t("pr.neto_unidad")} {usd(res.neto)} ·
              {t("pr.referral")} {usd(res.referral)} · {t("pr.ads")} {usd(res.ads)}
            </span>
          </div>
        </>
      )}

      <Card>
        <h3 className="font-bold text-[14px] mb-3 text-navy-deep">{t("pr_btn")}</h3>
        <div className="grid md:grid-cols-3 gap-3">
          <Campo label={t("pr.nombre_producto")} value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <Campo label={t("pr.asin_opcional")} value={asin} onChange={(e) => setAsin(e.target.value)} />
          <CampoNumero label={t("pr.techo_demanda_unid_mes")} value={techo} onValor={(v) => setTecho(Math.round(v))} />
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Boton onClick={() => void guardar()}>{t("pr_btn")}</Boton>
          {guardado === "ok" && <Badge texto={t("pr.guardado")} tono="verde" />}
          {guardado === "nombre" && <Badge texto={t("pr.falta_nombre")} tono="amarillo" />}
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
