"""Pruebas de xleer sin pantalla ni audio.

* Las de la clase PruebasLogica no necesitan nada externo: palabras inventadas con su posicion.
* Las de la clase PruebasOCR usan tesseract (idioma spa) y la fuente DejaVu sobre una imagen sintetica;
  si faltan, se omiten (no fallan).

Ejecutar:  python3 -m unittest discover -s tests -v      (o:  make test)
"""
import os
import shutil
import subprocess
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "src"))
sys.path.insert(0, AQUI)

import xleer                                   # noqa: E402
from imagen_sintetica import FUENTE, crear     # noqa: E402

xleer.log = lambda *a: None                     # las pruebas no escriben en el registro del usuario


def palabra(texto, x1, y1, x2, y2):
    return {"text": texto, "conf": 95.0, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "linea": (1, 1, 1)}


class PruebasLogica(unittest.TestCase):
    def test_unir_palabras_partidas_con_guion(self):
        segs = [{"ws": [{"text": "conti-"}]}, {"ws": [{"text": "nuacion"}]}]
        self.assertEqual(xleer.unir(segs), "continuacion")

    def test_segmentos_separa_columnas_por_huecos_grandes(self):
        pal = [palabra("uno", 0, 0, 50, 20), palabra("dos", 60, 0, 110, 20), palabra("tres", 400, 0, 450, 20)]
        segs = xleer.segmentos(pal)
        self.assertEqual([len(s["ws"]) for s in sorted(segs, key=lambda s: s["x1"])], [2, 1])

    def test_parrafo_agrupa_lineas_pegadas_y_deja_fuera_las_lejanas(self):
        pal = [palabra("a", 0, 0, 100, 20), palabra("b", 0, 25, 100, 45),
               palabra("c", 0, 50, 100, 70), palabra("lejos", 0, 200, 100, 220)]
        elegidos, info = xleer.parrafo_en(pal, 10, 10)
        self.assertEqual(sorted(p["text"] for s in elegidos for p in s["ws"]), ["a", "b", "c"])
        self.assertEqual(info[0]["text"], "a")

    def test_clic_lejos_de_todo_texto_no_elige_nada(self):
        pal = [palabra("a", 0, 0, 100, 20)]
        elegidos, _ = xleer.parrafo_en(pal, 500, 500)
        self.assertEqual(elegidos, [])

    def test_hasta_el_final_incluye_lo_de_debajo_en_su_columna_y_no_otras_columnas(self):
        pal = [palabra("arriba", 0, 0, 100, 20), palabra("debajo", 0, 200, 100, 220),
               palabra("otra_columna", 500, 200, 600, 220)]
        parrafo, _ = xleer.parrafo_en(pal, 10, 10)
        textos = sorted(p["text"] for s in xleer.hasta_el_final(pal, parrafo) for p in s["ws"])
        self.assertEqual(textos, ["arriba", "debajo"])

    def test_pixeles_funciona_con_el_pillow_instalado(self):
        from PIL import Image
        img = Image.new("RGB", (2, 1), (10, 20, 30))
        self.assertEqual(xleer._pixeles(img), [(10, 20, 30), (10, 20, 30)])


def hay_tesseract_spa():
    exe = shutil.which("tesseract")
    if not exe:
        return False
    return "spa" in subprocess.run([exe, "--list-langs"], capture_output=True, text=True).stdout.split()


@unittest.skipUnless(hay_tesseract_spa(), "falta tesseract con el idioma spa")
@unittest.skipUnless(os.path.exists(FUENTE), "falta la fuente DejaVu (paquete fonts-dejavu-core)")
class PruebasOCR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img = crear()

    def test_clic_lee_el_parrafo_y_todo_lo_que_sigue_debajo(self):
        t = xleer.texto_en_punto(self.img, 150, 75)
        self.assertTrue(t.startswith("El zorro marron salta"), t)
        self.assertIn("Segundo parrafo de la misma columna", t)
        self.assertNotIn("Columna derecha", t)

    def test_clic_en_la_columna_derecha_no_mezcla_la_izquierda(self):
        t = xleer.texto_en_punto(self.img, 700, 50)
        self.assertTrue(t.startswith("Columna derecha texto distinto"), t)
        self.assertNotIn("zorro", t)

    def test_clic_lejos_de_cualquier_texto_no_lee_nada(self):
        self.assertEqual(xleer.texto_en_punto(self.img, 500, 300), "")

    def test_clic_en_fondo_oscuro_con_letra_de_color(self):
        t = xleer.texto_en_punto(self.img, 150, 350)
        self.assertIn("ficheros de prueba", t)

    def test_recuadro_lee_solo_lo_de_dentro(self):
        t = xleer.texto_en_caja(self.img, (30, 180, 520, 250))
        self.assertIn("Segundo parrafo de la misma columna", t)
        self.assertNotIn("zorro", t)


if __name__ == "__main__":
    unittest.main()
