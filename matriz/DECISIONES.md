# DECISIONES

Registro de cada decisión de la herramienta y del análisis: qué se decidió, por qué y **qué la invalidaría**.
Lo que es criterio propio se dice. Lo que está pendiente también.

Marco: proceso de análisis de decisiones del NASA Systems Engineering Handbook (NASA/SP-2016-6105 Rev2, §6.8):
definir criterios → identificar alternativas → analizarlas → elegir. Umbrales y pesos se fijan **antes** de mirar a los candidatos.

Tres capas que no se mezclan, más una cuarta:

| Capa | Qué es | Dónde vive |
|---|---|---|
| Requisito derivado | número que sale de un cálculo sobre los datos de misión | `requirements_inputs.csv` → `core.derivarRequisitos` |
| Umbral | mínimo eliminatorio; no se compensa con nada | `thresholds.csv` |
| Peso | cuánto importa un criterio; sale de severidad × no detectabilidad | `criteria.csv` → `core.pesos` (nunca se guarda el %) |
| Nota | 1-5 contra anclas medibles definidas antes | `scale.csv` + `scores.csv` |

**El selector de ST filtra, yo pondero.** Filtrar es objetivo y automatizable. Priorizar exige saber qué falla en vuelo y qué se detecta en tierra.

---

## Estado de los diez puntos de «lo que hay que arreglar»

| # | Punto | Estado | Qué hace la herramienta | Qué falta |
|---|---|---|---|---|
| 1 | Umbrales de buses sin la reserva | **Cerrado y vigilado** | `validate.py` falla si un umbral `derivado_de = bus:X` no es igual a buses pedidos + reserva, y dice «cableado a la cuenta SIN reserva» si coincide con la cuenta sin ella. Test `test_umbral_sin_reserva`. | — |
| 2 | Falta de dato no es aprobado | **Implementado; abierto en los datos** | `aplicarFiltro` separa `no` / `sin_dato` / sospechoso. Nadie pasa el filtro estricto hoy (D-02). | Verificar en CubeMX (T18) todos los candidatos; placa del C5A3ZG (T15); longevidad (T17) con fuente. |
| 3 | El ESP32-S3 cae por familia y encapsulado | **Cerrado** | Test `test_esp32_cae_por_familia`: cae por familia aunque tenga los demás datos. **Ojo:** con tus propios datos también cae por UART (3 < 4, celda Umbrales L9 = NO), no solo por familia y encapsulado. | Decidir si lo cuentas así en la entrevista. |
| 4 | Aviso de interfaz incoherente | **Abierto (1 aviso)** | `coherencia` compara las interfaces citadas en la justificación con el campo `bus`. | S14 (divisor de tensión, bus ADC) menciona I2C: «si se me cae el bus I2C…». Probable falso positivo; revísalo. |
| 5 | Justificación de reparto obsoleta | **Abierto (1 aviso)** | Detecta dispositivos mencionados que no existen, la «IMU redundante» con 1 IMU y los «N chip-select, uno por dispositivo SPI» frente a la cuenta real. | La fila GPIO de `bus_rationale.csv` menciona la IMU redundante que ya no llevas (el propio texto lo dice). Decide si reescribirla. |
| 6 | Sensores en bahía sin decidir | **Abierto** | Solo se suma `bahia = principal`; las vacías cuentan como principal provisional con aviso (D-03). Resalta las tres dudosas porque su propio texto dice que van en el nodo del aerofreno. | Rellenar `bahia` en los 22 sensores con bus. Dudosas: S11 encoder, S12 corriente del servo, S23 servo. |
| 7 | Segundo barómetro contado dos veces | **Abierto (1 aviso)** | Aviso en S05: cantidad 2 y la justificación dice que el segundo va en la electrónica redundante (`funcion = independiente`). | Decidir: cantidad 1 aquí y el segundo dentro de S24, o dejarlo contado a propósito (tu texto de I2C dice que es a propósito). |
| 8 | Redondeo de pesos | **Cerrado** | `redondearA100` (mayor resto) en pantalla y en Markdown: suma exactamente 100,0. Validado. | — |
| 9 | Memoria de registro (18,41 MB) sin umbral | **Abierto (hueco visible)** | `requirements_derived_doc.csv` tiene `enganchado_a` vacío para ese requisito; la interfaz lo marca «HUECO» y el validador avisa. | Es un umbral sobre el **dispositivo de memoria** (flash NOR), no sobre el micro. No existe todavía: falta elegir la memoria y su ficha. |
| 10 | G474RE: 3 SPI, sin SD/MMC, consumo sin publicar | **Ya estaba aplicado en tu libro; abierto en la fuente** | Tu Matriz ya tenía un 2 en periféricos y un 3 (no un 5) en consumo para el G474. Importado tal cual, con `observacion` en `scores.csv`. El selector confirma `Supply Current` vacío para el G474RE. | Sacar el consumo del G474RE de su ficha técnica y sustituir la nota. |

---

## Decisiones de la herramienta

### D-01 · Regla de lista corta: un representante por serie con placa Nucleo
- **Qué:** de las piezas que sobreviven al embudo, un representante por serie, el que tiene placa Nucleo (umbral T15, el único que no se puede filtrar en el selector). Más dos controles que caen a propósito: ESP32-S3 y STM32F411RE (el micro del CATS Vega).
- **Por qué:** 337 piezas son una lista, no una matriz. La regla está declarada antes de puntuar, así que no depende del candidato que ya me gustaba.
- **Aplicación:** el F4 lo representa el F446RE y no el F405RG (sin Nucleo propia y sin QUADSPI). El F405RG entra en `candidates.csv` con `rol = lista_larga` y su motivo, así que se ve en la tabla del filtro pero no puntúa. El U5 lo representa el U5A5ZJ, porque el U575ZI sale en el catálogo con 0 timers (trampa 5).
- **Qué la invalidaría:** que dentro de una serie haya dos piezas con Nucleo y diferencias que cambien el ranking (por ejemplo, con ECC y sin él). Entonces la regla necesita un desempate declarado dentro de la serie.

### D-02 · Filtro estricto y ranking provisional aparte
- **Qué:** el veredicto del filtro es estricto: un `sin_dato` elimina. El ranking tiene un interruptor, activado por defecto, que admite a los **aprobados condicionados**: los que no fallan ningún umbral pero tienen alguno sin dato. Salen marcados con `*`.
- **Por qué:** «Por verificar» en CubeMX está en los 12 candidatos. Sin esta opción el ranking sale vacío y no hay nada que defender; con ella se ve el ranking y a la vez que es provisional.
- **Qué la invalidaría:** nada, mientras haya umbrales sin dato. Cuando T18 esté verificado, el ranking estricto y el provisional coinciden y el interruptor sobra.

### D-03 · Bahía vacía = principal provisional
- **Qué:** `derivarBuses` suma `principal` y las vacías, y descuenta `aerofreno`. Avisa de cuántas vacías hay y cuáles son dudosas.
- **Por qué:** es lo que hacía tu Excel («lo dejo contado aquí hasta cerrar el reparto de bahías») y es el lado seguro: pide más buses, no menos.
- **Qué la invalidaría:** que decidas que la cuenta tiene que ser literal. En ese caso, cambia en `core.js` y en `tools/core.py` la condición `bahia === 'aerofreno'` por `bahia !== 'principal'`.

### D-04 · Buses pedidos y reserva son datos tuyos, no fórmulas
- **Qué:** `bus_rationale.csv` lleva `buses_pedidos` y `reserva` (columnas C y D de tu tabla «De dispositivos a buses»). `dispositivos` y `total` se recalculan.
- **Por qué:** que 3 dispositivos SPI vayan en 2 buses es una decisión de latencia y aislamiento de fallos, no una fórmula. Lo mismo pasa con los 9 GPIO, que incluyen chip-select e interrupciones que no son sensores.
- **Consecuencia:** si pones la IMU a cantidad 2, suben los dispositivos SPI (3 → 4), pero los buses no cambian solos. Salta el aviso de que los chip-select ya no cuadran, y la decisión de reparto la tomas tú.
- **Qué la invalidaría:** tener una regla de reparto automática y defendible (por ejemplo, un bus por dispositivo crítico en tiempo). Se podría añadir como columna `grupo_bus` en `sensors.csv`.

### D-05 · Celdas multivalor del selector: se toma el mínimo (336 frente a 337)
- **Qué:** celdas como «18, 20» (un valor por variante de encapsulado) se leen por su **mínimo**.
- **Por qué:** es conservador y es la regla con la que está hecho `candidates_st_selector.csv` (H563: ADC 18 y 16 + 2 timers).
- **Resultado:** el embudo coincide paso a paso con tu tabla hasta la interfaz de registro (406). En «Canales ADC ≥ 12» sale 377 y no 378: la diferencia es el **STM32H725VG**, cuya celda de ADC de 16 bits dice «2, 14». Tu embudo lo conservó, así que el selector debió de tomar el máximo para esa celda. A partir de ahí la diferencia se arrastra: 377 → 371 → 345 → **336**. Las 10 series salen iguales (H7: 37 frente a 38).
- **Qué la invalidaría:** confirmar en el selector que filtra por cualquiera de los valores. En ese caso habría que cambiar a `max` en `num()` de `tools/import_st_selector.py`, pero solo para ese caso: con `max` en todas las celdas el embudo termina en 342, y con `max` desde el paso del ADC, en 338.

### D-06 · Fecha de consulta del selector
- **Qué:** `fecha_consulta = 2026-09-30`, tomada de la fecha de modificación de `ProductsList.xlsx`. El script lo avisa cada vez que se ejecuta.
- **Por qué:** el export no trae fecha ni URL del filtro, y no quería inventar ninguna de las dos.
- **Pendiente:** confírmala con `python3 tools/import_st_selector.py --fecha AAAA-MM-DD`. La URL es la del selector, no la de un filtro guardado.

### D-07 · Columna `critico` en `sensors.csv`, vacía
- **Qué:** la columna existe para que el validador compruebe «crítico ⇒ cantidad ≥ 1». Está vacía porque tu Inventario no tiene esa columna.
- **Regla:** la criticidad es un escalón (`si` / vacío), **no un peso**: nunca multiplica nada.

### D-08 · Sin openpyxl
- **Qué:** `tools/xlsx_stdlib.py` lee `.xlsx` con `zipfile` + `xml`. El repositorio no tiene ninguna dependencia.
- **Hallazgo:** tu libro **no guarda los resultados de las fórmulas** (las celdas con fórmula no tienen valor cacheado). Es una razón más para recalcular aquí y no depender de que Excel las abra bien.

### D-09 · De dónde sale cada dato de candidato
| Dato | Origen | Etiqueta |
|---|---|---|
| Paramétricos de los STM32 (FPU, buses, ADC, timers, RAM, flash, temperatura, encapsulado, estado, consumo) | `ProductsList.xlsx` (export del selector) | `fuente` |
| Placa (T15), stock y longevidad (T17), CubeMX (T18) | hoja Umbrales, filas 19-21 | `pendiente` |
| Todo el ESP32-S3 | hoja Umbrales, columna K: no está en el catálogo de ST | `pendiente` |

`candidates_st_selector.csv` se usa para cruzar datos. La única diferencia es el CAN del F411RE: el export tiene «-» y el CSV tiene 0 (ver D-10).

### D-10 · «-» en el selector = campo vacío, no cero
- **Qué:** se conserva como «-». El filtro lo trata como 0 para comparar, pero marca la eliminación como **sospechosa** («puede ser un hueco de la base de datos, no de la pieza»), distinta de «el valor no llega».
- **Excepción:** en FPU, «-» es «sin FPU» (núcleos M0/M3), así que no se cuenta como campo vacío en el embudo.
- **Efecto:** el F411RE cae por UART (3 reales: incumplimiento) y por CAN (vacío: sospechoso). `funnel_sospechosos.csv` lista 71 piezas que **solo** caen por campos vacíos, entre ellas el U575ZI (trampa 5).

### D-11 · Umbrales partidos
- La temperatura (fila 17) son dos umbrales: T12 (mínima ≤ −40 °C) y T13 (máxima ≥ 85 °C). El embudo solo filtró la máxima.
- La disponibilidad (fila 20) también son dos: T16 (estado comercial Active, del selector) y T17 (stock y longevidad; el export no trae `Longevity Commitment`).
- Quedan 18 filas en `thresholds.csv` para tus 16 umbrales; `fila_origen` dice de qué fila de la hoja sale cada una.

### D-12 · Umbral de RAM = 128 kB
- Tu hoja dice «≥ requisito del filtro + buffers», sin número. Uso 128 kB, que es la cifra de tu embudo.
- **Qué la invalidaría:** calcular la RAM del filtro (covarianzas 15×15 en float/double + buffers de registro) y que salga más. Ese cálculo sería un requisito derivado más.

### D-13 · El validador tiene tres niveles
| Nivel | Qué recoge | ¿Hace fallar? |
|---|---|---|
| ERROR | lo que rompe el método | siempre |
| PENDIENTE | dato `fuente` sin documento o sin revisión o fecha; dato `pendiente` | solo con `--estricto`: es la lista de tareas, y si el CI estuviera siempre rojo no avisaría de nada |
| AVISO | coherencia | nunca: se prefieren falsos positivos |

### D-14 · Espejo en Python del núcleo
- `tools/core.py` replica `app/core.js`, porque el validador y los tests tienen que correr con python3 solo.
- `tests/test_core.py` ejecuta cada caso contra las dos implementaciones, la de JS con Node si está instalado (en los runners de GitHub viene de serie). Si no hay Node, lo dice y se salta esa parte; no la da por buena.

### D-15 · Las notas se importan como `pendiente`
- Tu Matriz no dice la procedencia de cada nota, así que no la invento. Las anclas y el origen del dato están en `scale.csv`, y la justificación por criterio en `score_rationale.csv`.

### D-16 · Empate técnico: menos de 5 puntos
- Es tu regla (Matriz A22). Es la constante `EMPATE_TECNICO_PUNTOS` de `core.js`.
- Con los pesos del expediente: H743ZI 86,2 · H563ZI 82,4 (a 3,8) · U5A5ZJ 79,5 (a 6,7). Coincide con tu Excel.

### D-17 · Los criterios declaran su parámetro del selector
- `criteria.csv` lleva `selector_param` y `umbral_relacionado`. Si un criterio usa el mismo parámetro que un umbral sin declarar que pondera el **margen** sobre él, el validador falla, porque eso es un umbral disfrazado.
- Así pasa con la precisión: T02 exige FPU, y el criterio pondera la doble precisión frente a la simple.

### D-18 · La frecuencia del filtro no mueve la memoria
- En tu modelo (Requisitos B20), la memoria depende de la **frecuencia de registro** (B14), no de la del filtro (B10).
- Pasar el filtro de 200 a 400 Hz dobla los ciclos (16,2 → 32,4 Mciclos/s) y deja la memoria en 18,41. Pasar el **registro** a 400 Hz la lleva a 36,82.
- El «MB» de la fórmula divide entre 1 048 576: son MiB.

---

## Trampas del acoplamiento con el selector de ST

1. **`Cryptography → ECC` es criptografía de curva elíptica, NO memoria con corrección de errores.** El ECC de memoria pesa el 29,8 % a través de la robustez. `validate.py` falla si el `selector_param` de un criterio de robustez o ECC apunta a Cryptography (test `test_trampa_ecc_criptografia`). Ocurre de verdad en un candidato: el U5A5ZJ tiene «S-ECC» en Cryptography.
2. **USART y UART, y CAN FD y CAN 2.0, son columnas separadas.** El importador las suma en `uart_total` y `can_total`, y guarda aparte las columnas originales.
3. **`Number of Channels` aparece tres veces**, una por grupo de ADC. Se toma el máximo y `condiciones` dice qué grupo lo da.
4. **No hay precio en el selector.** El coste sale del distribuidor; su `selector_param` lo dice.
5. **Timers repartidos en otras columnas.** El U575ZI sale con timers vacíos. Las eliminaciones por campo vacío o a cero se marcan como sospechosas (D-10).
6. **(Nueva) El watchdog del H743ZI no aparece.** En su «Other timer functions» solo pone «LP timer», sin IWDG ni WWDG, cuando la pieza los tiene. Si alguna vez se puntúa la robustez desde el id 977, el H743 sale penalizado por un hueco de la base de datos. Por eso la robustez sigue saliendo de la ficha y de AN5342.

---

## Texto de tus hojas que no encaja en ningún campo

**Leyenda.** Método en orden: Requisitos → Umbrales → Pesos → Escala → Matriz → Sensibilidad. Las etiquetas y su punto débil están en el README. Una frase que conviene conservar: *«Lo que defiendo no es cada número, es el razonamiento que hay detrás y el hecho de haber comprobado cuánto depende la decisión de ellos.»*

**Pesos A16/A17: escalas de la derivación de pesos.**
- Severidad: 1 = molestia de proyecto · 2 = retrabajo · 3 = pierdo datos o rediseño la placa · 4 = vuelo abortado · 5 = pérdida del cohete.
- No detectabilidad: 1 = CubeMX me lo dice el primer día · 2 = se mide en el banco · 3 = solo aparece en un ensayo largo · 4 = solo en el perfil real de vuelo · 5 = no se reproduce en tierra.
- Pesos A19: el método da una frase de defensa por cada peso. Los números de severidad y de no detectabilidad siguen siendo criterio propio.

**Inventario.**
- A37: todo el tráfico de sensores ocupa un 3 % de un SPI a 10 MHz. Los buses no se separan por ancho de banda, sino por latencia y por aislamiento de fallos. La interfaz lo recalcula.
- A51: «dispositivos» no es «buses».
- A53: el conflicto de patillas en CubeMX es un umbral incumplido (T18), no un inconveniente.

**Requisitos A29.** Los ciclos del filtro son una fracción pequeña de los MHz de todos los candidatos, así que la potencia de cálculo no distingue entre ellos. Hay que medirlo con DWT en una Nucleo.

**Escala.**
- A15: las notas 2 y 4 son interpolación; ante la duda, la nota baja con su motivo.
- A17: no se puntúa con los MHz de portada, sino con el % de CPU libre medido.

**Umbrales.**
- A25: el F411RE cae sobre todo por CAN. No es un mal micro: la arquitectura con bus entre bahías pide CAN, y el CATS lo resuelve con un segundo micro.
- A27: la regla de lista corta (D-01).

**Matriz A24 y Sensibilidad A19: la decisión redactada.** Gana el H743ZI (86,2), pero el H563ZI queda a 3,8 y el U5A5ZJ a 6,7: es un empate técnico a tres. Lo que separa al H743 es la FPU de doble precisión (23,8 %). Si el filtro va en un marco local ENU con float, ese criterio se neutraliza y ganan las series con ECC y menos consumo. El desempate declarado es el marco de referencia: una decisión de software, no de catálogo. La herramienta lo cuantifica: el ganador cambia si la familia de fallo silencioso baja del **40,9 %** (hoy 53,6 %), y con los pesos iguales gana el H563ZI.

**Matriz fila 36 y Sensibilidad A21: lo que queda por cerrar.**
1. Medir los ciclos del filtro en una Nucleo con el contador DWT.
2. Medir la corriente media en rampa y sacar de la ficha la del G474RE.
3. Confirmar qué micro vuela hoy Faraday.
4. Decidir si el filtro va en doble precisión o en ENU con float, que es lo que desempata.
5. Confirmar si hay placa Nucleo del C5A3ZG.
