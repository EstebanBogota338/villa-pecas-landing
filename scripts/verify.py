#!/usr/bin/env python3
"""Puerta de verificación del ROADMAP de Villa Pecas.

Uso:
    python scripts/verify.py

Comprueba, en las dos páginas del sitio, las reglas de negocio y de calidad
descritas en ROADMAP.md (§8). Cada línea indica la tarea del roadmap a la que
pertenece, de modo que un fallo es directamente una tarea pendiente.

Devuelve código de salida 0 si todo pasa y 1 si algo falla.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lxml import html as lxml_html

# La consola de Windows usa cp1252 por defecto y rompe con ≥, § o →.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PAGES = {"index.html": "es", "en/index.html": "en"}
TEL = "573108137862"
TOTAL_ES = "$1.320.000"
TOTAL_EN = "COP $1,320,000"
PER_ES = "60.000"
PER_EN = "60,000"

results: list[tuple[str, str, str]] = []  # (estado, tarea, mensaje)


def check(ok: bool, task: str, msg: str) -> None:
    results.append(("OK" if ok else "FALLA", task, msg))


def load(rel: str):
    src = (ROOT / rel).read_text(encoding="utf-8")
    return src, lxml_html.fromstring(src)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def sentence_window(src: str, needle: str, radius: int = 220) -> list[str]:
    """Devuelve el texto alrededor de cada aparición de `needle`."""
    windows = []
    for m in re.finditer(re.escape(needle), src):
        start = max(0, m.start() - radius)
        end = min(len(src), m.end() + radius)
        windows.append(src[start:end])
    return windows


def main() -> int:
    # ---------------------------------------------------------------- estructura
    for rel, lang in PAGES.items():
        path = ROOT / rel
        if not path.exists():
            check(False, "1", f"falta {rel}")
            continue

        src, doc = load(rel)

        check(doc.get("lang") == lang, "1", f"{rel}: lang={doc.get('lang')!r} (esperado {lang!r})")
        check(len(doc.xpath("//h1")) == 1, "1", f"{rel}: {len(doc.xpath('//h1'))} <h1> (debe haber 1)")
        alt = doc.xpath("//link[@rel='alternate']")
        check(len(alt) == 3, "1", f"{rel}: {len(alt)} <link rel=alternate> (deben ser 3)")
        canon = len(doc.xpath("//link[@rel='canonical']"))
        check(canon == 1, "1", f"{rel}: {canon} <link rel=canonical> (debe ser 1)")

        scripts = doc.xpath("//script[@type='application/ld+json']")
        tipos = []
        datos = []
        for s in scripts:
            try:
                payload = json.loads(s.text or "{}")
                datos.append(payload)
                tipos.append(payload.get("@type"))
            except json.JSONDecodeError as exc:
                check(False, "1", f"{rel}: JSON-LD inválido ({exc})")
        check(sorted(t for t in tipos if t) == ["FAQPage", "LodgingBusiness"], "1",
              f"{rel}: tipos JSON-LD {tipos}")

        # ------------------------------------------------------------- WhatsApp
        wa = doc.xpath("//a[contains(@href,'wa.me')]")
        check(len(wa) == 13, "1.3", f"{rel}: {len(wa)} enlaces wa.me (deben ser 13)")
        sin_texto = [a.get("href") for a in wa if "text=" not in (a.get("href") or "")]
        check(not sin_texto, "1.3", f"{rel}: {len(sin_texto)} enlaces sin ?text=")
        otro_num = [a.get("href") for a in wa if TEL not in (a.get("href") or "")]
        check(not otro_num, "1.3", f"{rel}: {len(otro_num)} enlaces a un número distinto de {TEL}")
        sin_noopener = [a.get("href") for a in wa
                        if a.get("target") == "_blank" and "noopener" not in (a.get("rel") or "")]
        check(not sin_noopener, "1.3", f"{rel}: {len(sin_noopener)} enlaces _blank sin rel=noopener")

        # Un enlace doblemente codificado (text=Hola%252C...) hace que WhatsApp
        # muestre los códigos en crudo: el mensaje prellenado deja de servir.
        doble = []
        for a in wa:
            href = a.get("href") or ""
            texto = (parse_qs(urlparse(href).query).get("text") or [""])[0]
            if re.search(r"%[0-9A-Fa-f]{2}", texto):
                doble.append(texto[:60])
        check(not doble, "1.3",
              f"{rel}: {len(doble)} enlaces con el mensaje doblemente codificado "
              f"(WhatsApp mostraría los %20/%2C en crudo)")

        # ------------------------------------------------------- "Desde" / "From"
        if lang == "es":
            malos = re.findall(r">\s*Desde\s*<|Desde\s*\$", src)
        else:
            malos = re.findall(r">\s*From\s*<|From\s*COP", src)
        check(not malos, "1.2", f"{rel}: {len(malos)} apariciones de 'Desde/From' en el precio")

        # ---------------------------------------------------- precio y mínimos
        minimo = "sin mínimo" if lang == "es" else "no minimum"
        check(minimo in src.lower(), "1.1",
              f"{rel}: falta la cadena {minimo!r} (banda de tarifa y condiciones)")

        detalle = doc.xpath("//*[contains(@class,'price-band-detail')]")
        check(bool(detalle), "1.1", f"{rel}: falta .price-band-detail")

        per = PER_ES if lang == "es" else PER_EN
        malas_ventanas = [w for w in sentence_window(src, per) if "22" not in w]
        check(not malas_ventanas, "1.1/1.6",
              f"{rel}: {len(malas_ventanas)} apariciones del precio por persona sin '22' cerca")

        total = TOTAL_ES if lang == "es" else TOTAL_EN
        apariciones = src.count(total)
        check(apariciones >= 5, "1.1/1.2",
              f"{rel}: el total {total} aparece {apariciones} veces (se esperan ≥5: banda, "
              f"ficha, barra móvil, JSON-LD y FAQ)")

        # --------------------------------------------------------------- FAQ
        visibles = [norm(p.text_content()) for p in doc.xpath("//*[contains(@class,'faq-answer')]//p")]
        schema = next((d for d in datos if d.get("@type") == "FAQPage"), {})
        entidades = schema.get("mainEntity", [])
        check(len(visibles) == len(entidades),
              "1.6", f"{rel}: {len(visibles)} respuestas visibles vs {len(entidades)} en JSON-LD")
        desajustes = []
        for i, (texto, ent) in enumerate(zip(visibles, entidades), start=1):
            esperado = norm(ent.get("acceptedAnswer", {}).get("text", ""))
            if texto != esperado:
                desajustes.append(i)
        check(not desajustes, "1.6",
              f"{rel}: FAQ HTML/JSON-LD — discrepancias: {desajustes}")

        # ---------------------------------------------------- hero (jerarquía)
        claim = "Casa entera con piscina" if lang == "es" else "A whole villa with pool"
        check(claim.lower() in src.lower(), "1.4", f"{rel}: el claim del hero no está actualizado")

        # ------------------------------------------------------- condiciones
        check(bool(doc.xpath("//*[@id='condiciones']")), "1.5", f"{rel}: falta #condiciones")
        check(bool(doc.xpath("//*[@id='precios']")), "2.7", f"{rel}: falta id='precios' en la banda")

        # ------------------------------------------------------------ imágenes
        sin_alt = [img.get("src") for img in doc.xpath("//img") if not (img.get("alt") or "").strip()]
        check(not sin_alt, "8", f"{rel}: {len(sin_alt)} <img> sin alt")

        # -------------------------------------------------------------- enlaces
        nav = [norm(a.text_content()).upper() for a in doc.xpath("//*[contains(@class,'nav-menu')]//a")]
        foot = [norm(a.text_content()).upper() for a in doc.xpath("//*[contains(@class,'footer-navigation')]//a")]
        check(all(t in nav for t in ["INICIO"]) and all(
            t in foot for t in nav if t), "2.7",
            f"{rel}: navbar y footer no comparten etiquetas ({nav} vs {foot})")

    # ------------------------------------------------------------------- global
    for archivo, tarea in (("sitemap.xml", "2.1"), ("robots.txt", "2.2")):
        check((ROOT / archivo).exists(), tarea, f"falta {archivo} en la raíz")

    css = (ROOT / "style.css").read_text(encoding="utf-8")
    check(css.count("{") == css.count("}"), "8",
          f"style.css: {css.count('{')} llaves de apertura vs {css.count('}')} de cierre")

    og = ROOT / "assets" / "og-image.jpg"
    if og.exists():
        check(og.stat().st_size <= 200 * 1024, "2.4",
              f"og-image.jpg pesa {og.stat().st_size // 1024} KB (máx. 200)")

    node = shutil.which("node")
    if node:
        for js in ("js/main.js", "js/analytics.js"):
            proc = subprocess.run([node, "--check", str(ROOT / js)],
                                  capture_output=True, text=True)
            check(proc.returncode == 0, "8", f"{js}: sintaxis validada con node --check")
    else:
        results.append(("AVISO", "8", "node no está en PATH: no se validó la sintaxis JS"))

    # ------------------------------------------------------------------ salida
    ancho = max(len(m) for _, _, m in results)
    fallos = 0
    for estado, tarea, msg in results:
        if estado == "FALLA":
            fallos += 1
        print(f"[{estado:5}] §{tarea:<6} {msg}")

    total = len([r for r in results if r[0] != "AVISO"])
    print(f"\n{total - fallos}/{total} comprobaciones OK · {fallos} pendientes")
    if fallos:
        print("Los fallos son tareas del ROADMAP aún no implementadas (ver §3 y §4).")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
