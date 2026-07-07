#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/tutorial.py — Manual de uso completo de MV FBA IA.

Fuente unica del tutorial del programa: lo consume la pestana Ayuda (guia
visible paso a paso) y el asistente de dudas del programa (contexto para la
IA y fallback offline). Solo libreria estandar.

Cada seccion: {"titulo", "para_que", "pasos" [lista], "tips" [lista]}.
El orden de SECCIONES es el orden real de las pestanas del panel.
"""

SECCIONES = [
    {
        "clave": "flujo",
        "titulo": "El flujo completo en 5 pasos",
        "para_que": "Entender como se encadenan las pestanas, de la idea a la venta.",
        "pasos": [
            "DESCUBRIR: pestana Recomendador (sin keyword) o Investigacion (con tu keyword) "
            "para encontrar nichos con demanda real.",
            "VALIDAR: pestana Mercado para ver competidores reales, precios, reseñas y la "
            "probabilidad de exito del nicho elegido.",
            "CALCULAR: pestana Pricing con tus costos reales (costo, flete, arancel, prep) "
            "-> precio sugerido, margen, ROI y semaforo. Guarda el producto al portafolio.",
            "PLANIFICAR: pestanas Caja (proyeccion realista de plata mes a mes) y Plan "
            "(cuantos productos y capital para tu objetivo).",
            "OPERAR: pestana Publicar (paquete de listing completo), Ventas (registrar y "
            "seguir KPIs) y Asistente IA (preguntas sobre TU negocio).",
        ],
        "tips": [
            "El boton 'Cargar producto de ejemplo' del sidebar te deja recorrer TODO el "
            "flujo con numeros reales sin cargar nada.",
            "El 'Producto activo' del sidebar replica sus datos en Pricing, Caja y Ventas: "
            "elegis una vez y no reescribis.",
        ],
    },
    {
        "clave": "investigacion",
        "titulo": "Investigacion — keywords y nichos",
        "para_que": "Descubrir que buscan los compradores reales en Amazon, gratis.",
        "pasos": [
            "Elegi la fuente: 'Motor propio' (gratis, autocompletado real de Amazon) o "
            "'CSV de Helium 10 Cerebro' si tenes esa herramienta.",
            "Elegi idioma/marketplace (US, España, Mexico, Brasil...): las keywords vienen "
            "localizadas por API en el idioma del pais.",
            "Escribi tu seed (ej: 'bamboo kitchen') y toca Investigar.",
            "Mira 'Top keywords' (interes real) y 'Nichos candidatos' (agrupados por "
            "modificador long-tail).",
            "Abajo te genera un listing sugerido (titulo, bullets, descripcion) con esas "
            "keywords.",
        ],
        "tips": [
            "'Interes' es un proxy del autocompletado (posicion + long-tail), NO volumen "
            "de busqueda: para demanda numerica conecta Keepa o usa un CSV de Cerebro.",
            "Con clave de Claude podes traducir el seed al idioma del marketplace "
            "automaticamente.",
        ],
    },
    {
        "clave": "recomendador",
        "titulo": "Recomendador — oportunidades sin escribir nada",
        "para_que": "Que el programa te proponga nichos con potencial, en vez de esperar tu keyword.",
        "pasos": [
            "Defini tu rango de precio objetivo (ej: USD 15-45, el sweet spot FBA).",
            "Elegi el marketplace y toca 'Buscar oportunidades'.",
            "El sistema escanea categorias FBA probadas con el motor propio y rankea los "
            "nichos por potencial (demanda, competencia, precio).",
            "Copia el nicho que te interese y pegalo en Investigacion (keywords/listing) o "
            "Mercado (competidores y exito) para profundizar.",
        ],
        "tips": [
            "Con Keepa conectada, el ranking se afina con ventas estimadas y competencia "
            "reales; sin clave funciona igual con el proxy gratis.",
            "'Potencial' ordena candidatos, no garantiza ganancia: la orden de prueba "
            "sigue siendo obligatoria.",
        ],
    },
    {
        "clave": "mercado",
        "titulo": "Mercado — competidores y probabilidad de exito",
        "para_que": "Ver contra quien vas a competir y si el nicho es entrable.",
        "pasos": [
            "Escribi el producto/keyword y tu rango de precios; toca Explorar.",
            "Con Keepa: productos estrella reales (precio, BSR, ventas estimadas, rating, "
            "reseñas). Sin Keepa: links directos a Amazon filtrados por precio para mirar "
            "a mano.",
            "Revisa las señales agregadas: reseñas medianas altas = nicho defendido; "
            "ratings bajos = hueco de calidad para diferenciarte.",
            "Usa 'Asesor de probabilidad de exito' con tu precio objetivo y margen: "
            "veredicto VERDE/AMARILLO/ROJO con desglose auditable.",
            "Abajo tenes los links de proveedores serios (Alibaba Trade Assurance, "
            "Global Sources...) para pedir cotizaciones.",
        ],
        "tips": [
            "Abri las reseñas de 1-3 estrellas del lider (link directo) y pegalas en el "
            "Asistente IA: te resume que arreglar para diferenciarte.",
        ],
    },
    {
        "clave": "pricing",
        "titulo": "Pricing — precio, margen, ROI y semaforo",
        "para_que": "Saber ANTES de comprar stock si el producto deja plata de verdad.",
        "pasos": [
            "Carga tus costos reales: costo unitario, flete, arancel %, prep y FBA fee.",
            "Opcional: precio del competidor lider — el sistema intenta entrar 5% por "
            "debajo si el margen aguanta.",
            "Lee el resultado: landed cost, precio sugerido, margen %, ROI % y semaforo "
            "(VERDE >=25%, AMARILLO 12-25%, ROJO <12%).",
            "Si el semaforo acompaña, guarda el producto en el portafolio con su techo "
            "de demanda.",
        ],
        "tips": [
            "El margen ya descuenta comision de Amazon (referral ~15%), FBA fee y "
            "publicidad (ACoS supuesto): es margen REAL, no bruto.",
            "El break-even te dice el precio piso: por debajo perdes plata en cada venta.",
        ],
    },
    {
        "clave": "portafolio",
        "titulo": "Portafolio — tu negocio producto a producto",
        "para_que": "Ver todo el negocio junto: lo proyectado contra lo real.",
        "pasos": [
            "Agrega productos desde Pricing (recomendado) o directo con el formulario.",
            "Mira los KPIs de arriba: productos activos, sueldo meseta proyectado, "
            "capital en pipeline y ventas reales.",
            "Elegi un producto en 'Analisis financiero por producto': unit economics, "
            "proyeccion de caja a 12 meses y sus ventas reales.",
            "Exporta todo a CSV cuando quieras.",
        ],
        "tips": [
            "El producto que guardes aca aparece en el selector 'Producto activo' del "
            "sidebar y precarga Pricing, Caja y Ventas.",
        ],
    },
    {
        "clave": "publicar",
        "titulo": "Publicar — el paquete completo para Seller Central",
        "para_que": "Salir de la teoria: todo lo que necesitas para publicar el producto.",
        "pasos": [
            "Elegi el producto (o carga nombre y datos) y la fuente de keywords.",
            "Toca 'Armar paquete de publicacion': listing completo (titulo, bullets, "
            "descripcion, search terms), brief de fotos, precio y cantidades sugeridas, "
            "RFQ profesional en ingles para proveedores y checklist de Seller Central.",
            "Copia cada bloque donde corresponde (Seller Central, Alibaba, disenador).",
        ],
        "tips": [
            "El RFQ en ingles ya incluye las preguntas de verificacion serias (muestras, "
            "certificaciones, tiempos).",
        ],
    },
    {
        "clave": "caja",
        "titulo": "Caja — proyeccion realista mes a mes",
        "para_que": "Saber cuanta plata necesitas y cuando empezas a cobrar, sin humo.",
        "pasos": [
            "Carga capital, landed/unidad, precio y neto/unidad (precargado si hay "
            "producto activo).",
            "Defini el techo de demanda (unid/mes que el nicho absorbe) y los meses.",
            "Lee: sueldo en meseta, caja minima (colchon), mes del primer cobro y "
            "capital invertido; y el grafico de evolucion mensual.",
        ],
        "tips": [
            "La proyeccion incluye lead time y DD+7 (Amazon te paga a ~7 dias tras "
            "entrega): por eso el primer cobro no es el mes 1.",
            "Si la caja minima queda muy justa, estas fronteando todo el capital en "
            "stock: baja la primera orden o sube el colchon.",
        ],
    },
    {
        "clave": "ventas",
        "titulo": "Ventas — registrar y seguir KPIs",
        "para_que": "Pasar de proyectado a REAL: cada venta registrada alimenta todo el sistema.",
        "pasos": [
            "Registra cada venta (ASIN, unidades, precio, neto/unidad, pais, segmento).",
            "Mira los KPIs: facturacion, neto, margen global, ordenes.",
            "Revisa el mix por producto, pais y segmento para saber que escalar.",
        ],
        "tips": [
            "Las ventas reales aparecen tambien en Portafolio (por ASIN) y en el "
            "contexto del Asistente IA.",
        ],
    },
    {
        "clave": "inversores",
        "titulo": "Inversores y Plan — escalar con capital ajeno u objetivo propio",
        "para_que": "Modelar cuanto rinde un inversor o que se necesita para tu meta de ingreso.",
        "pasos": [
            "Inversores: capital propio + capital del inversor + comision % -> "
            "trayectoria honesta del retorno para ambos, con pitch HTML descargable.",
            "Plan: tu objetivo de ingreso mensual -> cuantos productos, con que capital "
            "y en que mes llegas.",
            "Plan incluye la calculadora de reinversion compuesta y las horas/semana "
            "reales que requiere el negocio.",
        ],
        "tips": [
            "El pitch usa los MISMOS numeros del sistema: nada de proyecciones infladas "
            "para el inversor.",
        ],
    },
    {
        "clave": "config",
        "titulo": "Config — claves y conexiones",
        "para_que": "Conectar los servicios opcionales que potencian el sistema.",
        "pasos": [
            "IA (opcional): elegi proveedor (Claude recomendado, OpenAI o Gemini) y pega "
            "tu clave -> habilita el Asistente IA y los analisis razonados.",
            "Keepa (opcional, ~19 EUR/mes): datos reales de productos (precio, BSR, "
            "ventas estimadas) en Mercado y Recomendador.",
            "Email SMTP (opcional): alertas reales de ventas; sin SMTP quedan en "
            "dry-run (registradas, no enviadas).",
            "Toca 'Probar conexiones' para verificar todo en vivo.",
        ],
        "tips": [
            "Las claves se guardan LOCALMENTE en tu .env: nunca salen de tu maquina ni "
            "van al repositorio.",
            "Sin ninguna clave el programa funciona igual: motor propio gratis + "
            "formulas deterministicas + modo offline del asistente.",
        ],
    },
    {
        "clave": "asistente",
        "titulo": "Asistente IA — preguntas sobre TU negocio",
        "para_que": "Un asesor que conoce tus numeros reales (ventas, portafolio, config).",
        "pasos": [
            "Conecta una clave de IA en Config (Claude recomendado).",
            "Pregunta en lenguaje natural: 'que producto conviene escalar?', 'como venia "
            "mi negocio segun mis ventas?'...",
            "Sin clave responde en modo offline desde el glosario (conceptos, no tus "
            "numeros).",
        ],
        "tips": [
            "Para dudas de COMO USAR el programa usa el chat de la pestana Ayuda; este "
            "asistente es para el negocio.",
        ],
    },
    {
        "clave": "demo_licencia",
        "titulo": "Demo, licencia e idioma",
        "para_que": "Como funciona el acceso al programa.",
        "pasos": [
            "Demo: 3 dias completos gratis con TODAS las funciones, registrandote con "
            "nombre y email. Sin tarjeta.",
            "Licencia: al comprar recibis una clave atada a tu email; se activa en la "
            "pantalla de inicio (pide internet una vez, despues funciona offline).",
            "Idioma: selector arriba del sidebar — un click cambia el programa a "
            "español, ingles o portugues.",
            "Garantia: 7 dias con devolucion automatica desde la pagina de compra.",
        ],
        "tips": [
            "La licencia vale para tu email en PC y Android segun el plan comprado.",
        ],
    },
]


def por_clave(clave):
    for s in SECCIONES:
        if s["clave"] == clave:
            return s
    return None


def buscar(texto):
    """Secciones cuyo titulo/pasos/tips contengan `texto` (case-insensitive)."""
    t = (texto or "").strip().lower()
    if not t:
        return []
    out = []
    for s in SECCIONES:
        blob = " ".join([s["titulo"], s["para_que"]] + s["pasos"] + s["tips"]).lower()
        if t in blob:
            out.append(s)
    return out


def contexto_para_ia():
    """Version compacta del manual completo para inyectar a la IA de dudas."""
    lineas = []
    for s in SECCIONES:
        lineas.append(f"## {s['titulo']}")
        lineas.append(f"Para que sirve: {s['para_que']}")
        for i, p in enumerate(s["pasos"], 1):
            lineas.append(f"{i}. {p}")
        for tip in s["tips"]:
            lineas.append(f"Tip: {tip}")
        lineas.append("")
    return "\n".join(lineas)


if __name__ == "__main__":
    print(f"{len(SECCIONES)} secciones de tutorial.")
    for s in SECCIONES:
        print(f"- {s['titulo']} ({len(s['pasos'])} pasos, {len(s['tips'])} tips)")
