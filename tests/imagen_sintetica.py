"""Imagen de prueba (sin pantalla real): dos columnas de texto negro sobre blanco y una franja
oscura con letra verde, como un terminal. Sirve a los tests y a packaging/probar-deb.sh."""
import sys

from PIL import Image, ImageDraw, ImageFont

FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"     # paquete fonts-dejavu-core

COLUMNA_IZQ = [("El zorro marron salta sobre el perro", 40), ("perezoso que duerme junto al rio", 66),
               ("cada tarde despues de comer", 92), ("Segundo parrafo de la misma columna", 190),
               ("con dos lineas de texto nuevas", 216)]
COLUMNA_DER = [("Columna derecha texto distinto", 40), ("que nunca debe mezclarse con la izquierda", 66)]


def crear(ruta=None):
    letra = ImageFont.truetype(FUENTE, 20)
    img = Image.new("RGB", (1000, 520), "white")
    d = ImageDraw.Draw(img)
    for texto, y in COLUMNA_IZQ:
        d.text((40, y), texto, fill="black", font=letra)
    for texto, y in COLUMNA_DER:
        d.text((560, y), texto, fill="black", font=letra)
    oscuro = Image.new("RGB", (700, 160), (20, 20, 24))
    d2 = ImageDraw.Draw(oscuro)
    d2.text((20, 20), "usuario@equipo:~$ ls -la carpeta", fill=(80, 250, 123), font=letra)
    d2.text((20, 50), "total 48 ficheros de prueba", fill=(80, 250, 123), font=letra)
    img.paste(oscuro, (40, 330))
    if ruta:
        img.save(ruta)
    return img


if __name__ == "__main__":
    crear(sys.argv[1])
    print("imagen creada:", sys.argv[1])
