// Componentes atomicos del design system (spec visual: mobile/css/estilos.css
// y el panel historico — navy/verde, KPI cards, badges de semaforo).
import { useT } from "../i18n";
import { ReactNode, InputHTMLAttributes, SelectHTMLAttributes } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-card border border-line rounded-2xl p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function Seccion({ titulo, sub, children }: { titulo: string; sub?: string; children?: ReactNode }) {
  return (
    <div className="mb-4">
      <div className="flex items-start gap-2">
        <div className="w-1 self-stretch rounded bg-green shrink-0" />
        <div>
          <h2 className="text-[17px] font-extrabold text-navy-deep leading-tight">{titulo}</h2>
          {sub && <p className="text-muted text-[12.5px] mt-0.5">{sub}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

type Tono = "navy" | "good" | "warn" | "bad";
const TONO_V: Record<Tono, string> = {
  navy: "text-navy-deep", good: "text-green-ink", warn: "text-amber", bad: "text-red",
};

export function Kpi({ label, valor, sub, tono = "navy", hero = false }: {
  label: string; valor: string; sub?: string; tono?: Tono; hero?: boolean;
}) {
  return (
    <div className={`rounded-xl border p-3.5 min-w-0 ${hero
      ? "bg-navy-deep border-navy-deep text-white"
      : "bg-card border-line"}`}>
      <div className={`text-[10.5px] font-bold uppercase tracking-wider truncate ${hero ? "text-white/70" : "text-muted"}`}>
        {label}
      </div>
      <div className={`tabular text-[22px] font-extrabold mt-0.5 truncate ${hero ? "text-white" : TONO_V[tono]}`}>
        {valor}
      </div>
      {sub && <div className={`text-[11px] mt-0.5 truncate ${hero ? "text-white/60" : "text-muted"}`}>{sub}</div>}
    </div>
  );
}

export function FilaKpis({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">{children}</div>;
}

const SEM: Record<string, string> = {
  verde: "bg-green/15 text-green-ink",
  amarillo: "bg-amber/15 text-amber",
  rojo: "bg-red/15 text-red",
  navy: "bg-navy/10 text-navy",
};

export function Badge({ texto, tono = "navy" }: { texto: string; tono?: string }) {
  return (
    <span className={`inline-block text-[11px] font-extrabold px-2.5 py-1 rounded-full ${SEM[tono] || SEM.navy}`}>
      {texto}
    </span>
  );
}

export function Semaforo({ valor }: { valor: string }) {
  // El backend manda el codigo (verde/amarillo/rojo); la etiqueta se traduce
  // aca. Si llega un valor inesperado se muestra tal cual, sin romper.
  const t = useT();
  const clave = `sem.${valor}`;
  const etiqueta = t(clave);
  return <Badge texto={(etiqueta === clave ? valor : etiqueta).toUpperCase()} tono={valor} />;
}

export function Boton({ children, onClick, tipo = "primario", disabled = false, className = "" }: {
  children: ReactNode; onClick?: () => void;
  tipo?: "primario" | "fantasma" | "peligro"; disabled?: boolean; className?: string;
}) {
  const estilos = {
    primario: "bg-navy text-white hover:bg-navy-deep",
    fantasma: "bg-transparent border border-line text-navy hover:bg-navy-soft",
    peligro: "bg-transparent border border-red/40 text-red hover:bg-red/5",
  }[tipo];
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2 rounded-lg font-bold text-[13.5px] transition-colors disabled:opacity-50 disabled:cursor-default ${estilos} ${className}`}
    >
      {children}
    </button>
  );
}

export function Campo(props: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  const { label, className = "", ...rest } = props;
  return (
    <label className="flex flex-col gap-1 min-w-0">
      <span className="text-[11px] font-bold uppercase tracking-wide text-muted truncate">{label}</span>
      <input
        {...rest}
        className={`border border-line rounded-lg px-3 py-2 text-[13.5px] bg-card focus:outline-none focus:border-navy ${className}`}
      />
    </label>
  );
}

export function CampoNumero(props: InputHTMLAttributes<HTMLInputElement> & {
  label: string; onValor: (v: number) => void;
}) {
  const { label, onValor, ...rest } = props;
  return (
    <Campo
      {...rest}
      label={label}
      type="number"
      onChange={(e) => onValor(parseFloat(e.target.value) || 0)}
    />
  );
}

export function Selector(props: SelectHTMLAttributes<HTMLSelectElement> & { label?: string }) {
  const { label, className = "", children, ...rest } = props;
  const sel = (
    <select
      {...rest}
      className={`border border-line rounded-lg px-3 py-2 text-[13.5px] bg-card focus:outline-none focus:border-navy ${className}`}
    >
      {children}
    </select>
  );
  if (!label) return sel;
  return (
    <label className="flex flex-col gap-1 min-w-0">
      <span className="text-[11px] font-bold uppercase tracking-wide text-muted truncate">{label}</span>
      {sel}
    </label>
  );
}

export function Alerta({ tipo = "info", children }: { tipo?: "info" | "warn" | "error" | "ok"; children: ReactNode }) {
  const estilos = {
    info: "bg-navy-soft text-navy-deep border-navy/20",
    warn: "bg-amber/10 text-amber border-amber/30",
    error: "bg-red/10 text-red border-red/30",
    ok: "bg-green/10 text-green-ink border-green/30",
  }[tipo];
  return <div className={`border rounded-xl px-4 py-3 text-[13px] my-3 ${estilos}`}>{children}</div>;
}

export function Spinner({ texto }: { texto?: string }) {
  return (
    <div className="flex items-center gap-2 text-muted text-[13px] py-3">
      <span className="inline-block w-4 h-4 border-2 border-line border-t-navy rounded-full animate-spin" />
      {texto}
    </div>
  );
}

export function Tabla({ cabeceras, filas }: { cabeceras: string[]; filas: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto border border-line rounded-xl">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="bg-navy-soft/60">
            {cabeceras.map((c, i) => (
              <th key={i} className="text-left font-bold text-[11px] uppercase tracking-wide text-muted px-3 py-2.5 whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i} className="border-t border-line hover:bg-navy-soft/30">
              {f.map((celda, j) => (
                <td key={j} className="px-3 py-2 tabular whitespace-nowrap">{celda}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export const usd = (v: number | null | undefined, dec = 2) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : `US$${v.toLocaleString("es-UY", { minimumFractionDigits: dec, maximumFractionDigits: dec })}`;

export const num = (v: number | null | undefined) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : v.toLocaleString("es-UY");

export const pct = (v: number | null | undefined, dec = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${v.toFixed(dec)}%`;
