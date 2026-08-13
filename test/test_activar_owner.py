#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
test_activar_owner.py — INSTALADOR/activar_owner.py encuentra la instalacion
SIN IMPORTAR que carpeta haya elegido el usuario al instalar.

POR QUE EXISTE: el instalador (.iss, DisableDirPage=no) deja elegir CUALQUIER
carpeta de destino. Antes, activar_owner.py (y el .bat que lo envuelve) solo
adivinaban 4 rutas fijas (Archivos de programa, Archivos de programa (x86),
LocalAppData\\Programs, Escritorio) -- si el usuario instalaba en, por
ejemplo, "D:\\Apps\\MV FBA IA", ninguna adivinanza matcheaba, y la unica salida
era copiar el .bat/.py A MANO dentro de esa carpeta. Ahora se busca primero
en el registro de Windows: todo instalador de Inno Setup registra su
instalacion real en "Agregar o quitar programas" (InstallLocation, bajo una
clave con el AppId del propio .iss) -- ese es el mismo mecanismo que usa
Windows para mostrar el programa en el panel de control, funciona sin
importar donde se haya instalado.

Como winreg no existe en Linux, estos tests inyectan un modulo winreg FALSO
(ver FakeWinreg) en vez de tocar un registro real.

Uso:   python -m pytest test/test_activar_owner.py -q
"""
import os
import re
import sys

import pytest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
_INSTALADOR = os.path.join(_RAIZ, "INSTALADOR")
if _INSTALADOR not in sys.path:
    sys.path.insert(0, _INSTALADOR)

import activar_owner  # noqa: E402


# --------------------------------------------------------------------------- #
# Fake de winreg: un registro en memoria, misma forma de API que el real
# (HKEY_*, OpenKey, QueryValueEx) para poder inyectarlo sin tocar Windows.
# --------------------------------------------------------------------------- #
class FakeWinreg:
    HKEY_CURRENT_USER = "HKCU"
    HKEY_LOCAL_MACHINE = "HKLM"

    def __init__(self, datos=None):
        # datos: {(raiz, subclave): {nombre_valor: valor}}
        self.datos = datos or {}

    def OpenKey(self, raiz, subclave):
        if (raiz, subclave) not in self.datos:
            raise FileNotFoundError(f"clave no encontrada: {raiz}\\{subclave}")
        return _FakeKey(self.datos[(raiz, subclave)])

    def QueryValueEx(self, clave, nombre):
        if nombre not in clave.valores:
            raise FileNotFoundError(f"valor no encontrado: {nombre}")
        return clave.valores[nombre], 1  # 1 = REG_SZ (no importa para el test)


class _FakeKey:
    def __init__(self, valores):
        self.valores = valores

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _subclave_uninstall():
    return ("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
            + activar_owner.APP_ID + "_is1")


def _crear_instalacion(tmp_path, nombre="Instalacion"):
    """Una carpeta que pasa es_instalacion(): con app.py y core/licencia.py."""
    carpeta = tmp_path / nombre
    (carpeta / "core").mkdir(parents=True)
    (carpeta / "app.py").write_text("# app\n")
    (carpeta / "core" / "licencia.py").write_text("# licencia\n")
    return carpeta


# --------------------------------------------------------------------------- #
# es_instalacion
# --------------------------------------------------------------------------- #
def test_es_instalacion_exige_app_y_core_licencia(tmp_path):
    completa = _crear_instalacion(tmp_path, "completa")
    assert activar_owner.es_instalacion(str(completa)) is True

    solo_app = tmp_path / "solo_app"
    solo_app.mkdir()
    (solo_app / "app.py").write_text("# app\n")
    assert activar_owner.es_instalacion(str(solo_app)) is False   # falta core/licencia.py

    assert activar_owner.es_instalacion("") is False
    assert activar_owner.es_instalacion(None) is False
    assert activar_owner.es_instalacion(str(tmp_path / "no_existe")) is False


# --------------------------------------------------------------------------- #
# _buscar_por_registro
# --------------------------------------------------------------------------- #
def test_registro_encuentra_una_carpeta_custom_cualquiera(tmp_path):
    """El caso que motivo el cambio: una carpeta que el usuario eligio a mano
    al instalar, que NINGUNA de las rutas adivinadas (CANDIDATAS) cubre."""
    custom = _crear_instalacion(tmp_path, "D_Apps_MV_FBA_IA_a_mano")
    assert str(custom) not in activar_owner.CANDIDATAS

    fake = FakeWinreg({("HKCU", _subclave_uninstall()): {"InstallLocation": str(custom)}})
    encontrada = activar_owner._buscar_por_registro(winreg_mod=fake)
    assert encontrada == os.path.abspath(str(custom))


def test_registro_prueba_hkcu_primero_y_cae_a_hklm(tmp_path):
    """HKCU es el caso mas comun (instalacion 'solo para mi', sin admin). Si
    ahi no hay nada, tiene que probar HKLM antes de rendirse."""
    solo_hklm = _crear_instalacion(tmp_path, "instalada_para_todos")
    fake = FakeWinreg({("HKLM", _subclave_uninstall()): {"InstallLocation": str(solo_hklm)}})
    encontrada = activar_owner._buscar_por_registro(winreg_mod=fake)
    assert encontrada == os.path.abspath(str(solo_hklm))


def test_registro_sin_ninguna_clave_no_rompe(tmp_path):
    fake = FakeWinreg({})   # ni HKCU ni HKLM tienen la clave
    assert activar_owner._buscar_por_registro(winreg_mod=fake) is None


def test_registro_con_installlocation_apuntando_a_basura_no_lo_acepta(tmp_path):
    """InstallLocation podria sobrevivir en el registro despues de una
    desinstalacion incompleta, o apuntar a una carpeta que ya no tiene el
    programa adentro -- no hay que devolver una ruta que despues explota."""
    basura = tmp_path / "carpeta_vacia"
    basura.mkdir()
    fake = FakeWinreg({("HKCU", _subclave_uninstall()): {"InstallLocation": str(basura)}})
    assert activar_owner._buscar_por_registro(winreg_mod=fake) is None


def test_registro_sin_winreg_disponible_no_rompe():
    """En Linux (o cualquier entorno sin winreg) tiene que devolver None en
    vez de lanzar -- es exactamente lo que pasa en este entorno de test."""
    assert activar_owner._buscar_por_registro(winreg_mod=None) is None


# --------------------------------------------------------------------------- #
# buscar_instalacion: orden de precedencia completo
# --------------------------------------------------------------------------- #
def test_buscar_instalacion_preferida_gana_a_todo(tmp_path, monkeypatch):
    preferida = _crear_instalacion(tmp_path, "la_que_pidio_el_usuario")
    otra_por_registro = _crear_instalacion(tmp_path, "la_del_registro")
    fake = FakeWinreg({("HKCU", _subclave_uninstall()): {"InstallLocation": str(otra_por_registro)}})
    monkeypatch.chdir(tmp_path)   # que cwd no interfiera
    r = activar_owner.buscar_instalacion(preferida=str(preferida), winreg_mod=fake)
    assert r == os.path.abspath(str(preferida))


def test_buscar_instalacion_usa_el_registro_cuando_no_hay_preferida_ni_cwd(tmp_path, monkeypatch):
    custom = _crear_instalacion(tmp_path, "carpeta_elegida_al_instalar")
    vacio = tmp_path / "cwd_vacio"
    vacio.mkdir()
    monkeypatch.chdir(vacio)
    fake = FakeWinreg({("HKCU", _subclave_uninstall()): {"InstallLocation": str(custom)}})
    r = activar_owner.buscar_instalacion(preferida=None, winreg_mod=fake)
    assert r == os.path.abspath(str(custom))


def test_buscar_instalacion_sin_nada_devuelve_none(tmp_path, monkeypatch):
    vacio = tmp_path / "nada_aca"
    vacio.mkdir()
    monkeypatch.chdir(vacio)
    fake = FakeWinreg({})
    r = activar_owner.buscar_instalacion(preferida=None, winreg_mod=fake)
    # Puede devolver una de las CANDIDATAS si por azar existe en esta maquina
    # de test (no deberia, son rutas de Windows) -- lo que se fija es que NO
    # invente una carpeta que no exista.
    assert r is None or activar_owner.es_instalacion(r)


# --------------------------------------------------------------------------- #
# El AppId no puede desincronizarse del .iss (ni del .bat)
# --------------------------------------------------------------------------- #
def test_app_id_coincide_con_el_iss():
    iss = os.path.join(_RAIZ, "installer", "MV_Amazon_FBA_IA.iss")
    contenido = open(iss, "r", encoding="utf-8").read()
    m = re.search(r"AppId=\{\{([0-9A-Fa-f-]+)\}", contenido)
    assert m, "no se encontro AppId en el .iss"
    app_id_iss = "{" + m.group(1) + "}"
    assert activar_owner.APP_ID == app_id_iss, (
        f"activar_owner.APP_ID ({activar_owner.APP_ID}) quedo desincronizado "
        f"del AppId real del .iss ({app_id_iss}) -- sin esto, la busqueda por "
        f"registro nunca encuentra nada.")


def test_activar_owner_bat_busca_en_el_registro_con_el_mismo_app_id():
    bat = os.path.join(_INSTALADOR, "ACTIVAR_OWNER.bat")
    contenido = open(bat, "r", encoding="utf-8").read()
    assert activar_owner.APP_ID in contenido, (
        "ACTIVAR_OWNER.bat no menciona el mismo AppId que activar_owner.py -- "
        "quedaria buscando una clave de registro que nunca va a existir.")
    assert "reg query" in contenido.lower(), "ACTIVAR_OWNER.bat no consulta el registro"
    assert "InstallLocation" in contenido

    # el chequeo de registro tiene que estar ANTES del bloque que se rinde
    # ("if not defined PROG ( ... No encontre la instalacion")-- si no, nunca
    # se llega a usarlo.
    idx_reg = contenido.find("reg query")
    idx_rendirse = contenido.find("No encontre la instalacion")
    assert idx_reg != -1 and idx_rendirse != -1 and idx_reg < idx_rendirse, (
        "la consulta al registro en el .bat no corre ANTES de rendirse")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
