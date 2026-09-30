#!/usr/bin/env python3
"""Valida data/*.csv. Indica archivo, fila y motivo.

Uso:  python3 tools/validate.py [--estricto] [--detalle]

Tres niveles:
  ERROR      rompe el método (pesos, trampa del ECC, umbrales sin reserva, notas fuera de 1-5...).
             Sale con código 1.
  PENDIENTE  dato etiquetado 'fuente' sin documento o sin revisión/fecha, o dato 'pendiente'.
             Es la lista de tareas, no un fallo del método: solo hace fallar con --estricto
             (pensado para el día antes de la entrevista).
  AVISO      coherencia (bahía sin decidir, interfaz incoherente, reparto obsoleto, doble cuenta,
             huecos de requisitos, CubeMX). Nunca hace fallar: se prefieren falsos positivos.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core  # noqa: E402
from common import ETIQUETAS_VALIDAS, leer_csv  # noqa: E402

BUSES_VALIDOS = {'spi', 'i2c', 'uart', 'can', 'qspi_sdmmc', 'adc', 'gpio', 'pwm', 'timer', 'ninguna'}
ROLES_VALIDOS = {'candidato', 'control', 'lista_larga'}
FAMILIAS_VALIDAS = {'fallo_silencioso', 'recursos_vuelo', 'programa_equipo'}
OPERADORES = {'>=', '<=', 'igual', 'en', 'contiene_alguno', 'afirmativo'}
CAMPOS_CON_CONDICIONES = re.compile(r'^(corriente_|temp_)')


class Informe:
    def __init__(self):
        self.errores, self.pendientes, self.avisos = [], [], []

    def error(self, archivo, fila, motivo):
        self.errores.append(f'ERROR     data/{archivo}:{fila}: {motivo}')

    def pendiente(self, archivo, fila, motivo):
        self.pendientes.append((archivo, f'PENDIENTE data/{archivo}:{fila}: {motivo}'))

    def aviso(self, archivo, fila, motivo):
        self.avisos.append(f'AVISO     data/{archivo}:{fila}: {motivo}')


def clave_param(sp):
    """'FPU (5529): doble...' -> 'fpu'. Los no paramétricos ('— ...') no cuentan."""
    sp = (sp or '').strip()
    if not sp or sp.startswith('—'):
        return None
    return re.split(r'[(:]', sp)[0].strip().lower()


def validar(m, inf):
    criterios, umbrales = m['criteria'], m['thresholds']
    ids_crit = {c['id'] for c in criterios}
    ids_cand = {c['id'] for c in m['candidates']}

    # --- pesos derivados
    w = core.pesos(criterios)
    if abs(sum(w.values()) - 100) > 0.01:
        inf.error('criteria.csv', '-', f'los pesos derivados suman {sum(w.values()):.4f}, no 100 ± 0,01')
    red = core.redondear_a_100(w, 1)
    if round(sum(red.values()), 6) != 100:
        inf.error('criteria.csv', '-', f'el redondeo de presentación suma {sum(red.values())}, no 100 exacto')
    for i, c in enumerate(criterios, 2):
        for campo in ('severidad', 'no_detectabilidad'):
            v = core.num(c[campo])
            if v is None or not 1 <= v <= 5:
                inf.error('criteria.csv', i, f'{c["id"]}: {campo} = {c[campo]!r} fuera de 1-5')
        if c['familia'] not in FAMILIAS_VALIDAS:
            inf.error('criteria.csv', i, f'{c["id"]}: familia {c["familia"]!r} no válida')
        if 'peso' in c or 'peso_%' in c:
            inf.error('criteria.csv', i, 'el peso no se guarda: se deriva de severidad × no detectabilidad')

    # --- ningún criterio ponderado duplica un umbral
    params_umbral = {clave_param(u['selector_param']): u['id'] for u in umbrales if clave_param(u['selector_param'])}
    nombres_umbral = {u['umbral'].strip().lower(): u['id'] for u in umbrales}
    for i, c in enumerate(criterios, 2):
        k = clave_param(c.get('selector_param'))
        if c['criterio'].strip().lower() in nombres_umbral:
            inf.error('criteria.csv', i, f'{c["id"]}: se llama igual que el umbral {nombres_umbral[c["criterio"].strip().lower()]}')
        if k and k in params_umbral and not c.get('umbral_relacionado'):
            inf.error('criteria.csv', i, f'{c["id"]}: usa el mismo parámetro del selector que el umbral {params_umbral[k]} '
                                         'y no declara umbral_relacionado: o es un umbral o pondera el margen sobre él')
        # --- trampa 1: el ECC del selector es criptografía
        if re.search(r'robustez|\bECC\b', f"{c['id']} {c['criterio']} {c['que_mide']}", re.I) and \
                re.search(r'cryptograph', c.get('selector_param') or '', re.I):
            inf.error('criteria.csv', i, f'{c["id"]}: selector_param apunta a Cryptography. Su «ECC» es criptografía de '
                                         'curva elíptica, NO memoria con corrección de errores (trampa 1)')

    # --- umbrales
    buses = core.derivar_buses(m['sensors'], m['bus_rationale'])
    for i, u in enumerate(umbrales, 2):
        if not (u.get('selector_param') or '').strip():
            inf.error('thresholds.csv', i, f'{u["id"]}: sin selector_param (rellénalo o márcalo «— no filtrable»)')
        if u.get('filtrable') == 'no' and 'no filtrable' not in u.get('selector_param', ''):
            inf.error('thresholds.csv', i, f'{u["id"]}: filtrable = no pero selector_param no lo dice explícitamente')
        if u['operador'] not in OPERADORES:
            inf.error('thresholds.csv', i, f'{u["id"]}: operador {u["operador"]!r} desconocido')
        d = u.get('derivado_de') or ''
        if d.startswith('bus:'):
            r = buses['porBus'].get(d[4:])
            if r is None:
                inf.error('thresholds.csv', i, f'{u["id"]}: derivado de {d}, que no existe en bus_rationale.csv')
                continue
            minimo = core.num(u['minimo'])
            if minimo != r['total']:
                if r['reserva'] and minimo == r['buses_pedidos']:
                    motivo = f'cableado a la cuenta SIN reserva ({r["buses_pedidos"]:g}); con reserva son {r["total"]:g}'
                elif minimo == r['dispositivos']:
                    motivo = f'cableado al número de dispositivos ({r["dispositivos"]:g}), no a buses + reserva ({r["total"]:g})'
                else:
                    motivo = f'minimo = {u["minimo"]} y dispositivos → buses + reserva da {r["total"]:g}'
                inf.error('thresholds.csv', i, f'{u["id"]}: {motivo}')

    # --- etiquetas y procedencia en todos los archivos
    def revisar(archivo, filas, col_fuente='fuente', fuente_alt=None):
        for i, f in enumerate(filas, 2):
            e = core.parse_etiqueta(f.get('etiqueta', ''))
            ref = f.get('id') or f.get('candidato_id', '') + ('.' + f['campo'] if 'campo' in f else '') or \
                f.get('criterio_id', '')
            if e['invalidas'] or not e['partes']:
                inf.error(archivo, i, f'{ref}: etiqueta {f.get("etiqueta")!r} no válida (válidas: {", ".join(ETIQUETAS_VALIDAS)}, '
                                      'combinadas con +)')
                continue
            if 'pendiente' in e['partes']:
                inf.pendiente(archivo, i, f'{ref}: etiqueta pendiente')
            elif 'fuente' in e['partes']:
                fuente = (f.get(col_fuente) or '').strip() or (fuente_alt(f) if fuente_alt else '')
                if not fuente:
                    inf.pendiente(archivo, i, f'{ref}: etiqueta fuente sin documento')
                elif not ((f.get('revision') or '').strip() or (f.get('fecha_consulta') or '').strip()):
                    inf.pendiente(archivo, i, f'{ref}: fuente «{fuente[:50]}» sin revisión ni fecha de consulta')

    escala = {s['criterio_id']: s for s in m['scale']}
    revisar('challenges.csv', m['challenges'])
    revisar('sensors.csv', m['sensors'])
    revisar('requirements_inputs.csv', m['requirements_inputs'], fuente_alt=lambda f: f.get('origen', ''))
    revisar('requirements_derived_doc.csv', m['requirements_derived_doc'])
    revisar('criteria.csv', criterios, fuente_alt=lambda f: escala.get(f['id'], {}).get('origen_dato', ''))
    revisar('candidate_data.csv', m['candidate_data'])
    revisar('scores.csv', m['scores'])
    for i, f in enumerate(m['candidate_data'], 2):
        if f['candidato_id'] not in ids_cand:
            inf.error('candidate_data.csv', i, f'{f["candidato_id"]} no está en candidates.csv')
        if CAMPOS_CON_CONDICIONES.match(f['campo']) and not f.get('condiciones', '').strip():
            inf.error('candidate_data.csv', i, f'{f["candidato_id"]}.{f["campo"]}: consumo y temperatura necesitan condiciones')

    # --- candidatos y sensores
    for i, c in enumerate(m['candidates'], 2):
        if c['rol'] not in ROLES_VALIDOS:
            inf.error('candidates.csv', i, f'{c["id"]}: rol {c["rol"]!r} no válido')
        if c['rol'] == 'lista_larga' and not c.get('motivo_rol', '').strip():
            inf.error('candidates.csv', i, f'{c["id"]}: está en lista_larga sin motivo')
    for i, s in enumerate(m['sensors'], 2):
        if s['bus'] not in BUSES_VALIDOS:
            inf.error('sensors.csv', i, f'{s["id"]}: bus {s["bus"]!r} no válido')
        if s.get('bahia', '') not in ('', 'principal', 'aerofreno'):
            inf.error('sensors.csv', i, f'{s["id"]}: bahia {s["bahia"]!r} no válida (principal / aerofreno)')
        if not s.get('bahia', '').strip():
            inf.aviso('sensors.csv', i, f'{s["id"]} ({s["modelo"]}): sin bahía asignada')

    # --- notas: 1-5, justificación y anclas
    justif = {r['criterio_id'] for r in m['score_rationale'] if r['justificacion'].strip()}
    for c in criterios:
        if c['id'] not in escala:
            inf.error('scale.csv', '-', f'el criterio {c["id"]} no tiene anclas')
        elif not all(escala[c['id']].get(k, '').strip() for k in ('ancla_5', 'ancla_3', 'ancla_1')):
            inf.error('scale.csv', '-', f'el criterio {c["id"]} tiene anclas vacías')
    for i, s in enumerate(m['scores'], 2):
        n = core.num(s['nota'])
        if n is None or not 1 <= n <= 5:
            inf.error('scores.csv', i, f'{s["candidato_id"]}.{s["criterio_id"]}: nota {s["nota"]!r} fuera de 1-5')
        if s['criterio_id'] not in ids_crit:
            inf.error('scores.csv', i, f'criterio {s["criterio_id"]!r} no existe en criteria.csv')
        elif s['criterio_id'] not in justif:
            inf.error('scores.csv', i, f'{s["criterio_id"]}: nota sin justificación en score_rationale.csv')
        if s['candidato_id'] not in ids_cand:
            inf.error('scores.csv', i, f'candidato {s["candidato_id"]!r} no existe en candidates.csv')

    # --- requisitos derivados sin enganchar (punto 9)
    for i, r in enumerate(m['requirements_derived_doc'], 2):
        if not r.get('enganchado_a', '').strip():
            inf.aviso('requirements_derived_doc.csv', i, f'{r["id"]}: hueco, el requisito no está enganchado a ningún umbral '
                                                          'ni criterio')

    # --- embudo: no puede crecer
    prev = None
    for i, p in enumerate(m['funnel'], 2):
        n = int(p['piezas_restantes'])
        if prev is not None and n > prev:
            inf.error('funnel.csv', i, f'el embudo crece ({prev} -> {n})')
        prev = n

    # --- coherencia (puntos 4 a 7 y CubeMX)
    for a in core.coherencia(m['sensors'], buses, m['bus_rationale'], m['ioc']):
        archivo = 'bus_rationale.csv' if a['codigo'] == 'reparto_obsoleto' else (
            'ioc_peripherals.csv' if a['codigo'] == 'ioc' else 'sensors.csv')
        if a['codigo'] == 'bahia_sin_decidir':
            continue  # ya avisado fila a fila
        (inf.error if a['nivel'] == 'error' else inf.aviso)(archivo, a['ref'] or '-', a['mensaje'])


def main():
    estricto = '--estricto' in sys.argv
    detalle = '--detalle' in sys.argv
    inf = Informe()
    validar(core.cargar(leer_csv), inf)
    for e in inf.errores:
        print(e)
    for a in inf.avisos:
        print(a)
    por_archivo = {}
    for archivo, linea in inf.pendientes:
        por_archivo.setdefault(archivo, []).append(linea)
    for archivo, lineas in por_archivo.items():
        if detalle or estricto:
            for linea in lineas:
                print(linea)
        else:
            print(f'PENDIENTE data/{archivo}: {len(lineas)} datos sin procedencia completa (--detalle para verlos)')
    print(f'\n{len(inf.errores)} errores · {len(inf.pendientes)} pendientes de fuente · {len(inf.avisos)} avisos'
          + (' · modo estricto' if estricto else ''))
    sys.exit(1 if inf.errores or (estricto and inf.pendientes) else 0)


if __name__ == '__main__':
    main()
