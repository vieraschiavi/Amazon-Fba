#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# © 2026 Martín Viera. Todos los derechos reservados.
"""
agents/creativos.py — Generador de creatividades visuales de MV FBA IA.

Genera IMAGENES reales (PNG), no solo un brief de texto: un banner hero para el
listing/A+ y una infografia de beneficios, con la paleta de marca (navy/verde),
listas para usar como material de referencia o base editable. Sin APIs pagas de
generacion de imagenes: todo se dibuja con Pillow (libreria estandar de imagenes).

HONESTIDAD: esto NO reemplaza la foto real del producto que Amazon exige (la
foto principal tiene que ser una foto de verdad). Sirve para el banner/infografia
de apoyo (A+ Content, redes, anuncios) y como referencia de estilo para el
disenador o para vos si editas a mano.
"""
import io
import os
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

NAVY = (30, 58, 138)
NAVY_DEEP = (21, 42, 99)
GREEN = (139, 195, 74)
WHITE = (255, 255, 255)
INK = (15, 23, 42)
SLATE = (100, 116, 139)


def _font(tam, negrita=False):
    """Fuente del sistema si existe; si no, la bitmap por defecto de Pillow."""
    candidatos = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if negrita else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    ) + ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/System/Library/Fonts/Helvetica.ttc"]
    for ruta in candidatos:
        if os.path.isfile(ruta):
            try:
                return ImageFont.truetype(ruta, tam)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


def _gradiente_diagonal(w, h, c1, c2):
    """Fondo con gradiente diagonal navy -> navy_deep (mismo estilo del header)."""
    base = Image.new("RGB", (w, h), c1)
    top = Image.new("RGB", (w, h), c2)
    mask = Image.new("L", (w, h))
    mdata = []
    diag = w + h
    for y in range(h):
        for x in range(w):
            mdata.append(int(255 * (x + y) / diag))
    mask.putdata(mdata)
    return Image.composite(top, base, mask)


def _texto_centrado(draw, cx, y, texto, fuente, color=WHITE):
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    w = bbox[2] - bbox[0]
    draw.text((cx - w / 2, y), texto, font=fuente, fill=color)
    return bbox[3] - bbox[1]


def _wrap_centrado(draw, cx, y, texto, fuente, max_chars, color=WHITE, salto=1.25):
    lineas = textwrap.wrap(texto, width=max_chars) or [texto]
    alto_total = 0
    for ln in lineas:
        alto = _texto_centrado(draw, cx, y + alto_total, ln, fuente, color)
        alto_total += alto * salto
    return alto_total


def _badge(draw, x0, y, texto, fuente):
    """Pill verde con texto, arrancando en x0. Devuelve (ancho, alto) real."""
    pad_x, pad_y = 18, 10
    bbox = draw.textbbox((0, 0), texto, font=fuente)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w, h = tw + pad_x * 2, th + pad_y * 2
    draw.rounded_rectangle([x0, y, x0 + w, y + h], radius=h / 2, fill=GREEN)
    draw.text((x0 + pad_x, y + pad_y - bbox[1]), texto, font=fuente, fill=NAVY_DEEP)
    return w, h


def generar_banner(titulo, badges=None, marca="MV FBA IA", size=1200):
    """
    Banner hero cuadrado (para A+ Content / redes / anuncio). Devuelve PNG bytes.
    """
    badges = (badges or [])[:3]
    img = _gradiente_diagonal(size, size, NAVY, NAVY_DEEP)
    draw = ImageDraw.Draw(img)
    cx = size / 2

    # circulo decorativo (acento, mismo estilo que el header del panel)
    r = size * 0.35
    draw.ellipse([size - r * 0.9, -r * 0.5, size + r * 0.5, r * 0.9],
                fill=(139, 195, 74, 40))

    f_marca = _font(int(size * 0.032))
    f_tit = _font(int(size * 0.062), negrita=True)
    f_badge = _font(int(size * 0.03))

    y = size * 0.10
    draw.text((size * 0.06, y), marca.upper(), font=f_marca, fill=(199, 210, 254))
    y += size * 0.10

    titulo_corto = titulo if len(titulo) <= 70 else titulo[:67].rstrip() + "…"
    alto_tit = _wrap_centrado(draw, cx, y, titulo_corto, f_tit, max_chars=22)
    y += alto_tit + size * 0.06

    x = size * 0.06
    gap = size * 0.025
    for b in badges:
        bw, bh = _badge(draw, x, y, b.upper()[:20], f_badge)
        x += bw + gap

    # franja inferior con marca
    banda_h = size * 0.09
    draw.rectangle([0, size - banda_h, size, size], fill=(255, 255, 255, 255))
    f_pie = _font(int(size * 0.026))
    draw.text((size * 0.06, size - banda_h + banda_h * 0.3),
              "Amazon FBA · mercado US", font=f_pie, fill=SLATE)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generar_infografia(bullets, size=(1200, 1200)):
    """Infografia de beneficios: hasta 4 bullets con numeral circular. PNG bytes."""
    w, h = size
    img = Image.new("RGB", (w, h), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, w, int(h * 0.14)], fill=NAVY)
    f_tit = _font(int(w * 0.04), negrita=True)
    draw.text((w * 0.06, h * 0.045), "POR QUE ELEGIRNOS", font=f_tit, fill=WHITE)

    items = (bullets or [])[:4]
    f_num = _font(int(w * 0.045), negrita=True)
    f_txt = _font(int(w * 0.028))
    y0 = h * 0.22
    paso = (h * 0.92 - y0) / max(1, len(items))
    for i, b in enumerate(items):
        y = y0 + i * paso
        cy = y + paso * 0.28
        r = w * 0.045
        cx = w * 0.11
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GREEN)
        num = str(i + 1)
        bbox = draw.textbbox((0, 0), num, font=f_num)
        draw.text((cx - (bbox[2] - bbox[0]) / 2, cy - (bbox[3] - bbox[1]) / 2 - bbox[1]),
                  num, font=f_num, fill=NAVY_DEEP)
        texto_corto = b if len(b) <= 90 else b[:87].rstrip() + "…"
        lineas = textwrap.wrap(texto_corto, width=48)
        ty = cy - (len(lineas) * w * 0.032) / 2
        for ln in lineas:
            draw.text((cx + r + w * 0.03, ty), ln, font=f_txt, fill=INK)
            ty += w * 0.032
        if i < len(items) - 1:
            draw.line([w * 0.06, y + paso - h * 0.02, w * 0.94, y + paso - h * 0.02],
                      fill=(226, 232, 240), width=2)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generar_icono_app(size=512, con_fondo=True):
    """
    Icono de la app (monograma MV) para el instalador de escritorio y la PWA.
    Cuadrado, esquinas redondeadas, gradiente navy + trazo verde en la V/IA.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = size * 0.22
    if con_fondo:
        grad = _gradiente_diagonal(size, size, NAVY, NAVY_DEEP).convert("RGBA")
        mask = Image.new("L", (size, size), 0)
        mdraw = ImageDraw.Draw(mask)
        mdraw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
        img.paste(grad, (0, 0), mask)

    # trazo "M" en blanco (dos picos) y "V" en verde, estilo monograma del logo
    lw = max(6, int(size * 0.052))
    m_pts = [(size * 0.20, size * 0.68), (size * 0.20, size * 0.32),
              (size * 0.36, size * 0.58), (size * 0.52, size * 0.32)]
    draw.line(m_pts, fill=WHITE, width=lw, joint="curve")
    for p in (m_pts[0], m_pts[-1]):
        draw.ellipse([p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2],
                     fill=WHITE)
    v_pts = [(size * 0.60, size * 0.32), (size * 0.72, size * 0.68),
             (size * 0.84, size * 0.32)]
    draw.line(v_pts, fill=GREEN, width=lw, joint="curve")
    for p in (v_pts[0], v_pts[-1]):
        draw.ellipse([p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2],
                     fill=GREEN)
    return img


def guardar_iconos(destino_ico=None, destino_png_dir=None):
    """
    Genera y guarda: un .ico multi-tamano (Windows) y PNG 192/512 (PWA/Android),
    incluida una variante 'maskable' con relleno de seguridad para Android.
    """
    rutas = {}
    if destino_ico:
        img = generar_icono_app(256)
        tamanos = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(destino_ico, format="ICO", sizes=tamanos)
        rutas["ico"] = destino_ico
    if destino_png_dir:
        os.makedirs(destino_png_dir, exist_ok=True)
        for tam in (192, 512):
            p = os.path.join(destino_png_dir, f"icon-{tam}.png")
            generar_icono_app(tam).save(p, format="PNG")
            rutas[f"png{tam}"] = p
        # maskable: mismo diseño pero con ~20% de margen de seguridad (Android
        # puede recortar en circulo/redondeado y no debe cortar el monograma)
        tam = 512
        safe = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        base = generar_icono_app(int(tam * 0.6))
        safe.paste(_gradiente_diagonal(tam, tam, NAVY, NAVY_DEEP).convert("RGBA"),
                  (0, 0))
        safe.paste(base, (int(tam * 0.2), int(tam * 0.2)), base)
        p = os.path.join(destino_png_dir, "icon-512-maskable.png")
        safe.save(p, format="PNG")
        rutas["maskable"] = p
    return rutas


def kit_creativo(titulo, bullets):
    """Devuelve {banner_png, infografia_png} listos para descargar/mostrar."""
    return {
        "banner_png": generar_banner(titulo, badges=[b.split()[0] for b in
                                                      (bullets or [])[:3]]),
        "infografia_png": generar_infografia(bullets),
        "nota": ("Banner e infografia generados localmente (Pillow, sin costo). "
                 "NO reemplazan la foto principal real que Amazon exige: usalos "
                 "como imagen secundaria/A+ o como referencia de estilo."),
    }


if __name__ == "__main__":
    k = kit_creativo("Bamboo Kitchen Utensils Set - Eco Friendly",
                     ["Premium eco material, BPA-free", "Heat resistant up to 446F",
                      "Dishwasher safe", "Perfect gift"])
    with open("/tmp/banner_test.png", "wb") as f:
        f.write(k["banner_png"])
    with open("/tmp/infografia_test.png", "wb") as f:
        f.write(k["infografia_png"])
    print("Escrito /tmp/banner_test.png y /tmp/infografia_test.png")
