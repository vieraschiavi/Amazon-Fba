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

/** Query string desde un objeto, omitiendo null/undefined/"". */
export function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}
