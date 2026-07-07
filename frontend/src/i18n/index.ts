// i18n del SPA — misma semantica que core/i18n.t() de Python: si la clave no
// existe devuelve la clave tal cual (nunca rompe la pantalla), y soporta
// interpolacion {var}. El idioma vive en el store global (persistido
// server-side en /api/prefs porque el puerto puede variar entre arranques).
import es from "./es.json";
import en from "./en.json";
import pt from "./pt.json";
import { useApp } from "../stores/app";

export type Idioma = "es" | "en" | "pt";
export const IDIOMAS: { codigo: Idioma; nombre: string }[] = [
  { codigo: "es", nombre: "Español" },
  { codigo: "en", nombre: "English" },
  { codigo: "pt", nombre: "Português" },
];

const DICCIONARIOS: Record<Idioma, Record<string, string>> = { es, en, pt };

export function traducir(
  idioma: Idioma,
  clave: string,
  vars?: Record<string, string | number>
): string {
  let texto = DICCIONARIOS[idioma]?.[clave] ?? DICCIONARIOS.es[clave] ?? clave;
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      texto = texto.replaceAll(`{${k}}`, String(v));
    }
  }
  return texto;
}

/** Hook: t("clave") en el idioma activo del store. */
export function useT() {
  const idioma = useApp((s) => s.idioma);
  return (clave: string, vars?: Record<string, string | number>) =>
    traducir(idioma, clave, vars);
}
