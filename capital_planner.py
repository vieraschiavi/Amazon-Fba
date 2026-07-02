#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents/capital_planner.py — Proyeccion realista de caja (FBA).
Modela lead time, DD+7 (cobro retrasado), sell-through parcial, devoluciones,
reposicion reciclando capital y TECHO DE DEMANDA (no vendes infinito).

Hallazgo clave (memoria del proyecto): retirar toda la ganancia da un pico de sueldo
que se desploma al agotarse el stock; reciclar capital (el costo desembarcado repone
stock y el neto se retira como sueldo) da un sueldo SOSTENIDO ~ techo * neto.
Sin techo de demanda la proyeccion explota y miente: por eso el techo es obligatorio.
"""
import argparse
import json


def proyeccion_realista(budget, landed, precio, net_unit, sell_through=0.5,
                        devoluciones=0.05, lead_time_meses=2, payout_delay_meses=1,
                        techo_demanda=290, meses=12):
    fees_unit = max(0.0, precio - net_unit - landed)   # referral+fba+ads por unidad
    unidades_compra = int(budget // landed) if landed > 0 else 0
    inversion = unidades_compra * landed
    caja = budget - inversion
    transito = [(lead_time_meses, unidades_compra)]    # (mes_llegada, unidades)
    disponible = 0
    cobros = {}                                        # mes -> {"ingreso":x,"unidades":u}
    filas = []
    caja_minima = caja
    sueldo_total = 0.0

    for mes in range(1, meses + 1):
        llegadas = sum(u for (m, u) in transito if m == mes)
        disponible += llegadas
        transito = [(m, u) for (m, u) in transito if m != mes]

        vendidas = min(int(round(disponible * sell_through)), disponible, techo_demanda)
        disponible -= vendidas
        netas = vendidas * (1 - devoluciones)
        ingreso = netas * precio
        mc = mes + payout_delay_meses
        c = cobros.setdefault(mc, {"ingreso": 0.0, "unidades": 0})
        c["ingreso"] += ingreso
        c["unidades"] += vendidas

        cob = cobros.pop(mes, {"ingreso": 0.0, "unidades": 0})
        caja += cob["ingreso"]
        gasto_repos = min(caja, cob["unidades"] * landed)
        unidades_repuestas = int(gasto_repos // landed) if landed > 0 else 0
        caja -= unidades_repuestas * landed
        if unidades_repuestas > 0:
            transito.append((mes + lead_time_meses, unidades_repuestas))
        fees = cob["unidades"] * (1 - devoluciones) * fees_unit
        caja -= fees
        # sueldo = lo que queda tras reponer stock y pagar fees (descuenta devoluciones)
        sueldo = max(0.0, cob["ingreso"] - unidades_repuestas * landed - fees)
        caja -= sueldo
        sueldo_total += sueldo

        caja_minima = min(caja_minima, caja)
        capital_atado = round((disponible + sum(u for _, u in transito)) * landed, 2)
        filas.append({"mes": mes, "llegan": llegadas, "vendidas": vendidas,
                      "ingreso": round(ingreso, 2), "cobrado": round(cob["ingreso"], 2),
                      "repuso_unid": unidades_repuestas, "sueldo": round(sueldo, 2),
                      "caja": round(caja, 2), "capital_atado": capital_atado,
                      "disponible": disponible})

    primer = next((f["mes"] for f in filas if f["cobrado"] > 0), None)
    estables = [f["sueldo"] for f in filas if f["sueldo"] > 0][-4:]
    meseta = round(sum(estables) / len(estables), 2) if estables else 0.0
    resumen = {"unidades_compra": unidades_compra, "inversion": round(inversion, 2),
               "caja_minima": round(caja_minima, 2), "sueldo_meseta": meseta,
               "sueldo_ultimo": filas[-1]["sueldo"] if filas else 0,
               "mes_primer_cobro": primer, "caja_final": filas[-1]["caja"] if filas else 0,
               "techo_demanda": techo_demanda,
               "alerta": "CAJA NEGATIVA: te quedas sin efectivo" if caja_minima < 0 else "ok"}
    return {"filas": filas, "resumen": resumen}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Proyeccion realista de caja FBA.")
    ap.add_argument("--budget", type=float, default=8000)
    ap.add_argument("--landed", type=float, default=5.5)
    ap.add_argument("--precio", type=float, default=24.0)
    ap.add_argument("--net", type=float, default=6.9)
    ap.add_argument("--techo", type=int, default=290)
    ap.add_argument("--meses", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    r = proyeccion_realista(args.budget, args.landed, args.precio, args.net,
                            techo_demanda=args.techo, meses=args.meses)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("Resumen:", r["resumen"])
        for f in r["filas"]:
            print(f"  mes {f['mes']:>2}: caja={f['caja']:>8.0f}  sueldo={f['sueldo']:>6.0f}  "
                  f"vendidas={f['vendidas']:>3}  atado={f['capital_atado']:>7.0f}")
    return 0


if __name__ == "__main__":
    main()


def escenario_inversor(capital_propio, n_productos, techo, precio, net_unit, landed,
                       capital_inversor=0, pct_facturacion=10, pipeline_meses=4):
    """
    Vista de MESETA (estado estable), no simulacion mes a mes.
    - El techo de demanda es compartido: cada producto vende como maximo 'techo' u/mes.
    - El capital total sostiene cierta cantidad de unidades (pipeline = ~4 meses de stock).
    - La comision del inversor = pct% de la FACTURACION que financia SU capital (su parte
      proporcional). Vos te quedas con todo el neto menos esa comision.
    Devuelve el sueldo tuyo con y sin inversor, para ver si te suma o te resta.
    """
    n_productos = max(1, int(n_productos))
    total_cap = capital_propio + max(0, capital_inversor)
    ceiling = n_productos * techo                        # tope por demanda (u/mes)
    cap_units = total_cap / (landed * pipeline_meses) if landed > 0 else 0
    cap_units_solo = capital_propio / (landed * pipeline_meses) if landed > 0 else 0

    unidades = min(ceiling, cap_units)                   # con inversor
    unidades_solo = min(ceiling, cap_units_solo)         # sin inversor
    cuello = "demanda" if ceiling <= cap_units else "capital"

    facturacion = unidades * precio
    net_total = unidades * net_unit
    inv_share = (max(0, capital_inversor) / total_cap) if total_cap > 0 else 0
    comision = (pct_facturacion / 100.0) * facturacion * inv_share
    sueldo = net_total - comision
    sueldo_solo = unidades_solo * net_unit

    ret_inv_mes = (comision / capital_inversor * 100.0) if capital_inversor > 0 else 0
    return {
        "n_productos": n_productos,
        "unidades_mes": round(unidades),
        "facturacion": round(facturacion),
        "net_total": round(net_total),
        "comision_inversor": round(comision),
        "sueldo_martin": round(sueldo),
        "sueldo_sin_inversor": round(sueldo_solo),
        "delta": round(sueldo - sueldo_solo),
        "cuello": cuello,
        "inv_share_pct": round(inv_share * 100, 1),
        "retorno_inversor_mes_pct": round(ret_inv_mes, 1),
    }
