import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import { Alerta, Badge, Boton, Campo, CampoNumero, Card, Seccion, Selector, Spinner, Tabla } from "../components/ui";
import { useT } from "../i18n";
import { useApp } from "../stores/app";

// Herramientas sueltas imitadas de SellerForge, todas offline y sin APIs pagas:
//  - Generador de URLs de Amazon (producto, búsqueda, add-to-cart, atribución).
//  - Generador de Plan de Acción (POA) para suspensiones (agents/poa.py).

export function Herramientas() {
  const t = useT();
  return (
    <>
      <Seccion titulo={t("hr_titulo")} sub={t("hr_sub")} />
      <GeneradorUrls />
      <GeneradorPoa />
    </>
  );
}

const DOMINIOS: [string, string][] = [
  ["amazon.com", "US"], ["amazon.co.uk", "UK"], ["amazon.de", "DE"],
  ["amazon.es", "ES"], ["amazon.fr", "FR"], ["amazon.it", "IT"],
  ["amazon.ca", "CA"], ["amazon.com.mx", "MX"], ["amazon.com.br", "BR"],
  ["amazon.co.jp", "JP"],
];

function BotonCopiar({ texto }: { texto: string }) {
  const [ok, setOk] = useState(false);
  const copiar = async () => {
    try { await navigator.clipboard.writeText(texto); setOk(true); setTimeout(() => setOk(false), 1500); }
    catch { /* clipboard bloqueado */ }
  };
  return (
    <button onClick={() => void copiar()}
            className="text-[12px] text-navy hover:underline underline-offset-2 whitespace-nowrap">
      {ok ? "✓ copiado" : "copiar"}
    </button>
  );
}

function GeneradorUrls() {
  const t = useT();
  const [asin, setAsin] = useState("");
  const [kw, setKw] = useState("");
  const [qty, setQty] = useState(1);
  const [dom, setDom] = useState("amazon.com");
  const [tag, setTag] = useState("");

  const a = asin.trim();
  const conTag = (u: string) => (tag.trim() ? u + (u.includes("?") ? "&" : "?") + "tag=" + encodeURIComponent(tag.trim()) : u);
  const urls: [string, string][] = [];
  if (a) {
    urls.push([t("hr_url_producto"), conTag(`https://www.${dom}/dp/${encodeURIComponent(a)}`)]);
    urls.push([t("hr_url_cart"), `https://www.${dom}/gp/aws/cart/add.html?ASIN.1=${encodeURIComponent(a)}&Quantity.1=${Math.max(1, qty)}`]);
  }
  if (kw.trim()) {
    urls.push([t("hr_url_busqueda"), conTag(`https://www.${dom}/s?k=${encodeURIComponent(kw.trim())}`)]);
    if (a) urls.push([t("hr_url_super"), conTag(`https://www.${dom}/s?k=${encodeURIComponent(kw.trim())}&field-asin=${encodeURIComponent(a)}`)]);
  }

  return (
    <Card className="mt-4">
      <h3 className="font-bold text-[14px] text-navy-deep mb-1">{t("hr_url_titulo")}</h3>
      <p className="text-[12px] text-muted mb-3">{t("hr_url_sub")}</p>
      <div className="flex gap-3 items-end flex-wrap">
        <Campo label="ASIN" value={asin} onChange={(e) => setAsin(e.target.value)} className="w-40" placeholder="B0..." />
        <Campo label={t("hr_url_kw")} value={kw} onChange={(e) => setKw(e.target.value)} className="w-52" placeholder="garlic press" />
        <CampoNumero label={t("hr_url_qty")} value={qty} onValor={(v) => setQty(Math.max(1, Math.round(v)))} className="w-24" />
        <Selector label="Marketplace" value={dom} onChange={(e) => setDom(e.target.value)}>
          {DOMINIOS.map(([d, c]) => <option key={d} value={d}>{c} — {d}</option>)}
        </Selector>
        <Campo label={t("hr_url_tag")} value={tag} onChange={(e) => setTag(e.target.value)} className="w-40" placeholder="tag-20" />
      </div>
      {urls.length === 0 ? (
        <p className="text-[12px] text-muted mt-3">{t("hr_url_vacio")}</p>
      ) : (
        <div className="mt-3">
          <Tabla
            cabeceras={["Tipo", "URL", ""]}
            filas={urls.map(([nombre, u]) => [
              nombre,
              <a key="u" href={u} target="_blank" rel="noreferrer"
                 className="text-[12px] text-navy break-all hover:underline">{u}</a>,
              <BotonCopiar key="c" texto={u} />,
            ])}
          />
        </div>
      )}
    </Card>
  );
}

interface PoaResp {
  ok: boolean; modo: "online" | "offline"; nota: string;
  secciones: { titulo: string; puntos: string[] }[]; texto: string;
}

function GeneradorPoa() {
  const t = useT();
  const idioma = useApp((s) => s.idioma);
  const [tipos, setTipos] = useState<Record<string, string>>({});
  const [tipo, setTipo] = useState("autenticidad");
  const [motivo, setMotivo] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [res, setRes] = useState<PoaResp | null>(null);

  useEffect(() => {
    api.get<{ tipos: Record<string, string> }>("/api/poa/tipos")
      .then((d) => { setTipos(d.tipos); setTipo(Object.keys(d.tipos)[0] || "otro"); })
      .catch(() => {});
  }, []);

  const generar = async () => {
    setOcupado(true);
    const d = await api.post<PoaResp>("/api/poa", { motivo, tipo, idioma }, 60000).catch(() => null);
    setRes(d);
    setOcupado(false);
  };

  const descargar = () => {
    if (!res) return;
    const blob = new Blob([res.texto], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "plan-de-accion-amazon.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="mt-4">
      <h3 className="font-bold text-[14px] text-navy-deep mb-1">{t("hr_poa_titulo")}</h3>
      <p className="text-[12px] text-muted mb-3">{t("hr_poa_sub")}</p>
      <div className="flex gap-3 items-end flex-wrap mb-3">
        <Selector label={t("hr_poa_tipo")} value={tipo} onChange={(e) => setTipo(e.target.value)} className="max-w-[320px]">
          {Object.entries(tipos).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Selector>
        <Boton onClick={() => void generar()} disabled={ocupado}>{t("hr_poa_btn")}</Boton>
      </div>
      <label className="flex flex-col gap-1">
        <span className="text-[11px] font-bold uppercase tracking-wide text-muted">{t("hr_poa_motivo")}</span>
        <textarea value={motivo} onChange={(e) => setMotivo(e.target.value)} rows={3}
                  placeholder={t("hr_poa_motivo_ph")}
                  className="border border-line rounded-lg px-3 py-2 text-[13.5px] bg-card focus:outline-none focus:border-navy" />
      </label>

      {ocupado && <Spinner texto="Generando…" />}
      {res && res.ok && (
        <div className="mt-4">
          <div className="flex items-center gap-3 mb-2">
            <Badge texto={res.modo === "online" ? t("hr_poa_ia") : t("hr_poa_plantilla")}
                   tono={res.modo === "online" ? "verde" : "navy"} />
            <Boton tipo="fantasma" onClick={descargar}>{t("hr_poa_descargar")}</Boton>
          </div>
          {res.secciones.map((s, i) => (
            <div key={i} className="mb-3">
              <h4 className="font-bold text-[13px] text-navy-deep">{i + 1}. {s.titulo}</h4>
              <ul className="list-disc ml-5 text-[13px]">
                {s.puntos.map((p, j) => <li key={j}>{p}</li>)}
              </ul>
            </div>
          ))}
          <Alerta tipo="warn">{res.nota}</Alerta>
        </div>
      )}
    </Card>
  );
}
