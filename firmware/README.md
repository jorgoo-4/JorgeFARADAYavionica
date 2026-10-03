# Firmware — ordenador de vuelo (STM32H743ZI)

Dos proyectos de STM32CubeIDE:

- **`FARADAYJorge/`**: ejercicios **1b** (configuración en CubeMX) y **2b** (inicialización y lectura de sensores).
- **`FARADAYJorge_Ej3/`**: ejercicio **3**. Es una copia del anterior con FreeRTOS: tareas, colas, mutex y event flags. Explicado en [`../ejercicio-3/README.md`](../ejercicio-3/README.md).

Lo que sigue describe `FARADAYJorge/`.

- **Abrirlo:** en STM32CubeIDE, *File → Import → STM32CubeMX/STM32CubeIDE Project* y seleccionar `firmware/FARADAYJorge`.
- **Compilar:** *Project → Build* (Ctrl+B).
- **Configuración:** `FARADAYJorge.ioc`. Se puede abrir con STM32CubeMX y regenerar: el código propio está dentro de los bloques `USER CODE` o en archivos aparte, así que se conserva.

| Qué | Dónde |
|---|---|
| Configuración del micro (relojes, pines, periféricos) | `FARADAYJorge.ioc`, explicada en [`../ejercicio-1/README.md`](../ejercicio-1/README.md#b-proyecto-en-stm32cubemx) |
| Drivers de sensores | `FARADAYJorge/Core/Src/sensors/` y `Core/Inc/sensors/`, explicados en [`../ejercicio-2/README.md`](../ejercicio-2/README.md#b-inicialización-y-lectura) |
| Punto de entrada | `FARADAYJorge/Core/Src/main.c`: `sensors_init()` y `sensors_read_all()` en los bloques `USER CODE` |
| Cierre del conmutador analógico de PC2_C/PC3_C (SPI2) | `FARADAYJorge/Core/Src/stm32h7xx_hal_msp.c`, en `HAL_MspInit` |

`Drivers/` contiene solo la HAL de ST y las cabeceras CMSIS que usa el proyecto, para que compile tal cual sin regenerar.

No está probado en hardware. Los valores tomados de las fichas técnicas están marcados `VERIFICAR` en el código.
