// © 2026 Martín Viera. Todos los derechos reservados.
import { useEffect, useState } from "react";
import { api, mensajeError } from "../api/cliente";
import type { Alerta as TAlerta } from "../api/tipos";
import { Alerta, Badge, Card, Seccion, Tabla } from "../components/ui";
import { useT } from "../i18n";

export function Alertas() {
  const t = useT();
  const [alertas, setAlertas] = useState<TAlerta[]>([]);
  // Distingue "no hay alertas" de "no se pudieron cargar" (antes ambos se
  // veian como "sin datos", ocultando un error de red).
  const [error, setError] = useState("");
  useEffect(() => {
    api.get<{ alertas: TAlerta[] }>("/api/alertas")
      .then((d) => { setAlertas(d.alertas); setError(""); })
      .catch((e) => setError(mensajeError(e)));
  }, []);

  return (
    <>
      <Seccion titulo={t("al_titulo")} sub={t("al_sub")} />
      {error && <Alerta tipo="error">{error}</Alerta>}
      <Card>
        {error && alertas.length === 0
          ? <p className="text-muted text-[13px]">{t("comun.error_carga")}</p>
          : alertas.length === 0
          ? <p className="text-muted text-[13px]">{t("comun.sin_datos")}</p>
          : <Tabla
              cabeceras={[t("al.fecha"), t("al.asunto"), t("al.para"), t("al.estado")]}
              filas={alertas.map((a) => [
                a.fecha, a.asunto, a.para,
                <Badge key="e" texto={a.enviado ? "enviada" : "dry-run"}
                       tono={a.enviado ? "verde" : "amarillo"} />,
              ])}
            />}
      </Card>
    </>
  );
}
