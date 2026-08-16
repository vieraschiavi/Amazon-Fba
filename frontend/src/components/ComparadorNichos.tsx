// © 2026 Martín Viera. Todos los derechos reservados.
// Comparador de nichos por demanda relativa (gratis, autocompletado Amazon).
// Reutilizado en Mercado y Recomendador — misma logica, un solo componente.
import { useState } from "react";
import { api, mensajeError } from "../api/cliente";
import { useApp } from "../stores/app";
import { useT } from "../i18n";
import { Alerta, Badge, Boton, Campo, Spinner, Tabla, num } from "./ui";

interface Demanda {
  ok: boolean; keyword: string; amplitud: number; demanda_score: number;
  nivel: string;
}
interface Comparacion { ok: boolean; ranking: Demanda[]; nota_honesta: string }

export function ComparadorNichos({ inicial = "" }: { inicial?: string }) {
  const t = useT();
  const modoDemo = useApp((s) => s.modoDemo);
  const [texto, setTexto] = useState(inicial);
  const [comparacion, setComparacion] = useState<Comparacion | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  const comparar = async () => {
    const lista = texto.split(",").map((s) => s.trim()).filter(Boolean).slice(0, 8);
    if (lista.length < 2) return;
    setOcupado(true); setComparacion(null);
    try {
      const d = await api.post<Comparacion>("/api/demanda/comparar",
        { keywords: lista, demo: modoDemo }, 120000);
      setComparacion(d); setError("");
    } catch (e) { setError(mensajeError(e)); }
    setOcupado(false);
  };

  return (
    <div>
      <div className="flex gap-3 items-end flex-wrap">
        <Campo label={t("cmp.productos_separados_coma")}
               value={texto} onChange={(e) => setTexto(e.target.value)}
               placeholder="yoga mat, garlic press, dog bed"
               className="w-96" />
        <Boton tipo="fantasma" onClick={() => void comparar()} disabled={ocupado}>
          {t("comun.comparar")}
        </Boton>
      </div>
      {ocupado && <Spinner texto={t("cmp.midiendo_demanda_cada_nicho")} />}
      {error && <Alerta tipo="error">{error}</Alerta>}
      {comparacion && comparacion.ok && (
        <div className="mt-3">
          <Tabla
            cabeceras={["#", "Nicho", "Demanda", "Nivel", "Amplitud"]}
            filas={comparacion.ranking.map((r, i) => [
              i + 1, r.keyword,
              r.ok ? `${r.demanda_score}/100` : "—",
              r.ok ? <Badge key="n" texto={r.nivel}
                tono={r.demanda_score >= 65 ? "verde" : r.demanda_score >= 40 ? "amarillo" : "rojo"} /> : "sin datos",
              r.ok ? num(r.amplitud) : "—",
            ])}
          />
        </div>
      )}
    </div>
  );
}
