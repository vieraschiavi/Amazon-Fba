#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/i18n.py — Traducciones ES/EN/PT del programa de escritorio (dashboard_app.py).

t(clave) devuelve el texto en el idioma activo (st.session_state["idioma"],
por defecto "es"). El selector de idioma vive en el sidebar de
dashboard_app.py — un click cambia TODA la navegacion, encabezados y botones
principales de las 14 pestañas.

Cobertura de esta primera pasada: pestañas, encabezado+subtitulo principal de
cada pestaña y los botones de accion primaria (los que dispara el usuario en
cada flujo). Los textos de ayuda/caption mas granulares siguen en español por
ahora — se puede sumar clave por clave sin romper nada (t() devuelve la clave
tal cual si no la encuentra, nunca revienta la pantalla).
"""
import streamlit as st

IDIOMAS = ["es", "en", "pt"]
NOMBRES_IDIOMA = {"es": "Español", "en": "English", "pt": "Português"}

TEXTOS = {
    # ---------- selector de idioma ---------- #
    "idioma_label": {"es": "Idioma", "en": "Language", "pt": "Idioma"},

    # ---------- pestañas (nav) ---------- #
    "tab_investigacion": {"es": "Investigacion", "en": "Research", "pt": "Pesquisa"},
    "tab_recomendador": {"es": "Recomendador", "en": "Recommender", "pt": "Recomendador"},
    "tab_mercado": {"es": "Mercado", "en": "Market", "pt": "Mercado"},
    "tab_pricing": {"es": "Pricing", "en": "Pricing", "pt": "Precificação"},
    "tab_portafolio": {"es": "Portafolio", "en": "Portfolio", "pt": "Portfólio"},
    "tab_publicar": {"es": "Publicar", "en": "Publish", "pt": "Publicar"},
    "tab_caja": {"es": "Caja", "en": "Cash Flow", "pt": "Caixa"},
    "tab_ventas": {"es": "Ventas", "en": "Sales", "pt": "Vendas"},
    "tab_inversores": {"es": "Inversores", "en": "Investors", "pt": "Investidores"},
    "tab_plan": {"es": "Plan", "en": "Plan", "pt": "Plano"},
    "tab_alertas": {"es": "Alertas", "en": "Alerts", "pt": "Alertas"},
    "tab_config": {"es": "Config", "en": "Settings", "pt": "Config"},
    "tab_asistente": {"es": "Asistente IA", "en": "AI Assistant", "pt": "Assistente IA"},
    "tab_ayuda": {"es": "Ayuda", "en": "Help", "pt": "Ajuda"},

    # ---------- 1) Investigacion ---------- #
    "inv_titulo": {"es": "Investigacion de nicho", "en": "Niche research",
                  "pt": "Pesquisa de nicho"},
    "inv_sub": {"es": "Motor propio gratis o CSV de Cerebro -> score -> listing",
               "en": "Free built-in engine or Cerebro CSV -> score -> listing",
               "pt": "Motor próprio gratuito ou CSV do Cerebro -> score -> listing"},
    "inv_btn": {"es": "Investigar", "en": "Research", "pt": "Pesquisar"},

    # ---------- 2) Recomendador ---------- #
    "rec_titulo": {"es": "Recomendador de oportunidades",
                  "en": "Opportunity recommender", "pt": "Recomendador de oportunidades"},
    "rec_sub": {"es": "Proactivo: sin escribir ninguna keyword, escanea nichos por "
                     "precio y demanda con buen potencial de ganancia — sin Helium "
                     "10 ni Jungle Scout",
               "en": "Proactive: with no keyword typed, scans niches by price and "
                     "demand with good profit potential — no Helium 10 or Jungle Scout",
               "pt": "Proativo: sem digitar nenhuma keyword, escaneia nichos por "
                     "preço e demanda com bom potencial de lucro — sem Helium 10 "
                     "ou Jungle Scout"},
    "rec_btn": {"es": "Buscar oportunidades", "en": "Find opportunities",
               "pt": "Buscar oportunidades"},

    # ---------- 3) Mercado ---------- #
    "mk_titulo": {"es": "Explorador de mercado", "en": "Market explorer",
                 "pt": "Explorador de mercado"},
    "mk_sub": {"es": "Productos estrella por rango de precios, competidores, "
                    "reseñas, proveedores y probabilidad de exito",
              "en": "Top products by price range, competitors, reviews, "
                    "suppliers and success probability",
              "pt": "Produtos estrela por faixa de preço, concorrentes, "
                    "avaliações, fornecedores e probabilidade de sucesso"},
    "mk_btn": {"es": "Explorar", "en": "Explore", "pt": "Explorar"},
    "mk_ex_btn": {"es": "Evaluar exito", "en": "Evaluate success", "pt": "Avaliar sucesso"},
    "mk_ga_btn": {"es": "Calcular ganancia potencial", "en": "Calculate potential profit",
                 "pt": "Calcular lucro potencial"},

    # ---------- 4) Pricing ---------- #
    "pr_titulo": {"es": "Pricing", "en": "Pricing", "pt": "Precificação"},
    "pr_sub": {"es": "Costo desembarcado -> precio -> margen -> ROI",
              "en": "Landed cost -> price -> margin -> ROI",
              "pt": "Custo desembarcado -> preço -> margem -> ROI"},
    "pr_btn": {"es": "Guardar en portafolio", "en": "Save to portfolio",
              "pt": "Salvar no portfólio"},

    # ---------- 5) Portafolio ---------- #
    "pf_titulo": {"es": "Portafolio de productos", "en": "Product portfolio",
                 "pt": "Portfólio de produtos"},
    "pf_sub": {"es": "El negocio producto a producto: proyectado vs real",
              "en": "The business product by product: projected vs. actual",
              "pt": "O negócio produto a produto: projetado vs. real"},
    "pf_btn": {"es": "Agregar al portafolio", "en": "Add to portfolio",
              "pt": "Adicionar ao portfólio"},
    "pf_del_btn": {"es": "Quitar del portafolio (baja logica)",
                  "en": "Remove from portfolio", "pt": "Remover do portfólio"},

    # ---------- 6) Publicar ---------- #
    "pub_titulo": {"es": "Publicar en Amazon — paquete completo",
                  "en": "Publish on Amazon — complete package",
                  "pt": "Publicar na Amazon — pacote completo"},
    "pub_sub": {"es": "Listing + fotos + precio + cantidades + proveedor + checklist "
                    "Seller Central, en un solo documento",
               "en": "Listing + photos + price + quantities + supplier + Seller "
                    "Central checklist, in a single document",
               "pt": "Listing + fotos + preço + quantidades + fornecedor + checklist "
                    "Seller Central, em um único documento"},
    "pub_btn": {"es": "Armar paquete de publicacion", "en": "Build publish package",
               "pt": "Montar pacote de publicação"},

    # ---------- 7) Caja ---------- #
    "cj_titulo": {"es": "Proyeccion realista de caja", "en": "Realistic cash flow projection",
                 "pt": "Projeção realista de caixa"},
    "cj_sub": {"es": "Con lead time, DD+7, devoluciones y techo de demanda",
              "en": "With lead time, DD+7, returns and demand ceiling",
              "pt": "Com lead time, DD+7, devoluções e teto de demanda"},

    # ---------- 8) Ventas ---------- #
    "vt_titulo": {"es": "Ventas y KPIs", "en": "Sales & KPIs", "pt": "Vendas e KPIs"},
    "vt_sub": {"es": "Registra una venta y segui el mix",
              "en": "Log a sale and track the mix", "pt": "Registre uma venda e acompanhe o mix"},
    "vt_btn": {"es": "Registrar venta", "en": "Log sale", "pt": "Registrar venda"},

    # ---------- 9) Inversores ---------- #
    "iv_titulo": {"es": "Escenario con inversor", "en": "Investor scenario",
                 "pt": "Cenário com investidor"},
    "iv_sub": {"es": "Comision = % variable de facturacion sobre la parte que "
                    "financia su capital",
              "en": "Commission = variable % of revenue on the part their "
                    "capital finances",
              "pt": "Comissão = % variável do faturamento sobre a parte que "
                    "seu capital financia"},

    # ---------- 10) Plan ---------- #
    "pl_titulo": {"es": "Recomendacion de portafolio", "en": "Portfolio recommendation",
                 "pt": "Recomendação de portfólio"},
    "pl_sub": {"es": "Cuantos productos, con que capital y en que mes llegas a tu objetivo",
              "en": "How many products, with what capital, and in which month you "
                    "hit your target",
              "pt": "Quantos produtos, com que capital e em que mês você atinge "
                    "sua meta"},

    # ---------- 11) Alertas ---------- #
    "al_titulo": {"es": "Alertas", "en": "Alerts", "pt": "Alertas"},
    "al_sub": {"es": "Sin SMTP, quedan en dry-run (registradas, no enviadas)",
              "en": "Without SMTP, alerts stay in dry-run (logged, not sent)",
              "pt": "Sem SMTP, ficam em dry-run (registrados, não enviados)"},

    # ---------- 12) Config ---------- #
    "cfg_titulo": {"es": "Configuracion y conexiones", "en": "Settings & connections",
                  "pt": "Configuração e conexões"},
    "cfg_sub": {"es": "Estado actual y verificacion en vivo",
               "en": "Current status and live verification",
               "pt": "Status atual e verificação ao vivo"},
    "cfg_test_btn": {"es": "Probar conexiones", "en": "Test connections",
                     "pt": "Testar conexões"},
    "cfg_save_btn": {"es": "Guardar", "en": "Save", "pt": "Salvar"},

    # ---------- 13) Asistente IA ---------- #
    "ia_titulo": {"es": "Asistente IA", "en": "AI Assistant", "pt": "Assistente IA"},
    "ia_sub": {"es": "Pregunta sobre tus metricas, tu portafolio o la estrategia FBA",
              "en": "Ask about your metrics, your portfolio or FBA strategy",
              "pt": "Pergunte sobre suas métricas, seu portfólio ou a estratégia FBA"},
    "ia_clear_btn": {"es": "Limpiar conversacion", "en": "Clear conversation",
                     "pt": "Limpar conversa"},

    # ---------- 14) Ayuda ---------- #
    "ayu_titulo": {"es": "Ayuda y glosario", "en": "Help & glossary", "pt": "Ajuda e glossário"},
    "ayu_sub": {"es": "Los conceptos de FBA y finanzas que usa el sistema, en criollo",
               "en": "The FBA and finance concepts the system uses, in plain words",
               "pt": "Os conceitos de FBA e finanças que o sistema usa, em bom português"},
    "ayu_contacto_btn": {"es": "Enviar consulta", "en": "Send inquiry", "pt": "Enviar consulta"},

    # ---------- sidebar (compartido en todas las pestañas) ---------- #
    "sb_demo_titulo": {"es": "Probar con un ejemplo", "en": "Try an example",
                       "pt": "Testar com um exemplo"},
    "sb_demo_cargar": {"es": "Cargar producto de ejemplo", "en": "Load example product",
                       "pt": "Carregar produto de exemplo"},
    "sb_demo_quitar": {"es": "Quitar producto de ejemplo", "en": "Remove example product",
                       "pt": "Remover produto de exemplo"},
    "sb_activo_titulo": {"es": "Producto activo", "en": "Active product",
                         "pt": "Produto ativo"},
}


def idioma_activo():
    """Idioma elegido en el selector del sidebar (default 'es')."""
    try:
        return st.session_state.get("idioma", "es")
    except Exception:
        return "es"


def t(clave, **kwargs):
    """Texto de `clave` en el idioma activo. Si no existe, devuelve la clave
    tal cual (nunca revienta la pantalla por una traduccion faltante)."""
    d = TEXTOS.get(clave)
    if not d:
        return clave
    texto = d.get(idioma_activo()) or d.get("es") or clave
    return texto.format(**kwargs) if kwargs else texto
