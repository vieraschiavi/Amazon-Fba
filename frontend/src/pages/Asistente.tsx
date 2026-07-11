import { useEffect, useState } from "react";
import { api } from "../api/cliente";
import type { EstadoAsistente } from "../api/tipos";
import { Chat } from "../components/Chat";
import { Badge, Card, Seccion } from "../components/ui";
import { useT } from "../i18n";

export function Asistente() {
  const t = useT();
  const [estado, setEstado] = useState<EstadoAsistente | null>(null);
  useEffect(() => {
    api.get<EstadoAsistente>("/api/asistente/estado").then(setEstado).catch(() => {});
  }, []);

  return (
    <>
      <Seccion titulo={t("ia_titulo")} sub={t("ia_sub")} />
      <Card>
        {estado && (
          <div className="mb-3">
            <Badge
              texto={estado.ok ? `${estado.proveedor ?? "IA"} ${t("chat.online")}` : t("chat.offline")}
              tono={estado.ok ? "verde" : "amarillo"}
            />
            <p className="text-muted text-[12px] mt-1.5">{estado.mensaje}</p>
            {estado.modo === "sin_creditos" && (
              <a href="https://mvfbaia.com/#precios" target="_blank" rel="noopener"
                 className="text-[12px] text-navy underline mt-1 inline-block">
                Recargar créditos →
              </a>
            )}
          </div>
        )}
        <Chat
          endpoint="/api/asistente/negocio"
          sugeridas={[
            "¿Cómo venía mi negocio según mis ventas?",
            "¿Qué producto de mi portafolio conviene escalar?",
            "¿Qué es el techo de demanda y por qué importa?",
          ]}
        />
      </Card>
    </>
  );
}
