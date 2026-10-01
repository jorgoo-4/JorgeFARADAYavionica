"""Utilidades compartidas por los scripts de tools/ y tests/ (solo stdlib)."""
import csv
import os
import re
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RAIZ, 'data')

ETIQUETAS_VALIDAS = ('fuente', 'vuelo', 'calculo', 'medido', 'criterio_propio', 'pendiente')

_ALIAS = {
    'fuente': 'fuente',
    'vuelo': 'vuelo',
    'calculo': 'calculo',
    'medido': 'medido',
    'criterio propio': 'criterio_propio',
    'criterio_propio': 'criterio_propio',
    'pendiente': 'pendiente',
}


def sin_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def normalizar_etiqueta(texto):
    """'Vuelo + Cálculo' -> ('vuelo+calculo', []). Devuelve también las partes no reconocidas."""
    if texto is None or not str(texto).strip():
        return 'pendiente', []
    partes, raras = [], []
    for p in str(texto).split('+'):
        clave = sin_acentos(p.strip().lower())
        if clave in _ALIAS:
            if _ALIAS[clave] not in partes:
                partes.append(_ALIAS[clave])
        elif clave:
            raras.append(p.strip())
    return ('+'.join(partes) if partes else 'pendiente'), raras


def partes_etiqueta(texto):
    return [p for p in (texto or '').split('+') if p]


def leer_csv(nombre):
    ruta = nombre if os.path.isabs(nombre) else os.path.join(DATA, nombre)
    with open(ruta, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def escribir_csv(nombre, columnas, filas):
    ruta = nombre if os.path.isabs(nombre) else os.path.join(DATA, nombre)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columnas, lineterminator='\n', extrasaction='raise')
        w.writeheader()
        for fila in filas:
            w.writerow({c: ('' if fila.get(c) is None else fila.get(c)) for c in columnas})
    return ruta


def primer_numero(texto):
    """Primer número de un texto ('3 — justo' -> 3, '−40/105' -> -40). None si no hay."""
    if texto is None:
        return None
    t = str(texto).replace('−', '-').replace(',', '.')
    m = re.search(r'-?\d+(?:\.\d+)?', t)
    if not m:
        return None
    v = float(m.group(0))
    return int(v) if v.is_integer() else v


def fmt_num(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


COLUMNAS_CANDIDATE_DATA = ['candidato_id', 'campo', 'valor', 'unidad', 'etiqueta', 'fuente',
                           'revision', 'fecha_consulta', 'condiciones', 'url', 'importado_de']


def fusionar_candidate_data(filas_nuevas, prefijo_propio):
    """Sustituye en candidate_data.csv las filas que este importador escribió la vez anterior
    (las que tienen importado_de que empieza por prefijo_propio) y conserva el resto."""
    ruta = os.path.join(DATA, 'candidate_data.csv')
    existentes = leer_csv(ruta) if os.path.exists(ruta) else []
    conservar = [f for f in existentes if not f.get('importado_de', '').startswith(prefijo_propio)]
    escribir_csv(ruta, COLUMNAS_CANDIDATE_DATA, conservar + filas_nuevas)
    return len(conservar), len(filas_nuevas)
