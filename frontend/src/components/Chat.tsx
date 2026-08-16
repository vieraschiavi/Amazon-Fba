// © 2026 Martín Viera. Todos los derechos reservados.
// Chat stateless reutilizable (Asistente IA de negocio y Dudas del programa):
// el cliente acumula el historial y lo reenvia completo en cada llamada.
import { FormEvent, useRef, useState } from "react";
import { api } from "../api/cliente";
import type { MensajeChat, RespuestaChat } from "../api/tipos";
import { useT } from "../i18n";
import { useApp } from "../stores/app";
import { Boton } from "./ui";

export function Chat({ endpoint, sugeridas }: {
  endpoint: string;                 // /api/asistente/negocio | /api/asistente/programa
  sugeridas: string[];
}) {
  const t = useT();
  const idioma = useApp((s) => s.idioma);
  const [historial, setHistorial] = useState<MensajeChat[]>([]);
  const [texto, setTexto] = useState("");
  const [pensando, setPensando] = useState(false);
  const fondo = useRef<HTMLDivElement>(null);

  const preguntar = async (pregunta: string) => {
    if (!pregunta.trim() || pensando) return;
    const nuevo: MensajeChat[] = [...historial, { role: "user", content: pregunta }];
    setHistorial(nuevo);
    setTexto("");
    setPensando(true);
    try {
      const r = await api.post<RespuestaChat>(endpoint, {
        pregunta, historial: nuevo.slice(0, -1), idioma,
      }, 120000);
      setHistorial([...nuevo, { role: "assistant", content: r.texto }]);
    } catch {
      setHistorial([...nuevo, { role: "assistant", content: t("comun.error") }]);
    }
    setPensando(false);
    setTimeout(() => fondo.current?.scrollIntoView({ behavior: "smooth" }), 50);
  };

  const enviar = (e: FormEvent) => { e.preventDefault(); void preguntar(texto); };

  return (
    <div className="flex flex-col gap-3">
      {historial.length === 0 && (
        <div className="flex flex-wrap gap-2">
          {sugeridas.map((s) => (
            <button key={s} onClick={() => void preguntar(s)}
              className="text-[12.5px] bg-navy text-white/90 hover:bg-navy-deep px-3 py-1.5 rounded-full">
              {s}
            </button>
          ))}
        </div>
      )}
      <div className="flex flex-col gap-2 max-h-[420px] overflow-y-auto pr-1">
        {historial.map((m, i) => (
          <div key={i}
            className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[13.5px] whitespace-pre-wrap leading-relaxed ${
              m.role === "user"
                ? "self-end bg-navy text-white rounded-br-sm"
                : "self-start bg-navy-soft text-ink rounded-bl-sm"}`}>
            {m.content}
          </div>
        ))}
        {pensando && (
          <div className="self-start bg-navy-soft rounded-2xl px-4 py-3 flex gap-1">
            <span className="punto w-2 h-2 rounded-full bg-navy inline-block" />
            <span className="punto w-2 h-2 rounded-full bg-navy inline-block" />
            <span className="punto w-2 h-2 rounded-full bg-navy inline-block" />
          </div>
        )}
        <div ref={fondo} />
      </div>
      <form onSubmit={enviar} className="flex gap-2">
        <input
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder={t("chat.escribi")}
          className="flex-1 border border-line rounded-full px-4 py-2.5 text-[13.5px] bg-card focus:border-navy"
        />
        <Boton disabled={pensando || !texto.trim()} ariaLabel={t("chat.enviar")}>➤</Boton>
      </form>
      {historial.length > 0 && (
        <button onClick={() => setHistorial([])}
          className="self-start text-[12px] text-muted hover:text-navy underline">
          {t("chat.limpiar")}
        </button>
      )}
    </div>
  );
}
