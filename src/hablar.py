#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hablar.py  -  El ordenador habla en voz alta con la voz de Alvaro (edge-tts).
Uso:  hablar.py "texto que quieres oir"
Si no pasas texto, saluda al sargento.
"""
import sys
import os
import asyncio
import shutil
import tempfile
import subprocess

import edge_tts

VOZ = "es-ES-AlvaroNeural"   # voz masculina de Edge en espanol (Alvaro)


async def _sintetizar(texto: str, destino: str) -> None:
    com = edge_tts.Communicate(texto, VOZ)
    await com.save(destino)


WIN = sys.platform == "win32"


def _reproducir_mci(ruta: str) -> bool:
    """Windows: reproduce el mp3 con el propio sistema (MCI/winmm), sin instalar nada."""
    import ctypes
    mci = ctypes.windll.winmm.mciSendStringW
    buf = ctypes.create_unicode_buffer(256)
    alias = "xleer_voz"
    if mci(f'open "{ruta}" type mpegvideo alias {alias}', buf, 255, 0):
        return False
    try:
        return mci(f"play {alias} wait", buf, 255, 0) == 0
    finally:
        mci(f"close {alias}", buf, 255, 0)


def _aviso(texto: str) -> None:
    """Programa sin consola (el .exe): un error que nadie ve no sirve; se muestra en una ventana."""
    if WIN and (sys.stdout is None or getattr(sys, "frozen", False)):    # el .exe va sin consola
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, texto, "xleer", 0x10)
        except OSError:
            pass


def _reproducir(ruta: str) -> bool:
    """Reproduce el mp3 con el primer reproductor que haya instalado."""
    if WIN and _reproducir_mci(ruta):
        return True
    reproductores = [
        ["mpv", "--no-video", "--really-quiet"],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
        ["cvlc", "--play-and-exit", "-I", "dummy"],
        ["play", "-q"],                 # sox
    ]
    for cmd in reproductores:
        if shutil.which(cmd[0]):
            subprocess.run(cmd + [ruta], creationflags=0x08000000 if WIN else 0)   # sin ventana de consola
            return True
    return False


def _texto_de_entrada() -> str:
    # 1) argumentos en la linea de comandos
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:]).strip()
    # 2) texto por tuberia (p.ej.  cat libro.txt | hablar )
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def hablar(texto: str) -> int:
    """Genera la voz y la reproduce.  Devuelve 0 si fue bien, 1 si falla la voz, 2 si no hay reproductor."""
    texto = (texto or "").strip()
    if not texto:
        texto = "Si, mi sargento Canovas, a la orden."

    mp3 = os.path.join(tempfile.gettempdir(), "hablar_alvaro.mp3")
    try:
        asyncio.run(_sintetizar(texto, mp3))
    except Exception as e:
        print("ERROR al generar la voz (revisa tu conexion a internet):", e)
        _aviso(f"No se pudo generar la voz (revisa tu conexion a internet).\n\n{e}")
        return 1

    if not _reproducir(mp3):
        print("No encuentro reproductor de audio.")
        print("Instala uno:  sudo apt install -y mpv")
        print("El audio quedo guardado en:", mp3)
        _aviso(f"No se pudo reproducir el audio.\nQuedo guardado en:\n{mp3}")
        return 2
    return 0


def main() -> int:
    return hablar(_texto_de_entrada())


if __name__ == "__main__":
    raise SystemExit(main())
