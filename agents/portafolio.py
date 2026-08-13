#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/portafolio.py — Reinversion compuesta y recomendacion de portafolio (FBA).

Dos herramientas, con la honestidad del proyecto incrustada:

1) interes_compuesto(): "si reinvierto X por mes/anio a tasa Y durante Z anios,
   cuanto tengo". Matematica financiera estandar MAS un parametro opcional
   `techo_capital`: en FBA el capital solo rinde mientras hay demanda que lo
   absorba; el excedente queda OCIOSO (rinde 0). Sin techo, la curva es la
   fantasia exponencial de folleto; con techo, es tu negocio real.

2) recomendar_portafolio(): dado un objetivo de ingreso mensual, cuantos
   productos necesitas, con que capital, en que mes llegas, y si conviene
   meter inversores (comision % de facturacion sobre el lote de ellos).
   Lanzamiento SECUENCIAL (validar antes de escalar), nunca paralelo ciego.
"""
import math


def interes_compuesto(aporte_inicial, aporte_periodico, tasa_anual_pct, anios,
                      frecuencia="mensual", techo_capital=0):
    """
    Simulacion mensual. Tasa efectiva anual -> mensual: (1+t)^(1/12)-1.
    frecuencia: 'mensual' (aporta cada mes) o 'anual' (aporta al cierre de cada anio).
    techo_capital: 0 = sin techo (tasa fija clasica). >0 = el capital por encima
    del techo NO genera rendimiento (queda ocioso), como pasa con un techo de demanda.
    Devuelve filas mensuales y resumen.
    """
    anios = max(0, int(anios))
    meses = anios * 12
    t_mes = (1 + max(0.0, tasa_anual_pct) / 100.0) ** (1 / 12.0) - 1
    capital = max(0.0, aporte_inicial)
    aportado = capital
    filas = []
    for mes in range(1, meses + 1):
        productivo = min(capital, techo_capital) if techo_capital > 0 else capital
        rendimiento = productivo * t_mes
        capital += rendimiento
        if frecuencia == "mensual" and aporte_periodico > 0:
            capital += aporte_periodico
            aportado += aporte_periodico
        elif frecuencia == "anual" and aporte_periodico > 0 and mes % 12 == 0:
            capital += aporte_periodico
            aportado += aporte_periodico
        ocioso = max(0.0, capital - techo_capital) if techo_capital > 0 else 0.0
        filas.append({"mes": mes, "anio": (mes - 1) // 12 + 1,
                      "capital": round(capital, 2), "aportado": round(aportado, 2),
                      "rendimiento_mes": round(rendimiento, 2),
                      "ocioso": round(ocioso, 2)})
    ganancia = capital - aportado
    resumen = {
        "capital_final": round(capital, 2),
        "total_aportado": round(aportado, 2),
        "ganancia": round(ganancia, 2),
        "multiplicador": round(capital / aportado, 2) if aportado > 0 else 0.0,
        "tasa_mensual_pct": round(t_mes * 100, 3),
        "capital_ocioso_final": filas[-1]["ocioso"] if filas else 0.0,
        "meses": meses,
    }
    return {"filas": filas, "resumen": resumen}


def recomendar_portafolio(objetivo_mensual, capital_propio, techo=290, precio=24.0,
                          net_unit=6.9, landed=5.5, usar_inversores=False,
                          pct_comision=5.0, mes_meseta_p1=7, gap_lanzamientos=5,
                          max_productos=6):
    """
    Cuantos productos hacen falta para el objetivo, en que mes se llega y como
    financiarlos. Modelo de meseta por producto (secuencial):
      - sueldo por producto propio  = techo * net * (1-devoluciones 5%)
      - producto financiado por inversor: se descuenta pct% de SU facturacion
      - capital de pipeline por producto ~= 4 meses de stock al techo
      - producto k llega a meseta en mes_meseta_p1 + (k-1)*gap_lanzamientos
    Los productos que exceden el capital propio se financian con ganancia
    acumulada o con inversores (si usar_inversores=True, llegan antes).
    """
    dev = 0.05
    sueldo_prod = techo * net_unit * (1 - dev)
    fact_prod = techo * precio * (1 - dev)
    cap_prod = techo * 4 * landed                     # ~4 meses de pipeline
    sueldo_prod_inv = max(0.0, sueldo_prod - fact_prod * pct_comision / 100.0)

    if sueldo_prod <= 0:
        return {"ok": False, "mensaje": "Parametros invalidos (neto o techo en cero)."}

    plan, ingreso, k = [], 0.0, 0
    cap_restante = capital_propio
    while ingreso < objetivo_mensual and k < max_productos:
        k += 1
        if cap_restante >= cap_prod:
            fuente, aporte_inv = "capital propio", 0.0
            cap_restante -= cap_prod
            sueldo_k = sueldo_prod
        elif usar_inversores:
            fuente, aporte_inv = f"inversores ({pct_comision:.0f}% facturacion)", cap_prod - max(0, cap_restante)
            cap_restante = 0
            share_inv = aporte_inv / cap_prod if cap_prod > 0 else 0
            sueldo_k = sueldo_prod - fact_prod * (pct_comision / 100.0) * share_inv
        else:
            fuente, aporte_inv = "ganancia reinvertida", 0.0
            sueldo_k = sueldo_prod
        mes_meseta = mes_meseta_p1 + (k - 1) * gap_lanzamientos
        # sin inversores, esperar a juntar la ganancia corre el lanzamiento
        if fuente == "ganancia reinvertida" and ingreso > 0:
            meses_ahorro = math.ceil(cap_prod / ingreso)
            mes_meseta = max(mes_meseta, mes_meseta_p1 + meses_ahorro + gap_lanzamientos * (k - 1))
        ingreso += sueldo_k
        plan.append({"producto": k, "fuente": fuente,
                     "capital": round(cap_prod), "capital_inversor": round(aporte_inv),
                     "sueldo_aporta": round(sueldo_k), "mes_meseta": mes_meseta,
                     "ingreso_acumulado": round(ingreso)})

    alcanzado = ingreso >= objetivo_mensual
    return {
        "ok": True, "alcanzado": alcanzado,
        "objetivo": objetivo_mensual,
        "n_productos": len(plan),
        "ingreso_final": round(ingreso),
        "mes_objetivo": plan[-1]["mes_meseta"] if plan else None,
        "capital_propio_usado": round(min(capital_propio, sum(p["capital"] for p in plan))),
        "capital_inversores": round(sum(p["capital_inversor"] for p in plan)),
        "sueldo_por_producto": round(sueldo_prod),
        "capital_por_producto": round(cap_prod),
        "plan": plan,
        "advertencia": ("Cada producto es una apuesta con su PROPIO techo de demanda; "
                        "estos numeros asumen que cada nicho valida con orden de prueba "
                        "(USD 1.000-2.000) antes de escalar."),
    }


if __name__ == "__main__":
    r = interes_compuesto(10000, 500, 12, 10, "mensual")
    print("Compuesto 10k + 500/mes al 12% x10a:", r["resumen"])
    r2 = interes_compuesto(10000, 500, 12, 10, "mensual", techo_capital=25000)
    print("Idem con techo 25k:", r2["resumen"])
    p = recomendar_portafolio(2500, 10000)
    print("Portafolio 2500/mes, 10k propio:",
          {k: v for k, v in p.items() if k not in ("plan", "advertencia")})
    for f in p["plan"]:
        print("  ", f)


def retorno_inversor(ticket=1000, pct_facturacion=10.0, techo=290, precio=24.0,
                     landed=5.5, meses=24, productos_financia=1.0,
                     pipeline_meses=4, devoluciones=0.05, mes_arranque=2):
    """
    Trayectoria de UN inversor con comision reinvertida y TECHO honesto.
    - Su capital financia unidades de un lote; la comision (% de la facturacion de
      SU lote) se reinvierte y compra mas unidades... hasta que su lote satura el
      techo de demanda que puede ocupar. De ahi en mas, el excedente queda OCIOSO.
    - productos_financia: cuantos techos puede ocupar su capital (1 = un producto;
      2 = su capital tambien entra al producto 2 cuando se lanza). Es el unico
      camino real para que la comision siga creciendo despues de la saturacion.
    - mes_arranque: primer mes con ventas (lead time de produccion/envio).
    Devuelve filas mensuales y resumen con el mes de saturacion.
    """
    cap = max(0.0, float(ticket))
    techo_u = max(0.0, techo * productos_financia)
    cap_max = techo_u * pipeline_meses * landed          # capital que satura su techo
    filas, mes_sat = [], None
    for mes in range(1, max(1, int(meses)) + 1):
        productivo = min(cap, cap_max)
        ocioso = cap - productivo
        if mes >= mes_arranque and landed > 0:
            u_vend = min(productivo / (landed * pipeline_meses), techo_u)
        else:
            u_vend = 0.0
        fact = u_vend * precio * (1 - devoluciones)
        comision = fact * pct_facturacion / 100.0
        cap += comision
        if mes_sat is None and cap_max > 0 and cap >= cap_max:
            mes_sat = mes
        filas.append({"mes": mes, "capital": round(cap, 2),
                      "productivo": round(min(cap, cap_max), 2),
                      "ocioso": round(max(0.0, cap - cap_max), 2),
                      "comision_mes": round(comision, 2),
                      "unidades_lote": round(u_vend)})
    con_com = [f["comision_mes"] for f in filas if f["comision_mes"] > 0]
    resumen = {
        "ticket": ticket,
        "capital_final": filas[-1]["capital"] if filas else ticket,
        "comision_inicial": round(con_com[0], 2) if con_com else 0.0,
        "comision_meseta": round(con_com[-1], 2) if con_com else 0.0,
        "mes_saturacion": mes_sat,
        "capital_max_productivo": round(cap_max, 2),
        "capital_ocioso_final": filas[-1]["ocioso"] if filas else 0.0,
        "multiplicador": round(filas[-1]["capital"] / ticket, 2) if (filas and ticket > 0) else 0.0,
    }
    return {"filas": filas, "resumen": resumen}
