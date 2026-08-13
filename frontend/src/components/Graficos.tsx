// © 2026 Martín Viera. Todos los derechos reservados.
// Graficos con Recharts + tokens de marca.
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
  BarChart, Bar, Legend,
} from "recharts";

const COLORES = ["#1e3a8a", "#3f9142", "#d97706", "#dc2626"];

export function GraficoLineas({ datos, x, series, alto = 260 }: {
  datos: Record<string, unknown>[];
  x: string;
  series: { campo: string; nombre: string }[];
  alto?: number;
}) {
  return (
    <div style={{ width: "100%", height: alto }}>
      <ResponsiveContainer>
        <LineChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis dataKey={x} tick={{ fontSize: 11 }} stroke="#64748b" />
          <YAxis tick={{ fontSize: 11 }} stroke="#64748b" width={70}
                 tickFormatter={(v: number) => v.toLocaleString("es-UY")} />
          <Tooltip formatter={(v: number) => v.toLocaleString("es-UY")} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Line key={s.campo} type="monotone" dataKey={s.campo} name={s.nombre}
                  stroke={COLORES[i % COLORES.length]} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GraficoBarras({ datos, x, series, alto = 240 }: {
  datos: Record<string, unknown>[];
  x: string;
  series: { campo: string; nombre: string }[];
  alto?: number;
}) {
  return (
    <div style={{ width: "100%", height: alto }}>
      <ResponsiveContainer>
        <BarChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis dataKey={x} tick={{ fontSize: 11 }} stroke="#64748b" />
          <YAxis tick={{ fontSize: 11 }} stroke="#64748b" width={70}
                 tickFormatter={(v: number) => v.toLocaleString("es-UY")} />
          <Tooltip formatter={(v: number) => v.toLocaleString("es-UY")} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Bar key={s.campo} dataKey={s.campo} name={s.nombre}
                 fill={COLORES[i % COLORES.length]} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
