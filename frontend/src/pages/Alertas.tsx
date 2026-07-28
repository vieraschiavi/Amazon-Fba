import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import type { Alerta as TAlerta } from "../api/tipos";
import { Badge, Card, Seccion, Tabla } from "../components/ui";
import { useT } from "../i18n";

export function Alertas() {
  const t = useT();
  const [alertas, setAlertas] = useState<TAlerta[]>([]);
  useEffect(() => {
    api.get<{ alertas: TAlerta[] }>("/api/alertas").then((d) => setAlertas(d.alertas))
      .catch(() => {});
  }, []);

  return (
    <>
      <Seccion titulo={t("al_titulo")} sub={t("al_sub")} />
      <Card>
        {alertas.length === 0
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
