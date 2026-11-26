#!/usr/bin/env python3
"""
Optimizador de imagenes del sitio Villa Pecas.

Procesa en un solo comando todas las imagenes que index.html y style.css
consumen, con un ancho maximo por grupo segun el tamano real al que se pintan:

    grupo        ancho max   motivo
    ----------   ---------   ------------------------------------------------
    carrusel     1200 px     .gallery-slide ~680x420 en pantalla
    grid          800 px     .room-image 443x280 (3 columnas en 1400px)
    hero         1920 px     fondo a pantalla completa
    naturaleza   1200 px     .about-image 766x520, recortada por object-fit

Salida:
    assets/optimizado/*.webp          todas las imagenes del sitio
    assets/og-image.jpg               1200x630 para el og:image
    assets/comparativa-carrusel.jpg   antes/despues del carrusel
    assets/comparativa-sitio.jpg      antes/despues del resto
    assets/optimizado/reporte-optimizacion.md

Uso:
    python scripts/optimizar_imagenes.py
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageEnhance

# --------------------------------------------------------------------------
# Configuracion
# --------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "img")
OUT_DIR = os.path.join(ROOT, "assets", "optimizado")
OG_IMAGE = os.path.join(ROOT, "assets", "og-image.jpg")

WEBP_METHOD = 6

# Compensacion de color: solo si el encoder pierde mas de este % de saturacion
# o contraste respecto a la imagen ya redimensionada.
SAT_LOSS_TOLERANCE = 0.02
CONTRAST_LOSS_TOLERANCE = 0.02
MAX_SAT_FACTOR = 1.10
MAX_CONTRAST_FACTOR = 1.06

OG_SIZE = (1200, 630)    # 1.91:1, formato estandar de Open Graph


@dataclass
class Grupo:
    nombre: str
    etiqueta: str
    max_ancho: int
    calidad: int
    # Techo de peso: si se pasa, se baja calidad escalonadamente hasta
    # `calidad_minima` y nunca por debajo (preferimos un archivo algo mas
    # pesado antes que uno visiblemente sucio).
    target_kb: int = 220
    calidad_minima: int = 76
    archivos: list[str] = field(default_factory=list)


GRUPOS = [
    Grupo(
        nombre="carrusel",
        etiqueta="Carrusel de galeria",
        max_ancho=1200,
        calidad=82,
        target_kb=220,
        archivos=[
            "PiscGal.webp",
            "TurcGal.webp",
            "SHumedGal.webp",
            "SSecaGal.webp",
            "CocGal.webp",
            "BBQGal.webp",
            "ParqGal.webp",
        ],
    ),
    Grupo(
        nombre="grid",
        etiqueta="Tarjetas de espacios",
        max_ancho=800,
        calidad=82,
        target_kb=120,
        archivos=[
            "HabGrid.webp",
            "PiscGrid.webp",
            "TurcoGrid.webp",
            "SHumedGrid.webp",
            "SSecaGrid.webp",
            "CocGrid.webp",
            "BBQGrid.webp",
            "ParqGrid.webp",
            "ECafeGrid.jpg",
        ],
    ),
    Grupo(
        nombre="hero",
        etiqueta="Fondo del hero",
        max_ancho=1920,
        # Lleva un overlay encima (.hero-overlay), asi que tolera algo mas de
        # compresion sin que se note.
        calidad=80,
        target_kb=200,
        archivos=["Hero.webp"],
    ),
    Grupo(
        nombre="naturaleza",
        etiqueta="Seccion Nosotros",
        max_ancho=1200,
        # Es la foto con mas detalle fino (follaje): pesa mas por pixel que el
        # resto, asi que se le da un techo mas alto en vez de castigar la calidad.
        calidad=80,
        target_kb=420,
        archivos=["Naturaleza.webp"],
    ),
]


# --------------------------------------------------------------------------
# Metricas de color
# --------------------------------------------------------------------------

@dataclass
class Metricas:
    saturacion: float


def medir_saturacion(im: Image.Image) -> float:
    """Saturacion media (0-1) ignorando pixeles casi negros."""
    small = im.convert("RGB")
    small = small.resize(
        (400, max(1, round(400 * small.height / small.width))),
        Image.Resampling.BILINEAR,
    )
    _, s_band, v_band = small.convert("HSV").split()
    utiles = [s for s, v in zip(s_band.tobytes(), v_band.tobytes()) if v > 24]
    return (sum(utiles) / len(utiles) / 255.0) if utiles else 0.0


# --------------------------------------------------------------------------
# Codificacion
# --------------------------------------------------------------------------

def codificar_webp(im: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    im.convert("RGB").save(
        buf, format="WEBP", quality=quality, method=WEBP_METHOD, exif=b""
    )
    return buf.getvalue()


def decodificar(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def destino_webp(nombre: str) -> str:
    return os.path.join(OUT_DIR, os.path.splitext(nombre)[0] + ".webp")


# --------------------------------------------------------------------------
# Procesamiento
# --------------------------------------------------------------------------

@dataclass
class Resultado:
    grupo: str
    nombre: str
    src_ancho: int
    src_alto: int
    out_ancho: int
    out_alto: int
    kb_antes: float
    kb_despues: float
    sat_base: float
    sat_encoded: float
    sat_factor: float
    contraste_factor: float
    calidad: float


def procesar(grupo: Grupo, nombre: str) -> Resultado:
    origen = os.path.join(SRC_DIR, nombre)
    if not os.path.exists(origen):
        raise FileNotFoundError(origen)

    im = Image.open(origen).convert("RGB")
    src_w, src_h = im.size

    # 1. Redimension proporcional con tope de ancho
    if src_w > grupo.max_ancho:
        out_w = grupo.max_ancho
        out_h = round(src_h * (grupo.max_ancho / src_w))
    else:
        out_w, out_h = src_w, src_h

    base = im.resize((out_w, out_h), Image.Resampling.LANCZOS)
    sat_base = medir_saturacion(base)

    # 2. Primer encode y medicion de lo que perdio el encoder
    calidad = float(grupo.calidad)
    data = codificar_webp(base, int(calidad))
    sat_encoded = medir_saturacion(decodificar(data))

    # 3. Compensacion de color basada en evidencia.
    # Comparamos contra "base" (ya redimensionada) para aislar la perdida del
    # encoder del suavizado normal del downscale.
    sat_factor = 1.0
    contraste_factor = 1.0
    perdida_sat = 1.0 - (sat_encoded / sat_base if sat_base else 1.0)

    if perdida_sat > SAT_LOSS_TOLERANCE:
        sat_factor = min(MAX_SAT_FACTOR, 1.0 + perdida_sat * 0.5)

    if sat_factor != 1.0:
        ajustada = ImageEnhance.Color(base).enhance(sat_factor)
        data_ajustada = codificar_webp(ajustada, int(calidad))
        sat_ajustada = medir_saturacion(decodificar(data_ajustada))
        if sat_ajustada > sat_encoded:
            data = data_ajustada
            sat_encoded = sat_ajustada
        else:
            sat_factor = 1.0

    # 4. Si sigue pesando demasiado, bajamos calidad escalonadamente
    #    (nunca por debajo de la calidad minima del grupo)
    kb = len(data) / 1024
    while kb > grupo.target_kb and calidad > grupo.calidad_minima:
        calidad = max(grupo.calidad_minima, calidad - 4)
        data = codificar_webp(decodificar(data), int(calidad))
        kb = len(data) / 1024

    with open(destino_webp(nombre), "wb") as fh:
        fh.write(data)

    return Resultado(
        grupo=grupo.etiqueta,
        nombre=nombre,
        src_ancho=src_w,
        src_alto=src_h,
        out_ancho=out_w,
        out_alto=out_h,
        kb_antes=os.path.getsize(origen) / 1024,
        kb_despues=kb,
        sat_base=sat_base,
        sat_encoded=sat_encoded,
        sat_factor=sat_factor,
        contraste_factor=contraste_factor,
        calidad=calidad,
    )


# --------------------------------------------------------------------------
# og:image
# --------------------------------------------------------------------------

def generar_og() -> tuple[int, int]:
    """Recorte 1200x630 del hero optimizado. JPEG: lo aceptan todas las redes."""
    hero = os.path.join(OUT_DIR, "Hero.webp")
    im = Image.open(hero).convert("RGB")

    escala = max(OG_SIZE[0] / im.width, OG_SIZE[1] / im.height)
    w, h = round(im.width * escala), round(im.height * escala)
    im = im.resize((w, h), Image.Resampling.LANCZOS)

    x, y = (w - OG_SIZE[0]) // 2, (h - OG_SIZE[1]) // 2
    im = im.crop((x, y, x + OG_SIZE[0], y + OG_SIZE[1]))

    im.save(OG_IMAGE, "JPEG", quality=88, optimize=True, progressive=True)
    return OG_SIZE


# --------------------------------------------------------------------------
# Hojas de comparacion
# --------------------------------------------------------------------------

def hoja_comparativa(nombres: list[str], salida: str, tw: int, th: int) -> None:
    filas = []
    for nombre in nombres:
        antes = Image.open(os.path.join(SRC_DIR, nombre)).convert("RGB")
        despues = Image.open(destino_webp(nombre)).convert("RGB")

        def encuadrar(im: Image.Image) -> Image.Image:
            e = max(tw / im.width, th / im.height)
            r = im.resize((round(im.width * e), round(im.height * e)), Image.Resampling.LANCZOS)
            x, y = (r.width - tw) // 2, (r.height - th) // 2
            return r.crop((x, y, x + tw, y + th))

        filas.append((nombre, encuadrar(antes), encuadrar(despues)))

    pad, etiqueta_h = 12, 30
    ancho = pad * 3 + tw * 2
    alto = pad + len(filas) * (th + etiqueta_h + pad)
    hoja = Image.new("RGB", (ancho, alto), (24, 30, 27))
    dibujo = ImageDraw.Draw(hoja)

    y = pad
    for nombre, a, d in filas:
        hoja.paste(a, (pad, y))
        hoja.paste(d, (pad * 2 + tw, y))
        kb_a = os.path.getsize(os.path.join(SRC_DIR, nombre)) / 1024
        kb_d = os.path.getsize(destino_webp(nombre)) / 1024
        dibujo.text((pad + 6, y + th + 8), f"ANTES  {nombre}  {kb_a:.0f} KB", fill=(200, 190, 170))
        dibujo.text((pad * 2 + tw + 6, y + th + 8), f"DESPUES  {nombre}  {kb_d:.0f} KB", fill=(196, 169, 104))
        y += th + etiqueta_h + pad

    hoja.save(salida, "JPEG", quality=86, optimize=True)


# --------------------------------------------------------------------------
# Reporte
# --------------------------------------------------------------------------

def peso_documentos() -> float:
    """KB de HTML + CSS + JS, lo unico que no toca este script."""
    total = 0.0
    for rel in ("index.html", "style.css", os.path.join("js", "main.js")):
        ruta = os.path.join(ROOT, rel)
        if os.path.exists(ruta):
            total += os.path.getsize(ruta) / 1024
    return total


def escribir_reporte(resultados: list[Resultado], og_size: tuple[int, int]) -> dict:
    kb_antes = sum(r.kb_antes for r in resultados)
    kb_despues = sum(r.kb_despues for r in resultados)
    kb_og = os.path.getsize(OG_IMAGE) / 1024
    kb_docs = peso_documentos()

    lineas = [
        "# Optimizacion de imagenes del sitio",
        "",
        "Generado por `scripts/optimizar_imagenes.py`. Los originales de `img/`",
        "**no se modifican**: las versiones optimizadas van a `assets/optimizado/`.",
        "",
        "## Peso de la pagina",
        "",
        "| | Antes | Despues |",
        "| --- | --- | --- |",
        f"| HTML + CSS + JS | {kb_docs:.0f} KB | {kb_docs:.0f} KB |",
        f"| Imagenes | {kb_antes/1024:.2f} MB | {kb_despues/1024:.2f} MB |",
        f"| **Lo que descarga el visitante** | **{(kb_docs+kb_antes)/1024:.2f} MB** | "
        f"**{(kb_docs+kb_despues)/1024:.2f} MB** |",
        f"| `og:image` (solo previews de enlaces, no la descarga el visitante) | — | {kb_og:.0f} KB |",
        "",
        f"Reduccion de la pagina: **{100*(1-(kb_docs+kb_despues)/(kb_docs+kb_antes)):.1f}%** "
        f"({(kb_antes-kb_despues)/1024:.2f} MB menos en imagenes).",
        "",
        "## Anchos aplicados",
        "",
        "| Grupo | Imagenes | Ancho maximo | Criterio |",
        "| --- | --- | --- | --- |",
        "| Carrusel de galeria | 7 | 1200 px | `.gallery-slide` se pinta a ~680x420 |",
        "| Tarjetas de espacios | 9 | 800 px | `.room-image` se pinta a 443x280 |",
        "| Fondo del hero | 1 | 1920 px | fondo a pantalla completa con overlay |",
        "| Seccion Nosotros | 1 | 1200 px | `.about-image` 766x520 recortada por `object-fit` |",
        "",
        "## Detalle por imagen",
        "",
        "| Imagen | Grupo | Original | Salida | Peso antes | Peso despues | Ahorro | Ajuste |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for r in resultados:
        ahorro = 100 * (1 - r.kb_despues / r.kb_antes)
        piezas = []
        if r.sat_factor != 1.0:
            piezas.append(f"sat x{r.sat_factor:.3f}")
        if r.contraste_factor != 1.0:
            piezas.append(f"contraste x{r.contraste_factor:.3f}")
        lineas.append(
            f"| `{r.nombre}` | {r.grupo} | {r.src_ancho}x{r.src_alto} | "
            f"{r.out_ancho}x{r.out_alto} | {r.kb_antes:.0f} KB | {r.kb_despues:.0f} KB | "
            f"-{ahorro:.0f}% | {' + '.join(piezas) if piezas else 'no aplicado'} |"
        )

    con_ajuste = [r for r in resultados if r.sat_factor != 1.0 or r.contraste_factor != 1.0]
    if con_ajuste:
        detalle = "Se aplico correccion de color en: " + ", ".join(
            f"`{r.nombre}`" for r in con_ajuste
        ) + "."
    else:
        detalle = (
            "**No se aplico ningun ajuste de color**: la perdida de saturacion tras "
            "codificar a WebP quedo por debajo del 2% en las 18 imagenes, asi que subir "
            "la saturacion solo habria inventado color que la foto no tenia."
        )

    lineas += [
        "",
        "## Nota sobre el color",
        "",
        "El script no sube la saturacion por defecto. Mide la saturacion de la imagen ya",
        "redimensionada y la compara con la misma imagen despues de codificarla a WebP.",
        "Solo si el encoder pierde mas de un 2% aplica una compensacion parcial y acotada",
        "(maximo +10%), y verifica que efectivamente recupere color antes de guardarla.",
        "",
        detalle,
        "",
        "## og:image",
        "",
        f"`assets/og-image.jpg` ({og_size[0]}x{og_size[1]}, formato Open Graph 1.91:1),",
        "recortada del hero optimizado. Se usa JPEG y no WebP porque WhatsApp y algunas",
        "redes antiguas no aceptan WebP como imagen de previsualizacion.",
        "",
        "## Lazy loading",
        "",
        "- **Hero: no.** Es el elemento mas grande de la primera pantalla (LCP). Ademas se",
        "  carga desde CSS (`.hero-background`), donde el atributo `loading` no existe.",
        "- **Carrusel: solo desde la 3a imagen.** Las dos primeras quedan visibles al entrar",
        "  a la seccion; el resto se carga con `loading=\"lazy\"`.",
        "- **Tarjetas de espacios, Nosotros y Contacto: si.** Estan bajo el pliegue.",
        "",
        "## Como regenerar",
        "",
        "```bash",
        "python scripts/optimizar_imagenes.py",
        "```",
    ]

    with open(os.path.join(OUT_DIR, "reporte-optimizacion.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")

    return {"kb_antes": kb_antes, "kb_despues": kb_despues, "kb_og": kb_og}


# --------------------------------------------------------------------------

def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)

    resultados: list[Resultado] = []
    for grupo in GRUPOS:
        print(f"\n== {grupo.etiqueta}  (max {grupo.max_ancho}px, q{grupo.calidad}) ==")
        for nombre in grupo.archivos:
            r = procesar(grupo, nombre)
            resultados.append(r)
            extra = f"  sat x{r.sat_factor:.3f}" if r.sat_factor != 1.0 else ""
            print(
                f"  {nombre:16} {r.src_ancho}x{r.src_alto:<5} -> {r.out_ancho}x{r.out_alto:<5} "
                f"{r.kb_antes:7.0f} KB -> {r.kb_despues:6.0f} KB  q={int(r.calidad)}{extra}"
            )

    og_size = generar_og()

    carrusel = [n for g in GRUPOS if g.nombre == "carrusel" for n in g.archivos]
    resto = [n for g in GRUPOS if g.nombre != "carrusel" for n in g.archivos]
    hoja_comparativa(carrusel, os.path.join(ROOT, "assets", "comparativa-carrusel.jpg"), 560, 315)
    hoja_comparativa(resto, os.path.join(ROOT, "assets", "comparativa-sitio.jpg"), 420, 236)

    tot = escribir_reporte(resultados, og_size)

    print("\n" + "=" * 70)
    print(f"IMAGENES   {tot['kb_antes']/1024:6.2f} MB -> {tot['kb_despues']/1024:6.2f} MB "
          f"({100*(1-tot['kb_despues']/tot['kb_antes']):.1f}% menos)")
    print(f"og:image   {tot['kb_og']:6.0f} KB (nueva, solo para previews de enlaces)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
