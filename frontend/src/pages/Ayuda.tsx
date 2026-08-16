// © 2026 Martín Viera. Todos los derechos reservados.
import { useEffect, useState } from "react";
import { api, mensajeError, qs } from "../api/cliente";
import type { SeccionTutorial } from "../api/tipos";
import { Chat } from "../components/Chat";
import { Alerta, Card, Campo, Seccion, Spinner } from "../components/ui";
import { useT } from "../i18n";
import { useApp } from "../stores/app";

interface TerminoGlosario { termino: string; definicion: string; categoria?: string }

function Tutorial() {
  const t = useT();
  const idioma = useApp((s) => s.idioma);
  const [secciones, setSecciones] = useState<SeccionTutorial[]>([]);
  const [abierta, setAbierta] = useState<string>("flujo");
  // Antes, si la carga fallaba, .catch(()=>{}) dejaba `secciones` vacio para
  // SIEMPRE y el spinner giraba eternamente. Ahora se registra el error y se
  // muestra un aviso con salida, en vez de un spinner infinito.
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    api.get<{ secciones: SeccionTutorial[] }>(`/api/tutorial${qs({ idioma })}`)
      .then((d) => setSecciones(d.secciones))
      .catch((e) => setError(mensajeError(e)));
  }, [idioma]);

  if (error && !secciones.length) return <Alerta tipo="error">{error}</Alerta>;
  if (!secciones.length) return <Spinner texto={t("comun.cargando")} />;
  return (
    <div className="flex flex-col gap-2">
      {secciones.map((s) => (
        <div key={s.clave} className="border border-line rounded-xl overflow-hidden">
          <button
            onClick={() => setAbierta(abierta === s.clave ? "" : s.clave)}
            className="w-full text-left px-4 py-3 font-bold text-[14px] text-navy-deep bg-navy-soft/40 hover:bg-navy-soft flex justify-between items-center"
          >
            {s.titulo}
            <span className="text-muted">{abierta === s.clave ? "–" : "+"}</span>
          </button>
          {abierta === s.clave && (
            <div className="px-4 py-3">
              <p className="text-muted text-[12.5px] italic mb-2">{s.para_que}</p>
              <ol className="list-decimal ml-5 flex flex-col gap-1.5 text-[13.5px]">
                {s.pasos.map((p, i) => <li key={i}>{p}</li>)}
              </ol>
              {s.tips.map((tip, i) => (
                <div key={i} className="border-l-2 border-green pl-3 mt-2 text-[12.5px] text-muted">
                  <b>Tip:</b> {tip}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Glosario() {
  const t = useT();
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState<TerminoGlosario[]>([]);
  const [categorias, setCategorias] = useState<Record<string, TerminoGlosario[]>>({});

  useEffect(() => {
    api.get<{ categorias: Record<string, TerminoGlosario[]> }>("/api/glosario")
      .then((d) => setCategorias(d.categorias)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!busqueda.trim()) { setResultados([]); return; }
    const timer = setTimeout(() => {
      api.get<{ resultados: TerminoGlosario[] }>(`/api/glosario${qs({ buscar: busqueda })}`)
        .then((d) => setResultados(d.resultados)).catch(() => {});
    }, 250);
    return () => clearTimeout(timer);
  }, [busqueda]);

  return (
    <>
      <Campo label={t("comun.buscar")} value={busqueda}
             onChange={(e) => setBusqueda(e.target.value)}
             placeholder={t("ayu.roi_bsr_landed_cost")} />
      <div className="mt-3 flex flex-col gap-2">
        {busqueda.trim()
          ? resultados.map((r) => (
              <div key={r.termino} className="text-[13.5px]">
                <b>{r.termino}</b> <span className="text-muted text-[11px]">· {r.categoria}</span>
                <p className="text-muted">{r.definicion}</p>
              </div>
            ))
          : Object.entries(categorias).map(([cat, items]) => (
              <details key={cat} className="border border-line rounded-xl px-4 py-2.5">
                <summary className="font-bold text-[13.5px] cursor-pointer text-navy-deep">
                  {cat} ({items.length})
                </summary>
                <div className="mt-2 flex flex-col gap-2">
                  {items.map((it) => (
                    <div key={it.termino} className="text-[13px]">
                      <b>{it.termino}</b> — <span className="text-muted">{it.definicion}</span>
                    </div>
                  ))}
                </div>
              </details>
            ))}
      </div>
    </>
  );
}

export function Ayuda() {
  const t = useT();
  return (
    <>
      <Seccion titulo={t("ayu_tut_titulo")} sub={t("ayu_tut_sub")} />
      <Card className="mb-5"><Tutorial /></Card>

      <Seccion titulo={t("ayu_ia_titulo")} sub={t("ayu_ia_sub")} />
      <Card className="mb-5">
        <Chat
          endpoint="/api/asistente/programa"
          sugeridas={[t("ayu_sug_1"), t("ayu_sug_2"), t("ayu_sug_3")]}
        />
      </Card>

      <Seccion titulo={t("ayu_titulo")} sub={t("ayu_sub")} />
      <Card><Glosario /></Card>
    </>
  );
}
