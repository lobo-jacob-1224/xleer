#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
xleer.py  -  la hermana de xkill, con punteria.

Congela la pantalla y saca una CRUZ:
  * CLIC sobre un texto      -> lee ese PARRAFO y todo lo que sigue debajo, en su columna;
                                después baja la página con la rueda y lee lo nuevo.
  * ARRASTRAR un recuadro    -> lee exactamente lo que hay dentro del recuadro.
  * Esc / clic derecho       -> cancelar.
El texto se lo pasa a hablar.py (voz de Alvaro).

Uso:  xleer.py                       (interactivo, con cruz)
      xleer.py --solo-texto          (no habla, solo imprime)
      xleer.py --punto X Y           (pruebas: simula un clic en X,Y de la pantalla)
      xleer.py --caja X1 Y1 X2 Y2    (pruebas: simula un recuadro)
"""
import os
import sys
import time
import functools
import subprocess
import tempfile
import argparse

from PIL import Image, ImageOps, ImageChops

# Multiplataforma: Linux/X11 (soportado) y Windows (experimental, sin validar; ver docs/windows.md).
WIN = sys.platform == "win32"
if getattr(sys, "frozen", False):                      # .exe hecho con PyInstaller
    DIR = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:                                                  # .py suelto o instalado en /usr/lib/xleer
    DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(DIR, "venv", "bin", "python")   # solo si existe (instalacion original)
HABLAR = os.path.join(DIR, "hablar.py")


def _carpeta_estado():
    """Carpeta donde se guarda xleer.log: la de estado del usuario (nunca junto al codigo)."""
    if WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    ruta = os.path.join(base, "xleer")
    try:
        os.makedirs(ruta, exist_ok=True)
    except OSError:
        return tempfile.gettempdir()
    return ruta


LOG = os.path.join(_carpeta_estado(), "xleer.log")
ARRASTRE_MIN = 6          # px: menos que esto es un clic, no un recuadro
ESCALA = 3                # ampliar la captura mejora el OCR de letra de pantalla
HUECO_MAX = 0.95          # hueco entre lineas (en alturas de letra) para seguir en el mismo parrafo
DIST_MAX = 45            # px: si pinchas mas lejos que esto de cualquier palabra, no lee


def _pixeles(img):
    """Lista de pixeles de la imagen. Pillow >= 12.1 renombra getdata() (el nombre antiguo avisa
    de que desaparecera en Pillow 14); aqui se usa el nuevo si existe y, si no, el antiguo."""
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


def log(*a):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")
    except OSError:
        pass


# ================================================================ captura
def _run(cmd, **kw):
    """subprocess.run; en Windows sin abrir una ventana de consola por cada programa."""
    if WIN:
        kw.setdefault("creationflags", 0x08000000)       # CREATE_NO_WINDOW
    if kw.get("text"):
        kw.setdefault("encoding", "utf-8")               # tesseract y xdotool dan UTF-8
        kw.setdefault("errors", "replace")
    return subprocess.run(cmd, **kw)


def capturar_pantalla() -> Image.Image:
    if WIN:
        from PIL import ImageGrab
        return ImageGrab.grab(include_layered_windows=True).convert("RGB")
    fd, ruta = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        _run(["maim", "-u", ruta], check=True)
        return Image.open(ruta).convert("RGB")
    finally:
        try:
            os.unlink(ruta)
        except OSError:
            pass


def _shell_vars(texto):
    d = {}
    for linea in texto.splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def _user32():
    """user32 con los tipos bien declarados (en 64 bits los HWND son de 64 bits)."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.WinDLL("user32", use_last_error=True)
    u.WindowFromPoint.argtypes = [wintypes.POINT]
    u.WindowFromPoint.restype = wintypes.HWND
    u.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    u.GetAncestor.restype = wintypes.HWND
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    u.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    u.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    u.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                              wintypes.DWORD, ctypes.c_size_t]
    return u


def raton_posicion():
    """(x, y) del puntero en pixeles de pantalla, o None si no se puede saber."""
    if WIN:
        try:
            import ctypes
            from ctypes import wintypes
            p = wintypes.POINT()
            if _user32().GetCursorPos(ctypes.byref(p)):
                return (p.x, p.y)
        except (OSError, AttributeError):
            pass
        return None
    raton = _shell_vars(_run(["xdotool", "getmouselocation", "--shell"],
                             capture_output=True, text=True).stdout)
    try:
        return (int(raton["X"]), int(raton["Y"]))
    except (KeyError, ValueError):
        return None


def mover_raton(x, y):
    if WIN:
        _user32().SetCursorPos(int(x), int(y))
    else:
        _run(["xdotool", "mousemove", str(x), str(y)])


def rueda_abajo(pasos):
    """Gira la rueda del raton hacia abajo 'pasos' golpes (baja la pagina)."""
    if WIN:
        u = _user32()
        for _ in range(pasos):
            u.mouse_event(0x0800, 0, 0, (-120) & 0xFFFFFFFF, 0)     # MOUSEEVENTF_WHEEL, -1 golpe
            time.sleep(0.03)
    else:
        _run(["xdotool", "click", "--repeat", str(pasos), "5"])       # 5 = rueda abajo


def _ventana_bajo_raton_windows():
    """Igual que la version X11, con la API de Windows: ventana de nivel superior bajo el puntero."""
    try:
        import ctypes
        from ctypes import wintypes
        u = _user32()
        p = wintypes.POINT()
        if not u.GetCursorPos(ctypes.byref(p)):
            return None
        hwnd = u.WindowFromPoint(p)
        if not hwnd:
            return None
        raiz = u.GetAncestor(hwnd, 2) or hwnd            # GA_ROOT: la ventana entera, no un boton
        r = wintypes.RECT()
        try:                                              # borde real (sin la sombra invisible de Win10/11)
            ok = ctypes.WinDLL("dwmapi").DwmGetWindowAttribute(
                wintypes.HWND(raiz), 9, ctypes.byref(r), ctypes.sizeof(r)) == 0   # DWMWA_EXTENDED_FRAME_BOUNDS
        except (OSError, AttributeError):
            ok = False
        if not ok and not u.GetWindowRect(raiz, ctypes.byref(r)):
            return None
        w, h = r.right - r.left, r.bottom - r.top
        if w < 40 or h < 20:
            return None
        return (r.left, r.top, r.right, r.bottom)
    except (OSError, AttributeError, ValueError):
        return None


def ventana_bajo_raton():
    """Rectangulo (x1,y1,x2,y2) de la ventana VISIBLE bajo el puntero (la de encima)."""
    if WIN:
        return _ventana_bajo_raton_windows()
    try:
        loc = _shell_vars(_run(["xdotool", "getmouselocation", "--shell"],
                               capture_output=True, text=True).stdout)
        wid = loc.get("WINDOW")
        if not wid:
            return None
        wid = hex(int(wid))
        # xdotool da la ventana MAS INTERNA (un boton, una etiqueta...). Subimos por los
        # padres hasta la hija directa del root = la ventana entera con su marco.
        import re
        for _ in range(15):
            t = _run(["xwininfo", "-tree", "-id", wid], capture_output=True, text=True).stdout
            raiz = re.search(r"Root window id: (0x[0-9a-f]+)", t)
            padre = re.search(r"Parent window id: (0x[0-9a-f]+)", t)
            if not raiz or not padre or padre.group(1) == raiz.group(1):
                break
            wid = padre.group(1)
        info = _run(["xwininfo", "-id", wid], capture_output=True, text=True).stdout
        x = int(re.search(r"Absolute upper-left X:\s+(-?\d+)", info).group(1))
        y = int(re.search(r"Absolute upper-left Y:\s+(-?\d+)", info).group(1))
        w = int(re.search(r"Width:\s+(\d+)", info).group(1))
        h = int(re.search(r"Height:\s+(\d+)", info).group(1))
        if w < 40 or h < 20:
            return None
        return (x, y, x + w, y + h)
    except (OSError, KeyError, ValueError, AttributeError):
        return None


# ================================================================ OCR
def preparar(img: Image.Image) -> Image.Image:
    g = ImageOps.grayscale(img)
    hist = g.histogram()
    total = sum(hist) or 1
    media = sum(i * n for i, n in enumerate(hist)) / total
    if media < 110:
        # Fondo oscuro (terminal, a veces TRANSPARENTE y con cosas detras).
        # Usamos el canal mas brillante (asi el texto azul/verde/rojo de colores no se pierde)
        # y binarizamos: lo que brilla de verdad es texto; lo que se transparenta, fuera.
        r, gg, b = img.convert("RGB").split()
        v = ImageChops.lighter(ImageChops.lighter(r, gg), b)
        hv = v.histogram()
        tot = sum(hv) or 1
        acum, med, p97 = 0, 0, 255
        for i, n in enumerate(hv):
            acum += n
            if acum <= tot * 0.5:
                med = i
            if acum <= tot * 0.97:
                p97 = i
        umbral = med + 0.6 * (max(p97, med + 60) - med)
        g = v.point(lambda x: 0 if x > umbral else 255)
    else:
        g = ImageOps.autocontrast(g, cutoff=1)
    return g.resize((g.width * ESCALA, g.height * ESCALA), Image.LANCZOS)


def _tesseract():
    """Ruta de tesseract: el que va dentro del .exe (carpeta 'tesseract'); si no, el del sistema."""
    propio = os.path.join(DIR, "tesseract", "tesseract.exe" if WIN else "tesseract")
    if os.path.isfile(propio):
        os.environ.setdefault("TESSDATA_PREFIX", os.path.join(DIR, "tesseract", "tessdata"))
        return propio
    return "tesseract"


@functools.lru_cache(maxsize=None)
def _langs():
    out = _run([_tesseract(), "--list-langs"], capture_output=True, text=True).stdout.split()
    if "spa" in out:
        return "spa+eng" if "eng" in out else "spa"
    return None


def ocr_palabras(img: Image.Image, psm: int = 3):
    """Lista de palabras {text, conf, x1,y1,x2,y2, linea} en coordenadas de 'img'."""
    fd, ruta = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        preparar(img).save(ruta)
        cmd = [_tesseract(), ruta, "stdout", "--psm", str(psm)]
        lg = _langs()
        if lg:
            cmd += ["-l", lg]
        out = _run(cmd + ["tsv"], capture_output=True, text=True).stdout
    finally:
        try:
            os.unlink(ruta)
        except OSError:
            pass
    palabras = []
    for linea in out.splitlines()[1:]:
        c = linea.split("\t")
        if len(c) < 12 or c[0] != "5":
            continue
        txt = c[11].strip()
        if not txt:
            continue
        try:
            conf = float(c[10])
        except ValueError:
            conf = -1
        if conf < 0:
            continue
        l, t, w, h = (int(v) / ESCALA for v in c[6:10])
        palabras.append({"text": txt, "conf": conf,
                         "x1": l, "y1": t, "x2": l + max(w, 1), "y2": t + max(h, 1),
                         "linea": (int(c[2]), int(c[3]), int(c[4]))})
    return palabras


# ================================================================ agrupar en parrafos
def segmentos(palabras):
    """Filas visuales (por posicion real, no por bloques de tesseract) partidas por
    huecos horizontales grandes (columnas)."""
    filas = []                      # cada fila: [centro_y, alto, [palabras]]
    for p in sorted(palabras, key=lambda p: (p["y1"] + p["y2"]) / 2):
        cy = (p["y1"] + p["y2"]) / 2
        h = p["y2"] - p["y1"]
        for f in filas:
            if abs(f[0] - cy) <= max(min(f[1], h), 4) * 0.5:
                f[2].append(p)
                n = len(f[2])
                f[0] = (f[0] * (n - 1) + cy) / n
                break
        else:
            filas.append([cy, h, [p]])
    segs = []
    for _cy, _h, ws in filas:
        ws.sort(key=lambda p: p["x1"])
        alto = max(p["y2"] - p["y1"] for p in ws)
        actual = [ws[0]]
        for p in ws[1:]:
            if p["x1"] - actual[-1]["x2"] > max(alto, 8) * 1.8:
                segs.append(actual)
                actual = [p]
            else:
                actual.append(p)
        segs.append(actual)
    res = []
    for s in segs:
        alturas = sorted(p["y2"] - p["y1"] for p in s)
        res.append({"ws": s,
                    "x1": min(p["x1"] for p in s), "x2": max(p["x2"] for p in s),
                    "y1": min(p["y1"] for p in s), "y2": max(p["y2"] for p in s),
                    "alto": alturas[len(alturas) // 2]})
    return res


def distancia(b, x, y):
    dx = max(b["x1"] - x, 0, x - b["x2"])
    dy = max(b["y1"] - y, 0, y - b["y2"])
    return (dx * dx + dy * dy) ** 0.5


def _fondo(gris, x1, y1, x2, y2):
    """Gris tipico (mediana) del rectangulo: en una zona de texto es el color de fondo."""
    x1, y1 = max(int(x1), 0), max(int(y1), 0)
    x2, y2 = min(int(x2), gris.width), min(int(y2), gris.height)
    if x2 <= x1 or y2 <= y1:
        return None
    h = gris.crop((x1, y1, x2, y2)).histogram()
    mitad, acum = sum(h) / 2, 0
    for i, n in enumerate(h):
        acum += n
        if acum >= mitad:
            return i
    return None


def hay_separador(gris, fondo, x1, x2, ya, yb):
    """True si entre las filas ya..yb hay una raya o un cambio de fondo (barra de menus,
    pestana, borde de panel...).  Mira cada fila de pixeles del hueco."""
    if gris is None or fondo is None:
        return False
    x1, x2 = max(int(x1), 0), min(int(x2), gris.width)
    ya, yb = max(int(ya), 0), min(int(yb), gris.height)
    if x2 - x1 < 4 or yb <= ya:
        return False
    franja = gris.crop((x1, ya, x2, yb))
    w = franja.width
    datos = _pixeles(franja)
    for f in range(franja.height):
        fila = datos[f * w:(f + 1) * w]
        if abs(sum(fila) / w - fondo) > 40:
            return True
    return False


def parrafo_en(palabras, x, y, img=None):
    """Segmentos del parrafo que contiene (o tiene mas cerca) el punto x,y."""
    segs = segmentos(palabras)
    if not segs:
        return [], None
    # palabra pinchada (o la mas cercana) -> su segmento
    pal = min(palabras, key=lambda p: distancia(p, x, y))
    d = distancia(pal, x, y)
    if d > DIST_MAX:
        return [], (pal, d)
    semilla = next(s for s in segs if pal in s["ws"])
    alto = max(semilla["alto"], 6)
    gris = ImageOps.grayscale(img) if img is not None else None
    fondo = _fondo(gris, semilla["x1"], semilla["y1"], semilla["x2"], semilla["y2"]) if gris else None
    elegidos = [semilla]
    cx1, cx2 = semilla["x1"], semilla["x2"]
    cy1, cy2 = semilla["y1"], semilla["y2"]
    usados = {id(semilla)}
    # crecer hacia arriba y hacia abajo: lineas pegadas, de altura parecida y en la misma columna
    cambio = True
    while cambio:
        cambio = False
        for s in segs:
            if id(s) in usados:
                continue
            solape = min(s["x2"], cx2) - max(s["x1"], cx1)
            if solape <= 0:
                continue
            if not (0.6 * alto <= s["alto"] <= 1.6 * alto):
                continue
            hueco = max(s["y1"] - cy2, cy1 - s["y2"])   # <0 si se solapan en vertical
            if hueco <= alto * HUECO_MAX:
                if hueco > 0:
                    ya, yb = (cy2, s["y1"]) if s["y1"] >= cy2 else (s["y2"], cy1)
                    if hay_separador(gris, fondo, max(s["x1"], cx1), min(s["x2"], cx2), ya, yb):
                        continue
                elegidos.append(s)
                usados.add(id(s))
                cy1, cy2 = min(cy1, s["y1"]), max(cy2, s["y2"])
                cambio = True
    elegidos.sort(key=lambda s: ((s["y1"] + s["y2"]) / 2, s["x1"]))
    return elegidos, (pal, d)


def hasta_el_final(palabras, parrafo):
    """El parrafo pinchado + todo lo que hay DEBAJO de el en su misma columna,
    hasta el final de la pagina (lo de arriba y lo de otras columnas no)."""
    if not parrafo:
        return parrafo
    suyas = {id(p) for s in parrafo for p in s["ws"]}
    px1 = min(s["x1"] for s in parrafo)
    px2 = max(s["x2"] for s in parrafo)
    py2 = max(s["y2"] for s in parrafo)
    debajo = []
    for s in segmentos(palabras):
        if any(id(p) in suyas for p in s["ws"]):
            continue
        if (s["y1"] + s["y2"]) / 2 <= py2:
            continue                       # esta arriba o a la altura del parrafo
        if min(s["x2"], px2) - max(s["x1"], px1) <= 0:
            continue                       # otra columna
        debajo.append(s)
    debajo.sort(key=lambda s: ((s["y1"] + s["y2"]) / 2, s["x1"]))
    return list(parrafo) + debajo


def unir(segs):
    texto = " ".join(" ".join(p["text"] for p in s["ws"]) for s in segs)
    texto = " ".join(texto.split())
    # palabra partida con guion al final de linea:  "conti- nuacion" -> "continuacion"
    import re
    texto = re.sub(r"(\w)- (\w)", r"\1\2", texto)
    return texto


def texto_en_punto(img: Image.Image, x: int, y: int, ventana=None) -> str:
    if ventana:
        x1, y1, x2, y2 = ventana
        x1, y1 = max(x1, 0), max(y1, 0)
        x2, y2 = min(x2, img.width), min(y2, img.height)
    else:
        x1, y1, x2, y2 = 0, 0, img.width, img.height
    recorte = img.crop((x1, y1, x2, y2))
    palabras = ocr_palabras(recorte)
    if not palabras:
        return ""
    segs, info = parrafo_en(palabras, x - x1, y - y1, recorte)
    if info:
        log(f"clic=({x},{y}) ventana={ventana} palabra='{info[0]['text']}' dist={info[1]:.0f}")
    # Texto de COLOR (terminal con colores, enlaces...): segunda pasada quedandonos solo con
    # los pixeles de ese color. Asi no se cuela lo que se transparenta por detras.
    if segs and info:
        tinta = color_tinta(recorte, info[0])
        if tinta:
            log("texto de color", tinta, "-> pasada filtrando por color")
            mascara = filtrar_color(recorte, tinta)
            pal2 = ocr_palabras(mascara)
            if pal2:
                segs2, info2 = parrafo_en(pal2, x - x1, y - y1, None)
                if segs2:
                    return unir(recordar(hasta_el_final(pal2, segs2), (x1, y1, x2, y2)))
    return unir(recordar(hasta_el_final(palabras, segs), (x1, y1, x2, y2)))


# ================================================================ seguir leyendo (bajando la pagina)
SEGUIR = {}            # donde se quedo la lectura: ventana, columna y ultimas lineas leidas
PASOS_RUEDA = 5        # golpes de rueda por vuelta (cada uno baja unas 3 lineas)
VUELTAS_MAX = 200      # tope de seguridad


def recordar(leidos, ventana):
    if leidos:
        SEGUIR["ventana"] = ventana
        SEGUIR["col"] = (min(s["x1"] for s in leidos), max(s["x2"] for s in leidos))
        SEGUIR["ultimas"] = [unir([s]) for s in leidos[-3:]]
    return leidos


def lineas_columna(foto, col):
    """Lineas de texto de la foto de la ventana, solo las de la columna col=(x1,x2)."""
    segs = [s for s in segmentos(ocr_palabras(foto))
            if min(s["x2"], col[1]) - max(s["x1"], col[0]) > 0]
    segs.sort(key=lambda s: ((s["y1"] + s["y2"]) / 2, s["x1"]))
    return [unir([s]) for s in segs]


def lo_que_sigue(lineas, ultimas):
    """Busca en 'lineas' la ultima linea ya leida y devuelve lo que viene detras.
    None = no se encuentra el enganche (mejor parar que leer repetido)."""
    import difflib
    for vieja in reversed(ultimas):            # la mas reciente primero
        for i in range(len(lineas) - 1, -1, -1):
            if difflib.SequenceMatcher(None, lineas[i], vieja).ratio() > 0.8:
                return lineas[i + 1:]
    return None


def color_tinta(img, palabra):
    """Color (R,G,B) de las letras de esa palabra si es un color vivo; None si es gris/blanco/negro."""
    caja = img.crop((int(palabra["x1"]), int(palabra["y1"]),
                     int(palabra["x2"]) + 1, int(palabra["y2"]) + 1)).convert("RGB")
    px = _pixeles(caja)
    if not px:
        return None
    lum = sorted(sum(p) for p in px)
    fondo = lum[len(lum) // 2]
    if fondo > 3 * 110:
        return None      # solo en fondos oscuros (terminales); en paginas claras un enlace azul
                         # dentro de un parrafo negro no debe cortar el parrafo
    # tinta = pixeles que se separan mucho del fondo
    tinta = [p for p in px if abs(sum(p) - fondo) > 120]
    if len(tinta) < 8:
        return None
    m = len(tinta) // 2
    r = sorted(p[0] for p in tinta)[m]
    g = sorted(p[1] for p in tinta)[m]
    b = sorted(p[2] for p in tinta)[m]
    if max(r, g, b) - min(r, g, b) < 70:
        return None          # la tinta tipica es gris/blanca: no es texto de color
    return (r, g, b)


def filtrar_color(img, tinta, tolerancia=60):
    """Imagen blanca con en negro SOLO los pixeles del mismo color VIVO que 'tinta'
    (lo que se transparenta por detras suele ser grisaceo: poca saturacion -> fuera)."""
    r0, g0, b0 = tinta
    sat0 = max(tinta) - min(tinta)
    sat_min = sat0 * 0.6
    t2 = tolerancia * tolerancia
    rgb = img.convert("RGB")
    out = Image.new("L", rgb.size, 255)
    out.putdata([0 if ((r - r0) ** 2 + (g - g0) ** 2 + (b - b0) ** 2 < t2
                       and max(r, g, b) - min(r, g, b) >= sat_min) else 255
                 for r, g, b in _pixeles(rgb)])
    return out.convert("RGB")


def texto_en_caja(img: Image.Image, caja) -> str:
    x1, y1, x2, y2 = caja
    recorte = img.crop((x1, y1, x2, y2))
    palabras = ocr_palabras(recorte, psm=6 if (y2 - y1) < 60 else 3)
    segs = segmentos(palabras)
    segs.sort(key=lambda s: ((s["y1"] + s["y2"]) / 2, s["x1"]))
    return unir(segs)


# ================================================================ seleccion con cruz (Tk)
def seleccionar(img: Image.Image):
    """Pantalla congelada + cruz.  -> ('punto',x,y) | ('caja',x1,y1,x2,y2) | None"""
    import tkinter as tk
    from PIL import ImageTk

    raiz = tk.Tk()
    raiz.title("xleer")
    raiz.overrideredirect(True)
    raiz.geometry(f"{img.width}x{img.height}+0+0")
    raiz.attributes("-topmost", True)
    lienzo = tk.Canvas(raiz, width=img.width, height=img.height, highlightthickness=0,
                       cursor="crosshair", bd=0)
    lienzo.pack()
    foto = ImageTk.PhotoImage(img)
    lienzo.create_image(0, 0, anchor="nw", image=foto)
    aviso = "xleer:  CLIC en el texto que quieres oir   ·   o ARRASTRA un recuadro   ·   Esc = cancelar"
    lienzo.create_rectangle(img.width // 2 - 400, 60, img.width // 2 + 400, 92, fill="#000000", outline="#ffeb3b")
    lienzo.create_text(img.width // 2, 76, fill="#ffeb3b",
                       font=("Segoe UI" if WIN else "DejaVu Sans", 12, "bold"), text=aviso)
    estado = {"ini": None, "rect": None, "res": None}

    def pulsar(e):
        estado["ini"] = (e.x_root, e.y_root)

    def mover(e):
        if not estado["ini"]:
            return
        x0, y0 = estado["ini"]
        if estado["rect"]:
            lienzo.coords(estado["rect"], x0, y0, e.x_root, e.y_root)
        elif abs(e.x_root - x0) + abs(e.y_root - y0) > ARRASTRE_MIN:
            estado["rect"] = lienzo.create_rectangle(x0, y0, e.x_root, e.y_root,
                                                     outline="#ff1744", width=2)

    def soltar(e):
        if not estado["ini"]:
            return
        x0, y0 = estado["ini"]
        x1, y1 = e.x_root, e.y_root
        if abs(x1 - x0) > ARRASTRE_MIN and abs(y1 - y0) > ARRASTRE_MIN:
            estado["res"] = ("caja", min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        else:
            estado["res"] = ("punto", x0, y0)
        raiz.destroy()

    def cancelar(_e=None):
        estado["res"] = None
        raiz.destroy()

    lienzo.bind("<ButtonPress-1>", pulsar)
    lienzo.bind("<B1-Motion>", mover)
    lienzo.bind("<ButtonRelease-1>", soltar)
    lienzo.bind("<Button-3>", cancelar)
    raiz.bind("<Escape>", cancelar)

    def agarrar(intentos=[0]):
        try:
            raiz.focus_force()
            raiz.grab_set_global()
        except tk.TclError:
            intentos[0] += 1
            if intentos[0] < 30:
                raiz.after(100, agarrar)
    raiz.after(60, agarrar)
    raiz.mainloop()
    return estado["res"]


# ================================================================ principal
def decir(texto: str):
    if WIN:                                   # en el .exe todo va en el mismo programa
        sys.path.insert(0, DIR)
        import hablar
        hablar.hablar(texto)
        return
    py = VENV_PY if os.path.exists(VENV_PY) else sys.executable
    env = dict(os.environ)
    vendor = os.path.join(DIR, "vendor")      # edge_tts empaquetado (instalacion .deb)
    if os.path.isdir(vendor):
        env["PYTHONPATH"] = vendor + os.pathsep + env.get("PYTHONPATH", "")
    _run([py, HABLAR], input=texto, text=True, env=env)


def callar_lecturas_anteriores():
    """Si ya habia un xleer hablando, se calla (en Linux lo hace el lanzador con pkill)."""
    if not WIN:
        return
    yo = {os.getpid(), os.getppid()}          # el .exe de PyInstaller tiene un proceso padre
    nombre = os.path.basename(sys.executable) if getattr(sys, "frozen", False) else None
    if not nombre:
        return
    out = _run(["tasklist", "/FI", f"IMAGENAME eq {nombre}", "/FO", "CSV", "/NH"],
               capture_output=True, text=True).stdout
    for linea in out.splitlines():
        c = [x.strip('"') for x in linea.split('","')]
        if len(c) > 1 and c[0].strip('"').lower() == nombre.lower() and c[1].isdigit() and int(c[1]) not in yo:
            _run(["taskkill", "/F", "/T", "/PID", c[1]], capture_output=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo-texto", action="store_true")
    ap.add_argument("--punto", type=int, nargs=2)
    ap.add_argument("--caja", type=int, nargs=4)
    ap.add_argument("--imagen", help="pruebas: usa esta imagen en vez de capturar la pantalla")
    a = ap.parse_args()

    for _flujo in ("stdout", "stderr"):       # .exe sin consola: no hay salida estandar (es None) y print/flush fallan
        if getattr(sys, _flujo) is None:
            setattr(sys, _flujo, open(os.devnull, "w", encoding="utf-8"))

    if WIN:
        try:                                  # pixeles reales: que la captura y la cruz coincidan
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except (OSError, AttributeError):
            pass
        if not a.imagen:
            callar_lecturas_anteriores()

    img = Image.open(a.imagen).convert("RGB") if a.imagen else capturar_pantalla()
    if a.caja:
        sel = ("caja", *a.caja)
    elif a.punto:
        sel = ("punto", *a.punto)
        if not a.imagen:
            mover_raton(*a.punto)
        time.sleep(0.2)
    else:
        sel = seleccionar(img)
        time.sleep(0.25)        # que desaparezca la pantalla congelada antes de mirar la ventana

    if sel is None:
        print("Seleccion cancelada.")
        return 1

    if sel[0] == "caja":
        texto = texto_en_caja(img, sel[1:])
    else:
        texto = texto_en_punto(img, sel[1], sel[2], None if a.imagen else ventana_bajo_raton())
    log("seleccion:", sel, "->", texto[:300])

    print(">> Texto:", texto if texto else "(nada)")
    sys.stdout.flush()
    if not a.solo_texto:
        decir(texto if texto else "No hay texto donde has pinchado.")
    if not texto or sel[0] != "punto" or not SEGUIR or a.imagen:
        return 0 if texto else 3

    # ---- seguir leyendo: bajar la pagina con la rueda y leer solo lo nuevo
    ventana = SEGUIR["ventana"]
    ultimas = SEGUIR["ultimas"]
    foto_antes = img.crop(ventana)
    for i in range(VUELTAS_MAX):
        pos = raton_posicion()
        movido = bool(pos) and abs(pos[0] - sel[1]) + abs(pos[1] - sel[2]) > 30
        if movido:
            log("sigue: has movido el raton, paro")
            break
        rueda_abajo(PASOS_RUEDA)
        time.sleep(0.7)
        foto = capturar_pantalla().crop(ventana)
        if ImageChops.difference(foto, foto_antes).getbbox() is None:
            log("sigue: la pagina ya no baja, fin")
            break
        foto_antes = foto
        nuevas = lo_que_sigue(lineas_columna(foto, SEGUIR["col"]), ultimas)
        if nuevas is None:
            log("sigue: no encuentro donde me quede, paro")
            break
        if not nuevas:
            continue
        ultimas = (ultimas + nuevas)[-3:]
        trozo = " ".join(nuevas)
        log(f"sigue vuelta {i + 1}:", trozo[:300])
        print(">> Sigue:", trozo)
        sys.stdout.flush()
        if not a.solo_texto:
            decir(trozo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
