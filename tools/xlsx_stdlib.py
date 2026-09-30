"""Lector mínimo de .xlsx con la librería estándar (zipfile + xml).

Sustituye a openpyxl (decisión D-08 de DECISIONES.md): el repositorio no
tiene ninguna dependencia. Devuelve los valores cacheados de las celdas
(lo que Excel mostró la última vez que guardó) y, aparte, las fórmulas.
"""
import re
import zipfile
import xml.etree.ElementTree as ET

_M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_NS = {'m': _M}


def col_a_num(letras):
    n = 0
    for ch in letras:
        n = n * 26 + ord(ch) - 64
    return n


def num_a_col(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def leer(path):
    """{hoja: {(fila, col): (valor_str_o_None, formula_o_None)}}"""
    z = zipfile.ZipFile(path)
    compartidas = []
    if 'xl/sharedStrings.xml' in z.namelist():
        raiz = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in raiz.findall('m:si', _NS):
            compartidas.append(''.join(t.text or '' for t in si.iter('{%s}t' % _M)))
    libro = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target')
            for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    hojas = {}
    for s in libro.find('m:sheets', _NS):
        destino = rels[s.get('{%s}id' % _R)].lstrip('/')
        if not destino.startswith('xl/'):
            destino = 'xl/' + destino
        celdas = {}
        for c in ET.fromstring(z.read(destino)).iter('{%s}c' % _M):
            m = re.match(r'([A-Z]+)(\d+)', c.get('r'))
            fila, col = int(m.group(2)), col_a_num(m.group(1))
            t = c.get('t')
            v = c.find('m:v', _NS)
            f = c.find('m:f', _NS)
            if t == 's' and v is not None:
                val = compartidas[int(v.text)]
            elif t == 'inlineStr':
                val = ''.join(x.text or '' for x in c.iter('{%s}t' % _M))
            else:
                val = v.text if v is not None else None
            if val is None and f is None:
                continue
            celdas[(fila, col)] = (val, f.text if f is not None else None)
        hojas[s.get('name')] = celdas
    return hojas


def valor(hoja, ref):
    """Valor de una celda por referencia 'B12'; '' si está vacía."""
    m = re.match(r'([A-Z]+)(\d+)', ref)
    v = hoja.get((int(m.group(2)), col_a_num(m.group(1))))
    return '' if v is None or v[0] is None else str(v[0]).strip()


def formula(hoja, ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    v = hoja.get((int(m.group(2)), col_a_num(m.group(1))))
    return None if v is None else v[1]
