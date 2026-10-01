"""Espejo en Python de app/core.js (misma lógica, mismos nombres).

Existe porque el validador y los tests tienen que correr con python3 y nada más.
tests/test_core.py comprueba que core.js y este archivo dan lo mismo con los datos
reales (si hay Node en la máquina; si no, lo dice y se salta esa comparación).
"""
import math
import re

ETIQUETAS = ['fuente', 'vuelo', 'calculo', 'medido', 'criterio_propio', 'pendiente']
EMPATE_TECNICO_PUNTOS = 5
EPS = 1e-9
_NUM = re.compile(r'^-?\d+(\.\d+)?$')


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    t = str(v).strip().replace('−', '-').replace(',', '.', 1)
    return float(t) if _NUM.match(t) else None


def parse_etiqueta(texto):
    partes, invalidas = [], []
    for p in str(texto or '').split('+'):
        p = p.strip()
        if not p:
            continue
        if p in ETIQUETAS:
            if p not in partes:
                partes.append(p)
        else:
            invalidas.append(p)
    return {'partes': partes, 'invalidas': invalidas}


def redondear_a_100(valores, decimales=1):
    escala = 10 ** decimales
    total = sum(valores.values())
    base, resto = {}, []
    for k, v0 in valores.items():
        v = v0 / total * 100 * escala
        base[k] = math.floor(v + EPS)
        resto.append((k, v - base[k]))
    resto.sort(key=lambda x: (-x[1], x[0]))
    falta = round(100 * escala) - sum(base.values())
    for i in range(falta):
        base[resto[i % len(resto)][0]] += 1
    return {k: base[k] / escala for k in valores}


# ------------------------------------------------------------------ requisitos
def derivar_requisitos(e):
    dur = e['vuelo_s'] * (1 + e['margen'])
    ops = e['coste_por_paso'] * e['n_estados'] ** 3
    mops = ops * e['f_filtro_hz'] / 1e6
    vuelta = 2 ** 32 / 1e6 / 60
    return {
        'duracion_diseno_s': dur,
        'memoria_registro_mb': e['bytes_muestra'] * e['f_registro_hz'] * dur / 1048576,
        'ops_paso': ops,
        'mops_s': mops,
        'mciclos_s': mops * e['ciclos_por_op'],
        'resolucion_ecef_m': 2.0 ** (math.floor(math.log2(e['escala_ecef_m']) + EPS) - 23),
        'vuelta_contador_min': vuelta,
        'vueltas_rampa': e['rampa_h'] * 60 / vuelta,
    }


# ------------------------------------------------------------------ buses
def derivar_buses(sensores, bus_rationale):
    por_bus, recursos, avisos, sin_bahia = {}, [], [], []
    for b in bus_rationale:
        r = {'bus': b['bus'], 'recurso': b['recurso'], 'tipo': b['tipo'], 'dispositivos': 0,
             'buses_pedidos': num(b['buses_pedidos']) or 0, 'reserva': num(b['reserva']) or 0,
             'sensores': [], 'provisionales': 0, 'avisos': []}
        r['total'] = r['buses_pedidos'] + r['reserva']
        por_bus[b['bus']] = r
        recursos.append(r)
    for s in sensores:
        if not s.get('bus') or s['bus'] == 'ninguna':
            continue
        bahia = (s.get('bahia') or '').strip()
        if bahia == '':
            sin_bahia.append(s['id'])
        if bahia == 'aerofreno':
            continue
        r = por_bus.get(s['bus'])
        if r is None:
            avisos.append(f"El sensor {s['id']} usa el bus «{s['bus']}», que no tiene fila en bus_rationale.csv")
            continue
        n = num(s.get('cantidad')) or 0
        r['dispositivos'] += n
        if bahia == '':
            r['provisionales'] += n
        r['sensores'].append({'id': s['id'], 'modelo': s['modelo'], 'cantidad': n, 'bahia': bahia or 'sin decidir'})
    for r in recursos:
        if r['tipo'] == 'punto_a_punto' and r['buses_pedidos'] < r['dispositivos']:
            r['avisos'].append('faltan canales')
        if r['tipo'] == 'punto_a_punto' and r['buses_pedidos'] > r['dispositivos']:
            r['avisos'].append('pide más que dispositivos')
        if r['tipo'] == 'compartido' and r['dispositivos'] > 0 and r['buses_pedidos'] < 1:
            r['avisos'].append('dispositivos sin bus')
        if r['tipo'] == 'compartido' and r['buses_pedidos'] > r['dispositivos']:
            r['avisos'].append('más buses que dispositivos')
    if sin_bahia:
        avisos.append(f'{len(sin_bahia)} sensores sin bahía asignada: se cuentan como principal provisional.')
    return {'recursos': recursos, 'porBus': por_bus, 'sin_bahia': sin_bahia, 'avisos': avisos}


# ------------------------------------------------------------------ filtro
def exigido(u, buses):
    d = u.get('derivado_de') or ''
    if d.startswith('bus:'):
        r = buses['porBus'].get(d[4:]) if buses else None
        return r['total'] if r else num(u['minimo'])
    return num(u['minimo']) if u['operador'] in ('>=', '<=') else u['minimo']


_AFIRMA_NO = re.compile(r'^(no\b|sin\b|ninguna|-$)', re.I | re.A)


def aplicar_filtro(datos, umbrales, buses):
    fallos, sin_dato, detalle = [], [], []
    for u in umbrales:
        fila = datos.get(u['campo'])
        raw = str(fila.get('valor') or '').strip() if fila else ''
        req = exigido(u, buses)
        d = {'umbral_id': u['id'], 'umbral': u['umbral'], 'campo': u['campo'], 'valor': raw, 'exigido': req,
             'etiqueta': fila.get('etiqueta', '') if fila else '', 'estado': 'pasa', 'sospechoso': False, 'motivo': ''}
        vacio = raw == '-'
        if raw == '':
            d['estado'] = 'sin_dato'
            d['motivo'] = 'celda vacía en el registro' if fila else 'no hay dato: no lo he mirado'
        elif u['operador'] in ('>=', '<='):
            v = 0.0 if vacio else num(raw)
            if v is None:
                d['estado'], d['motivo'] = 'sin_dato', f'valor no numérico: «{raw}»'
            else:
                ok = v >= req - EPS if u['operador'] == '>=' else v <= req + EPS
                if not ok:
                    d['estado'], d['sospechoso'] = 'no', vacio or v == 0
        else:
            bajo = raw.lower()
            lista = [x.strip().lower() for x in str(req or '').split(';') if x.strip()]
            op = u['operador']
            if op == 'igual':
                pasa = bajo == lista[0]
            elif op == 'en':
                pasa = bajo in lista
            elif op == 'contiene_alguno':
                pasa = any(x in bajo for x in lista)
            elif op == 'afirmativo':
                pasa = not _AFIRMA_NO.search(raw)
            else:
                d['estado'], d['motivo'], pasa = 'sin_dato', f'operador desconocido «{op}»', True
            if not pasa:
                d['estado'], d['sospechoso'] = 'no', vacio
        if d['estado'] == 'no':
            d['motivo'] = ('campo vacío o a cero en la fuente: puede ser un hueco de la base de datos, no de la pieza'
                           if d['sospechoso'] else 'el valor no llega')
            fallos.append(d)
        elif d['estado'] == 'sin_dato':
            sin_dato.append(d)
        detalle.append(d)
    return {'pasa': not fallos and not sin_dato,
            'estado': 'ELIMINADO' if fallos else ('SIN_DATO' if sin_dato else 'PASA'),
            'fallos': fallos, 'sin_dato': sin_dato, 'sospechosos': [f for f in fallos if f['sospechoso']],
            'detalle': detalle}


# ------------------------------------------------------------------ puntuación
def pesos(criterios):
    bruto = {c['id']: (num(c['severidad']) or 0) * (num(c['no_detectabilidad']) or 0) for c in criterios}
    s = sum(bruto.values())
    return {k: (v / s * 100 if s else 0) for k, v in bruto.items()}


def puntuar(notas, criterios, w):
    desglose, faltan, total = [], [], 0.0
    for c in criterios:
        n = num(notas.get(c['id'])) if notas else None
        if n is None:
            faltan.append(c['id'])
            continue
        aporte = w[c['id']] * n / 5
        total += aporte
        desglose.append({'criterio': c['id'], 'familia': c['familia'], 'peso': w[c['id']], 'nota': n,
                         'aporte': aporte})
    return {'total': None if faltan else total, 'desglose': desglose, 'faltan': faltan}


def ranking(candidatos, filtros, notas, criterios, w, provisional=False):
    sup, elim, sin_notas, fuera = [], [], [], []
    for c in candidatos:
        if c.get('rol') == 'lista_larga':
            fuera.append({'id': c['id'], 'motivo': c.get('motivo_rol', '')})
            continue
        f = filtros[c['id']]
        if not (f['pasa'] or (provisional and not f['fallos'])):
            elim.append({'id': c['id'], 'estado': f['estado'], 'fallos': f['fallos'], 'sin_dato': f['sin_dato'],
                         'sospechosos': f['sospechosos']})
            continue
        p = puntuar(notas.get(c['id']), criterios, w)
        if p['total'] is None:
            sin_notas.append({'id': c['id'], 'faltan': p['faltan']})
            continue
        sup.append({'id': c['id'], 'total': p['total'], 'desglose': p['desglose'], 'condicionado': not f['pasa'],
                    'sin_dato': f['sin_dato']})
    sup.sort(key=lambda s: (-s['total'], s['id']))
    for i, s in enumerate(sup):
        s['posicion'] = sup[i - 1]['posicion'] if i > 0 and abs(s['total'] - sup[i - 1]['total']) < EPS else i + 1
    margen = sup[0]['total'] - sup[1]['total'] if len(sup) > 1 else None
    return {'supervivientes': sup, 'eliminados': elim, 'sin_notas': sin_notas, 'fuera_de_lista': fuera,
            'margen': margen, 'empate': margen is not None and margen < EPS,
            'empate_tecnico': margen is not None and margen < EMPATE_TECNICO_PUNTOS}


# ------------------------------------------------------------------ sensibilidad
def totales(ids, notas, criterios, w):
    return {i: puntuar(notas.get(i), criterios, w)['total'] for i in ids}


def ganador(t):
    mx = max(t.values())
    g = sorted(k for k, v in t.items() if abs(v - mx) < EPS)
    return {'ganador': g[0], 'ganadores': g, 'empate': len(g) > 1}


def vuelco_lineal(ids, A, R, x0):
    def S(c, x):
        return x * A[c] + (100 - x) * R[c]
    g = ganador({c: S(c, x0) for c in ids})
    if g['empate']:
        return {'ganador': g['ganador'], 'x': x0, 'delta': 0, 'nuevo_ganador': g['ganadores'][1], 'ya_empatado': True}
    w, mejor = g['ganador'], None
    for c in ids:
        if c == w:
            continue
        dA, dR = A[w] - A[c], R[w] - R[c]
        den = dA - dR
        if abs(den) < 1e-12:
            continue
        x = -100 * dR / den
        if x < -EPS or x > 100 + EPS or abs(x - x0) < EPS:
            continue
        if mejor is None or abs(x - x0) < abs(mejor[0] - x0) - EPS:
            mejor = (x, c)
    if mejor is None:
        return {'ganador': w, 'x': None, 'delta': None, 'nuevo_ganador': None}
    return {'ganador': w, 'x': mejor[0], 'delta': mejor[0] - x0, 'nuevo_ganador': mejor[1]}


def sensibilidad(ids, notas, criterios, w):
    ids = [i for i in ids if puntuar(notas.get(i), criterios, w)['total'] is not None]
    base = totales(ids, notas, criterios, w)
    iguales = {c['id']: 100 / len(criterios) for c in criterios}
    t_ig = totales(ids, notas, criterios, iguales)
    sin = []
    for c in criterios:
        resto = 100 - w[c['id']]
        w2 = {k['id']: 0 if k['id'] == c['id'] else (w[k['id']] / resto * 100 if resto > EPS else 0) for k in criterios}
        t = totales(ids, notas, criterios, w2)
        sin.append({'criterio': c['id'], 'totales': t, 'ganador': ganador(t)})

    def nota(i, c):
        return num(notas[i][c])
    vuelco = []
    for c in criterios:
        wi = w[c['id']]
        A = {i: nota(i, c['id']) / 5 for i in ids}
        R = {i: ((base[i] - wi * nota(i, c['id']) / 5) / (100 - wi) if wi < 100 - EPS else 0) for i in ids}
        v = vuelco_lineal(ids, A, R, wi)
        v.update(criterio=c['id'], peso_actual=wi)
        vuelco.append(v)
    familias = []
    for c in criterios:
        if c['familia'] not in familias:
            familias.append(c['familia'])
    vf = []
    for f in familias:
        WF = sum(w[c['id']] for c in criterios if c['familia'] == f)
        A, R = {}, {}
        for i in ids:
            a = sum(w[c['id']] * nota(i, c['id']) / 5 for c in criterios if c['familia'] == f)
            r = sum(w[c['id']] * nota(i, c['id']) / 5 for c in criterios if c['familia'] != f)
            A[i] = a / WF if WF > EPS else 0
            R[i] = r / (100 - WF) if WF < 100 - EPS else 0
        v = vuelco_lineal(ids, A, R, WF)
        v.update(familia=f, peso_actual=WF)
        vf.append(v)
    return {'ids': ids, 'base': {'totales': base, 'ganador': ganador(base)},
            'iguales': {'totales': t_ig, 'ganador': ganador(t_ig)}, 'sin': sin, 'vuelco': vuelco,
            'vuelco_familia': vf}


# ------------------------------------------------------------------ coherencia
_F = re.I | re.A
PALABRAS_BUS = {
    'spi': re.compile(r'\bSPI\d?\b', re.A), 'i2c': re.compile(r'\bI2C\b', _F),
    'uart': re.compile(r'\bU(S)?ART\b', re.A), 'can': re.compile(r'\bCAN\b', re.A),
    'adc': re.compile(r'\bADC\b', re.A),
    'qspi_sdmmc': re.compile(r'QSPI|QUADSPI|OCTOSPI|SDMMC|SD/MMC|microSD|\bSDIO\b', _F),
    'gpio': re.compile(r'\bGPIO\b', re.A), 'pwm': re.compile(r'\bPWM\b', re.A),
    'timer': re.compile(r'\btimer\b', _F),
}
DISPOSITIVOS = [
    ('IMU', r'\bIMU\b', r'\bIMU\b', 0), ('acelerómetro', r'aceler[oó]metro', r'aceler[oó]metro', re.I),
    ('magnetómetro', r'magnet[oó]metro', r'magnet[oó]metro', re.I), ('barómetro', r'bar[oó]metro', r'bar[oó]metro', re.I),
    ('GNSS', r'\bGNSS\b', r'\bGNSS\b', 0), ('radio', r'\bradio\b', r'radio|telemetr[ií]a|mLRS', re.I),
    ('consola', r'consola', r'consola', re.I), ('servo', r'\bservo\b', r'\bservo\b', re.I),
    ('zumbador', r'zumbador', r'zumbador', re.I), ('giróscopo', r'gir[oó]scopo', r'gir[oó]scopo', re.I),
    ('termistor', r'termistor', r'termistor|NTC', re.I), ('continuidad', r'continuidad', r'continuidad', re.I),
    ('breakwire', r'breakwire', r'breakwire', re.I), ('armado', r'\barmado\b', r'armad', re.I),
    ('PPS', r'\bPPS\b', r'\bPPS\b', 0),
    ('memoria de registro', r'memoria de registro', r'flash NOR|registro|guardar el vuelo', re.I),
]


def _sensores_que(sensores, patron, flags):
    return [s for s in sensores if re.search(patron, f"{s['modelo']} {s['para_que']}", flags | re.A)]


def coherencia(sensores, buses, bus_rationale, ioc=None):
    out = []

    def add(codigo, nivel, mensaje, ref=''):
        out.append({'codigo': codigo, 'nivel': nivel, 'mensaje': mensaje, 'ref': ref})

    if ioc:
        en_ioc = {}
        for p in ioc:
            en_ioc[p['bus']] = en_ioc.get(p['bus'], 0) + (num(p.get('unidades')) or 0)
        for r in buses['recursos']:
            n = en_ioc.get(r['bus'], 0)
            if r['dispositivos'] > 0 and n == 0:
                add('ioc', 'aviso', f"{r['recurso']}: {r['dispositivos']:g} dispositivos y ningún periférico en CubeMX.", r['bus'])
            elif n > 0 and r['dispositivos'] == 0:
                add('ioc', 'aviso', f"{r['recurso']}: periférico en CubeMX ({n:g}) sin sensor que lo justifique.", r['bus'])
            elif 0 < n < r['buses_pedidos']:
                add('ioc', 'aviso', f"{r['recurso']}: CubeMX tiene {n:g}, por debajo de los {r['buses_pedidos']:g} pedidos.", r['bus'])
            elif n > r['total']:
                add('ioc', 'info', f"{r['recurso']}: CubeMX tiene {n:g}, por encima del umbral de {r['total']:g}.", r['bus'])
        for b in en_ioc:
            if b not in buses['porBus']:
                add('ioc', 'info', f'CubeMX habilita «{b}», que no es ningún recurso de bus_rationale.csv.', b)

    for s in sensores:
        j = s.get('justificacion') or ''
        for b, pat in PALABRAS_BUS.items():
            if b != s['bus'] and pat.search(j):
                add('interfaz_incoherente', 'aviso',
                    f"{s['id']} ({s['modelo']}): la justificación menciona {b.upper()} y su bus es {s['bus']}.", s['id'])
        if not (s.get('bahia') or '').strip() and s['bus'] != 'ninguna' and re.search(
                r'otra bah[ií]a|nodo del aerofreno|nodo de la otra', j, re.I):
            add('bahia_dudosa', 'aviso', f"{s['id']} ({s['modelo']}): sin bahía y el texto dice que va en el nodo del "
                                         'aerofreno; hoy se cuenta en la principal.', s['id'])
        if s.get('funcion') != 'independiente' and (num(s.get('cantidad')) or 0) >= 2 and re.search(
                r'no cuelga de mi|electr[oó]nica (de recuperaci[oó]n )?redundante', j, re.I):
            add('doble_cuenta', 'aviso', f"{s['id']} ({s['modelo']}): cantidad {s['cantidad']} e incluye una unidad de la "
                                         f"electrónica redundante (funcion = independiente): posible doble cuenta en {s['bus']}.",
                s['id'])
        if str(s.get('critico') or '').strip().lower() == 'si' and (num(s.get('cantidad')) or 0) < 1:
            add('critico_sin_unidades', 'error', f"{s['id']} ({s['modelo']}): marcado crítico con cantidad {s['cantidad']}.",
                s['id'])
    if buses['sin_bahia']:
        add('bahia_sin_decidir', 'aviso', f"{len(buses['sin_bahia'])} sensores sin bahía: se cuentan como principal provisional.",
            ' '.join(buses['sin_bahia']))

    for b in bus_rationale:
        t = b.get('justificacion') or ''
        for nombre, en_texto, en_sensor, flags in DISPOSITIVOS:
            if re.search(en_texto, t, flags | re.A) and not _sensores_que(sensores, en_sensor, flags):
                add('reparto_obsoleto', 'aviso',
                    f"{b['recurso']}: la justificación menciona «{nombre}» y no hay ningún sensor así en sensors.csv.", b['bus'])
        if re.search(r'IMU redundante|segunda IMU|dos IMU', t, re.I):
            imus = sum(num(s.get('cantidad')) or 0 for s in _sensores_que(sensores, r'\bIMU\b', 0))
            if imus < 2:
                add('reparto_obsoleto', 'aviso', f"{b['recurso']}: la justificación menciona una IMU redundante y "
                                                 f"sensors.csv tiene {imus:g} IMU.", b['bus'])
        m = re.search(r'(\d+)\s+chip-select,\s+uno por dispositivo (\w+)', t, re.I)
        if m:
            r = buses['porBus'].get(m.group(2).lower())
            if r and r['dispositivos'] != int(m.group(1)):
                add('reparto_obsoleto', 'aviso', f"{b['recurso']}: cuenta {m.group(1)} chip-select «uno por dispositivo "
                                                 f"{m.group(2)}» y hay {r['dispositivos']:g} dispositivos {m.group(2)}.",
                    b['bus'])
    return out


# ------------------------------------------------------------------ carga de datos
def cargar(leer_csv):
    """Carga todos los CSV y devuelve el modelo con el que trabajan validate.py y los tests."""
    import os
    from common import DATA
    m = {n: leer_csv(f'{n}.csv') for n in (
        'challenges', 'sensors', 'bus_rationale', 'requirements_inputs', 'requirements_derived_doc', 'thresholds',
        'criteria', 'scale', 'candidates', 'candidate_data', 'scores', 'score_rationale', 'funnel')}
    m['ioc'] = leer_csv('ioc_peripherals.csv') if os.path.exists(os.path.join(DATA, 'ioc_peripherals.csv')) else []
    return m


def datos_por_candidato(candidate_data):
    out = {}
    for f in candidate_data:
        out.setdefault(f['candidato_id'], {})[f['campo']] = f
    return out


def notas_por_candidato(scores):
    out = {}
    for f in scores:
        out.setdefault(f['candidato_id'], {})[f['criterio_id']] = f['nota']
    return out


def entradas(requirements_inputs):
    return {f['id']: num(f['valor']) for f in requirements_inputs}
