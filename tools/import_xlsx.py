#!/usr/bin/env python3
"""Importación única de los dos libros de Excel a data/*.csv.

Uso:  python3 tools/import_xlsx.py ["softwareFARADAY 1.xlsx"] ["softwareFARADAY 2.xlsx"]

Qué hace y qué NO hace:
  - Copia textos y números tal cual. No inventa fuentes, revisiones ni valores.
  - Las fórmulas (anchos de banda, requisitos derivados, veredictos, pesos en %)
    NO se importan: se recalculan en app/core.js y tools/core.py.
  - Todo dato sin procedencia identificable queda con etiqueta = pendiente.
  - Los datos paramétricos de los micros NO salen de aquí: salen del selector de
    ST (tools/import_st_selector.py). De la hoja Umbrales solo se importa lo que el
    selector no sabe (placa, stock/longevidad, CubeMX) y el candidato que no está en
    el catálogo de ST (ESP32-S3).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (RAIZ, escribir_csv, fmt_num, fusionar_candidate_data,  # noqa: E402
                    normalizar_etiqueta, primer_numero, leer_csv)
from xlsx_stdlib import leer, valor, formula, col_a_num, num_a_col  # noqa: E402

PREFIJO = 'softwareFARADAY'
AVISOS = []


def aviso(msg):
    AVISOS.append(msg)


def etq(texto, donde):
    e, raras = normalizar_etiqueta(texto)
    if raras:
        aviso(f'{donde}: etiqueta no reconocida {raras!r} -> pendiente')
    return e


# ---------------------------------------------------------------- FARADAY 1
def importar_challenges(libro, nombre):
    h = libro['Hoja 1']
    filas = []
    for r in range(2, 12):
        if not valor(h, f'A{r}'):
            continue
        filas.append({
            'id': f'C{r - 1:02d}',
            'condicion': valor(h, f'A{r}'), 'dato': valor(h, f'B{r}'),
            'problema': valor(h, f'C{r}'), 'implicacion': valor(h, f'D{r}'),
            'etiqueta': 'pendiente', 'fuente': '', 'revision': '',
        })
    escribir_csv('challenges.csv', ['id', 'condicion', 'dato', 'problema', 'implicacion',
                                    'etiqueta', 'fuente', 'revision'], filas)
    return len(filas)


# ---------------------------------------------------------------- Inventario
BUS = {'SPI': 'spi', 'I2C': 'i2c', 'UART': 'uart', 'CAN': 'can', 'QSPI/SDMMC': 'qspi_sdmmc',
       'ADC': 'adc', 'GPIO': 'gpio', 'PWM': 'pwm', 'TIMER': 'timer', 'NINGUNA': 'ninguna',
       '—': 'ninguna', '-': 'ninguna', '': 'ninguna'}
SECCION = {'ESTIMAR ESTADOS': 'estimar_estado', 'DETECTAR EVENTOS': 'detectar_eventos',
           'VIGILAR LA SALUD': 'vigilar_salud', 'REGISTRAR Y COMUNICAR': 'registrar_comunicar',
           'INDEPENDIENTES': 'independiente'}


def importar_inventario(libro):
    h = libro['Inventario']
    filas, funcion, n = [], None, 0
    for r in range(5, 35):
        a, b = valor(h, f'A{r}'), valor(h, f'B{r}')
        if a and not b:
            clave = next((k for k in SECCION if a.upper().startswith(k)), None)
            if clave is None:
                aviso(f'Inventario fila {r}: fila de sección no reconocida {a!r}')
            funcion = SECCION.get(clave)
            continue
        if not b:
            continue
        n += 1
        bus_txt = valor(h, f'E{r}')
        bus = BUS.get(bus_txt.upper(), None)
        if bus is None:
            aviso(f'Inventario fila {r}: interfaz {bus_txt!r} no reconocida')
            bus = bus_txt.lower()
        filas.append({
            'id': f'S{n:02d}', 'funcion': funcion, 'para_que': a, 'modelo': b,
            'cantidad': valor(h, f'C{r}'), 'justificacion': valor(h, f'D{r}'), 'bus': bus,
            'bytes_lectura': valor(h, f'F{r}'), 'frecuencia_hz': valor(h, f'G{r}'),
            'etiqueta': etq(valor(h, f'I{r}'), f'Inventario!I{r}'),
            'fuente': '', 'revision': '', 'bahia': '', 'critico': '', 'fila_origen': r,
        })
    escribir_csv('sensors.csv', ['id', 'funcion', 'para_que', 'modelo', 'cantidad', 'justificacion',
                                 'bus', 'bytes_lectura', 'frecuencia_hz', 'etiqueta', 'fuente',
                                 'revision', 'bahia', 'critico', 'fila_origen'], filas)

    # De dispositivos a buses: B y E son fórmulas (se recalculan); C y D son datos tuyos.
    recursos = {41: ('spi', 'compartido'), 42: ('uart', 'punto_a_punto'), 43: ('i2c', 'compartido'),
                44: ('can', 'compartido'), 45: ('adc', 'punto_a_punto'), 46: ('pwm', 'punto_a_punto'),
                47: ('gpio', 'punto_a_punto'), 48: ('qspi_sdmmc', 'punto_a_punto'),
                49: ('timer', 'punto_a_punto')}
    br = []
    for r, (bus, tipo) in recursos.items():
        br.append({'recurso': valor(h, f'A{r}'), 'bus': bus, 'tipo': tipo,
                   'buses_pedidos': valor(h, f'C{r}'), 'reserva': valor(h, f'D{r}'),
                   'justificacion': valor(h, f'F{r}')})
    escribir_csv('bus_rationale.csv', ['recurso', 'bus', 'tipo', 'buses_pedidos', 'reserva',
                                       'justificacion'], br)
    return len(filas), len(br)


# ---------------------------------------------------------------- Requisitos
ENTRADAS = ['vuelo_s', 'margen', 'rampa_h', 'n_estados', 'f_filtro_hz', 'coste_por_paso',
            'ciclos_por_op', 'bytes_muestra', 'f_registro_hz', 'escala_ecef_m']
DERIVADOS = [
    ('duracion_diseno_s', 'derivado', 'requisito memoria_registro_mb'),
    ('memoria_registro_mb', 'derivado', ''),  # punto 9: no enganchado a ningún umbral
    ('ops_paso', 'derivado', 'requisito mops_s'),
    ('mops_s', 'derivado', 'requisito mciclos_s'),
    ('mciclos_s', 'derivado', 'criterio calculo'),
    ('resolucion_ecef_m', 'derivado', 'criterio precision'),
    ('vuelta_contador_min', 'derivado', 'firmware (base de tiempo, sensor TCXO + PPS)'),
    ('vueltas_rampa', 'derivado', 'firmware (base de tiempo, sensor TCXO + PPS)'),
    ('rango_temperatura', 'constante', 'umbrales T12 y T13'),
]


def importar_requisitos(libro):
    h = libro['Requisitos']
    ins = []
    for i, r in enumerate(range(6, 16)):
        ins.append({'id': ENTRADAS[i], 'parametro': valor(h, f'A{r}'), 'valor': valor(h, f'B{r}'),
                    'unidad': valor(h, f'C{r}'), 'origen': valor(h, f'D{r}'),
                    'etiqueta': etq(valor(h, f'E{r}'), f'Requisitos!E{r}'), 'fuente': '', 'revision': ''})
    escribir_csv('requirements_inputs.csv', ['id', 'parametro', 'valor', 'unidad', 'origen', 'etiqueta',
                                             'fuente', 'revision'], ins)
    der = []
    for i, r in enumerate(range(19, 28)):
        ident, tipo, eng = DERIVADOS[i]
        der.append({'id': ident, 'requisito': valor(h, f'A{r}'), 'unidad': valor(h, f'C{r}'),
                    'como_se_obtiene': valor(h, f'D{r}'),
                    'etiqueta': etq(valor(h, f'E{r}'), f'Requisitos!E{r}'), 'tipo': tipo,
                    'valor_constante': valor(h, f'B{r}') if tipo == 'constante' else '',
                    'enganchado_a': eng, 'formula_excel': formula(h, f'B{r}') or ''})
    escribir_csv('requirements_derived_doc.csv', ['id', 'requisito', 'unidad', 'como_se_obtiene', 'etiqueta',
                                                  'tipo', 'valor_constante', 'enganchado_a',
                                                  'formula_excel'], der)
    return len(ins), len(der)


# ---------------------------------------------------------------- Umbrales
# Estructura del filtro (operador, campo, derivación) + mapeo al selector de ST.
# Los textos "Umbral" y "Mínimo exigido" vienen de la hoja; lo demás es el esquema.
UMBRALES = [
    # id, fila, nombre (None = el de la hoja), campo, operador, minimo, unidad, derivado_de,
    # selector_param, selector_id, filtrable, notas
    ('T01', 6, None, 'familia', 'igual', 'STM32', '', '',
     '— (implícito: el selector solo tiene STM32)', '', 'implicito', ''),
    ('T02', 7, None, 'fpu', 'contiene_alguno', 'Single-precision;Double-precision;Half-precision', '', '',
     'FPU (Single / Double / Half-precision)', '5529', 'si',
     "En FPU el '-' del selector significa «sin FPU» (núcleos M0/M3), no un hueco de la base de datos."),
    ('T03', 8, None, 'spi', '>=', '3', 'buses', 'bus:spi', 'SPI', '5032', 'si', ''),
    ('T04', 9, None, 'uart_total', '>=', '4', 'puertos', 'bus:uart', 'USART + UART (dos columnas distintas)',
     '5033+5062', 'si', 'Trampa 2: el selector separa USART y UART; el umbral los suma.'),
    ('T05', 10, None, 'i2c', '>=', '2', 'buses', 'bus:i2c', 'I2C', '5031', 'si', ''),
    ('T06', 11, None, 'can_total', '>=', '1', 'buses', 'bus:can', 'CAN (FD) + CAN (2.0) (dos columnas)',
     '5501+5468', 'si', 'Trampa 2: CAN FD y CAN 2.0 son columnas separadas; el umbral las suma.'),
    ('T07', 12, None, 'interfaz_registro', 'contiene_alguno',
     'Quad SPI;Octo SPI;xSPI;QUADSPI;OCTOSPI;SD/MMC;SDMMC;SDIO', '', '',
     'External Memory Interfaces / Additional Interfaces', '5440/5439', 'si', ''),
    ('T08', 13, None, 'adc_canales', '>=', '12', 'canales', 'bus:adc',
     'Number of Channels (aparece 3 veces, una por grupo de ADC)', '5279/5422/5280', 'si',
     'Trampa 3: se toma el máximo de los tres grupos; condiciones dice cuál.'),
    ('T09', 14, None, 'timers_total', '>=', '3', 'timers', 'bus:pwm',
     'Timers 16-bit + 32-bit, Other timer functions', '5045+5046/977', 'si',
     'Trampa 5: timers repartidos en otras columnas (el U575ZI sale con 0).'),
    ('T10', 15, None, 'ram_kb', '>=', '128', 'kB', '', 'RAM Size', '1901', 'si',
     'La hoja no fija número ("≥ requisito del filtro + buffers"); 128 kB es la cifra del embudo.'),
    ('T11', 16, None, 'flash_kb', '>=', '256', 'kB', '', 'Flash Size', '3144', 'si', ''),
    ('T12', 17, 'Temperatura mínima', 'temp_min_c', '<=', '-40', '°C', '', 'Operating Temperature min',
     '960', 'si', 'El embudo solo filtró la máxima.'),
    ('T13', 17, 'Temperatura máxima', 'temp_max_c', '>=', '85', '°C', '', 'Operating Temperature max',
     '962', 'si', ''),
    ('T14', 18, None, 'encapsulado', 'contiene_alguno', 'LQFP', '', '', 'Package', '4363', 'si', ''),
    ('T15', 19, None, 'placa_evaluacion', 'afirmativo', '', '', '', '— no filtrable: comprobación manual',
     '', 'no', 'El único umbral que el selector no sabe filtrar: define la regla de lista corta.'),
    ('T16', 20, 'Disponibilidad: estado comercial', 'estado_comercial', 'igual', 'Active', '', '',
     'Marketing Status', '163', 'si', ''),
    ('T17', 20, 'Disponibilidad: stock y longevidad', 'disponibilidad_longevidad', 'afirmativo', '', '', '',
     'Longevity Commitment', '62', 'si',
     'El export ProductsList.xlsx no trae la columna Longevity: el dato viene de la hoja Umbrales (pendiente).'),
    ('T18', 21, None, 'coexistencia_cubemx', 'afirmativo', '', '', '', '— no filtrable: es CubeMX', '',
     'no', ''),
]

CANDIDATOS_HOJA = ['C', 'E', 'G', 'I', 'K', 'M', 'O', 'Q', 'S', 'U', 'W', 'Y']
VACIOS = ('por verificar', 'por confirmar', '—', '-', '')


def texto_minimo(h, r):
    v = valor(h, f'B{r}')
    if v:
        return v
    f = formula(h, f'B{r}') or ''
    # '"≥ "&Inventario!E41&" buses SPI (...)"'  ->  '≥ Inventario!E41 buses SPI (...)'
    return re.sub(r'"?&"?', ' ', f).replace('"', '').replace('  ', ' ').strip()


def importar_umbrales(libro, sel_csv):
    h = libro['Umbrales']
    filas = []
    for (i, r, nombre, campo, op, minimo, unidad, der, sp, sid, filt, notas) in UMBRALES:
        filas.append({'id': i, 'umbral': nombre or valor(h, f'A{r}'), 'fila_origen': r, 'campo': campo,
                      'operador': op, 'minimo': minimo, 'unidad': unidad, 'derivado_de': der,
                      'minimo_texto': texto_minimo(h, r), 'selector_param': sp, 'selector_id': sid,
                      'filtrable': filt, 'notas': notas})
    escribir_csv('thresholds.csv', ['id', 'umbral', 'fila_origen', 'campo', 'operador', 'minimo', 'unidad',
                                    'derivado_de', 'minimo_texto', 'selector_param', 'selector_id',
                                    'filtrable', 'notas'], filas)

    # ---- candidatos: los 12 de la hoja + los del CSV del selector que no están en ella
    ids_hoja = [valor(h, f'{c}4') for c in CANDIDATOS_HOJA]
    sel = {f['candidato_id']: f for f in sel_csv}
    cands = []
    for cid in ids_hoja + [k for k in sel if k not in ids_hoja]:
        s = sel.get(cid, {})
        en_st = cid.startswith('STM32')
        m = re.match(r'STM32([A-Z]+\d)', cid)
        rol = s.get('rol') or 'candidato'
        motivo = ''
        if cid not in ids_hoja:
            rol = 'lista_larga'
            motivo = ('No es el representante de su serie según la regla declarada (Umbrales A27): '
                      'sin Nucleo propia y sin QUADSPI; la serie F4 la representa el F446RE.'
                      if cid == 'STM32F405RG' else 'No figura en la hoja Umbrales.')
        notas = s.get('notas', '')
        if cid == 'STM32U5A5ZJ':
            notas = ('Representa a la serie U5 en lugar del STM32U575ZI, que aparece en el catálogo con '
                     '0 timers: hueco de la base de datos, no de la pieza (Umbrales A27).')
        if cid == 'STM32C5A3ZG':
            notas = 'Placa de evaluación por confirmar: es lo único que podría eliminarlo (Umbrales A27).'
        cands.append({'id': cid, 'fabricante': s.get('fabricante') or ('STMicroelectronics' if en_st else ''),
                      'modelo': s.get('modelo') or cid, 'serie': s.get('serie') or (m.group(1) if m else ''),
                      'rol': rol, 'motivo_rol': motivo, 'en_catalogo_st': 'si' if en_st else 'no',
                      'notas': notas})
    escribir_csv('candidates.csv', ['id', 'fabricante', 'modelo', 'serie', 'rol', 'motivo_rol',
                                    'en_catalogo_st', 'notas'], cands)

    # ---- datos de candidato que el selector de ST no da
    cd = []

    def dato(cid, campo, val, ref, unidad='', cond=''):
        cd.append({'candidato_id': cid, 'campo': campo, 'valor': val, 'unidad': unidad, 'etiqueta': 'pendiente',
                   'fuente': '', 'revision': '', 'fecha_consulta': '', 'condiciones': cond, 'url': '',
                   'importado_de': f'{PREFIJO} 2.xlsx!Umbrales!{ref}'})

    def texto_o_vacio(t):
        return '' if t.strip().lower().rstrip('.').startswith(VACIOS[:2]) or t.strip() in VACIOS[2:] else t

    for c, cid in zip(CANDIDATOS_HOJA, ids_hoja):
        filas_no_param = {19: 'placa_evaluacion', 20: 'disponibilidad_longevidad', 21: 'coexistencia_cubemx'}
        if not cid.startswith('STM32'):
            # Fuera del catálogo de ST: la hoja Umbrales es el único registro que tengo.
            filas_no_param = {6: 'familia', 7: 'fpu', 8: 'spi', 9: 'uart_total', 10: 'i2c', 11: 'can_total',
                              12: 'interfaz_registro', 13: 'adc_canales', 14: 'timers_total', 15: 'ram_kb',
                              16: 'flash_kb', 17: 'temp', 18: 'encapsulado', **filas_no_param}
        for r, campo in filas_no_param.items():
            ref = f'{c}{r}'
            t = valor(h, ref)
            limpio = texto_o_vacio(t)
            cond = f'texto original: {t}' if limpio != t else ''
            if campo in ('spi', 'uart_total', 'i2c', 'can_total', 'adc_canales', 'timers_total', 'ram_kb',
                         'flash_kb'):
                n = primer_numero(t)
                if n is not None and campo == 'ram_kb' and 'MB' in t:
                    n = n * 1024
                val = fmt_num(n) if n is not None else t
                if val != t:
                    cond = f'texto original: {t}'
                unidad = 'kB' if campo in ('ram_kb', 'flash_kb') else ''
                dato(cid, campo, val, ref, unidad, cond)
            elif campo == 'fpu':
                val = 'Double-precision' if 'doble' in t.lower() else 'Single-precision' if (
                    'simple' in t.lower()) else t
                dato(cid, campo, val, ref, '', f'texto original: {t}')
            elif campo == 'temp':
                a, _, b = t.replace('−', '-').partition('/')
                cond_t = f'texto original: {t}; condiciones de medida sin documentar (pendiente)'
                dato(cid, 'temp_min_c', fmt_num(primer_numero(a)), ref, '°C', cond_t)
                dato(cid, 'temp_max_c', fmt_num(primer_numero(b)), ref, '°C', cond_t)
            else:
                dato(cid, campo, limpio, ref, '', cond)
    return len(filas), len(cands), cd


# ---------------------------------------------------------------- Pesos, Escala, Matriz
CRITERIOS = [  # id, nombre en la hoja, familia, selector_param, umbral_relacionado
    ('calculo', 'Margen de cálculo del filtro', 'recursos_vuelo',
     '— no paramétrico: se mide con el contador DWT en una Nucleo', ''),
    ('precision', 'Precisión numérica y marco de referencia', 'fallo_silencioso',
     'FPU (5529): Double-precision frente a Single-precision', 'T02'),
    ('perifericos', 'Margen de periféricos y patillas', 'programa_equipo',
     '— no paramétrico: rutado en CubeMX', 'T03;T04;T05;T06;T08;T09'),
    ('registro', 'Arquitectura y ancho de banda del registro', 'recursos_vuelo',
     'External Memory Interfaces / Additional Interfaces (5440/5439)', 'T07'),
    ('consumo', 'Consumo durante la espera en rampa', 'recursos_vuelo',
     'Supply Current Run Mode per MHz (4409); Supply Current @ Lowest Power (4343)', ''),
    ('robustez', 'Funciones de robustez', 'fallo_silencioso',
     'Other timer functions (977): solo el watchdog. ECC de memoria, CSS y BOR no son paramétricos: '
     'ficha técnica y AN5342', ''),
    ('continuidad', 'Continuidad con el equipo y ecosistema', 'programa_equipo', '— no paramétrico', ''),
    ('calendario', 'Riesgo de calendario', 'programa_equipo', '— no paramétrico', ''),
    ('coste', 'Coste y disponibilidad real', 'programa_equipo',
     '— no paramétrico: el selector no tiene precio (distribuidor)', ''),
]
POR_NOMBRE = {c[1]: c for c in CRITERIOS}


def criterio_de(nombre, donde):
    c = POR_NOMBRE.get(nombre)
    if c is None:
        raise SystemExit(f'{donde}: criterio {nombre!r} no reconocido')
    return c


def importar_pesos_escala_matriz(libro):
    hp, he, hm = libro['Pesos'], libro['Escala'], libro['Matriz']
    crit = []
    for r in range(5, 14):
        cid, _, fam, sp, ur = criterio_de(valor(hp, f'A{r}'), f'Pesos!A{r}')
        crit.append({'id': cid, 'criterio': valor(hp, f'A{r}'), 'que_mide': valor(hp, f'B{r}'),
                     'consecuencia': valor(hp, f'C{r}'), 'severidad': valor(hp, f'D{r}'),
                     'no_detectabilidad': valor(hp, f'E{r}'), 'etiqueta': etq(valor(hp, f'I{r}'), f'Pesos!I{r}'),
                     'familia': fam, 'selector_param': sp, 'umbral_relacionado': ur})
    escribir_csv('criteria.csv', ['id', 'criterio', 'que_mide', 'consecuencia', 'severidad', 'no_detectabilidad',
                                  'etiqueta', 'familia', 'selector_param', 'umbral_relacionado'], crit)
    esc = []
    for r in range(5, 14):
        cid = criterio_de(valor(he, f'A{r}'), f'Escala!A{r}')[0]
        esc.append({'criterio_id': cid, 'ancla_5': valor(he, f'B{r}'), 'ancla_3': valor(he, f'C{r}'),
                    'ancla_1': valor(he, f'D{r}'), 'origen_dato': valor(he, f'E{r}')})
    escribir_csv('scale.csv', ['criterio_id', 'ancla_5', 'ancla_3', 'ancla_1', 'origen_dato'], esc)

    cols = {num_a_col(c): valor(hm, f'{num_a_col(c)}4') for c in range(col_a_num('C'), col_a_num('N') + 1)}
    notas = []
    obs = {('STM32G474RE', 'consumo'): 'Sin fuente: ST no publica el consumo del G474RE en el selector. '
                                       'Nota 3 por la regla de quedarse con la nota baja (punto 10).',
           ('STM32G474RE', 'perifericos'): 'SPI = 3 según el catálogo de ST, no 4: margen cero, igual que el '
                                           'F446 (punto 10).'}
    for r in range(5, 14):
        cid = criterio_de(valor(hm, f'A{r}'), f'Matriz!A{r}')[0]
        for col, cand in cols.items():
            v = valor(hm, f'{col}{r}')
            if v == '':
                continue
            notas.append({'criterio_id': cid, 'candidato_id': cand, 'nota': v, 'etiqueta': 'pendiente',
                          'observacion': obs.get((cand, cid), ''), 'celda_origen': f'Matriz!{col}{r}'})
    escribir_csv('scores.csv', ['criterio_id', 'candidato_id', 'nota', 'etiqueta', 'observacion', 'celda_origen'],
                 notas)
    raz = []
    for r in range(27, 37):
        nombre = valor(hm, f'A{r}')
        if nombre in POR_NOMBRE:
            raz.append({'criterio_id': POR_NOMBRE[nombre][0], 'justificacion': valor(hm, f'B{r}')})
        else:
            aviso(f'Matriz fila {r} ({nombre!r}) no es un criterio: va a DECISIONES.md, no a score_rationale.csv')
    escribir_csv('score_rationale.csv', ['criterio_id', 'justificacion'], raz)
    return len(crit), len(esc), len(notas), len(raz)


def main():
    f1 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'softwareFARADAY 1.xlsx')
    f2 = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, 'softwareFARADAY 2.xlsx')
    sel_path = os.path.join(RAIZ, 'candidates_st_selector.csv')
    sel = leer_csv(sel_path) if os.path.exists(sel_path) else []
    l1, l2 = leer(f1), leer(f2)
    print('challenges.csv            ', importar_challenges(l1, f1))
    print('sensors.csv, bus_rationale', importar_inventario(l2))
    print('requirements (in, derived)', importar_requisitos(l2))
    nu, nc, cd = importar_umbrales(l2, sel)
    print('thresholds.csv            ', nu, ' candidates.csv', nc)
    print('candidate_data (propias)  ', fusionar_candidate_data(cd, PREFIJO))
    print('criteria, scale, scores, rationale', importar_pesos_escala_matriz(l2))
    for a in AVISOS:
        print('AVISO', a)


if __name__ == '__main__':
    main()
