// © 2026 Martín Viera. Todos los derechos reservados.
// Cliente HTTP del SPA. Base relativa: en produccion FastAPI sirve el SPA y
// la API desde el mismo origen (127.0.0.1:puerto); en dev Vite proxya a 8000.
export class ErrorApi extends Error {
  status: number;
  detalle: unknown;
  constructor(status: number, detalle: unknown) {
    super(`HTTP ${status}`);
    this.status = status;
    this.detalle = detalle;
  }
}

async function pedir<T>(
  ruta: string,
  init?: RequestInit,
  timeoutMs = 30000
): Promise<T> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(ruta, {
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      signal: ctl.signal,
      ...init,
    });
    if (!r.ok) {
      let detalle: unknown = null;
      try { detalle = await r.json(); } catch { /* sin body */ }
      throw new ErrorApi(r.status, detalle);
    }
    return (await r.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  get: <T>(ruta: string, timeoutMs?: number) =>
    pedir<T>(ruta, undefined, timeoutMs),
  post: <T>(ruta: string, body?: unknown, timeoutMs?: number) =>
    pedir<T>(ruta, { method: "POST", body: JSON.stringify(body ?? {}) }, timeoutMs),
  put: <T>(ruta: string, body?: unknown) =>
    pedir<T>(ruta, { method: "PUT", body: JSON.stringify(body ?? {}) }),
  del: <T>(ruta: string) => pedir<T>(ruta, { method: "DELETE" }),
  /** multipart (upload CSV Cerebro) — sin Content-Type manual. */
  subir: async <T>(ruta: string, archivo: File): Promise<T> => {
    const fd = new FormData();
    fd.append("file", archivo);
    const r = await fetch(ruta, { method: "POST", body: fd });
    if (!r.ok) throw new ErrorApi(r.status, await r.text());
    return (await r.json()) as T;
  },
};

/** Traduce un item de error de Pydantic (ver ctx.ge/le/lt) a espanol. */
function mensajePydantic(item: { msg?: string; type?: string; ctx?: Record<string, unknown> }): string {
  const ctx = item.ctx || {};
  switch (item.type) {
    case "greater_than_equal": return `tiene que ser mayor o igual a ${ctx.ge}`;
    case "less_than_equal": return `tiene que ser menor o igual a ${ctx.le}`;
    case "less_than": return `tiene que ser menor a ${ctx.lt}`;
    case "greater_than": return `tiene que ser mayor a ${ctx.gt}`;
    case "missing": return "es obligatorio";
    default: return item.msg || "valor invalido";
  }
}

/**
 * Convierte cualquier error de una llamada a la API en un mensaje en
 * español, listo para un <Alerta tipo="error">.
 *
 * POR QUE EXISTE: varias pantallas (Pricing, Caja, Inversores, Ventas, Plan)
 * mandan numeros que la API ahora valida (costo/flete/unidades no pueden ser
 * negativos, meses tiene un tope, etc. -- ver PricingIn/CajaIn/VentaIn en
 * api_rutas.py). Antes de esa validacion, un `.catch(() => {})` en cada
 * pantalla no perdia nada porque la API nunca fallaba por estos campos. Con
 * la validacion agregada, ese mismo catch silencioso paso a esconder un 422
 * real: el usuario escribe un valor invalido, la pantalla se queda mostrando
 * el ULTIMO resultado bueno sin ningun aviso, y no hay forma de saber que su
 * numero nuevo no se aplico.
 *
 * Usa el nombre TECNICO del campo (el que manda el backend en loc), no la
 * etiqueta traducida de cada pantalla -- es menos prolijo que mapear cada
 * campo a su etiqueta exacta, pero es siempre correcto: no hay riesgo de
 * mapear mal un campo a otro en alguna de las 5 pantallas que usan esto.
 */
export function mensajeError(e: unknown): string {
  if (e instanceof ErrorApi && e.status === 422 && e.detalle && typeof e.detalle === "object") {
    const cuerpo = e.detalle as { detail?: Array<{ loc?: unknown[]; msg?: string; type?: string; ctx?: Record<string, unknown> }> };
    if (Array.isArray(cuerpo.detail) && cuerpo.detail.length > 0) {
      const partes = cuerpo.detail.map((item) => {
        const loc = Array.isArray(item.loc) ? item.loc : [];
        const campo = loc.length ? String(loc[loc.length - 1]) : "un campo";
        return `${campo} ${mensajePydantic(item)}`;
      });
      return `Revisá estos valores: ${partes.join(" · ")}.`;
    }
  }
  if (e instanceof ErrorApi) return `No se pudo completar (error ${e.status}). Probá de nuevo.`;
  return "No se pudo completar. Probá de nuevo.";
}

/** Query string desde un objeto, omitiendo null/undefined/"". */
export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}
