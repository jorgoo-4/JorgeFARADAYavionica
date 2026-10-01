#!/usr/bin/env python3
"""Tests del núcleo, con casos escritos a mano.

Uso:  python3 tests/test_core.py        (o python3 -m unittest discover tests)

Cada caso se comprueba contra tools/core.py y, si hay Node en la máquina, también contra
app/core.js con las mismas entradas: así las dos implementaciones no se pueden separar.
Sin Node, las comprobaciones de JS se saltan y se dice (no se dan por buenas).
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import core  # noqa: E402
import validate  # noqa: E402
from common import leer_csv  # noqa: E402

NODE = shutil.which('node')
_JS = r"""
const Core = require(process.argv[1]);
let s = ''; process.stdin.on('data', d => s += d).on('end', () => {
  const q = JSON.parse(s);
  process.stdout.write(JSON.stringify(Core[q.fn].apply(null, q.args)));
});
"""


def js(fn, *args):
    """Llama a Core[fn](...args) de app/core.js. None si no hay Node."""
    if not NODE:
        return None
    r = subprocess.run([NODE, '-e', _JS, os.path.join(RAIZ, 'app', 'core.js')],
                       input=json.dumps({'fn': fn, 'args': args}), capture_output=True, text=True,
                       encoding='utf-8', check=True)
    return json.loads(r.stdout)


M = core.cargar(leer_csv)
DATOS = core.datos_por_candidato(M['candidate_data'])
NOTAS = core.notas_por_candidato(M['scores'])
BUSES = core.derivar_buses(M['sensors'], M['bus_rationale'])
PESOS = core.pesos(M['criteria'])


def filtro(cid_o_datos):
    datos = DATOS.get(cid_o_datos, {}) if isinstance(cid_o_datos, str) else cid_o_datos
    py = core.aplicar_filtro(datos, M['thresholds'], BUSES)
    return py, js('aplicarFiltro', datos, M['thresholds'], BUSES)


def ids(lista):
    return sorted(d['umbral_id'] for d in lista)


class Requisitos(unittest.TestCase):
    ESPERADO = {'duracion_diseno_s': 1508, 'memoria_registro_mb': 18.41, 'ops_paso': 20250, 'mops_s': 4.05,
                'mciclos_s': 16.2, 'resolucion_ecef_m': 0.5, 'vuelta_contador_min': 71.58, 'vueltas_rampa': 5.03}

    def test_los_ocho_derivados(self):
        e = core.entradas(M['requirements_inputs'])
        for r in (core.derivar_requisitos(e), js('derivarRequisitos', e)):
            if r is None:
                continue
            for k, v in self.ESPERADO.items():
                self.assertAlmostEqual(r[k], v, places=2, msg=k)

    def test_a_400_hz(self):
        # En tu modelo los ciclos dependen de la frecuencia del FILTRO y la memoria de la de REGISTRO.
        e = core.entradas(M['requirements_inputs'])
        e['f_filtro_hz'] = 400
        r = core.derivar_requisitos(e)
        self.assertAlmostEqual(r['mciclos_s'], 32.4)
        self.assertAlmostEqual(r['memoria_registro_mb'], 18.41, places=2)
        e['f_registro_hz'] = 400
        self.assertAlmostEqual(core.derivar_requisitos(e)['memoria_registro_mb'], 36.82, places=2)


class Buses(unittest.TestCase):
    # recurso: (dispositivos, pedidos, reserva, total exigido)
    ESPERADO = {'spi': (3, 2, 1, 3), 'uart': (3, 3, 1, 4), 'i2c': (5, 1, 1, 2), 'can': (1, 1, 0, 1),
                'adc': (11, 11, 1, 12), 'pwm': (2, 2, 1, 3), 'gpio': (3, 9, 2, 11), 'qspi_sdmmc': (1, 1, 0, 1),
                'timer': (1, 1, 0, 1)}

    def test_cuentas_con_reserva(self):
        for b in (BUSES, js('derivarBuses', M['sensors'], M['bus_rationale'])):
            if b is None:
                continue
            for bus, (d, p, r, t) in self.ESPERADO.items():
                x = b['porBus'][bus]
                self.assertEqual((x['dispositivos'], x['buses_pedidos'], x['reserva'], x['total']), (d, p, r, t), bus)
            self.assertEqual(len(b['sin_bahia']), 22)  # los 25 menos los 3 sin bus

    def test_imu_a_cantidad_2_mueve_spi(self):
        sens = copy.deepcopy(M['sensors'])
        next(s for s in sens if s['id'] == 'S01')['cantidad'] = '2'
        for b in (core.derivar_buses(sens, M['bus_rationale']), js('derivarBuses', sens, M['bus_rationale'])):
            if b is None:
                continue
            self.assertEqual(b['porBus']['spi']['dispositivos'], 4)
        cods = [a['mensaje'] for a in core.coherencia(sens, core.derivar_buses(sens, M['bus_rationale']),
                                                       M['bus_rationale'])]
        self.assertTrue(any('3 chip-select' in m and '4 dispositivos' in m for m in cods), cods)
        self.assertFalse(any('IMU redundante' in m for m in cods))

    def test_aerofreno_fuera_de_la_cuenta(self):
        sens = copy.deepcopy(M['sensors'])
        for s in sens:
            if s['id'] in ('S11', 'S12', 'S23'):
                s['bahia'] = 'aerofreno'
        b = core.derivar_buses(sens, M['bus_rationale'])
        self.assertEqual(b['porBus']['adc']['dispositivos'], 9)
        self.assertEqual(b['porBus']['pwm']['dispositivos'], 1)
        self.assertIn('pide más que dispositivos', b['porBus']['adc']['avisos'])


class Filtro(unittest.TestCase):
    def test_f411_cae_por_can_y_uart(self):
        for f in filtro('STM32F411RE'):
            if f is None:
                continue
            self.assertEqual(f['estado'], 'ELIMINADO')
            self.assertEqual(ids(f['fallos']), ['T04', 'T06'])
            sosp = {d['umbral_id']: d['sospechoso'] for d in f['fallos']}
            self.assertFalse(sosp['T04'])  # 3 UART reales: no llega
            self.assertTrue(sosp['T06'])   # CAN vacío en el selector: sospechoso

    def test_sin_ningun_dato_nunca_pasa(self):
        for f in filtro({}):
            if f is None:
                continue
            self.assertFalse(f['pasa'])
            self.assertEqual(f['estado'], 'SIN_DATO')
            self.assertEqual(len(f['sin_dato']), len(M['thresholds']))
            self.assertEqual(f['fallos'], [])
        vacio = {'id': 'VACIO', 'rol': 'candidato'}
        r = core.ranking([vacio], {'VACIO': core.aplicar_filtro({}, M['thresholds'], BUSES)}, {}, M['criteria'], PESOS)
        self.assertEqual([e['id'] for e in r['eliminados']], ['VACIO'])
        self.assertEqual(r['supervivientes'], [])

    def test_esp32_cae_por_familia(self):
        for f in filtro('ESP32-S3'):
            if f is None:
                continue
            self.assertIn('T01', ids(f['fallos']))
            self.assertIn('T14', ids(f['fallos']))
            self.assertFalse(next(d for d in f['fallos'] if d['umbral_id'] == 'T01')['sospechoso'])
        # aunque tuviera todos los demás datos buenos: los del H743 con otra familia
        datos = copy.deepcopy(DATOS['STM32H743ZI'])
        datos['familia']['valor'] = 'Xtensa LX7, no es ST'
        for f in filtro(datos):
            if f is None:
                continue
            self.assertEqual(ids(f['fallos']), ['T01'])
            self.assertEqual(f['estado'], 'ELIMINADO')

    def test_campo_vacio_es_sospechoso_no_incumplimiento(self):
        datos = copy.deepcopy(DATOS['STM32H743ZI'])
        datos['timers_total']['valor'] = '-'
        for f in filtro(datos):
            if f is None:
                continue
            d = next(x for x in f['fallos'] if x['umbral_id'] == 'T09')
            self.assertTrue(d['sospechoso'])
            self.assertEqual(ids(f['sospechosos']), ['T09'])
        datos['timers_total']['valor'] = '2'
        for f in filtro(datos):
            if f is None:
                continue
            d = next(x for x in f['fallos'] if x['umbral_id'] == 'T09')
            self.assertFalse(d['sospechoso'])

    def test_cubemx_sin_verificar_es_sin_dato(self):
        f, _ = filtro('STM32H743ZI')
        self.assertEqual(f['estado'], 'SIN_DATO')
        self.assertIn('T18', ids(f['sin_dato']))


class Puntuacion(unittest.TestCase):
    def test_pesos_derivados(self):
        self.assertAlmostEqual(sum(PESOS.values()), 100)
        self.assertAlmostEqual(PESOS['robustez'], 25 / 84 * 100)
        self.assertAlmostEqual(PESOS['precision'], 20 / 84 * 100)
        red = core.redondear_a_100(PESOS, 1)
        self.assertEqual(round(sum(red.values()), 6), 100)
        for k in PESOS:
            self.assertLess(abs(red[k] - PESOS[k]), 0.1 + 1e-9)
        j = js('redondearA100', PESOS, 1)
        if j is not None:
            self.assertEqual(j, red)

    def test_regresion_contra_el_excel(self):
        filtros = {c['id']: core.aplicar_filtro(DATOS.get(c['id'], {}), M['thresholds'], BUSES)
                   for c in M['candidates']}
        r = core.ranking(M['candidates'], filtros, NOTAS, M['criteria'], PESOS, provisional=True)
        tot = {s['id']: s['total'] for s in r['supervivientes']}
        self.assertEqual(r['supervivientes'][0]['id'], 'STM32H743ZI')
        self.assertAlmostEqual(tot['STM32H743ZI'], 86.19, places=2)
        self.assertAlmostEqual(tot['STM32H743ZI'] - tot['STM32H563ZI'], 3.81, places=2)
        self.assertAlmostEqual(tot['STM32H743ZI'] - tot['STM32U5A5ZJ'], 6.67, places=2)
        self.assertTrue(r['empate_tecnico'])
        self.assertTrue(all(s['condicionado'] for s in r['supervivientes']))
        estricto = core.ranking(M['candidates'], filtros, NOTAS, M['criteria'], PESOS)
        self.assertEqual(estricto['supervivientes'], [])  # CubeMX sin verificar: nadie pasa todavía

    def test_empate(self):
        crit = [{'id': 'a', 'severidad': '2', 'no_detectabilidad': '2', 'familia': 'fallo_silencioso'},
                {'id': 'b', 'severidad': '2', 'no_detectabilidad': '2', 'familia': 'programa_equipo'}]
        notas = {'X': {'a': '5', 'b': '1'}, 'Y': {'a': '1', 'b': '5'}}
        cands = [{'id': 'X', 'rol': 'candidato'}, {'id': 'Y', 'rol': 'candidato'}]
        pasa = {'pasa': True, 'estado': 'PASA', 'fallos': [], 'sin_dato': [], 'sospechosos': []}
        filtros = {'X': pasa, 'Y': pasa}
        w = core.pesos(crit)
        for r in (core.ranking(cands, filtros, notas, crit, w), js('ranking', cands, filtros, notas, crit, w)):
            if r is None:
                continue
            self.assertTrue(r['empate'])
            self.assertEqual([s['posicion'] for s in r['supervivientes']], [1, 1])
            self.assertAlmostEqual(r['supervivientes'][0]['total'], 60)


class Sensibilidad(unittest.TestCase):
    CRIT = [{'id': 'a', 'severidad': '3', 'no_detectabilidad': '2', 'familia': 'fallo_silencioso'},
            {'id': 'b', 'severidad': '2', 'no_detectabilidad': '2', 'familia': 'programa_equipo'}]
    NOTAS = {'X': {'a': '5', 'b': '1'}, 'Y': {'a': '1', 'b': '5'}}

    def test_punto_de_vuelco_a_mano(self):
        # Pesos 60/40. X = 60·5/5 + 40·1/5 = 68; Y = 60·1/5 + 40·5/5 = 52.
        # Con a = x y b = 100 − x: X = x + (100−x)/5, Y = x/5 + (100−x). Igualando: x = 50.
        w = core.pesos(self.CRIT)
        for s in (core.sensibilidad(['X', 'Y'], self.NOTAS, self.CRIT, w),
                  js('sensibilidad', ['X', 'Y'], self.NOTAS, self.CRIT, w)):
            if s is None:
                continue
            self.assertEqual(s['base']['ganador']['ganador'], 'X')
            va = next(v for v in s['vuelco'] if v['criterio'] == 'a')
            self.assertAlmostEqual(va['x'], 50)
            self.assertAlmostEqual(va['delta'], -10)
            self.assertEqual(va['nuevo_ganador'], 'Y')
            vb = next(v for v in s['vuelco'] if v['criterio'] == 'b')
            self.assertAlmostEqual(vb['x'], 50)
            self.assertAlmostEqual(vb['delta'], 10)
            vf = next(v for v in s['vuelco_familia'] if v['familia'] == 'fallo_silencioso')
            self.assertAlmostEqual(vf['x'], 50)

    def test_familia_fallo_silencioso_con_mis_datos(self):
        # A mano: A_H743 = 1, A_H563 = 185/225; R_H743 = 137/195, R_H563 = 161/195 -> y = 40,91 %
        ids_ = [c['id'] for c in M['candidates'] if c['id'] in NOTAS]
        s = core.sensibilidad(ids_, NOTAS, M['criteria'], PESOS)
        vf = next(v for v in s['vuelco_familia'] if v['familia'] == 'fallo_silencioso')
        self.assertEqual(vf['ganador'], 'STM32H743ZI')
        self.assertEqual(vf['nuevo_ganador'], 'STM32H563ZI')
        self.assertAlmostEqual(vf['x'], 100 * (137 - 161) / 195 / ((137 - 161) / 195 - (1 - 185 / 225)), places=6)
        self.assertEqual(s['iguales']['ganador']['ganador'], 'STM32H563ZI')


class Validador(unittest.TestCase):
    def validar(self, m):
        inf = validate.Informe()
        validate.validar(m, inf)
        return inf

    def test_datos_actuales_sin_errores(self):
        self.assertEqual(self.validar(M).errores, [])

    def test_trampa_ecc_criptografia(self):
        m = copy.deepcopy(M)
        next(c for c in m['criteria'] if c['id'] == 'robustez')['selector_param'] = 'Cryptography (ECC)'
        self.assertTrue(any('Cryptography' in e for e in self.validar(m).errores))

    def test_umbral_sin_reserva(self):
        m = copy.deepcopy(M)
        next(u for u in m['thresholds'] if u['id'] == 'T03')['minimo'] = '2'
        self.assertTrue(any('SIN reserva' in e for e in self.validar(m).errores))

    def test_peso_guardado_en_csv(self):
        m = copy.deepcopy(M)
        m['criteria'][0]['peso'] = '11.9'
        self.assertTrue(any('no se guarda' in e for e in self.validar(m).errores))


class Repositorio(unittest.TestCase):
    def test_js_sin_datos_cableados(self):
        for f in ('core.js', 'ui.js'):
            ruta = os.path.join(RAIZ, 'app', f)
            if os.path.exists(ruta):
                with open(ruta, encoding='utf-8') as fh:
                    texto = fh.read()
                for prohibido in ('STM32', 'ESP32', 'Nucleo', 'ICM-42686'):
                    self.assertNotIn(prohibido, texto, f'{f} contiene «{prohibido}»: los datos van en CSV')

    def test_sin_dependencias(self):
        for f in ('package.json', 'requirements.txt', 'node_modules'):
            self.assertFalse(os.path.exists(os.path.join(RAIZ, f)), f)

    def test_embudo_se_regenera(self):
        export = os.path.join(RAIZ, 'ProductsList.xlsx')
        if not os.path.exists(export):
            self.skipTest('no está el export del selector')
        import import_st_selector as st
        pasos, _, _, _ = st.embudo(st.leer_export(export), M['thresholds'], M['candidates'])
        self.assertEqual([p['piezas_restantes'] for p in pasos],
                         [int(p['piezas_restantes']) for p in M['funnel']])


@unittest.skipIf(NODE is None, 'no hay Node: no se contrasta core.js con tools/core.py')
class EquivalenciaJS(unittest.TestCase):
    def test_filtro_de_todos_los_candidatos(self):
        for c in M['candidates']:
            py, j = filtro(c['id'])
            self.assertEqual(py['estado'], j['estado'], c['id'])
            self.assertEqual(ids(py['fallos']), ids(j['fallos']), c['id'])
            self.assertEqual(ids(py['sin_dato']), ids(j['sin_dato']), c['id'])
            self.assertEqual(ids(py['sospechosos']), ids(j['sospechosos']), c['id'])

    def test_sensibilidad_y_coherencia(self):
        ids_ = [c['id'] for c in M['candidates'] if c['id'] in NOTAS]
        py = core.sensibilidad(ids_, NOTAS, M['criteria'], PESOS)
        j = js('sensibilidad', ids_, NOTAS, M['criteria'], PESOS)
        for a, b in zip(py['vuelco'] + py['vuelco_familia'], j['vuelco'] + j['vuelco_familia']):
            self.assertEqual(a['nuevo_ganador'], b['nuevo_ganador'])
            if a['x'] is not None:
                self.assertAlmostEqual(a['x'], b['x'], places=9)
        cp = core.coherencia(M['sensors'], BUSES, M['bus_rationale'], M['ioc'])
        cj = js('coherencia', M['sensors'], BUSES, M['bus_rationale'], M['ioc'])
        self.assertEqual(sorted((a['codigo'], a['ref']) for a in cp), sorted((a['codigo'], a['ref']) for a in cj))


if __name__ == '__main__':
    if NODE is None:
        print('AVISO: no hay Node en esta máquina; solo se prueba tools/core.py.')
    unittest.main(verbosity=2)
