#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
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
            "Demo: 7 dias completos gratis con TODAS las funciones, registrandote con "
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


# --------------------------------------------------------------------------- #
# Traducciones EN / PT del manual completo (mismo orden y claves que SECCIONES)
# --------------------------------------------------------------------------- #
SECCIONES_EN = [
    {
        "clave": "flujo",
        "titulo": "The complete flow in 5 steps",
        "para_que": "Understand how the tabs chain together, from idea to sale.",
        "pasos": [
            "DISCOVER: Recommender tab (no keyword needed) or Research (with your "
            "keyword) to find niches with real demand.",
            "VALIDATE: Market tab to see real competitors, prices, reviews and the "
            "success probability of your chosen niche.",
            "CALCULATE: Pricing tab with your real costs (cost, freight, tariff, prep) "
            "-> suggested price, margin, ROI and traffic light. Save the product to "
            "your portfolio.",
            "PLAN: Cash Flow tab (realistic month-by-month money projection) and Plan "
            "(how many products and how much capital for your goal).",
            "OPERATE: Publish tab (complete listing package), Sales (log and track "
            "KPIs) and AI Assistant (questions about YOUR business).",
        ],
        "tips": [
            "The 'Load example product' button in the sidebar lets you walk the WHOLE "
            "flow with real numbers without entering anything.",
            "The sidebar 'Active product' replicates its data into Pricing, Cash Flow "
            "and Sales: pick once, never re-type.",
        ],
    },
    {
        "clave": "investigacion",
        "titulo": "Research — keywords and niches",
        "para_que": "Discover what real buyers search on Amazon, for free.",
        "pasos": [
            "Pick the source: 'Built-in engine' (free, real Amazon autocomplete) or "
            "'Helium 10 Cerebro CSV' if you have that tool.",
            "Pick language/marketplace (US, Spain, Mexico, Brazil...): keywords come "
            "localized by API in that country's language.",
            "Type your seed (e.g. 'bamboo kitchen') and hit Research.",
            "Check 'Top keywords' (real interest) and 'Candidate niches' (grouped by "
            "long-tail modifier).",
            "Below it generates a suggested listing (title, bullets, description) "
            "with those keywords.",
        ],
        "tips": [
            "'Interest' is an autocomplete proxy (position + long-tail), NOT search "
            "volume: for numeric demand connect Keepa or use a Cerebro CSV.",
            "With a Claude key you can auto-translate the seed into the "
            "marketplace's language.",
        ],
    },
    {
        "clave": "recomendador",
        "titulo": "Recommender — opportunities without typing anything",
        "para_que": "Let the program propose promising niches instead of waiting for your keyword.",
        "pasos": [
            "Set your target price range (e.g. USD 15-45, the FBA sweet spot).",
            "Pick the marketplace and hit 'Find opportunities'.",
            "The system scans proven FBA categories with the built-in engine and "
            "ranks niches by potential (demand, competition, price).",
            "Copy the niche you like into Research (keywords/listing) or Market "
            "(competitors and success) to go deeper.",
        ],
        "tips": [
            "With Keepa connected the ranking is refined with real estimated sales "
            "and competition; without a key it still works using the free proxy.",
            "'Potential' ranks candidates, it does not guarantee profit: the test "
            "order is still mandatory.",
        ],
    },
    {
        "clave": "mercado",
        "titulo": "Market — competitors and success probability",
        "para_que": "See who you'll compete against and whether the niche is enterable.",
        "pasos": [
            "Type the product/keyword and your price range; hit Explore.",
            "With Keepa: real star products (price, BSR, estimated sales, rating, "
            "reviews). Without Keepa: direct Amazon links filtered by price to "
            "check manually.",
            "Read the aggregate signals: high median reviews = defended niche; low "
            "ratings = quality gap you can exploit.",
            "Use the 'Success probability advisor' with your target price and "
            "margin: GREEN/YELLOW/RED verdict with an auditable breakdown.",
            "Below you get serious supplier links (Alibaba Trade Assurance, Global "
            "Sources...) to request quotes.",
        ],
        "tips": [
            "Open the leader's 1-3 star reviews (direct link) and paste them into "
            "the AI Assistant: it summarizes what to fix to differentiate.",
        ],
    },
    {
        "clave": "pricing",
        "titulo": "Pricing — price, margin, ROI and traffic light",
        "para_que": "Know BEFORE buying stock whether the product really makes money.",
        "pasos": [
            "Enter your real costs: unit cost, freight, tariff %, prep and FBA fee.",
            "Optional: the leading competitor's price — the system tries to enter "
            "5% below if the margin holds.",
            "Read the result: landed cost, suggested price, margin %, ROI % and "
            "traffic light (GREEN >=25%, YELLOW 12-25%, RED <12%).",
            "If the light is good, save the product to the portfolio with its "
            "demand ceiling.",
        ],
        "tips": [
            "The margin already subtracts Amazon's referral (~15%), FBA fee and "
            "advertising (assumed ACoS): it's REAL margin, not gross.",
            "Break-even is your floor price: below it you lose money on every sale.",
        ],
    },
    {
        "clave": "portafolio",
        "titulo": "Portfolio — your business product by product",
        "para_que": "See the whole business together: projected vs. actual.",
        "pasos": [
            "Add products from Pricing (recommended) or directly with the form.",
            "Check the top KPIs: active products, projected plateau salary, capital "
            "in pipeline and actual sales.",
            "Pick a product under 'Financial analysis per product': unit economics, "
            "12-month cash projection and its actual sales.",
            "Export everything to CSV whenever you want.",
        ],
        "tips": [
            "Products saved here appear in the sidebar 'Active product' selector "
            "and pre-fill Pricing, Cash Flow and Sales.",
        ],
    },
    {
        "clave": "publicar",
        "titulo": "Publish — the complete package for Seller Central",
        "para_que": "Leave theory behind: everything you need to publish the product.",
        "pasos": [
            "Pick the product (or enter name and data) and the keyword source.",
            "Hit 'Build publish package': complete listing (title, bullets, "
            "description, search terms), photo brief, suggested price and "
            "quantities, professional English RFQ for suppliers and a Seller "
            "Central checklist.",
            "Copy each block where it belongs (Seller Central, Alibaba, designer).",
        ],
        "tips": [
            "The English RFQ already includes the serious verification questions "
            "(samples, certifications, lead times).",
        ],
    },
    {
        "clave": "caja",
        "titulo": "Cash Flow — realistic month-by-month projection",
        "para_que": "Know how much money you need and when you start collecting, no hype.",
        "pasos": [
            "Enter capital, landed/unit, price and net/unit (pre-filled if there's "
            "an active product).",
            "Set the demand ceiling (units/month the niche absorbs) and the months.",
            "Read: plateau salary, minimum cash (cushion), first-collection month "
            "and invested capital; plus the monthly evolution chart.",
        ],
        "tips": [
            "The projection includes lead time and DD+7 (Amazon pays ~7 days after "
            "delivery): that's why the first collection isn't month 1.",
            "If minimum cash is too tight, you're fronting all capital into stock: "
            "lower the first order or raise the cushion.",
        ],
    },
    {
        "clave": "ventas",
        "titulo": "Sales — log and track KPIs",
        "para_que": "Go from projected to REAL: every logged sale feeds the whole system.",
        "pasos": [
            "Log each sale (ASIN, units, price, net/unit, country, segment).",
            "Check the KPIs: revenue, net, global margin, orders.",
            "Review the mix by product, country and segment to know what to scale.",
        ],
        "tips": [
            "Actual sales also show up in Portfolio (by ASIN) and in the AI "
            "Assistant's context.",
        ],
    },
    {
        "clave": "inversores",
        "titulo": "Investors and Plan — scale with outside capital or your own goal",
        "para_que": "Model what an investor earns, or what your income goal requires.",
        "pasos": [
            "Investors: own capital + investor capital + commission % -> honest "
            "return trajectory for both, with a downloadable HTML pitch.",
            "Plan: your monthly income goal -> how many products, with how much "
            "capital and in which month you get there.",
            "Plan includes the compound reinvestment calculator and the real "
            "hours/week the business takes.",
        ],
        "tips": [
            "The pitch uses the SAME numbers as the system: no inflated projections "
            "for the investor.",
        ],
    },
    {
        "clave": "config",
        "titulo": "Settings — keys and connections",
        "para_que": "Connect the optional services that boost the system.",
        "pasos": [
            "AI (optional): pick a provider (Claude recommended, OpenAI or Gemini) "
            "and paste your key -> enables the AI Assistant and reasoned analyses.",
            "Keepa (optional, ~19 EUR/month): real product data (price, BSR, "
            "estimated sales) in Market and Recommender.",
            "SMTP email (optional): real sales alerts; without SMTP they stay in "
            "dry-run (logged, not sent).",
            "Hit 'Test connections' to verify everything live.",
        ],
        "tips": [
            "Keys are stored LOCALLY in your .env: they never leave your machine "
            "nor go to the repository.",
            "Without any key the program still works: free built-in engine + "
            "deterministic formulas + the assistant's offline mode.",
        ],
    },
    {
        "clave": "asistente",
        "titulo": "AI Assistant — questions about YOUR business",
        "para_que": "An advisor that knows your real numbers (sales, portfolio, config).",
        "pasos": [
            "Connect an AI key in Settings (Claude recommended).",
            "Ask in natural language: 'which product should I scale?', 'how was my "
            "business doing based on my sales?'...",
            "Without a key it answers offline from the glossary (concepts, not "
            "your numbers).",
        ],
        "tips": [
            "For HOW-TO-USE questions use the Help tab chat; this assistant is for "
            "the business.",
        ],
    },
    {
        "clave": "demo_licencia",
        "titulo": "Demo, license and language",
        "para_que": "How access to the program works.",
        "pasos": [
            "Demo: 3 full free days with ALL features, registering with name and "
            "email. No card.",
            "License: when you buy you receive a key tied to your email; activate "
            "it on the start screen (needs internet once, then works offline).",
            "Language: selector at the top of the sidebar — one click switches the "
            "program to Spanish, English or Portuguese.",
            "Guarantee: 7 days with automatic refund from the purchase page.",
        ],
        "tips": [
            "The license covers your email on PC and Android depending on the "
            "plan purchased.",
        ],
    },
]

SECCIONES_PT = [
    {
        "clave": "flujo",
        "titulo": "O fluxo completo em 5 passos",
        "para_que": "Entender como as abas se encadeiam, da ideia à venda.",
        "pasos": [
            "DESCOBRIR: aba Recomendador (sem keyword) ou Pesquisa (com a sua "
            "keyword) para encontrar nichos com demanda real.",
            "VALIDAR: aba Mercado para ver concorrentes reais, preços, avaliações e "
            "a probabilidade de sucesso do nicho escolhido.",
            "CALCULAR: aba Precificação com seus custos reais (custo, frete, tarifa, "
            "prep) -> preço sugerido, margem, ROI e semáforo. Salve o produto no "
            "portfólio.",
            "PLANEJAR: abas Caixa (projeção realista de dinheiro mês a mês) e Plano "
            "(quantos produtos e capital para a sua meta).",
            "OPERAR: aba Publicar (pacote completo de listing), Vendas (registrar e "
            "acompanhar KPIs) e Assistente IA (perguntas sobre o SEU negócio).",
        ],
        "tips": [
            "O botão 'Carregar produto de exemplo' da barra lateral permite "
            "percorrer TODO o fluxo com números reais sem digitar nada.",
            "O 'Produto ativo' da barra lateral replica seus dados em Precificação, "
            "Caixa e Vendas: escolha uma vez e não redigite.",
        ],
    },
    {
        "clave": "investigacion",
        "titulo": "Pesquisa — keywords e nichos",
        "para_que": "Descobrir o que os compradores reais buscam na Amazon, de graça.",
        "pasos": [
            "Escolha a fonte: 'Motor próprio' (grátis, autocomplete real da Amazon) "
            "ou 'CSV do Helium 10 Cerebro' se você tiver essa ferramenta.",
            "Escolha idioma/marketplace (US, Espanha, México, Brasil...): as "
            "keywords vêm localizadas por API no idioma do país.",
            "Digite sua seed (ex: 'bamboo kitchen') e toque em Pesquisar.",
            "Veja 'Top keywords' (interesse real) e 'Nichos candidatos' (agrupados "
            "por modificador long-tail).",
            "Abaixo é gerado um listing sugerido (título, bullets, descrição) com "
            "essas keywords.",
        ],
        "tips": [
            "'Interesse' é um proxy do autocomplete (posição + long-tail), NÃO "
            "volume de busca: para demanda numérica conecte o Keepa ou use um CSV "
            "do Cerebro.",
            "Com uma chave do Claude você pode traduzir a seed automaticamente para "
            "o idioma do marketplace.",
        ],
    },
    {
        "clave": "recomendador",
        "titulo": "Recomendador — oportunidades sem digitar nada",
        "para_que": "Deixar o programa propor nichos com potencial, em vez de esperar sua keyword.",
        "pasos": [
            "Defina sua faixa de preço alvo (ex: USD 15-45, o sweet spot do FBA).",
            "Escolha o marketplace e toque em 'Buscar oportunidades'.",
            "O sistema varre categorias FBA comprovadas com o motor próprio e "
            "rankeia os nichos por potencial (demanda, concorrência, preço).",
            "Copie o nicho que interessar para Pesquisa (keywords/listing) ou "
            "Mercado (concorrentes e sucesso) para aprofundar.",
        ],
        "tips": [
            "Com o Keepa conectado o ranking é refinado com vendas estimadas e "
            "concorrência reais; sem chave funciona igual com o proxy grátis.",
            "'Potencial' ordena candidatos, não garante lucro: o pedido de teste "
            "continua obrigatório.",
        ],
    },
    {
        "clave": "mercado",
        "titulo": "Mercado — concorrentes e probabilidade de sucesso",
        "para_que": "Ver contra quem você vai competir e se dá para entrar no nicho.",
        "pasos": [
            "Digite o produto/keyword e sua faixa de preços; toque em Explorar.",
            "Com Keepa: produtos estrela reais (preço, BSR, vendas estimadas, "
            "rating, avaliações). Sem Keepa: links diretos da Amazon filtrados por "
            "preço para olhar manualmente.",
            "Leia os sinais agregados: mediana de avaliações alta = nicho "
            "defendido; ratings baixos = brecha de qualidade para se diferenciar.",
            "Use o 'Assessor de probabilidade de sucesso' com seu preço alvo e "
            "margem: veredito VERDE/AMARELO/VERMELHO com detalhamento auditável.",
            "Abaixo estão os links de fornecedores sérios (Alibaba Trade "
            "Assurance, Global Sources...) para pedir cotações.",
        ],
        "tips": [
            "Abra as avaliações de 1-3 estrelas do líder (link direto) e cole no "
            "Assistente IA: ele resume o que corrigir para se diferenciar.",
        ],
    },
    {
        "clave": "pricing",
        "titulo": "Precificação — preço, margem, ROI e semáforo",
        "para_que": "Saber ANTES de comprar estoque se o produto dá dinheiro de verdade.",
        "pasos": [
            "Informe seus custos reais: custo unitário, frete, tarifa %, prep e "
            "FBA fee.",
            "Opcional: preço do concorrente líder — o sistema tenta entrar 5% "
            "abaixo se a margem aguentar.",
            "Leia o resultado: landed cost, preço sugerido, margem %, ROI % e "
            "semáforo (VERDE >=25%, AMARELO 12-25%, VERMELHO <12%).",
            "Se o semáforo ajudar, salve o produto no portfólio com seu teto de "
            "demanda.",
        ],
        "tips": [
            "A margem já desconta a comissão da Amazon (referral ~15%), FBA fee e "
            "publicidade (ACoS suposto): é margem REAL, não bruta.",
            "O break-even é seu preço piso: abaixo dele você perde dinheiro em "
            "cada venda.",
        ],
    },
    {
        "clave": "portafolio",
        "titulo": "Portfólio — seu negócio produto a produto",
        "para_que": "Ver o negócio inteiro junto: projetado vs. real.",
        "pasos": [
            "Adicione produtos a partir da Precificação (recomendado) ou direto "
            "pelo formulário.",
            "Veja os KPIs de cima: produtos ativos, salário de platô projetado, "
            "capital em pipeline e vendas reais.",
            "Escolha um produto em 'Análise financeira por produto': unit "
            "economics, projeção de caixa de 12 meses e suas vendas reais.",
            "Exporte tudo para CSV quando quiser.",
        ],
        "tips": [
            "O produto salvo aqui aparece no seletor 'Produto ativo' da barra "
            "lateral e pré-preenche Precificação, Caixa e Vendas.",
        ],
    },
    {
        "clave": "publicar",
        "titulo": "Publicar — o pacote completo para o Seller Central",
        "para_que": "Sair da teoria: tudo o que você precisa para publicar o produto.",
        "pasos": [
            "Escolha o produto (ou informe nome e dados) e a fonte de keywords.",
            "Toque em 'Montar pacote de publicação': listing completo (título, "
            "bullets, descrição, search terms), brief de fotos, preço e "
            "quantidades sugeridas, RFQ profissional em inglês para fornecedores "
            "e checklist do Seller Central.",
            "Copie cada bloco onde corresponde (Seller Central, Alibaba, designer).",
        ],
        "tips": [
            "O RFQ em inglês já inclui as perguntas sérias de verificação "
            "(amostras, certificações, prazos).",
        ],
    },
    {
        "clave": "caja",
        "titulo": "Caixa — projeção realista mês a mês",
        "para_que": "Saber quanto dinheiro você precisa e quando começa a receber, sem ilusão.",
        "pasos": [
            "Informe capital, landed/unidade, preço e líquido/unidade "
            "(pré-preenchido se houver produto ativo).",
            "Defina o teto de demanda (unid/mês que o nicho absorve) e os meses.",
            "Leia: salário de platô, caixa mínimo (colchão), mês do primeiro "
            "recebimento e capital investido; e o gráfico de evolução mensal.",
        ],
        "tips": [
            "A projeção inclui lead time e DD+7 (a Amazon paga ~7 dias após a "
            "entrega): por isso o primeiro recebimento não é no mês 1.",
            "Se o caixa mínimo ficar apertado demais, você está colocando todo o "
            "capital em estoque: reduza o primeiro pedido ou aumente o colchão.",
        ],
    },
    {
        "clave": "ventas",
        "titulo": "Vendas — registrar e acompanhar KPIs",
        "para_que": "Passar do projetado para o REAL: cada venda registrada alimenta todo o sistema.",
        "pasos": [
            "Registre cada venda (ASIN, unidades, preço, líquido/unidade, país, "
            "segmento).",
            "Veja os KPIs: faturamento, líquido, margem global, pedidos.",
            "Revise o mix por produto, país e segmento para saber o que escalar.",
        ],
        "tips": [
            "As vendas reais também aparecem no Portfólio (por ASIN) e no contexto "
            "do Assistente IA.",
        ],
    },
    {
        "clave": "inversores",
        "titulo": "Investidores e Plano — escalar com capital de fora ou meta própria",
        "para_que": "Modelar quanto rende um investidor ou o que a sua meta de renda exige.",
        "pasos": [
            "Investidores: capital próprio + capital do investidor + comissão % -> "
            "trajetória honesta do retorno para ambos, com pitch HTML para baixar.",
            "Plano: sua meta de renda mensal -> quantos produtos, com quanto "
            "capital e em que mês você chega lá.",
            "O Plano inclui a calculadora de reinvestimento composto e as "
            "horas/semana reais que o negócio exige.",
        ],
        "tips": [
            "O pitch usa os MESMOS números do sistema: nada de projeções infladas "
            "para o investidor.",
        ],
    },
    {
        "clave": "config",
        "titulo": "Config — chaves e conexões",
        "para_que": "Conectar os serviços opcionais que potencializam o sistema.",
        "pasos": [
            "IA (opcional): escolha o provedor (Claude recomendado, OpenAI ou "
            "Gemini) e cole sua chave -> habilita o Assistente IA e as análises "
            "fundamentadas.",
            "Keepa (opcional, ~19 EUR/mês): dados reais de produtos (preço, BSR, "
            "vendas estimadas) em Mercado e Recomendador.",
            "Email SMTP (opcional): alertas reais de vendas; sem SMTP ficam em "
            "dry-run (registrados, não enviados).",
            "Toque em 'Testar conexões' para verificar tudo ao vivo.",
        ],
        "tips": [
            "As chaves ficam salvas LOCALMENTE no seu .env: nunca saem da sua "
            "máquina nem vão para o repositório.",
            "Sem nenhuma chave o programa funciona igual: motor próprio grátis + "
            "fórmulas determinísticas + modo offline do assistente.",
        ],
    },
    {
        "clave": "asistente",
        "titulo": "Assistente IA — perguntas sobre o SEU negócio",
        "para_que": "Um assessor que conhece seus números reais (vendas, portfólio, config).",
        "pasos": [
            "Conecte uma chave de IA em Config (Claude recomendado).",
            "Pergunte em linguagem natural: 'qual produto vale escalar?', 'como ia "
            "meu negócio segundo minhas vendas?'...",
            "Sem chave, responde em modo offline a partir do glossário (conceitos, "
            "não seus números).",
        ],
        "tips": [
            "Para dúvidas de COMO USAR o programa use o chat da aba Ajuda; este "
            "assistente é para o negócio.",
        ],
    },
    {
        "clave": "demo_licencia",
        "titulo": "Demo, licença e idioma",
        "para_que": "Como funciona o acesso ao programa.",
        "pasos": [
            "Demo: 7 dias completos grátis com TODAS as funções, cadastrando nome "
            "e email. Sem cartão.",
            "Licença: ao comprar você recebe uma chave vinculada ao seu email; "
            "ative na tela inicial (precisa de internet uma vez, depois funciona "
            "offline).",
            "Idioma: seletor no topo da barra lateral — um clique muda o programa "
            "para espanhol, inglês ou português.",
            "Garantia: 7 dias com devolução automática pela página de compra.",
        ],
        "tips": [
            "A licença vale para o seu email no PC e Android conforme o plano "
            "comprado.",
        ],
    },
]

_POR_IDIOMA = {"es": SECCIONES, "en": SECCIONES_EN, "pt": SECCIONES_PT}


def secciones(idioma="es"):
    """Manual completo en `idioma` ('es'/'en'/'pt'); cae a español si no existe."""
    return _POR_IDIOMA.get(idioma, SECCIONES)


def por_clave(clave, idioma="es"):
    for s in secciones(idioma):
        if s["clave"] == clave:
            return s
    return None


def buscar(texto, idioma="es"):
    """Secciones cuyo titulo/pasos/tips contengan `texto` (case-insensitive).
    Las que matchean por TITULO van primero: preguntar 'recomendador' debe
    devolver la seccion Recomendador antes que otra que solo lo mencione."""
    t = (texto or "").strip().lower()
    if not t:
        return []
    out = []
    for s in secciones(idioma):
        blob = " ".join([s["titulo"], s["para_que"]] + s["pasos"] + s["tips"]).lower()
        if t in blob:
            out.append(s)
    return sorted(out, key=lambda s: t not in s["titulo"].lower())


def contexto_para_ia(idioma="es"):
    """Version compacta del manual completo para inyectar a la IA de dudas."""
    lineas = []
    for s in secciones(idioma):
        lineas.append(f"## {s['titulo']}")
        lineas.append(f"Para que sirve: {s['para_que']}")
        for i, p in enumerate(s["pasos"], 1):
            lineas.append(f"{i}. {p}")
        for tip in s["tips"]:
            lineas.append(f"Tip: {tip}")
        lineas.append("")
    return "\n".join(lineas)


if __name__ == "__main__":
    for idi, lista in _POR_IDIOMA.items():
        claves = [s["clave"] for s in lista]
        print(f"[{idi}] {len(lista)} secciones: {', '.join(claves)}")
    # sanity: mismas claves y mismo orden en los 3 idiomas
    base = [s["clave"] for s in SECCIONES]
    for idi, lista in _POR_IDIOMA.items():
        assert [s["clave"] for s in lista] == base, f"claves desalineadas en {idi}"
    print("Claves alineadas en los 3 idiomas.")
