.PHONY: test deb check descargas clean

test:            ## pruebas unitarias (sin pantalla ni audio)
	python3 -m unittest discover -s tests -v

deb:             ## construye dist/xleer_*_all.deb
	bash packaging/build-deb.sh

check: deb       ## construye el .deb, lo revisa con lintian y lo prueba sin instalarlo
	lintian dist/xleer_*_all.deb
	bash packaging/probar-deb.sh

descargas: deb   ## deja el .deb y su huella en descargas/ (a la vista en el repositorio)
	mkdir -p descargas
	cp dist/xleer_*_all.deb dist/SHA256SUMS descargas/

clean:
	rm -rf build dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
