// © 2026 Martín Viera. Todos los derechos reservados.
// Store global: idioma, licencia, prefs. Se hidrata del server al arrancar
// (las prefs viven en SQLite via /api/prefs — el puerto puede variar entre
// arranques, asi que localStorage no es confiable en el desktop).
import { create } from "zustand";
import { api } from "../api/cliente";
import type { EstadoLicencia, Prefs } from "../api/tipos";
import type { Idioma } from "../i18n";

interface AppState {
  cargado: boolean;
  idioma: Idioma;
  licencia: EstadoLicencia | null;
  modoDemo: boolean;
  hidratar: () => Promise<void>;
  fijarIdioma: (i: Idioma) => void;
  fijarModoDemo: (v: boolean) => void;
  refrescarLicencia: () => Promise<void>;
}

export const useApp = create<AppState>((set, get) => ({
  cargado: false,
  idioma: "es",
  licencia: null,
  modoDemo: true,

  hidratar: async () => {
    try {
      const [prefs, lic] = await Promise.all([
        api.get<Prefs>("/api/prefs"),
        api.get<EstadoLicencia>("/api/licencia"),
      ]);
      set({
        idioma: (prefs.idioma as Idioma) || "es",
        modoDemo: prefs.modo_demo !== "0",
        licencia: lic,
        cargado: true,
      });
    } catch {
      set({ cargado: true }); // sin server no bloqueamos el render del error
    }
  },

  fijarIdioma: (i) => {
    set({ idioma: i });
    api.put("/api/prefs", { idioma: i }).catch(() => {});
  },

  fijarModoDemo: (v) => {
    set({ modoDemo: v });
    api.put("/api/prefs", { modo_demo: v ? "1" : "0" }).catch(() => {});
  },

  refrescarLicencia: async () => {
    const lic = await api.get<EstadoLicencia>("/api/licencia");
    set({ licencia: lic });
    void get; // (sin uso adicional)
  },
}));
