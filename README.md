# Matriz de decisión de la aviónica

Herramienta para defender la elección de sensores y de microcontrolador de un cohete experimental de alta altitud (apogeo > 100 km, Mach ~5,2, vuelo de referencia de 754 s, hasta 6 h en rampa).

Es el análisis de `softwareFARADAY 1.xlsx` y `softwareFARADAY 2.xlsx` convertido en algo que se recalcula, se comprueba y se puede actualizar dentro de dos años sin depender de Excel.

**El selector de ST filtra, yo pondero.**

## Uso

```bash
python3 -m http.server 8000
```

Abre <http://localhost:8000>. No hace falta instalar nada. Abierta como `file://` no funciona, porque el navegador no deja leer los CSV. En GitHub Pages funciona sin configuración.

La página tiene siete bloques:

| Bloque | Qué hace |
|---|---|
| 0. Misión | trazabilidad condición de vuelo → problema → implicación |
| 1. Requisitos | los 10 datos de entrada son editables y los derivados se recalculan al vuelo, junto con el % de CPU del filtro en cada candidato |
| 2. Inventario y buses | sensores (cantidad y bahía se pueden cambiar para probar), derivación a buses con reserva, y avisos de coherencia con CubeMX y de los puntos 4 a 7 |
| 3. Embudo | cómo se pasa de 1644 referencias STM32 a la lista corta, con la regla declarada y las eliminaciones sospechosas |
| 4. Filtro | pasa / no / sin dato / sospechoso por umbral y candidato, y lo que le falta a cada uno |
| 5. Ranking | barras de peso × nota por familia, deslizadores de peso con renormalización, y las anclas a la vista junto a las notas |
| 6. Sensibilidad | pesos iguales, leave-one-out y punto de vuelco por criterio y por familia, en texto llano |

El botón **Exportar a Markdown** descarga el estado actual. Los pesos se redondean con reparto del resto, así que suman exactamente 100.

Los cambios hechos en pantalla no se guardan: lo definitivo se edita en `data/*.csv`.

## Etiquetas de procedencia

Cada dato lleva una o varias, unidas con `+` (por ejemplo `vuelo+calculo`).

| Etiqueta | Qué es | Cómo se defiende | Punto débil |
|---|---|---|---|
| `fuente` | ficha técnica, nota de aplicación, norma o artículo | se cita el documento y la página | cifras del fabricante en condiciones ideales: hay que leer las condiciones de medida |
| `vuelo` | lo que pasó en un vuelo o competición real | ocurrió, con informe público | era otro cohete: hay que argumentar por qué aplica |
| `calculo` | número que se rehace en la pizarra | se repite delante del entrevistador | solo vale si las hipótesis son buenas |
| `medido` | medido en hardware propio | el dato más fuerte | — |
| `criterio_propio` | razonamiento de ingeniería sin fuente única | se explica y se dice qué pasa si cambia | es opinión: nunca se presenta como fuente |
| `pendiente` | procedencia sin identificar | — | es la lista de tareas |

En pantalla, `PENDIENTE` va en rojo macizo. Un dato `fuente` sin documento o sin revisión lleva además un recuadro discontinuo («sin documento» / «sin revisión»).

## Estructura

```
index.html              la página (sin build, sin framework, sin CDN)
app/core.js             requisitos, buses, filtro, puntuación, sensibilidad, coherencia (sin DOM)
app/ui.js               pinta la página a partir de data/*.csv
app/csv.js              lector de CSV
app/style.css
data/                   todos los datos (ver abajo)
tools/import_xlsx.py    importación única de los dos libros de Excel
tools/import_st_selector.py  datos del selector de ST y embudo (el único sitio que lee algo de fuera)
tools/parse_ioc.py      proyecto de CubeMX -> data/ioc_peripherals.csv
tools/validate.py       validador (errores, pendientes, avisos)
tools/core.py           espejo en Python de app/core.js para el validador y los tests
tools/common.py, tools/xlsx_stdlib.py
tests/test_core.py      casos escritos a mano, contra core.py y core.js
.claude/skills/matriz-avionica/SKILL.md
.github/workflows/validate.yml
```

### Datos

| Archivo | Contenido | Origen |
|---|---|---|
| `challenges.csv` | misión → problema → implicación | FARADAY 1 |
| `sensors.csv` | inventario (`funcion`, `bus`, `bahia`, `critico`) | Inventario |
| `bus_rationale.csv` | buses pedidos, reserva y justificación por recurso | Inventario, filas 41-49 |
| `requirements_inputs.csv` | los 10 datos de entrada | Requisitos, filas 6-15 |
| `requirements_derived_doc.csv` | cómo se obtiene cada derivado y a qué se engancha | Requisitos, filas 19-27 |
| `thresholds.csv` | umbrales, operador, derivación y `selector_param` | Umbrales + mapeo al selector |
| `criteria.csv` | severidad, no detectabilidad y familia (**el % no se guarda**) | Pesos |
| `scale.csv` | anclas 5 / 3 / 1 | Escala |
| `candidates.csv` | lista corta, controles y lista larga con motivo | Umbrales + selector |
| `candidate_data.csv` | formato largo: un dato por fila, con procedencia | selector de ST + Umbrales |
| `scores.csv`, `score_rationale.csv` | notas y su justificación | Matriz |
| `funnel.csv`, `funnel_series.csv`, `funnel_sospechosos.csv` | el embudo regenerado | selector de ST |
| `ioc_peripherals.csv` | periféricos habilitados en CubeMX | `.ioc` |

## Cómo se actualiza

| Cambio | Qué hacer | ¿Toca `.js`? |
|---|---|---|
| Añadir un microcontrolador | una fila en `candidates.csv`, sus filas en `candidate_data.csv` (si está en el catálogo de ST, con `import_st_selector.py`) y en `scores.csv` | no |
| Añadir un criterio ponderado | una fila en `criteria.csv` y otra en `scale.csv` (más sus notas y su justificación) | no |
| Añadir un umbral | una fila en `thresholds.csv` y el campo en `candidate_data.csv` | no |
| Cambiar un sensor o su bahía | editar `sensors.csv`; si cambia el reparto, también `bus_rationale.csv` y el `minimo` del umbral | no |

Para regenerar desde las fuentes:

```bash
python3 tools/import_xlsx.py
```

```bash
python3 tools/import_st_selector.py --fecha AAAA-MM-DD
```

```bash
python3 tools/parse_ioc.py
```

Para comprobar:

```bash
python3 tools/validate.py
```

```bash
python3 tests/test_core.py
```

`validate.py --estricto` hace fallar también por los datos pendientes de fuente; está pensado para el día antes de la entrevista. `--detalle` los lista uno a uno.

Con Claude Code, la skill `matriz-avionica` guía estos cambios y se niega a rellenar valores sin fuente.

## Restricciones

- Sin `npm`, sin `package.json`, sin `node_modules`, sin `requirements.txt`, sin CDN, sin backend, sin telemetría.
- Scripts en Python 3 con librería estándar; ni siquiera openpyxl (DECISIONES.md, D-08).
- Node solo se usa, si está instalado, para contrastar `core.js` en los tests.

Cada decisión, con su motivo, qué la invalidaría y el estado de los puntos abiertos, está en [DECISIONES.md](DECISIONES.md).
