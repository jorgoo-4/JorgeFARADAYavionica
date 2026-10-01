# Aviónica Software — prueba técnica Faraday

Jorge Gallego Broto

Este repositorio contiene mis respuestas a la prueba de Aviónica Software. Cada ejercicio tiene su carpeta con un README que responde a cada apartado y enlaza al código o a los datos en los que se apoya.

## Dónde está cada ejercicio

| Ejercicio | Apartado | Dónde |
|---|---|---|
| **1. Microcontrolador** | a) Elección y justificación | [`ejercicio-1/README.md`](ejercicio-1/README.md#a-elección-del-microcontrolador) |
| | b) Proyecto STM32CubeMX (SPI, I²C, ST-LINK) | [`ejercicio-1/README.md`](ejercicio-1/README.md#b-proyecto-en-stm32cubemx) → proyecto en [`firmware/FARADAYJorge/`](firmware/FARADAYJorge/) |
| **2. Sensores** | a) Sensores imprescindibles y modelos | [`ejercicio-2/README.md`](ejercicio-2/README.md#a-sensores-y-modelos) |
| | b) Inicialización y lectura | [`ejercicio-2/README.md`](ejercicio-2/README.md#b-inicialización-y-lectura) → código en [`firmware/FARADAYJorge/Core/Src/sensors/`](firmware/FARADAYJorge/Core/Src/sensors/) |
| **3. Especialización** | — | en preparación |

## Qué hay en el repositorio

```
ejercicio-1/        respuesta al ejercicio 1
ejercicio-2/        respuesta al ejercicio 2
firmware/           proyecto STM32CubeIDE (STM32H743ZI): configuración de CubeMX + drivers de sensores
matriz/             herramienta con la que elegí el micro: requisitos, umbrales, pesos y sensibilidad
```

- **El firmware** es un único proyecto, como pide el enunciado: el 2b se integra en el mismo proyecto generado en el 1b. Se abre en STM32CubeIDE con *File → Import → STM32CubeMX/STM32CubeIDE Project*, seleccionando `firmware/FARADAYJorge`. Compila sin errores ni avisos.
- **La matriz** es una página web estática con los datos en CSV. Se abre con `python3 -m http.server 8000 --directory matriz` y luego <http://localhost:8000>. Detalles en [`matriz/README.md`](matriz/README.md).

## Lo que no he podido hacer

- **No he probado el firmware en hardware**, porque no tengo la placa. Compila, y cada driver comprueba al arrancar el registro de identificación de su sensor y devuelve un error en vez de bloquearse. Así, el primer día con la Nucleo se ve en la consola qué sensor responde y cuál no.
- **Faltan las páginas de las fichas técnicas.** Los valores de registro están marcados `VERIFICAR` en el código hasta que los contraste con la ficha de cada sensor y anote la página.

## Herramientas

He usado Claude Code (Anthropic) como asistente para programar la herramienta de la matriz, revisar la configuración de CubeMX y escribir los drivers. Los datos, los criterios, los pesos y las decisiones son míos y salen de mis libros de Excel (`matriz/softwareFARADAY *.xlsx`). La matriz incluye una skill de Claude Code (`.claude/skills/matriz-avionica/`) para poder actualizarla cuando cambie un sensor o aparezca un candidato nuevo, sin rellenar datos sin fuente.
