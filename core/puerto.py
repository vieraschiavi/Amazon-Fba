#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/puerto.py — Imprime el primer puerto LIBRE desde uno base.

POR QUE NO SE HACE EN EL .BAT: la version en batch parseaba la salida de
`netstat -ano | findstr LISTENING`, y eso tiene tres problemas: depende de que
netstat exista y hable el idioma esperado, hace falso positivo con puertos
parecidos (el 8000 "matchea" dentro de 18000 si el filtro no es exacto), y no
prueba lo unico que importa de verdad -- si el servidor va a poder tomar el
puerto. Aca se intenta el bind real: si liga, esta libre.

Se usa el mismo host que uvicorn (0.0.0.0): un puerto puede estar libre en
127.0.0.1 y ocupado en 0.0.0.0, y en ese caso uvicorn falla igual.

Uso:
    python core/puerto.py 8000        -> imprime 8000, u 8001, etc.
    python core/puerto.py 8000 --n 5  -> prueba 5 puertos, no 20

Sale 1 (sin imprimir nada) si no hay ninguno libre en el rango.
"""
import argparse
import socket
import sys


def libre(puerto, host="0.0.0.0"):
    """True si se puede ligar ese puerto AHORA (que es lo que hara uvicorn)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Sin SO_REUSEADDR a proposito: queremos saber si esta realmente libre,
        # no si podriamos reusar un socket en TIME_WAIT.
        s.bind((host, puerto))
        return True
    except OSError:
        return False
    finally:
        s.close()


def primero_libre(base, cuantos=20, host="0.0.0.0"):
    for p in range(base, base + cuantos):
        if 0 < p <= 65535 and libre(p, host):
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="Primer puerto libre desde uno base")
    ap.add_argument("base", type=int, help="puerto donde empezar a buscar")
    ap.add_argument("--n", type=int, default=20, help="cuantos probar (default 20)")
    ap.add_argument("--host", default="0.0.0.0", help="host a ligar (default 0.0.0.0)")
    a = ap.parse_args()
    p = primero_libre(a.base, a.n, a.host)
    if p is None:
        return 1
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
