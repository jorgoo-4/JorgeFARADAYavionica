# Aviónica Software — prueba técnica Faraday

Jorge Gallego Broto

Este repositorio contiene mis respuestas a la prueba de Aviónica Software. Cada ejercicio tiene su carpeta con un README que responde a cada apartado y enlaza al código o a los datos en los que se apoya.

Mi documento de respuestas completo, en PDF, está en [`docs/Resolucion_ejercicios_FARADAY.pdf`](docs/Resolucion_ejercicios_FARADAY.pdf). Su contenido está repartido y ordenado en los README de cada ejercicio. Las fuentes consultadas están en [`docs/BIBLIOGRAFIA.md`](docs/BIBLIOGRAFIA.md).

## Dónde está cada ejercicio

| Ejercicio | Apartado | Dónde |
|---|---|---|
| **Contexto** | Misión y problemas de vuelo | [`ejercicio-1/README.md`](ejercicio-1/README.md#contexto-de-la-misión) |
| **1. Microcontrolador** | a) Elección y justificación | [`ejercicio-1/README.md`](ejercicio-1/README.md#a-elección-del-microcontrolador) |
| | b) Proyecto STM32CubeMX (SPI, I²C, ST-LINK) | [`ejercicio-1/README.md`](ejercicio-1/README.md#b-proyecto-en-stm32cubemx) → proyecto en [`firmware/FARADAYJorge/`](firmware/FARADAYJorge/) |
| **2. Sensores** | a) Sensores imprescindibles, modelos y por qué cada uno | [`ejercicio-2/README.md`](ejercicio-2/README.md#a-sensores-y-modelos) |
| | b) Inicialización y lectura | [`ejercicio-2/README.md`](ejercicio-2/README.md#b-inicialización-y-lectura) → código en [`firmware/FARADAYJorge/Core/Src/sensors/`](firmware/FARADAYJorge/Core/Src/sensors/) |
| **3. Especialización** | Opción III: FreeRTOS (tareas, prioridades y esqueletos) | [`ejercicio-3/README.md`](ejercicio-3/README.md) → proyecto en [`firmware/FARADAYJorge_Ej3/`](firmware/FARADAYJorge_Ej3/) |
| **Proyectos personales** | Resumen de mis proyectos tecnológicos | [ver el PDF](https://jorgoo-4.github.io/JorgeFARADAYavionica/Ejercicio-Personal/Proyectos_tecnologicos_Jorge_Gallego.pdf) · [`Ejercicio-Personal/`](Ejercicio-Personal/) |

## Qué hay en el repositorio

```
docs/                documentos de respuestas (PDF) y bibliografía
ejercicio-1/         respuesta al ejercicio 1
ejercicio-2/         respuesta al ejercicio 2
ejercicio-3/         respuesta al ejercicio 3 (opción III, FreeRTOS)
Ejercicio-Personal/  resumen de mis proyectos tecnológicos (PDF)
firmware/            proyectos STM32CubeIDE (STM32H743ZI)
  FARADAYJorge/        ejercicios 1 y 2: CubeMX + drivers de sensores
  FARADAYJorge_Ej3/    ejercicio 3: el mismo proyecto con FreeRTOS
matriz/              herramienta con la que elegí el micro: requisitos, umbrales, pesos y sensibilidad
```

- **El firmware** son dos proyectos de STM32CubeIDE. `FARADAYJorge` contiene los ejercicios 1 y 2: como pide el enunciado, el 2b va en el mismo proyecto generado en el 1b. `FARADAYJorge_Ej3` es una copia con FreeRTOS para el ejercicio 3, para no tocar la entrega anterior. Se abren con *File → Import → STM32CubeMX/STM32CubeIDE Project*. Los dos compilan sin errores.
- **La matriz** es una página web estática con los datos en CSV. **Se ve en línea en <https://jorgoo-4.github.io/JorgeFARADAYavionica/matriz/>.** En local se abre con doble clic en `matriz/index.html`, sin instalar nada (también sirve `python3 -m http.server 8000 --directory matriz`). Detalles en [`matriz/README.md`](matriz/README.md).

## Proyectos personales

[**Ver el PDF**](https://jorgoo-4.github.io/JorgeFARADAYavionica/Ejercicio-Personal/Proyectos_tecnologicos_Jorge_Gallego.pdf) resume mis proyectos tecnológicos. Pesa 9,4 MB y el visor de GitHub no lo muestra; el enlace lo abre en el navegador. También se puede descargar desde [`Ejercicio-Personal/`](Ejercicio-Personal/).
- **Evaluación interna de Física (Bachillerato Internacional):** número de nodos de sustentación de un levitador acústico TinyLev de 40 kHz en función del voltaje.
- **Monografía de Física (Bachillerato Internacional):** la modulación Chirp Spread Spectrum en LoRa. Medí alcance, sensibilidad y tolerancia al efecto Doppler según el factor de dispersión, con dos módulos LoRa y ESP32.
- **Sport Lines** (ganador del SIE Huesca 2025): líneas de pista deportiva reconfigurables con tinta electrónica.
- **Guiado para atletas con discapacidad visual** (SIE Huesca 2024): sensores piezoeléctricos y aviso sonoro por conducción ósea.

El PDF es solo un resumen. La monografía y la evaluación interna completas no están publicadas aquí: por las normas del Bachillerato Internacional las envío por correo electrónico.

## Lo que no he podido hacer

- **No he probado el firmware en hardware**, porque no tengo la placa. Compila, y cada driver comprueba al arrancar el registro de identificación de su sensor y devuelve un error en vez de bloquearse. Así, el primer día con la Nucleo se ve en la consola qué sensor responde y cuál no.
- **Faltan las páginas de las fichas técnicas.** Los valores de registro están marcados `VERIFICAR` en el código hasta que los contraste con la ficha de cada sensor y anote la página.

## Herramientas

He usado Claude Code (Anthropic) como asistente para programar la herramienta de la matriz, revisar la configuración de CubeMX, escribir los drivers y preparar el proyecto de FreeRTOS. Los datos, los criterios, los pesos y las decisiones son míos y salen de mis libros de Excel (`matriz/softwareFARADAY *.xlsx`). La matriz incluye una skill de Claude Code (`.claude/skills/matriz-avionica/`) para poder actualizarla cuando cambie un sensor o aparezca un candidato nuevo, sin rellenar datos sin fuente.
