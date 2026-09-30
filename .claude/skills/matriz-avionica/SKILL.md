---
name: matriz-avionica
description: Mantener la matriz de decisión de aviónica (data/*.csv). Úsala cuando el usuario pida añadir o quitar un microcontrolador candidato, cambiar un sensor o su cantidad, mover un sensor de bahía (principal / aerofreno), cambiar un requisito de misión, un umbral, un criterio, un peso (severidad o no detectabilidad) o una nota, o actualizar datos del selector de ST o de CubeMX. Ejemplos: «añade el STM32H563 a los candidatos», «he cambiado de IMU», «el aerofreno pasa a la bahía principal».
---

# Matriz de aviónica: cómo cambiar datos sin inventar nada

El repositorio separa cuatro capas que no se mezclan: requisitos derivados, umbrales (eliminatorios), pesos (derivados de severidad × no detectabilidad) y notas (1-5 contra anclas). Antes de tocar nada, lee `DECISIONES.md`.

## Reglas duras

1. **No inventes datos.** Antes de escribir un valor, una fuente, una revisión, una fecha o una nota, pregunta por:
   - la ficha técnica o el documento (nombre y página),
   - la revisión del documento,
   - la fecha de consulta.

   Si el usuario no da el valor, **niégate a rellenarlo**. Déjalo vacío (es `sin_dato`, que nunca aprueba) o con `etiqueta = pendiente`, y dilo.
2. Las etiquetas válidas son `fuente`, `vuelo`, `calculo`, `medido`, `criterio_propio` y `pendiente`, combinables con `+`. No presentes `criterio_propio` como `fuente`.
3. Los datos de consumo y temperatura llevan siempre `condiciones`.
4. **Nunca** guardes el peso en %: se deriva. Nunca conviertas un umbral (número de buses, FPU, temperatura, encapsulado) en criterio ponderado. Lo que se pondera es el margen sobre el umbral.
5. **Nunca** cablees la robustez al campo `Cryptography` del selector: su «ECC» es criptografía de curva elíptica, no memoria con corrección de errores.
6. La criticidad de un sensor (`critico`) es un escalón, no un peso: no la multipliques por nada.
7. No corrijas incoherencias en silencio. Enséñalas.
8. No toques `app/*.js` para añadir datos. Si crees que hace falta, dilo y explica por qué.

## Procedimiento

1. **Pregunta** por la procedencia (regla 1) y espera la respuesta.
2. **Edita las filas respetando el esquema:**
   - **Candidato nuevo:** una fila en `data/candidates.csv` (`rol` = `candidato`, `control` o `lista_larga`, con `motivo_rol` si es lista larga), sus filas en `data/candidate_data.csv` (formato largo) y sus notas en `data/scores.csv`.
     - Si la pieza está en el catálogo de ST (`en_catalogo_st = si`), **no metas los datos paramétricos a mano**. Recuerda al usuario que descargue el export actualizado del selector y ejecute `python3 tools/import_st_selector.py --fecha AAAA-MM-DD`. Así se reejecuta el embudo y se comprueba que la pieza sobrevive al filtro.
     - Comprueba también la regla de lista corta (DECISIONES D-01): un representante por serie, el que tiene placa Nucleo. Si el candidato nuevo es el segundo de su serie, pregunta cuál representa a la serie y por qué.
   - **Sensor:** edita `data/sensors.csv` (`bus` en minúsculas: `spi`, `i2c`, `uart`, `can`, `qspi_sdmmc`, `adc`, `gpio`, `pwm`, `timer`, `ninguna`; `bahia` = `principal`, `aerofreno` o vacía).
   - **Criterio nuevo:** una fila en `data/criteria.csv` (con `familia`, `selector_param` y `umbral_relacionado` si pondera el margen sobre un umbral), otra en `data/scale.csv` (anclas 5 / 3 / 1 medibles), su justificación en `data/score_rationale.csv` y las notas.
3. **Recalcula lo derivado:**
   - Si cambió `sensors.csv`, mira en la interfaz o con `tools/core.py` los dispositivos por bus. Si el reparto cambia, actualiza `buses_pedidos` y `reserva` en `data/bus_rationale.csv` (es decisión del usuario: pregunta) y el `minimo` de los umbrales `derivado_de = bus:*` en `data/thresholds.csv`, que tiene que ser **buses + reserva**.
   - Si cambió `requirements_inputs.csv`, los derivados se recalculan solos. Revisa si algún umbral depende de ellos.
4. **Valida:**
   ```bash
   python3 tools/validate.py
   ```
   ```bash
   python3 tests/test_core.py
   ```
   Si falla un test de regresión (por ejemplo, la regresión contra el Excel) porque el usuario ha cambiado datos a propósito, dilo y pregunta antes de actualizar el valor esperado.
5. **Informa**, en este orden:
   - qué filas cambiaron;
   - qué cambió en el ranking: ganador, margen y si hay empate técnico (< 5 puntos);
   - qué cambió en la sensibilidad: punto de vuelco por familia, sobre todo `fallo_silencioso`, y ganador con pesos iguales;
   - qué queda pendiente de fuente (salida de `validate.py`, con `--detalle` si hace falta) y qué avisos nuevos hay.
