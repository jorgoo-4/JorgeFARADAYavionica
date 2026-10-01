#!/usr/bin/env python3
"""Importa el export del selector paramétrico de ST y reproduce el embudo.

Uso:
  python3 tools/import_st_selector.py [--export ProductsList.xlsx] [--fecha AAAA-MM-DD] [--url URL]
  python3 tools/import_st_selector.py --desde-csv candidates_st_selector.csv   (sin export: no hay embudo)

Es el ÚNICO sitio del repositorio que lee algo de fuera (un archivo descargado
de st.com). No usa la red: el export se descarga a mano desde el selector.

Escribe:
  data/candidate_data.csv   filas de los candidatos de data/candidates.csv que están en el catálogo
                            (sustituye solo las filas que escribió este script la vez anterior)
  data/funnel.csv           paso, piezas_restantes, ... (el embudo, regenerable)
  data/funnel_series.csv    supervivientes por serie y su representante
  data/funnel_sospechosos.csv  piezas que solo caen por campos vacíos (trampa 5)

Reglas de lectura del export (DECISIONES.md, D-05 y trampas 1-5):
  - '-' en una celda = campo vacío en el selector. No es cero: se conserva como '-'
    y el filtro lo marca como eliminación SOSPECHOSA, no como incumplimiento.
  - Celdas con varios valores ('18, 20', una por variante de encapsulado): se toma el MÍNIMO.
  - USART + UART y CAN (FD) + CAN (2.0) se suman (columnas separadas en el selector).
  - Canales ADC: máximo de los tres grupos (12/14/16 bits); se anota cuál.
  - Timers: 16-bit + 32-bit. Los que ST pone en otras columnas no cuentan (trampa 5).
  - 'Cryptography' se guarda SOLO para documentar la trampa 1: su 'ECC' es criptografía
    de curva elíptica, no memoria con corrección de errores.
"""
import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAIZ, escribir_csv, fmt_num, fusionar_candidate_data, leer_csv  # noqa: E402
from xlsx_stdlib import leer  # noqa: E402

FUENTE = 'ST STM32 MCU product selector'
URL = 'https://www.st.com/content/st_com/en/stm32-mcu-product-selector.html'
PREFIJO_EXPORT = 'ProductsList'
PREFIJO_CSV = 'candidates_st_selector.csv'

C = {  # nombre corto -> cabecera del export
    'pn': 'Part Number', 'estado': 'Marketing Status', 'pkg': 'Package', 'core': 'Core',
    'mhz': 'Operating Frequency (MHz)', 'fpu': 'FPU', 'flash': 'Flash Size (kB) (Prog)',
    'ram': 'RAM Size (kB)', 't16': 'Timers (16-bit) typ', 't32': 'Timers (32-bit) typ',
    'tother': 'Other timer functions',
    'adc12': 'A/D Converters 12-bit / Number of Channels typ',
    'adc14': 'A/D Converters 14-bit / Number of Channels typ',
    'adc16': 'A/D Converters 16-bit / Number of Channels typ',
    'canfd': 'CAN (FD)', 'can20': 'CAN (2.0)', 'i2c': 'I2C typ', 'spi': 'SPI typ', 'usart': 'USART typ',
    'uart': 'UART typ', 'adic': 'Additional Interfaces', 'extmem': 'External Memory Interfaces',
    'crypto': 'Cryptography', 'ilow': 'Supply Current (µA) (@ Lowest Power) typ',
    'irun': 'Supply Current (µA) (Run Mode (per MHz)) typ',
    'tmin': 'Operating Temperature (°C) min', 'tmax': 'Operating Temperature (°C) max',
}


# ------------------------------------------------------------------ lectura del export
def leer_export(path):
    hoja = next(iter(leer(path).values()))
    filas = {}
    for (r, c), (v, _) in hoja.items():
        filas.setdefault(r, {})[c] = (v or '').strip()
    fila_cab = next(r for r in sorted(filas) if filas[r].get(1) == 'Part Number')
    cab, sub = filas[fila_cab], filas.get(fila_cab + 1, {})
    nombres, padre = {}, ''
    for c in range(1, max(cab) + 2):
        if cab.get(c):
            padre = cab[c]
        if sub.get(c):
            nombres[c] = f'{padre} / {sub[c]}'
        elif cab.get(c):
            nombres[c] = cab[c]
    faltan = [k for k, v in C.items() if v not in nombres.values()]
    if faltan:
        raise SystemExit(f'El export no tiene las columnas {faltan}: ¿ha cambiado el formato del selector?')
    piezas = []
    for r in sorted(filas):
        if r <= fila_cab + 1 or not filas[r].get(1):
            continue
        piezas.append({nombres[c]: v for c, v in filas[r].items() if c in nombres})
    return piezas


def g(p, k):
    v = p.get(C[k], '')
    return v if v else '-'


def nums(t):
    return [float(x) for x in re.findall(r'(?<![\d.])-?\d+(?:\.\d+)?', t or '')]


def num(t):
    """(valor, multivalor). None si el selector deja el campo vacío ('-')."""
    v = nums(t)
    if not v:
        return None, False
    return min(v), len(v) > 1


def suma(*ts):
    vals = [num(t)[0] for t in ts]
    if all(v is None for v in vals):
        return None
    return sum(v for v in vals if v is not None)


def adc(p):
    grupos = [('12 bits', num(g(p, 'adc12'))[0]), ('14 bits', num(g(p, 'adc14'))[0]),
              ('16 bits', num(g(p, 'adc16'))[0])]
    validos = [x for x in grupos if x[1] is not None]
    if not validos:
        return None, ''
    mejor = max(validos, key=lambda x: x[1])
    return mejor[1], mejor[0]


def serie(pn):
    m = re.match(r'STM32([A-Z]+\d)', pn)
    return m.group(1) if m else '?'


# ------------------------------------------------------------------ embudo
def pasos_embudo(umbrales):
    u = {x['id']: x for x in umbrales}

    def mn(i):
        return float(u[i]['minimo'])

    pat_reg = re.compile('|'.join(re.escape(x) for x in u['T07']['minimo'].split(';')), re.I)
    pat_pkg = re.compile('|'.join(re.escape(x) for x in u['T14']['minimo'].split(';')), re.I)
    pat_fpu = re.compile('|'.join(re.escape(x) for x in u['T02']['minimo'].split(';')), re.I)
    # (etiqueta, id umbral, función que devuelve (pasa, vacio))
    return [
        ('Estado comercial Active', 'T16', lambda p: (g(p, 'estado') == u['T16']['minimo'], g(p, 'estado') == '-')),
        # En FPU el '-' es «sin FPU», no un hueco: no cuenta como campo vacío.
        ('FPU en hardware', 'T02', lambda p: (bool(pat_fpu.search(g(p, 'fpu'))), False)),
        ('Encapsulado LQFP', 'T14', lambda p: (bool(pat_pkg.search(g(p, 'pkg'))), g(p, 'pkg') == '-')),
        (f'Temperatura máx ≥ {fmt_num(mn("T13"))} °C', 'T13', lambda p: _cmp(num(g(p, 'tmax'))[0], mn('T13'))),
        (f'SPI ≥ {fmt_num(mn("T03"))}', 'T03', lambda p: _cmp(num(g(p, 'spi'))[0], mn('T03'))),
        (f'USART + UART ≥ {fmt_num(mn("T04"))}', 'T04', lambda p: _cmp(suma(g(p, 'usart'), g(p, 'uart')), mn('T04'))),
        (f'I2C ≥ {fmt_num(mn("T05"))}', 'T05', lambda p: _cmp(num(g(p, 'i2c'))[0], mn('T05'))),
        (f'CAN ≥ {fmt_num(mn("T06"))}', 'T06', lambda p: _cmp(suma(g(p, 'canfd'), g(p, 'can20')), mn('T06'))),
        ('Interfaz de registro (Quad/Octo/xSPI o SD-MMC)', 'T07',
         lambda p: (bool(pat_reg.search(g(p, 'extmem') + ' ' + g(p, 'adic'))),
                    g(p, 'extmem') == '-' and g(p, 'adic') == '-')),
        (f'Canales ADC ≥ {fmt_num(mn("T08"))}', 'T08', lambda p: _cmp(adc(p)[0], mn('T08'))),
        (f'Timers ≥ {fmt_num(mn("T09"))}', 'T09', lambda p: _cmp(suma(g(p, 't16'), g(p, 't32')), mn('T09'))),
        (f'Flash ≥ {fmt_num(mn("T11"))} kB', 'T11', lambda p: _cmp(num(g(p, 'flash'))[0], mn('T11'))),
        (f'RAM ≥ {fmt_num(mn("T10"))} kB', 'T10', lambda p: _cmp(num(g(p, 'ram'))[0], mn('T10'))),
    ]


def _cmp(v, minimo):
    if v is None:
        return False, True
    return v >= minimo, False


def embudo(piezas, umbrales, candidatos):
    pasos = pasos_embudo(umbrales)
    u = {x['id']: x for x in umbrales}
    filas = [{'orden': 0, 'paso': 'Catálogo STM32 completo', 'umbral_id': '', 'selector_param': '',
              'piezas_restantes': len(piezas), 'eliminadas': 0, 'eliminadas_campo_vacio': 0}]
    vivas = piezas
    for i, (nombre, uid, fn) in enumerate(pasos, 1):
        quedan, vacio = [], 0
        for p in vivas:
            ok, es_vacio = fn(p)
            if ok:
                quedan.append(p)
            elif es_vacio:
                vacio += 1
        filas.append({'orden': i, 'paso': nombre, 'umbral_id': uid, 'selector_param': u[uid]['selector_param'],
                      'piezas_restantes': len(quedan), 'eliminadas': len(vivas) - len(quedan),
                      'eliminadas_campo_vacio': vacio})
        vivas = quedan

    # Piezas que SOLO caen por campos vacíos (evaluando cada paso por separado): falsos negativos posibles.
    sospechosas = []
    for p in piezas:
        fallos = [(n, fn(p)[1]) for n, _, fn in pasos if not fn(p)[0]]
        if fallos and all(v for _, v in fallos):
            sospechosas.append({'pieza': g(p, 'pn'), 'serie': serie(g(p, 'pn')),
                                'pasos_con_campo_vacio': '; '.join(n for n, _ in fallos)})

    por_serie = {}
    for p in vivas:
        por_serie.setdefault(serie(g(p, 'pn')), []).append(g(p, 'pn'))
    reps = {}
    for c in candidatos:
        if c['rol'] == 'candidato' and c['en_catalogo_st'] == 'si':
            reps.setdefault(c['serie'], []).append(c['id'])
    series = []
    for s, lista in sorted(por_serie.items(), key=lambda x: (-len(x[1]), x[0])):
        rep = reps.get(s, [])
        series.append({'serie': s, 'piezas': len(lista), 'representante': ';'.join(rep),
                       'representante_sobrevive': 'si' if rep and all(r in lista for r in rep) else 'no'})
    return filas, series, sospechosas, {g(p, 'pn') for p in vivas}


# ------------------------------------------------------------------ datos de candidato
def filas_candidato(p, cid, fecha, url, origen):
    out = []

    def d(campo, val, unidad='', cond=''):
        out.append({'candidato_id': cid, 'campo': campo, 'valor': val, 'unidad': unidad, 'etiqueta': 'fuente',
                    'fuente': FUENTE, 'revision': '', 'fecha_consulta': fecha, 'condiciones': cond, 'url': url,
                    'importado_de': origen})

    def dnum(campo, clave, unidad=''):
        v, multi = num(g(p, clave))
        cond = f"celda multivalor '{g(p, clave)}' (una por variante de encapsulado): se toma el mínimo" if multi else ''
        d(campo, '-' if v is None else fmt_num(v), unidad, cond)

    def dsuma(campo, claves, unidad, cond):
        v = suma(*(g(p, k) for k in claves))
        crudo = ' + '.join(f"{C[k]}='{g(p, k)}'" for k in claves)
        d(campo, '-' if v is None else fmt_num(v), unidad, f'{cond}: {crudo}')

    d('familia', 'STM32', '', 'implícito: el selector solo contiene STM32')
    d('estado_comercial', g(p, 'estado'))
    d('encapsulado', g(p, 'pkg'))
    d('core', g(p, 'core'))
    dnum('mhz', 'mhz', 'MHz')
    d('fpu', g(p, 'fpu'))
    dnum('flash_kb', 'flash', 'kB')
    dnum('ram_kb', 'ram', 'kB')
    dnum('spi', 'spi')
    dnum('usart', 'usart')
    dnum('uart', 'uart')
    dsuma('uart_total', ['usart', 'uart'], 'puertos', 'suma USART + UART (trampa 2)')
    dnum('i2c', 'i2c')
    dnum('can_fd', 'canfd')
    dnum('can_20', 'can20')
    dsuma('can_total', ['canfd', 'can20'], 'buses', 'suma CAN (FD) + CAN (2.0) (trampa 2)')
    dnum('adc_canales_12b', 'adc12')
    dnum('adc_canales_14b', 'adc14')
    dnum('adc_canales_16b', 'adc16')
    v, grupo = adc(p)
    d('adc_canales', '-' if v is None else fmt_num(v), 'canales',
      f'máximo de los tres grupos de ADC (trampa 3): lo da el grupo de {grupo}' if grupo else
      'los tres grupos de ADC vacíos en el selector')
    dnum('timers_16b', 't16')
    dnum('timers_32b', 't32')
    dsuma('timers_total', ['t16', 't32'], 'timers',
          'suma 16-bit + 32-bit; los timers que ST pone en otras columnas no cuentan (trampa 5)')
    d('otras_funciones_timer', g(p, 'tother'), '',
      'Other timer functions (977): es la única parte paramétrica de la robustez (watchdog)')
    d('memoria_externa', g(p, 'extmem'))
    d('interfaces_adicionales', g(p, 'adic'))
    d('interfaz_registro', f"{g(p, 'extmem')}; {g(p, 'adic')}", '',
      'External Memory Interfaces; Additional Interfaces')
    d('criptografia', g(p, 'crypto'), '',
      'TRAMPA 1: aquí «ECC» es criptografía de curva elíptica, NO memoria con corrección de errores')
    dnum('corriente_run_ua_mhz', 'irun', 'µA/MHz')
    out[-1]['condiciones'] = ('typ; Run Mode por MHz según el selector; tensión, temperatura y ejecución desde '
                              'flash/caché: ver ficha técnica (pendiente)' +
                              ('; campo vacío en el selector' if out[-1]['valor'] == '-' else ''))
    dnum('corriente_low_power_ua', 'ilow', 'µA')
    out[-1]['condiciones'] = ('typ; @ Lowest Power según el selector; qué modo exactamente: ver ficha técnica '
                              '(pendiente)' + ('; campo vacío en el selector' if out[-1]['valor'] == '-' else ''))
    for campo, clave in (('temp_min_c', 'tmin'), ('temp_max_c', 'tmax')):
        dnum(campo, clave, '°C')
        out[-1]['condiciones'] = ('Operating Temperature del selector: depende del sufijo de temperatura del número '
                                  'de pieza que se pida')
    return out


def desde_csv(path, candidatos, fecha, url):
    """Modo sin export: lee candidates_st_selector.csv. No puede reproducir el embudo."""
    filas = leer_csv(path)
    ids = {c['id'] for c in candidatos if c['en_catalogo_st'] == 'si'}
    out = []
    mapa = [('spi', 'spi', ''), ('uart_total', 'uart_total', 'puertos'), ('i2c', 'i2c', ''),
            ('can_total', 'can', 'buses'), ('adc_canales', 'adc_canales', 'canales'),
            ('timers_total', 'timers', 'timers'), ('ram_kb', 'ram_kb', 'kB'), ('flash_kb', 'flash_kb', 'kB'),
            ('temp_max_c', 'temp_max_c', '°C'), ('encapsulado', 'encapsulado', ''), ('fpu', 'fpu', ''),
            ('core', 'core', ''), ('mhz', 'mhz', 'MHz'), ('corriente_run_ua_mhz', 'corriente_run_ua_mhz', 'µA/MHz'),
            ('corriente_low_power_ua', 'corriente_low_power', 'µA')]
    for f in filas:
        if f['candidato_id'] not in ids:
            continue
        for campo, col, unidad in mapa:
            v = f.get(col, '')
            v = '-' if v.strip().lower() in ('sin dato', '-') else v
            cond = ''
            if campo.startswith('corriente'):
                cond = 'según el selector; condiciones de medida en la ficha técnica (pendiente)'
            if campo == 'temp_max_c':
                cond = 'Operating Temperature del selector (sufijo de temperatura de la pieza)'
            out.append({'candidato_id': f['candidato_id'], 'campo': campo, 'valor': v, 'unidad': unidad,
                        'etiqueta': 'fuente', 'fuente': FUENTE, 'revision': '', 'fecha_consulta': fecha,
                        'condiciones': cond, 'url': url, 'importado_de': PREFIJO_CSV})
        reg = '; '.join(x for x in (f.get('interfaz_memoria_externa', ''),
                                    'SD/MMC' if f.get('sdmmc') == 'si' else '') if x)
        out.append({'candidato_id': f['candidato_id'], 'campo': 'interfaz_registro', 'valor': reg or '-',
                    'unidad': '', 'etiqueta': 'fuente', 'fuente': FUENTE, 'revision': '', 'fecha_consulta': fecha,
                    'condiciones': '', 'url': url, 'importado_de': PREFIJO_CSV})
    return out


CRUCE = [('spi', 'spi'), ('uart_total', 'uart_total'), ('i2c', 'i2c'), ('can_total', 'can'),
         ('adc_canales', 'adc_canales'), ('timers_total', 'timers'), ('ram_kb', 'ram_kb'), ('flash_kb', 'flash_kb'),
         ('temp_max_c', 'temp_max_c'), ('corriente_run_ua_mhz', 'corriente_run_ua_mhz')]


def cruzar(filas, csv_path):
    """Compara lo importado del export con candidates_st_selector.csv y enseña las diferencias."""
    if not os.path.exists(csv_path):
        return []
    idx = {(f['candidato_id'], f['campo']): f['valor'] for f in filas}
    difs = []
    for f in leer_csv(csv_path):
        for campo, col in CRUCE:
            a = idx.get((f['candidato_id'], campo))
            b = f.get(col, '').strip()
            if a is None:
                continue
            na, nb = nums(a), nums(b)
            if (na[:1] or a) != (nb[:1] or ('-' if b.lower() in ('sin dato', '', '-') else b)):
                difs.append(f"{f['candidato_id']}.{campo}: export='{a}'  csv='{b}'")
    return difs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', default=os.path.join(RAIZ, 'ProductsList.xlsx'))
    ap.add_argument('--desde-csv', default=None)
    ap.add_argument('--fecha', default=None, help='fecha de consulta del selector, AAAA-MM-DD')
    ap.add_argument('--url', default=URL)
    a = ap.parse_args()

    candidatos = leer_csv('candidates.csv')
    umbrales = leer_csv('thresholds.csv')
    origen_path = a.desde_csv or a.export
    fecha = a.fecha
    if not fecha:
        fecha = datetime.date.fromtimestamp(os.path.getmtime(origen_path)).isoformat()
        print(f'AVISO: fecha_consulta = {fecha}, tomada de la fecha de modificación de {os.path.basename(origen_path)}. '
              'Confírmala con --fecha.')

    if a.desde_csv:
        filas = desde_csv(a.desde_csv, candidatos, fecha, a.url)
        print('candidate_data (conservadas, nuevas):', fusionar_candidate_data(filas, PREFIJO_CSV))
        print('Sin export no se puede reproducir el embudo: data/funnel.csv no se toca.')
        return

    piezas = leer_export(a.export)
    por_pn = {g(p, 'pn'): p for p in piezas}
    origen = os.path.basename(a.export)
    filas = []
    for c in candidatos:
        if c['en_catalogo_st'] != 'si':
            continue
        p = por_pn.get(c['id'])
        if p is None:
            print(f"AVISO: {c['id']} está marcado en_catalogo_st=si pero no aparece en el export")
            continue
        filas += filas_candidato(p, c['id'], fecha, a.url, f'{origen}!{c["id"]}')
    print('candidate_data (conservadas, nuevas):', fusionar_candidate_data(filas, PREFIJO_EXPORT))

    pasos, series, sosp, vivas = embudo(piezas, umbrales, candidatos)
    escribir_csv('funnel.csv', ['orden', 'paso', 'umbral_id', 'selector_param', 'piezas_restantes', 'eliminadas',
                                'eliminadas_campo_vacio'], pasos)
    escribir_csv('funnel_series.csv', ['serie', 'piezas', 'representante', 'representante_sobrevive'], series)
    escribir_csv('funnel_sospechosos.csv', ['pieza', 'serie', 'pasos_con_campo_vacio'], sosp)
    for p in pasos:
        print(f"  {p['piezas_restantes']:5d}  {p['paso']}  (vacío: {p['eliminadas_campo_vacio']})")
    print('  series:', ', '.join(f"{s['serie']} ({s['piezas']})" for s in series))
    print('  sospechosas (solo caen por campos vacíos):', len(sosp))
    for c in candidatos:
        if c['en_catalogo_st'] == 'si':
            print(f"  {c['id']:14s} {'sobrevive' if c['id'] in vivas else 'NO sobrevive'} al embudo  ({c['rol']})")
    for dlin in cruzar(filas, os.path.join(RAIZ, 'candidates_st_selector.csv')):
        print('  DIFERENCIA con candidates_st_selector.csv:', dlin)


if __name__ == '__main__':
    main()
