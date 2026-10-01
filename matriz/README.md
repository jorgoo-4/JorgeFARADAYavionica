# Matriz de decisión del microcontrolador

Es la herramienta con la que elegí el micro (ejercicio 1a) y con la que derivé los buses a partir de los sensores (ejercicio 2a). Empezó como dos libros de Excel (`softwareFARADAY 1.xlsx` y `softwareFARADAY 2.xlsx`). Lo pasé a CSV y a una página web para poder recalcularlo y comprobarlo sin depender de que Excel abra bien las fórmulas.

## Abrirla

Desde la raíz del repositorio:

```bash
python3 -m http.server 8000 --directory matriz
```

y abrir <http://localhost:8000>. No hace falta instalar nada. Abierta como `file://` no funciona, porque el navegador no deja leer los CSV.

La página tiene siete secciones:

| Sección | Qué contiene |
|---|---|
| 0. Misión | qué condiciones de vuelo crean qué problemas de aviónica |
| 1. Requisitos | duración, memoria de registro, carga del filtro, resolución numérica… Se recalculan al cambiar las entradas |
| 2. Inventario y buses | de los sensores al número de buses que se le pide al micro, con reserva |
| 3. Embudo | de 1644 referencias STM32 a la lista corta, con el selector de ST |
| 4. Filtro | qué candidato pasa cada umbral, cuál no, y cuál no tiene dato |
| 5. Ranking | puntuación ponderada, con los pesos ajustables |
| 6. Sensibilidad | cuánto tendría que cambiar un peso para que cambie el ganador |

Cada dato lleva su procedencia: ficha técnica, vuelo real, cálculo, medida o criterio propio. Lo que aún no tiene fuente está marcado como pendiente.

## El método

Sigue el proceso de análisis de decisiones del NASA Systems Engineering Handbook (§6.8), con tres cosas separadas:
- **Umbral:** un mínimo eliminatorio, que no se compensa con nada.
- **Peso:** cuánto importa un criterio. Sale de la severidad del fallo que evita multiplicada por su no detectabilidad; no lo pongo a ojo.
- **Nota:** de 1 a 5, contra unas anclas medibles definidas antes de puntuar.

Las decisiones de detalle, con lo que haría cambiar cada una, están en [`DECISIONES.md`](DECISIONES.md).

## Estructura

```
index.html, app/      página (HTML + JS sin dependencias)
data/                 todos los datos en CSV
tools/                importadores (Excel y selector de ST), validador, lectura del .ioc
tests/                pruebas del cálculo
```

Para regenerar y comprobar:

```bash
python3 matriz/tools/import_xlsx.py
```

```bash
python3 matriz/tools/import_st_selector.py --fecha 2026-09-30
```

```bash
python3 matriz/tools/parse_ioc.py
```

```bash
python3 matriz/tools/validate.py
```

```bash
python3 matriz/tests/test_core.py
```

Los dos últimos se ejecutan en cada push (GitHub Actions).

## Mantenimiento con Claude Code

La herramienta está hecha con ayuda de Claude Code. Para actualizarla («añade este micro», «he cambiado de IMU»…) hay una skill en `.claude/skills/matriz-avionica/`. Antes de escribir un dato, la skill pide la ficha técnica, la revisión y la fecha. Al terminar, vuelve a pasar el validador y los tests.
