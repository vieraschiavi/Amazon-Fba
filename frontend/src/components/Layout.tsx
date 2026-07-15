// Layout SaaS: sidebar de navegacion agrupada + topbar con idioma, producto
// activo y badge de licencia/demo.
import { ReactNode, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useApp } from "../stores/app";
import { useProductoActivo } from "../stores/productoActivo";
import { useT, IDIOMAS, Idioma } from "../i18n";
import { api } from "../api/cliente";
import { Badge, Selector } from "./ui";

const GRUPOS: { grupo: string; items: { ruta: string; clave: string }[] }[] = [
  { grupo: "sb.grupo.descubrir", items: [
    { ruta: "/recomendador", clave: "tab_recomendador" },
    { ruta: "/investigacion", clave: "tab_investigacion" },
    { ruta: "/mercado", clave: "tab_mercado" },
    { ruta: "/jungle-scout", clave: "tab_jungle" },
  ]},
  { grupo: "sb.grupo.operar", items: [
    { ruta: "/pricing", clave: "tab_pricing" },
    { ruta: "/portafolio", clave: "tab_portafolio" },
    { ruta: "/publicar", clave: "tab_publicar" },
    { ruta: "/ventas", clave: "tab_ventas" },
    { ruta: "/inventario", clave: "tab_inventario" },
  ]},
  { grupo: "sb.grupo.planificar", items: [
    { ruta: "/caja", clave: "tab_caja" },
    { ruta: "/inversores", clave: "tab_inversores" },
    { ruta: "/plan", clave: "tab_plan" },
  ]},
  { grupo: "sb.grupo.sistema", items: [
    { ruta: "/herramientas", clave: "tab_herramientas" },
    { ruta: "/asistente", clave: "tab_asistente" },
    { ruta: "/alertas", clave: "tab_alertas" },
    { ruta: "/config", clave: "tab_config" },
    { ruta: "/ayuda", clave: "tab_ayuda" },
  ]},
];

function SelectorProductoActivo() {
  const t = useT();
  const { lista, activo, elegir, cargar } = useProductoActivo();
  useEffect(() => { void cargar(); }, [cargar]);
  return (
    <Selector
      value={activo?.id ?? ""}
      onChange={(e) => elegir(e.target.value ? parseInt(e.target.value, 10) : null)}
      title={t("top.producto_activo")}
      className="max-w-[230px]"
    >
      <option value="">{t("top.sin_producto")}</option>
      {lista.map((p) => (
        <option key={p.id} value={p.id}>{p.nombre} · {p.asin || "s/ASIN"}</option>
      ))}
    </Selector>
  );
}

function BotonEjemplo() {
  const t = useT();
  const { cargar } = useProductoActivo();
  const alternar = async () => {
    const { cargado } = await api.get<{ cargado: boolean }>("/api/demo/ejemplo");
    if (cargado) await api.del("/api/demo/ejemplo");
    else await api.post("/api/demo/ejemplo");
    await cargar();
  };
  return (
    <button
      onClick={() => void alternar()}
      className="text-[11.5px] text-muted hover:text-navy underline underline-offset-2"
    >
      {t("sb.ejemplo_cargar")} / {t("sb.ejemplo_quitar").toLowerCase()}
    </button>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const t = useT();
  const { idioma, fijarIdioma, licencia } = useApp();
  const loc = useLocation();

  return (
    <div className="flex h-full">
      {/* ---------- Sidebar ---------- */}
      <aside className="w-56 shrink-0 bg-navy-deep text-white flex flex-col">
        <div className="flex items-center gap-2.5 px-4 py-4">
          <img src="./icon.png" alt="" className="w-8 h-8 rounded-lg" />
          <div className="leading-tight">
            <div className="font-extrabold text-[15px]">MV <span className="text-green">FBA IA</span></div>
            <div className="text-[10px] text-white/50">{t("app.tagline")}</div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 pb-4">
          {GRUPOS.map((g) => (
            <div key={g.grupo} className="mt-3">
              <div className="px-2 text-[10px] font-bold uppercase tracking-widest text-white/40">
                {t(g.grupo)}
              </div>
              {g.items.map((it) => (
                <NavLink
                  key={it.ruta}
                  to={it.ruta}
                  className={({ isActive }) =>
                    `block px-3 py-2 mt-0.5 rounded-lg text-[13px] font-semibold transition-colors ${
                      isActive
                        ? "bg-white/12 text-white border-l-2 border-green"
                        : "text-white/65 hover:text-white hover:bg-white/5"
                    }`
                  }
                >
                  {t(it.clave)}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-white/10">
          <BotonEjemplo />
        </div>
      </aside>

      {/* ---------- Main ---------- */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-5 py-2.5 bg-card border-b border-line">
          <div className="flex-1 min-w-0">
            <SelectorProductoActivo />
          </div>
          {licencia && (
            <Badge
              texto={licencia.licencia
                ? t("badge.licencia")
                : t("badge.demo", { n: Math.ceil(licencia.dias_restantes) })}
              tono={licencia.licencia || licencia.dias_restantes > 1 ? "verde" : "amarillo"}
            />
          )}
          <Selector
            value={idioma}
            onChange={(e) => fijarIdioma(e.target.value as Idioma)}
            aria-label="Idioma"
          >
            {IDIOMAS.map((i) => (
              <option key={i.codigo} value={i.codigo}>{i.nombre}</option>
            ))}
          </Selector>
        </header>
        <main key={loc.pathname} className="flex-1 overflow-y-auto p-5">
          <div className="max-w-6xl mx-auto">{children}</div>
        </main>
      </div>
    </div>
  );
}
