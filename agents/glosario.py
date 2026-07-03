#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/glosario.py — Glosario y ayudas de MV Amazon FBA IA.

Diccionario de terminos FBA + finanzas (en espanol), agrupados por categoria.
Fuente unica para la pestana Ayuda del panel y para el fallback offline del
asistente IA. Solo libreria estandar.
"""

# Cada termino: (definicion, categoria). Sin acentos raros para portabilidad.
GLOSARIO = {
    "FBA": ("Fulfillment by Amazon: Amazon almacena tu stock, prepara y envia los "
            "pedidos y atiende devoluciones a cambio de una tarifa (FBA fee).",
            "Amazon"),
    "ASIN": ("Amazon Standard Identification Number: el codigo unico de 10 caracteres "
             "que identifica cada producto en Amazon.", "Amazon"),
    "BSR": ("Best Sellers Rank: ranking de ventas de un producto dentro de su "
            "categoria. Mas bajo = vende mas. Keepa lo expone; las ventas exactas "
            "son una estimacion, no un dato fino.", "Amazon"),
    "Referral fee": ("Comision que cobra Amazon por cada venta (tipicamente ~15% del "
                     "precio). Se descuenta del ingreso antes de tu neto.", "Amazon"),
    "FBA fee": ("Tarifa fija por unidad que cobra Amazon por almacenar, preparar y "
                "enviar tu producto. Depende de tamano y peso.", "Amazon"),
    "ACoS": ("Advertising Cost of Sale: gasto en publicidad dividido por la "
             "facturacion que genero, en %. Menor ACoS = publicidad mas eficiente.",
             "Amazon"),
    "Buy Box": ("El recuadro de compra donde Amazon pone el boton 'Agregar al "
                "carrito'. Ganarlo depende de precio, stock y metricas de vendedor.",
                "Amazon"),
    "Landed cost": ("Costo desembarcado: lo que te cuesta poner una unidad lista para "
                    "vender = costo del producto + flete + arancel + prep. Es la base "
                    "real del margen.", "Finanzas"),
    "Margen": ("Neto dividido por el precio de venta, en %. Mide cuanto te queda de "
               "cada dolar facturado despues de TODOS los costos.", "Finanzas"),
    "ROI": ("Return on Investment: neto dividido por el capital invertido (landed), "
            "en %. Mide cuanto rinde tu plata, no cuanto factura el producto.",
            "Finanzas"),
    "Neto": ("Lo que te queda por unidad tras restar referral, FBA fee, publicidad y "
             "landed cost. Es tu ganancia real por venta.", "Finanzas"),
    "Break-even": ("Precio de equilibrio: el precio al que no ganas ni perdes "
                   "(margen 0). Vender por debajo es perder plata en cada unidad.",
                   "Finanzas"),
    "Semaforo": ("Codigo de color del margen: VERDE (>=25%) sano, AMARILLO (12-25%) "
                 "ajustado, ROJO (<12%) no conviene. Es una guia rapida de decision.",
                 "Finanzas"),
    "Techo de demanda": ("El maximo de unidades/mes que un nicho puede absorber. Sin "
                         "techo, cualquier proyeccion 'explota' y miente: mas capital "
                         "no vende mas si no hay demanda. Por eso es obligatorio.",
                         "Estrategia"),
    "Sueldo en meseta": ("El ingreso mensual SOSTENIDO cuando reciclas capital (el "
                         "landed repone stock y el neto se retira). Se estabiliza en "
                         "~techo x neto. No confundir con un pico que se desploma.",
                         "Estrategia"),
    "Capital en pipeline": ("La plata inmovilizada en stock (en produccion, en "
                            "transito y en Amazon). Estimamos ~4 meses de stock al "
                            "techo por producto.", "Estrategia"),
    "Orden de prueba": ("Compra chica (USD 1.000-2.000) para VALIDAR un producto "
                        "antes de escalar. Ningun score reemplaza vender de verdad "
                        "una primera tanda.", "Estrategia"),
    "Score de nicho": ("Puntaje 0-100 que mide la GANABILIDAD de un nicho (demanda, "
                       "competencia y hueco de valor). No es el margen: el margen lo "
                       "decide el pricing y el costo real del proveedor.", "Estrategia"),
    "Lead time": ("El tiempo desde que pagas al proveedor hasta que el stock esta "
                  "vendible en Amazon (produccion + envio + recepcion). Retrasa tu "
                  "primer cobro.", "Estrategia"),
    "Keepa": ("Servicio con API de pago (~19 EUR/mes) que da precio historico y BSR "
              "de cualquier ASIN. Es la fuente programatica de datos de mercado del "
              "sistema.", "Herramientas"),
    "Cerebro": ("Herramienta de keywords de Helium 10. Como no expone API en "
                "Platinum, el sistema consume su export CSV (boton 'Export Data').",
                "Herramientas"),
    "Landed vs precio": ("Landed es lo que te cuesta la unidad; precio es a cuanto la "
                         "vendes. La diferencia, menos las tarifas de Amazon y "
                         "publicidad, es tu neto.", "Finanzas"),
}

# Orden de categorias para mostrar en la pestana Ayuda.
CATEGORIAS = ["Amazon", "Finanzas", "Estrategia", "Herramientas"]


def por_categoria():
    """Devuelve {categoria: [(termino, definicion), ...]} ordenado."""
    out = {c: [] for c in CATEGORIAS}
    for termino, (definicion, cat) in GLOSARIO.items():
        out.setdefault(cat, []).append((termino, definicion))
    for c in out:
        out[c].sort(key=lambda x: x[0].lower())
    return out


def buscar(texto):
    """Busca terminos cuyo nombre o definicion contenga `texto` (case-insensitive)."""
    t = (texto or "").strip().lower()
    if not t:
        return []
    res = []
    for termino, (definicion, cat) in GLOSARIO.items():
        if t in termino.lower() or t in definicion.lower():
            res.append((termino, definicion, cat))
    return sorted(res, key=lambda x: (t not in x[0].lower(), x[0].lower()))


def contexto_para_ia():
    """Version compacta del glosario para inyectar como contexto del asistente."""
    return "\n".join(f"- {term}: {defi}" for term, (defi, _) in GLOSARIO.items())


if __name__ == "__main__":
    print(f"{len(GLOSARIO)} terminos en {len(CATEGORIAS)} categorias.")
    for cat, items in por_categoria().items():
        print(f"\n[{cat}] {len(items)} terminos")
        for term, _ in items[:3]:
            print("  -", term)
