#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
scripts/generar_video.py — Renderiza el video de 60s a un .mp4 compartible.

POR QUE EXISTE
La landing ya tiene el video: un reproductor que sincroniza la narracion
(landing/media/narracion-XX.mp3) con 9 escenas (7 capturas REALES del programa
+ placa de apertura y de cierre). Pero eso solo se ve DENTRO del sitio: no se
puede subir a Instagram/TikTok/YouTube ni adjuntar a un anuncio. Este script
arma el mismo video, con los mismos assets y los mismos tiempos, como un .mp4.

NO INVENTA NADA: usa las capturas reales de landing/media/, la narracion real
ya grabada, y los mismos cortes de escena que usa el reproductor (STARTS en
landing/index.html). Si cambian ahi, hay que actualizarlos aca (ver CUES).

Uso:
    python scripts/generar_video.py            # los 3 idiomas
    python scripts/generar_video.py --idioma es
    python scripts/generar_video.py --listar   # solo muestra que haria

Requiere ffmpeg en el PATH y Pillow (ya esta en requirements.txt).
Salida: landing/media/video-mvfbaia-XX.mp4
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(_RAIZ, "landing", "media")

W, H = 1600, 900                      # mismo tamano que las capturas reales
NAVY = (11, 18, 48)
ACC = (240, 172, 63)
INK = (238, 241, 251)
SLATE = (170, 179, 204)
GREEN = (142, 210, 74)

F_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
F_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# Orden de escenas y de que archivo sale la imagen de cada una (None = placa
# de texto que se dibuja aca). Igual que ORDER en landing/index.html.
ESCENAS = [
    ("intro", None),
    ("keywords", "escena-investigacion"),
    ("pricing", "escena-pricing"),
    ("portafolio", "escena-portafolio"),
    ("ganancias", "escena-ganancias"),
    ("mercado", "escena-mercado"),
    ("asistente", "escena-asistente"),
    ("multiplataforma", "escena-plataformas"),
    ("cierre", None),
]

# Los MISMOS cortes que usa el reproductor de la landing (const STARTS).
CUES = {
    "es": [0, 8.75, 15.29, 22.03, 27.93, 34.15, 40.52, 47.19, 55.7],
    "en": [0, 10.24, 18.27, 26.82, 33.77, 41.29, 48.95, 55.64, 65.5],
    "pt": [0, 9.44, 16.78, 24.63, 31.55, 38.88, 46.4, 54.28, 65.02],
}

PLACAS = {
    "es": {"intro": ("MV FBA IA", "Tu negocio Amazon, con IA propia"),
           "cierre": ("7 días gratis", "Tu negocio en Amazon, bajo control")},
    "en": {"intro": ("MV FBA IA", "Your Amazon business, with your own AI"),
           "cierre": ("7 days free", "Your Amazon business, under control")},
    "pt": {"intro": ("MV FBA IA", "Seu negócio Amazon, com IA própria"),
           "cierre": ("7 dias grátis", "Seu negócio na Amazon, sob controle")},
}


def _placa(titulo, subtitulo, destino):
    """Dibuja una placa de apertura/cierre con los colores de marca."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 12, H], fill=ACC)
    f_t = ImageFont.truetype(F_BOLD, 96)
    f_s = ImageFont.truetype(F_REG, 42)
    wt = d.textlength(titulo, font=f_t)
    ws = d.textlength(subtitulo, font=f_s)
    d.text(((W - wt) / 2, H / 2 - 96), titulo, font=f_t, fill=INK)
    d.text(((W - ws) / 2, H / 2 + 26), subtitulo, font=f_s, fill=ACC)
    dom = "mvfbaia.com"
    f_d = ImageFont.truetype(F_BOLD, 30)
    d.text(((W - d.textlength(dom, font=f_d)) / 2, H - 96), dom, font=f_d, fill=SLATE)
    img.save(destino, "JPEG", quality=92)


def _fotograma(nombre, base, idioma, tmp):
    """Devuelve la ruta de la imagen de una escena, generandola si es placa."""
    from PIL import Image
    destino = os.path.join(tmp, f"{nombre}.jpg")
    if base is None:
        t, s = PLACAS[idioma][nombre]
        _placa(t, s, destino)
        return destino
    # Captura real del programa. Se usa la del idioma si existe; si no, la ES
    # (las capturas de mercado/plataformas no siempre estan en los 3).
    for cand in (f"{base}-{idioma}.jpg", f"{base}-es.jpg"):
        ruta = os.path.join(MEDIA, cand)
        if not os.path.isfile(ruta):
            continue
        im = Image.open(ruta).convert("RGB")
        if im.size == (W, H):
            im.save(destino, "JPEG", quality=92)
            return destino
        # NO estirar: la captura de "multiplataforma" es del celular (430x880,
        # vertical) y forzarla a 16:9 deforma la pantalla. Se escala
        # respetando la proporcion y se centra sobre el fondo navy -- es lo
        # mismo que hace la landing con object-fit:contain para esa escena.
        esc = min(W / im.width, H / im.height)
        nuevo = im.resize((max(1, int(im.width * esc)), max(1, int(im.height * esc))),
                          Image.LANCZOS)
        lienzo = Image.new("RGB", (W, H), NAVY)
        lienzo.paste(nuevo, ((W - nuevo.width) // 2, (H - nuevo.height) // 2))
        lienzo.save(destino, "JPEG", quality=92)
        return destino
    raise FileNotFoundError(f"falta la captura de la escena '{nombre}' ({base})")


def duracion_audio(ruta):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", ruta],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def generar(idioma, listar=False):
    audio = os.path.join(MEDIA, f"narracion-{idioma}.mp3")
    if not os.path.isfile(audio):
        print(f"  [{idioma}] falta {audio} — se saltea")
        return None
    total = duracion_audio(audio)
    cues = CUES[idioma]
    if len(cues) != len(ESCENAS):
        raise ValueError(f"{idioma}: {len(cues)} cues para {len(ESCENAS)} escenas")

    # duracion de cada escena = hasta el proximo cue (la ultima, hasta el final)
    dur = [(cues[i + 1] if i + 1 < len(cues) else total) - cues[i]
           for i in range(len(cues))]

    salida = os.path.join(MEDIA, f"video-mvfbaia-{idioma}.mp4")
    print(f"  [{idioma}] narracion {total:.1f}s, {len(ESCENAS)} escenas -> {os.path.basename(salida)}")
    if listar:
        for (n, _), d in zip(ESCENAS, dur):
            print(f"        {n:<18} {d:5.2f}s")
        return salida

    tmp = tempfile.mkdtemp(prefix="mvfba-video-")
    try:
        rutas = [_fotograma(n, b, idioma, tmp) for n, b in ESCENAS]
        # concat demuxer: cada imagen con su duracion exacta
        lista = os.path.join(tmp, "lista.txt")
        with open(lista, "w", encoding="utf-8") as f:
            for r, d in zip(rutas, dur):
                f.write(f"file '{r}'\nduration {d:.3f}\n")
            f.write(f"file '{rutas[-1]}'\n")   # el concat pide repetir la ultima
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", lista,
            "-i", audio,
            "-c:v", "libx264", "-preset", "medium", "-crf", "21",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",       # arranca a reproducir sin bajar todo
            "-shortest", salida,
        ]
        subprocess.run(cmd, check=True)
        return salida
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Renderiza el video de la landing a .mp4")
    ap.add_argument("--idioma", choices=["es", "en", "pt"], help="solo este idioma")
    ap.add_argument("--listar", action="store_true", help="no renderiza, solo informa")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        print("Falta ffmpeg en el PATH.", file=sys.stderr)
        return 1
    idiomas = [a.idioma] if a.idioma else ["es", "en", "pt"]
    print("Generando video desde las capturas y la narracion reales:")
    for i in idiomas:
        r = generar(i, a.listar)
        if r and not a.listar and os.path.isfile(r):
            print(f"        OK {os.path.getsize(r) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
