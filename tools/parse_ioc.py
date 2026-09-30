#!/usr/bin/env python3
"""Lee un proyecto de CubeMX (.ioc) y escribe data/ioc_peripherals.csv.

Uso:  python3 tools/parse_ioc.py [ruta.ioc]
      (por defecto, el primer .ioc que encuentre bajo el directorio del repositorio)

Cuenta, por tipo de recurso de bus_rationale.csv, lo que está habilitado en CubeMX:
  spi / uart / i2c / can / qspi_sdmmc : una unidad por periférico habilitado (Mcu.IPn)
  adc   : una unidad por patilla con señal ADCx_INPy / ADCx_INy
  gpio  : una unidad por patilla GPIO_Input / GPIO_Output / GPXTI
  pwm   : una unidad por canal de timer configurado como PWM Generation
  timer : una unidad por canal de timer configurado como Input Capture
Es una aproximación declarada: no sustituye mirar el pinout en CubeMX.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAIZ, escribir_csv  # noqa: E402

PERIFERICO_BUS = [
    (re.compile(r'^SPI\d+$'), 'spi'), (re.compile(r'^(LP)?U(S)?ART\d+$'), 'uart'),
    (re.compile(r'^I2C\d+$'), 'i2c'), (re.compile(r'^(FD)?CAN\d*$'), 'can'),
    (re.compile(r'^(QUADSPI|OCTOSPI\d*|XSPI\d*|SDMMC\d*|SDIO)$'), 'qspi_sdmmc'),
]


def leer_ioc(ruta):
    kv = {}
    with open(ruta, encoding='utf-8', errors='replace') as f:
        for linea in f:
            linea = linea.rstrip('\n')
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            k, v = linea.split('=', 1)
            kv[k.strip()] = v.replace('\\:', ':').replace('\\#', '#').strip()
    return kv


def analizar(ruta):
    kv = leer_ioc(ruta)
    mcu = kv.get('Mcu.UserName') or kv.get('Mcu.Name', '')
    ips = [kv[k] for k in kv if re.match(r'^Mcu\.IP\d+$', k)]
    senales = {k[:-len('.Signal')]: v for k, v in kv.items() if k.endswith('.Signal')}
    filas = []
    for ip in sorted(ips):
        for pat, bus in PERIFERICO_BUS:
            if pat.match(ip):
                pines = [p for p, s in senales.items() if s.startswith(ip + '_')]
                filas.append({'periferico': ip, 'bus': bus, 'unidades': 1, 'pines': ' '.join(sorted(pines))})
    adc = {}
    for p, s in senales.items():
        m = re.match(r'^(ADC\d*)_INP?\d+', s)
        if m:
            adc.setdefault(m.group(1), []).append(p)
    for ip, pines in sorted(adc.items()):
        filas.append({'periferico': ip, 'bus': 'adc', 'unidades': len(pines), 'pines': ' '.join(sorted(pines))})
    gpio = sorted(p for p, s in senales.items() if s in ('GPIO_Input', 'GPIO_Output') or s.startswith('GPXTI'))
    if gpio:
        filas.append({'periferico': 'GPIO', 'bus': 'gpio', 'unidades': len(gpio), 'pines': ' '.join(gpio)})
    for ip in sorted(i for i in ips if re.match(r'^TIM\d+$', i)):
        pwm = [k for k in kv if k.startswith(ip + '.Channel-PWM Generation')]
        cap = [k for k in kv if k.startswith(ip + '.Channel-Input_Capture')]
        if pwm:
            filas.append({'periferico': ip, 'bus': 'pwm', 'unidades': len(pwm), 'pines': ''})
        if cap:
            filas.append({'periferico': ip, 'bus': 'timer', 'unidades': len(cap), 'pines': ''})
    archivo = os.path.relpath(ruta, RAIZ).replace('\\', '/')
    for f in filas:
        f['ioc'] = archivo
        f['mcu'] = mcu
    return mcu, filas


def main():
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        encontrados = sorted(glob.glob(os.path.join(RAIZ, '**', '*.ioc'), recursive=True))
        if not encontrados:
            raise SystemExit('No hay ningún .ioc en el repositorio.')
        ruta = encontrados[0]
    mcu, filas = analizar(ruta)
    escribir_csv('ioc_peripherals.csv', ['ioc', 'mcu', 'periferico', 'bus', 'unidades', 'pines'], filas)
    print(f'{os.path.basename(ruta)}: {mcu}, {len(filas)} periféricos de bus habilitados')
    for f in filas:
        print(f"  {f['bus']:11s} {f['periferico']:10s} {f['unidades']}  {f['pines']}")


if __name__ == '__main__':
    main()
