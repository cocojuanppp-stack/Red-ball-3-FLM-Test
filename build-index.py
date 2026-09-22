#!/usr/bin/env python3
"""
Organiza el repositorio en carpetas independientes por juego:

  games/<slug>/index.html   -> reproductor standalone de ESE juego
  games/<slug>/juego.swf    -> el archivo original (se copia/renombra una vez)
  games/<slug>/juego.json   -> metadatos de ese juego

y genera catalog-index.json en la raíz para que el catálogo principal
(index.html) enlace a cada carpeta.

Cómo usarlo:
  1. Coloca tus .swf en CUALQUIER parte del repositorio (cualquier subcarpeta).
  2. Ejecuta: python3 build-index.py   (o build.bat / build.command)
  3. El script:
       - detecta .swf nuevos que aún no tienen carpeta propia y les crea una
         en games/<slug>/, con su index.html standalone ya listo para abrir
         o compartir solo.
       - vuelve a escanear las carpetas games/<slug>/ ya existentes y
         regenera catalog-index.json con todas ellas.
  4. Puedes borrar los .swf sueltos originales después de organizados
     (quedan copiados dentro de games/<slug>/juego.swf).

Ejecutarlo de nuevo es seguro: no duplica juegos ya organizados (los
detecta por el nombre de archivo original guardado en juego.json).
"""
import json
import os
import re
import shutil

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_GAMES = os.path.join(RAIZ, "games")
PLANTILLA = os.path.join(RAIZ, "_plantilla_juego.html")
SALIDA_CATALOGO = os.path.join(RAIZ, "catalog-index.json")

IGNORAR_CARPETAS = {".git", "node_modules", "assets", "__pycache__", "games"}

# ---------- Reconocimiento de juego por nombre de archivo ----------
PATRONES = [
    (re.compile(r"red_ball_4.*vol.*1|redball4.*vol.*1", re.I),
     dict(nombre="Red Ball 4", vol="Volumen 1", desc="75 niveles, física mejorada",
          color1="#e5341f", color2="#6b1206", busqueda="Red Ball 4 Volume 1 walkthrough gameplay")),
    (re.compile(r"red_ball_4.*vol.*2|redball4.*vol.*2", re.I),
     dict(nombre="Red Ball 4", vol="Volumen 2", desc="Nuevos escenarios y jefes",
          color1="#e5341f", color2="#5c0f05", busqueda="Red Ball 4 Volume 2 walkthrough gameplay")),
    (re.compile(r"red_ball_4.*vol.*3|redball4.*vol.*3", re.I),
     dict(nombre="Red Ball 4", vol="Volumen 3", desc="El desafío final de la saga",
          color1="#e5341f", color2="#4d0c04", busqueda="Red Ball 4 Volume 3 walkthrough gameplay")),
    (re.compile(r"redball.*17|17.*level", re.I),
     dict(nombre="Red Ball 17 Levels", vol="Edición extendida", desc="Versión con 17 niveles extra",
          color1="#ff9a7c", color2="#c23515", busqueda="Red Ball 17 levels walkthrough gameplay")),
    (re.compile(r"red_ball_2|redball2", re.I),
     dict(nombre="Red Ball 2", vol="2ª entrega", desc="Nuevos obstáculos y trampas",
          color1="#ff6a4a", color2="#8f1c0c", busqueda="Red Ball 2 walkthrough gameplay")),
    (re.compile(r"red_ball_3|redball3", re.I),
     dict(nombre="Red Ball 3", vol="3ª entrega", desc="Más niveles, más dificultad",
          color1="#ff5a3a", color2="#7a1608", busqueda="Red Ball 3 walkthrough gameplay")),
    (re.compile(r"red.*blue.*balls.*2|red_+_blue_balls_2", re.I),
     dict(nombre="Red & Blue Balls 2", vol="2ª entrega", desc="Puzzles duales más complejos",
          color1="#1f6fe5", color2="#e5341f", busqueda="Red and Blue Balls 2 walkthrough gameplay")),
    (re.compile(r"red.*blue.*balls.*3|red_+_blue_balls_3", re.I),
     dict(nombre="Red & Blue Balls 3", vol="3ª entrega", desc="La aventura dual definitiva",
          color1="#1f6fe5", color2="#e5341f", busqueda="Red and Blue Balls 3 walkthrough gameplay")),
    (re.compile(r"red.*blue.*balls|red_+_blue_balls", re.I),
     dict(nombre="Red & Blue Balls", vol="1ª entrega", desc="Cooperativo: controla ambas bolas",
          color1="#1f6fe5", color2="#e5341f", busqueda="Red and Blue Balls 1 walkthrough gameplay")),
    (re.compile(r"red_ball|redball", re.I),
     dict(nombre="Red Ball", vol="1ª entrega", desc="El clásico original",
          color1="#ff7a5c", color2="#a3220f", busqueda="Red Ball 1 walkthrough gameplay")),
]


def metadatos_para(nombre_archivo):
    for patron, meta in PATRONES:
        if patron.search(nombre_archivo):
            return dict(meta)
    limpio = re.sub(r"\.swf$", "", nombre_archivo, flags=re.I)
    limpio = re.sub(r"[_\-]+", " ", limpio).strip()
    return dict(
        nombre=limpio or "Juego sin nombre",
        vol="Sin catalogar",
        desc="Archivo detectado automáticamente",
        color1="#9a9186", color2="#4a453d",
        busqueda=limpio + " walkthrough gameplay",
    )


def slug_para(nombre_archivo, meta):
    base = f"{meta['nombre']}-{meta['vol']}"
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return base or re.sub(r"[^a-zA-Z0-9]+", "-", nombre_archivo).strip("-").lower()


def swfs_ya_organizados():
    """Nombres de archivo original ya registrados dentro de games/*/juego.json"""
    registrados = set()
    if not os.path.isdir(CARPETA_GAMES):
        return registrados
    for slug in os.listdir(CARPETA_GAMES):
        ruta_json = os.path.join(CARPETA_GAMES, slug, "juego.json")
        if os.path.isfile(ruta_json):
            try:
                with open(ruta_json, encoding="utf-8") as f:
                    datos = json.load(f)
                    registrados.add(datos.get("archivo_original"))
            except Exception:
                pass
    return registrados


def encontrar_swfs_sueltos():
    """Busca .swf en todo el repo, fuera de games/, para organizarlos."""
    sueltos = []
    for actual, carpetas, archivos in os.walk(RAIZ):
        carpetas[:] = [c for c in carpetas if c not in IGNORAR_CARPETAS]
        for nombre in archivos:
            if nombre.lower().endswith(".swf"):
                sueltos.append(os.path.join(actual, nombre))
    return sueltos


def crear_carpeta_juego(ruta_swf_original, plantilla_html):
    nombre_archivo = os.path.basename(ruta_swf_original)
    meta = metadatos_para(nombre_archivo)
    slug = slug_para(nombre_archivo, meta)

    destino = os.path.join(CARPETA_GAMES, slug)
    sufijo = 2
    slug_final = slug
    while os.path.isdir(destino):
        slug_final = f"{slug}-{sufijo}"
        destino = os.path.join(CARPETA_GAMES, slug_final)
        sufijo += 1

    os.makedirs(destino, exist_ok=True)
    shutil.copy2(ruta_swf_original, os.path.join(destino, "juego.swf"))

    with open(os.path.join(destino, "juego.json"), "w", encoding="utf-8") as f:
        json.dump({"archivo_original": nombre_archivo, **meta}, f, ensure_ascii=False, indent=2)

    html = plantilla_html
    html = html.replace("__NOMBRE__", meta["nombre"])
    html = html.replace("__VOL__", meta["vol"])
    html = html.replace("__ARCHIVO_SWF__", "juego.swf")
    html = html.replace("__BUSQUEDA_URL__", meta["busqueda"].replace(" ", "+"))
    html = html.replace("__RUTA_CATALOGO__", "../../index.html")
    with open(os.path.join(destino, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  + games/{slug_final}/  <-  {nombre_archivo}")
    return slug_final


def main():
    if not os.path.isfile(PLANTILLA):
        print("ERROR: no se encontró _plantilla_juego.html junto a este script.")
        return

    with open(PLANTILLA, encoding="utf-8") as f:
        plantilla_html = f.read()

    os.makedirs(CARPETA_GAMES, exist_ok=True)

    ya_organizados = swfs_ya_organizados()
    sueltos = encontrar_swfs_sueltos()
    nuevos = [r for r in sueltos if os.path.basename(r) not in ya_organizados]

    if nuevos:
        print(f"Organizando {len(nuevos)} archivo(s) .swf nuevo(s) en carpetas propias:")
        for ruta in nuevos:
            crear_carpeta_juego(ruta, plantilla_html)
    else:
        print("No hay archivos .swf sueltos nuevos por organizar.")

    # Reconstruir el catálogo a partir de TODAS las carpetas games/<slug>/
    catalogo = []
    if os.path.isdir(CARPETA_GAMES):
        for slug in sorted(os.listdir(CARPETA_GAMES)):
            ruta_json = os.path.join(CARPETA_GAMES, slug, "juego.json")
            ruta_html = os.path.join(CARPETA_GAMES, slug, "index.html")
            if os.path.isfile(ruta_json) and os.path.isfile(ruta_html):
                with open(ruta_json, encoding="utf-8") as f:
                    meta = json.load(f)
                catalogo.append({
                    "slug": slug,
                    "ruta": f"games/{slug}/index.html",
                    "nombre": meta.get("nombre", slug),
                    "vol": meta.get("vol", ""),
                    "desc": meta.get("desc", ""),
                    "color1": meta.get("color1", "#9a9186"),
                    "color2": meta.get("color2", "#4a453d"),
                })

    with open(SALIDA_CATALOGO, "w", encoding="utf-8") as f:
        json.dump({"juegos": catalogo}, f, ensure_ascii=False, indent=2)

    print(f"\nCatálogo actualizado: {len(catalogo)} juego(s) en total.")
    print(f"Guardado en: {SALIDA_CATALOGO}")
    print("Abre index.html para ver el catálogo, o entra directo a games/<carpeta>/index.html")


if __name__ == "__main__":
    main()
