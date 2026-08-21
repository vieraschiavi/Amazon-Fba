// © 2026 Martín Viera. Todos los derechos reservados.
/* nucleo-demo.js — MOTOR FALSO, solo para la demo web publica (/app/).
 *
 * POR QUE EXISTE
 * --------------
 * El motor real (nucleo.js) es el port fiel de agents/pricing, ganancias,
 * exito, dedicacion y capital_planner: cada formula, cada umbral y cada curva
 * de BSR. Publicarlo en /app/ era entregar el activo de ingenieria completo,
 * en JavaScript legible, a cualquiera que abriera el inspector -- incluida la
 * competencia. La demo web ahora muestra PANTALLAS, no el motor.
 *
 * QUE HACE
 * --------
 * Expone exactamente la misma API que nucleo.js, pero cada funcion devuelve
 * SIEMPRE el mismo resultado congelado, ignorando lo que se le pase. Los
 * valores no son inventados a mano: se generaron corriendo el motor real una
 * vez sobre un producto de ejemplo (organizador de bambu, costo 4.20 + flete
 * 1.10 + 6% arancel + 0.35 prep, precio 24.99), asi las pantallas se ven
 * exactamente como se veran con datos propios.
 *
 * REGLA DEL PROYECTO: nunca simular un resultado haciendolo pasar por real.
 * Por eso este archivo marca DEMO = true y la copia web muestra un cartel
 * fijo aclarando que son datos de ejemplo. Sin ese cartel, esto violaria
 * "sin datos inventados".
 *
 * NO se copia a la app instalada ni a la APK: ahi va el motor de verdad.
 * Ver scripts/vercel-build.sh (elige uno u otro) y el test
 * test/verificar_demo_sin_motor.mjs (falla si el motor real vuelve a /app/).
 */

const MV = (function () {
  const F = {
  "landedCost": 5.968,
  "evaluarPrecio": {
    "precio": 25.55,
    "referral": 3.83,
    "fba_fee": 4.1,
    "ads": 2.56,
    "landed": 5.97,
    "neto": 9.1,
    "margen_pct": 35.6,
    "roi_pct": 152.5,
    "semaforo": "verde",
    "estrategia": "competitivo (-5% vs lider)",
    "precio_objetivo": 20.14,
    "break_even": 13.42,
    "precio_competencia": 26.9,
    "margen_objetivo": 25
  },
  "simularGanancias": {
    "ok": true,
    "entrada": "USD 2,000 de inversion",
    "unit_economics": {
      "landed": 5.97,
      "precio_venta": 24.99,
      "precio_es_sugerido": false,
      "referral_unidad": 3.75,
      "fba_fee": 4.1,
      "publicidad_unidad": 2.5,
      "neto_unidad": 8.67,
      "semaforo": "verde"
    },
    "lote": {
      "unidades_compradas": 335,
      "inversion_usada": 1999.28,
      "unidades_vendidas_netas": 318.2,
      "devoluciones_pct": 5,
      "ingreso_bruto": 7953.07,
      "costos": {
        "producto": 1407,
        "flete": 368.5,
        "arancel": 106.53,
        "prep": 117.25,
        "comision_amazon_referral": 1192.96,
        "fba_fee": 1304.82,
        "publicidad_acos": 795.31
      },
      "total_costos": 5292.37,
      "ganancia_neta": 2660.7,
      "ganancia_por_unidad": 8.67,
      "margen_pct": 33.5,
      "roi_inversion_pct": 133.1,
      "meses_para_venderlo": 2,
      "ganancia_por_mes_promedio": 1330.35
    },
    "reciclado": {
      "sueldo_meseta_mensual": 666.66,
      "ganancia_12m_estimada": 7118.38,
      "caja_minima": 5.97,
      "mes_primer_cobro": 3,
      "alerta": "ok",
      "filas": [
        {
          "mes": 1,
          "llegan": 0,
          "vendidas": 0,
          "ingreso": 0,
          "cobrado": 0,
          "repuso_unid": 0,
          "sueldo": 0,
          "caja": 5.97,
          "capital_atado": 1993.31,
          "disponible": 0
        },
        {
          "mes": 2,
          "llegan": 334,
          "vendidas": 167,
          "ingreso": 3964.66,
          "cobrado": 0,
          "repuso_unid": 0,
          "sueldo": 0,
          "caja": 5.97,
          "capital_atado": 996.66,
          "disponible": 167
        },
        {
          "mes": 3,
          "llegan": 0,
          "vendidas": 84,
          "ingreso": 1994.2,
          "cobrado": 3964.66,
          "repuso_unid": 166,
          "sueldo": 1332.34,
          "caja": 5.97,
          "capital_atado": 1486.03,
          "disponible": 83
        },
        {
          "mes": 4,
          "llegan": 0,
          "vendidas": 42,
          "ingreso": 997.1,
          "cobrado": 1994.2,
          "repuso_unid": 84,
          "sueldo": 667.16,
          "caja": 5.97,
          "capital_atado": 1736.69,
          "disponible": 41
        },
        {
          "mes": 5,
          "llegan": 166,
          "vendidas": 104,
          "ingreso": 2469.01,
          "cobrado": 997.1,
          "repuso_unid": 42,
          "sueldo": 333.58,
          "caja": 5.97,
          "capital_atado": 1366.67,
          "disponible": 103
        },
        {
          "mes": 6,
          "llegan": 84,
          "vendidas": 94,
          "ingreso": 2231.61,
          "cobrado": 2469.01,
          "repuso_unid": 104,
          "sueldo": 826.01,
          "caja": 5.97,
          "capital_atado": 1426.35,
          "disponible": 93
        },
        {
          "mes": 7,
          "llegan": 42,
          "vendidas": 68,
          "ingreso": 1614.35,
          "cobrado": 2231.61,
          "repuso_unid": 93,
          "sueldo": 752.55,
          "caja": 5.97,
          "capital_atado": 1575.55,
          "disponible": 67
        },
        {
          "mes": 8,
          "llegan": 104,
          "vendidas": 86,
          "ingreso": 2041.68,
          "cobrado": 1614.35,
          "repuso_unid": 68,
          "sueldo": 540.08,
          "caja": 5.97,
          "capital_atado": 1468.13,
          "disponible": 85
        },
        {
          "mes": 9,
          "llegan": 93,
          "vendidas": 89,
          "ingreso": 2112.9,
          "cobrado": 2041.68,
          "repuso_unid": 86,
          "sueldo": 683.04,
          "caja": 5.97,
          "capital_atado": 1450.22,
          "disponible": 89
        },
        {
          "mes": 10,
          "llegan": 68,
          "vendidas": 78,
          "ingreso": 1851.76,
          "cobrado": 2112.9,
          "repuso_unid": 89,
          "sueldo": 706.87,
          "caja": 5.97,
          "capital_atado": 1515.87,
          "disponible": 79
        },
        {
          "mes": 11,
          "llegan": 86,
          "vendidas": 82,
          "ingreso": 1946.72,
          "cobrado": 1851.76,
          "repuso_unid": 78,
          "sueldo": 619.51,
          "caja": 5.97,
          "capital_atado": 1492,
          "disponible": 83
        },
        {
          "mes": 12,
          "llegan": 89,
          "vendidas": 86,
          "ingreso": 2041.68,
          "cobrado": 1946.72,
          "repuso_unid": 81,
          "sueldo": 657.24,
          "caja": 5.97,
          "capital_atado": 1462.16,
          "disponible": 86
        }
      ]
    },
    "caveat": "Proyeccion, no promesa: asume que vendes al precio indicado y al ritmo del techo de demanda; el resultado real depende del ranking, el PPC y la calidad del producto. Si la ganancia por unidad es negativa, NO compres: estarias pagando por vender."
  },
  "evaluarExito": {
    "ok": true,
    "keyword": {
      "precio": 24.99,
      "resenas": 120,
      "rating": 4.4,
      "bsr": 38000
    },
    "probabilidad": 60,
    "veredicto": "AMARILLO",
    "comentario": "Marginal: solo avanzar con una diferenciacion clara (mejor producto, bundle, nicho mas fino).",
    "factores": {
      "demanda": {
        "valor": 0.4,
        "detalle": "sin dato de demanda: se asume neutral-bajo"
      },
      "entrada": {
        "valor": 0.5,
        "detalle": "sin datos de competidores: se asume neutral"
      },
      "calidad_gap": {
        "valor": 0.5,
        "detalle": "sin ratings: se asume neutral"
      },
      "precio": {
        "valor": 1,
        "detalle": "USD 24.99 en el sweet spot FBA (15-45)"
      },
      "margen": {
        "valor": 1,
        "detalle": "margen calculado 32.0% (verde >= 25%)"
      }
    },
    "pesos": {
      "demanda": 0.3,
      "entrada": 0.25,
      "calidad_gap": 0.2,
      "precio": 0.15,
      "margen": 0.1
    },
    "datos_faltantes": [
      "demanda (motor propio o Keepa)",
      "competidores (Productos estrella)",
      "calidad de competidores"
    ],
    "recomendaciones": [
      "Pedi muestras a 3 proveedores verificados y valida con la orden de prueba antes de escalar."
    ],
    "caveat": "Estimacion para ordenar candidatos, NO una garantia: el exito real depende del proveedor, el listing y la ejecucion. Ninguna probabilidad reemplaza la orden de prueba (USD 1.000-2.000)."
  },
  "estimarDedicacion": {
    "n_productos_operacion": 3,
    "lanzando_producto": false,
    "horas_semana_min": 4.5,
    "horas_semana_max": 8.2,
    "desglose": [
      {
        "tarea": "Revisar PPC, precio y stock (x3 producto/s)",
        "horas_min": 1.5,
        "horas_max": 3,
        "frecuencia": "por semana",
        "fase": "operacion"
      },
      {
        "tarea": "Atender casos que el bot deriva (no son FAQ) (x3 producto/s)",
        "horas_min": 1.5,
        "horas_max": 3,
        "frecuencia": "por semana",
        "fase": "operacion"
      },
      {
        "tarea": "Seguimiento de reposicion con el proveedor (x3 producto/s)",
        "horas_min": 0.8,
        "horas_max": 1.5,
        "frecuencia": "por semana",
        "fase": "operacion"
      },
      {
        "tarea": "Leer KPIs y alertas (ya automatizadas) (x3 producto/s)",
        "horas_min": 0.8,
        "horas_max": 0.8,
        "frecuencia": "por semana",
        "fase": "operacion"
      }
    ],
    "automatizado_por_el_sistema": [
      "Clasificar y responder consultas FAQ (envio, garantia, estado de pedido...)",
      "Registrar ventas, calcular KPIs y margen global",
      "Enviar alertas por email de cada venta/consulta",
      "Calcular pricing, proyeccion de caja y semaforo de margen",
      "Investigar keywords con el motor propio (corre solo, vos revisas el resultado)"
    ],
    "caveat": "Rangos de referencia. Un producto con problemas de calidad, reclamos o guerra de precios exige mas horas que estas; un producto sano con proveedor solido puede exigir menos."
  },
  "estimarPorBsr": {
    "ok": true,
    "bsr": 38000,
    "categoria": "Home & Kitchen",
    "ventas_estim": 59,
    "confianza": "alta",
    "fuente": "BSR de Amazon (curva)",
    "mensaje": "BSR #38000 en Home & Kitchen → ~59 u/mes estimadas (confianza alta). Es una estimación por curva, igual que la que hacen Jungle Scout y Helium 10."
  },
  "estimarDemanda": {
    "ok": true,
    "amplitud": 6,
    "demanda_score": 24,
    "nivel": "BAJA",
    "seed_directo": true
  },
  "analizarSugerencias": {
    "keywords": [
      {
        "keyword": "0",
        "interes": null
      },
      {
        "keyword": "1",
        "interes": null
      },
      {
        "keyword": "2",
        "interes": null
      },
      {
        "keyword": "3",
        "interes": null
      },
      {
        "keyword": "4",
        "interes": null
      },
      {
        "keyword": "5",
        "interes": null
      }
    ],
    "nichos": []
  },
  "vendedoresPrincipales": {
    "ok": false,
    "productos": [
      {
        "asin": null,
        "titulo": "Sold by ACME Home and ships from Amazon Fulfillment",
        "precio": null,
        "bsr": null,
        "categoria": null,
        "ventas_estim": null,
        "confianza": null,
        "potencial": null,
        "potencial_parcial": true,
        "link": null,
        "cuota_pct": null,
        "ingreso_estim_mes": null
      }
    ],
    "ventas_estim_total": 0,
    "ventas_estim_lider": 0,
    "mensaje": "1 línea(s) sin BSR: se listan sin estimación. La cuota es sobre los competidores que pegaste, no sobre el nicho entero."
  },
  "CFG": {
    "REFERRAL_PCT": 15,
    "ACOS_PCT": 10,
    "TARGET_MARGIN": 25,
    "FBA_FEE_DEFAULT": 3.65,
    "UMBRAL_VERDE": 25,
    "UMBRAL_AMARILLO": 12
  }
};

  // Congelado: nada de lo que entre cambia lo que sale.
  const fijo = (clave) => function () { return JSON.parse(JSON.stringify(F[clave])); };

  return {
    DEMO: true,
    CFG: F.CFG,
    landedCost: () => F.landedCost,
    evaluarPrecio: fijo("evaluarPrecio"),
    simularGanancias: fijo("simularGanancias"),
    evaluarExito: fijo("evaluarExito"),
    estimarDedicacion: fijo("estimarDedicacion"),
    estimarPorBsr: fijo("estimarPorBsr"),
    estimarDemanda: fijo("estimarDemanda"),
    analizarSugerencias: fijo("analizarSugerencias"),
    vendedoresPrincipales: fijo("vendedoresPrincipales"),
    // Auxiliares que el motor real expone: en la demo no se usan solas, pero
    // se mantienen para que ningun llamado quede en undefined.
    proyeccionRealista: fijo("simularGanancias"),
    confianzaBsr: () => F.estimarPorBsr.confianza,
    parsearBloqueBsr: () => ({ ok: false, mensaje: "Vista de ejemplo: pedí la demo 1:1 para probarlo con tus datos." }),
    potencialProducto: fijo("evaluarExito"),
    scoreInteres: () => F.estimarDemanda.demanda_score,
    scoreDemanda: () => F.estimarDemanda.demanda_score,
    nivelDemanda: () => F.estimarDemanda.nivel,
  };
})();

if (typeof module !== "undefined" && module.exports) module.exports = MV;
