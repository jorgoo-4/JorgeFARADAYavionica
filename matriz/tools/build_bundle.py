#!/usr/bin/env python3
"""Empaqueta data/*.csv en app/data_bundle.js.

Uso:  python3 tools/build_bundle.py

Sirve para que index.html funcione abierto con doble clic (file://), donde el
navegador no deja leer los CSV con fetch. Los CSV siguen siendo la fuente: este
archivo se regenera a partir de ellos y validate.py comprueba que está al día.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DATA, RAIZ  # noqa: E402

DESTINO = os.path.join(RAIZ, 'app', 'data_bundle.js')


def contenido():
    datos = {}
    for nombre in sorted(os.listdir(DATA)):
        if nombre.endswith('.csv'):
            with open(os.path.join(DATA, nombre), encoding='utf-8') as f:
                datos[nombre[:-4]] = f.read()
    return ('/* Generado por tools/build_bundle.py a partir de data/*.csv. No editar a mano. */\n'
            'window.DATA_BUNDLE = ' + json.dumps(datos, ensure_ascii=False, indent=0) + ';\n')


def main():
    with open(DESTINO, 'w', encoding='utf-8', newline='\n') as f:
        f.write(contenido())
    print('app/data_bundle.js regenerado')


if __name__ == '__main__':
    main()
