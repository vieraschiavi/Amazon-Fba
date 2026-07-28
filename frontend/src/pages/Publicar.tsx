import { useState } from "react";
import { api } from "../api/cliente";
import { Boton, Campo, CampoNumero, Card, Seccion, Spinner } from "../components/ui";
import { useT } from "../i18n";
import { useApp } from "../stores/app";
import { useProductoActivo } from "../stores/productoActivo";

interface Paquete { [k: string]: unknown }

export function Publicar() {
  const t = useT();
  const modoDemo = useApp((s) => s.modoDemo);
  const { activo, A } = useProductoActivo();
  const [nombre, setNombre] = useState(activo?.nombre ?? "");
  const [costo, setCosto] = useState(() => A("costo", 2.1));
  const [flete, setFlete] = useState(() => A("flete", 0.8));
  const [arancel, setArancel] = useState(() => A("arancel_pct", 6));
  const [prep, setPrep] = useState(() => A("prep", 0.5));
  const [techo, setTecho] = useState(() => A("techo_demanda", 290));
  const [html, setHtml] = useState("");
  const [paquete, setPaquete] = useState<Paquete | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const armar = async () => {
    if (!nombre.trim()) return;
    setOcupado(true);
    try {
      const d = await api.post<{ paquete: Paquete; html: string }>("/api/publicar", {
        nombre, costo, flete, arancel_pct: arancel, prep,
        techo_demanda: techo, usar_motor_propio: true, demo: modoDemo,
      }, 120000);
      setPaquete(d.paquete);
      setHtml(d.html);
    } catch { /* mantiene */ }
    setOcupado(false);
  };

  const descargar = () => {
    const blob = new Blob([html], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `paquete-publicacion-${nombre.replace(/\s+/g, "-")}.html`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <>
      <Seccion titulo={t("pub_titulo")} sub={t("pub_sub")} />
      <Card className="mb-4">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <Campo label={t("pub.producto")} value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <CampoNumero label={t("pub.costo")} value={costo} step={0.1} onValor={setCosto} />
          <CampoNumero label={t("pub.flete")} value={flete} step={0.1} onValor={setFlete} />
          <CampoNumero label={t("pub.arancel")} value={arancel} step={0.5} onValor={setArancel} />
          <CampoNumero label={t("pub.prep")} value={prep} step={0.1} onValor={setPrep} />
          <CampoNumero label={t("pub.techo_demanda")} value={techo} onValor={(v) => setTecho(Math.round(v))} />
        </div>
        <div className="mt-3 flex gap-3">
          <Boton onClick={() => void armar()} disabled={ocupado || !nombre.trim()}>{t("pub_btn")}</Boton>
          {html && <Boton tipo="fantasma" onClick={descargar}>{t("comun.descargar")} HTML</Boton>}
        </div>
        {ocupado && <Spinner texto={t("comun.cargando")} />}
      </Card>

      {paquete && html && (
        <Card>
          <iframe
            srcDoc={html}
            title="Paquete de publicación"
            className="w-full border border-line rounded-xl"
            style={{ height: "70vh" }}
            sandbox=""
          />
        </Card>
      )}
    </>
  );
}
