#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/poa.py — Generador de Plan de Accion (POA) para suspensiones de Amazon.

Imita el generador de POA de SellerForge: arma un borrador de Plan of Action en
las 3 partes que Amazon espera (causa raiz / acciones correctivas inmediatas /
medidas preventivas), en el idioma del vendedor. Con ANTHROPIC_API_KEY Claude lo
redacta a medida del motivo; sin clave, cae a una plantilla deterministica util
(nunca deja el campo vacio, nunca lanza).

Es un BORRADOR para acelerar: siempre aclara que hay que revisarlo y adaptarlo
con los datos reales del caso antes de enviarlo a Amazon.
"""
import argparse
import json
import os
import sys

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import config  # noqa: E402

# Tipos de motivo mas comunes (para guiar el prompt y la plantilla offline).
TIPOS = {
    "autenticidad": "Queja de autenticidad / producto falsificado (inauthentic)",
    "condicion": "Queja de condicion del producto (used sold as new / defectos)",
    "seguridad": "Reclamo de seguridad del producto o del listado",
    "propiedad_intelectual": "Reclamo de propiedad intelectual (marca/patente/derechos)",
    "resenas": "Manipulacion de resenas / politicas de review",
    "rendimiento": "Metricas de cuenta (ODR, late shipment, cancelaciones)",
    "otro": "Otro motivo (describilo abajo)",
}

_TITULOS = {
    "es": ("Causa raiz del problema", "Acciones correctivas inmediatas",
           "Medidas preventivas para que no vuelva a pasar"),
    "en": ("Root cause of the issue", "Immediate corrective actions",
           "Preventive measures so it does not happen again"),
    "pt": ("Causa raiz do problema", "Ações corretivas imediatas",
           "Medidas preventivas para não se repetir"),
}

_INTRO = {
    "es": "Estimado equipo de Amazon,\n\nAgradecemos la oportunidad de presentar "
          "nuestro Plan de Accion. A continuacion detallamos la causa raiz, las "
          "acciones ya tomadas y las medidas preventivas implementadas.",
    "en": "Dear Amazon Team,\n\nThank you for the opportunity to submit our Plan "
          "of Action. Below we detail the root cause, the actions already taken, "
          "and the preventive measures implemented.",
    "pt": "Prezada equipe da Amazon,\n\nAgradecemos a oportunidade de apresentar "
          "nosso Plano de Ação. A seguir detalhamos a causa raiz, as ações já "
          "tomadas e as medidas preventivas implementadas.",
}

_CIERRE = {
    "es": "Quedamos a disposicion para aportar cualquier documentacion adicional. "
          "Solicitamos amablemente la reactivacion de nuestra cuenta/listado.",
    "en": "We remain available to provide any additional documentation. We kindly "
          "request the reinstatement of our account/listing.",
    "pt": "Permanecemos à disposição para fornecer qualquer documentação adicional. "
          "Solicitamos gentilmente a reativação da nossa conta/anúncio.",
}


def _plantilla_offline(motivo, tipo, idioma):
    """POA deterministico (sin IA): estructura correcta + guias por seccion."""
    idi = idioma if idioma in _TITULOS else "es"
    t1, t2, t3 = _TITULOS[idi]
    etiqueta = TIPOS.get(tipo, TIPOS["otro"])
    guias = {
        "es": (
            [f"Identificamos que el problema ({etiqueta.lower()}) se origino en: "
             f"{motivo or '[describi el motivo puntual]'}.",
             "Reconocemos el impacto en la experiencia del cliente y asumimos la responsabilidad."],
            ["Retiramos/corregimos de inmediato los listados afectados.",
             "Revisamos el inventario y la documentacion (facturas del proveedor autorizado).",
             "Contactamos a los clientes afectados y resolvimos reclamos pendientes."],
            ["Implementamos un control de calidad en cada recepcion de inventario.",
             "Solo compramos a proveedores autorizados con factura verificable.",
             "Capacitamos al equipo en las politicas de Amazon y auditamos las metricas semanalmente."]),
        "en": (
            [f"We identified that the issue ({etiqueta.lower()}) originated from: "
             f"{motivo or '[describe the specific reason]'}.",
             "We acknowledge the impact on the customer experience and take responsibility."],
            ["We immediately removed/corrected the affected listings.",
             "We reviewed inventory and documentation (invoices from the authorized supplier).",
             "We contacted affected customers and resolved pending claims."],
            ["We implemented a quality check on every inventory intake.",
             "We only buy from authorized suppliers with verifiable invoices.",
             "We trained the team on Amazon policies and audit metrics weekly."]),
        "pt": (
            [f"Identificamos que o problema ({etiqueta.lower()}) teve origem em: "
             f"{motivo or '[descreva o motivo específico]'}.",
             "Reconhecemos o impacto na experiência do cliente e assumimos a responsabilidade."],
            ["Removemos/corrigimos imediatamente os anúncios afetados.",
             "Revisamos o estoque e a documentação (notas do fornecedor autorizado).",
             "Contatamos os clientes afetados e resolvemos reclamações pendentes."],
            ["Implementamos um controle de qualidade em cada recebimento de estoque.",
             "Compramos apenas de fornecedores autorizados com nota verificável.",
             "Treinamos a equipe nas políticas da Amazon e auditamos as métricas semanalmente."]),
    }[idi]
    secciones = [{"titulo": t, "puntos": p} for t, p in zip((t1, t2, t3), guias)]
    return secciones


def _a_texto(secciones, idioma):
    idi = idioma if idioma in _INTRO else "es"
    partes = [_INTRO[idi], ""]
    for i, s in enumerate(secciones, 1):
        partes.append(f"{i}. {s['titulo']}")
        partes += [f"   - {p}" for p in s["puntos"]]
        partes.append("")
    partes.append(_CIERRE[idi])
    return "\n".join(partes)


def generar(motivo="", tipo="otro", idioma="es"):
    """Devuelve {ok, tipo, idioma, secciones, texto, modo, nota}. Con clave, Claude
    redacta; sin clave, plantilla. Nunca lanza."""
    idioma = idioma if idioma in _TITULOS else "es"
    nota = {
        "es": "Borrador orientativo: revisalo y adaptalo con los datos reales de tu "
              "caso (fechas, ordenes, facturas) antes de enviarlo a Amazon.",
        "en": "Draft only: review and adapt it with the real details of your case "
              "(dates, orders, invoices) before submitting it to Amazon.",
        "pt": "Rascunho orientativo: revise e adapte com os dados reais do seu caso "
              "(datas, pedidos, notas) antes de enviar à Amazon.",
    }[idioma]
    secciones = _plantilla_offline(motivo, tipo, idioma)
    if not config.ANTHROPIC_API_KEY:
        return {"ok": True, "tipo": tipo, "idioma": idioma, "secciones": secciones,
                "texto": _a_texto(secciones, idioma), "modo": "offline", "nota": nota}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        idioma_nombre = {"es": "espanol rioplatense", "en": "English",
                         "pt": "portugues do Brasil"}[idioma]
        resp = client.messages.create(
            model=config.MODEL_OPUS, max_tokens=1200,
            system=(f"Sos experto en apelaciones de Amazon. Redacta un Plan de "
                    f"Accion (POA) profesional en {idioma_nombre}, en las 3 partes "
                    "que Amazon espera: (1) causa raiz, (2) acciones correctivas "
                    "inmediatas, (3) medidas preventivas. Tono responsable y "
                    "concreto, sin excusas ni promesas vacias, orientado a hechos. "
                    "Devolve SOLO un JSON valido con esta forma exacta: "
                    '{"secciones":[{"titulo":"...","puntos":["...","..."]},'
                    '{"titulo":"...","puntos":[...]},{"titulo":"...","puntos":[...]}]}. '
                    "Sin texto fuera del JSON."),
            messages=[{"role": "user", "content":
                       f"Tipo de suspension: {TIPOS.get(tipo, TIPOS['otro'])}\n"
                       f"Motivo / contexto del vendedor: {motivo or '(no especificado)'}"}])
        crudo = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        datos = json.loads(crudo[crudo.index("{"):crudo.rindex("}") + 1])
        secs = datos.get("secciones") or []
        secs = [{"titulo": str(s.get("titulo", "")),
                 "puntos": [str(p) for p in (s.get("puntos") or [])]}
                for s in secs if s.get("titulo") and s.get("puntos")]
        if len(secs) < 3:
            raise ValueError("respuesta incompleta")
        return {"ok": True, "tipo": tipo, "idioma": idioma, "secciones": secs,
                "texto": _a_texto(secs, idioma), "modo": "online", "nota": nota}
    except Exception:
        return {"ok": True, "tipo": tipo, "idioma": idioma, "secciones": secciones,
                "texto": _a_texto(secciones, idioma), "modo": "offline", "nota": nota}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generador de Plan de Accion (POA) Amazon.")
    ap.add_argument("--motivo", default="")
    ap.add_argument("--tipo", default="autenticidad", choices=list(TIPOS))
    ap.add_argument("--idioma", default="es", choices=["es", "en", "pt"])
    args = ap.parse_args(argv)
    print(json.dumps(generar(args.motivo, args.tipo, args.idioma),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
