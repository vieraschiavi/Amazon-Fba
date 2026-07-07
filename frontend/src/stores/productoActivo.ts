// Producto activo: el patron A() del panel historico. Elegis un producto del
// portafolio UNA vez y sus datos precargan los formularios de Pricing, Caja
// y Ventas. El id elegido persiste server-side (/api/prefs).
import { create } from "zustand";
import { api } from "../api/cliente";
import type { Producto } from "../api/tipos";

interface ProductoActivoState {
  lista: Producto[];
  activo: Producto | null;
  cargar: () => Promise<void>;
  elegir: (id: number | null) => void;
  /** A(campo, defecto): valor del producto activo o el defecto. */
  A: (campo: keyof Producto, defecto: number) => number;
}

export const useProductoActivo = create<ProductoActivoState>((set, get) => ({
  lista: [],
  activo: null,

  cargar: async () => {
    try {
      const [{ productos }, prefs] = await Promise.all([
        api.get<{ productos: Producto[] }>("/api/productos"),
        api.get<{ producto_activo_id: string }>("/api/prefs"),
      ]);
      const idGuardado = parseInt(prefs.producto_activo_id || "", 10);
      const activo = productos.find((p) => p.id === idGuardado) || null;
      set({ lista: productos, activo });
    } catch {
      set({ lista: [], activo: null });
    }
  },

  elegir: (id) => {
    const activo = get().lista.find((p) => p.id === id) || null;
    set({ activo });
    api.put("/api/prefs", { producto_activo_id: id ? String(id) : "" })
      .catch(() => {});
  },

  A: (campo, defecto) => {
    const v = get().activo?.[campo];
    return typeof v === "number" && !Number.isNaN(v) ? v : defecto;
  },
}));
