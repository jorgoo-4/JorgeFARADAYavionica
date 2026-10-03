# Ejercicio 3 — Especialización: opción III (FreeRTOS)

Elijo la **opción III**: configurar en FreeRTOS las funciones principales de la aviónica. La opción II (el filtro de Kalman) la tengo en cuenta solo como contexto, porque condiciona la tarea de estimación.

- **Proyecto:** [`../firmware/FARADAYJorge_Ej3/`](../firmware/FARADAYJorge_Ej3/). Es una copia del proyecto de los ejercicios 1 y 2, con FreeRTOS añadido; el original se conserva intacto como entrega de esos ejercicios.
- **Configuración:** [`FARADAYJorge_Ej3.ioc`](../firmware/FARADAYJorge_Ej3/FARADAYJorge_Ej3.ioc).
- **Tareas:** al final de [`Core/Src/main.c`](../firmware/FARADAYJorge_Ej3/Core/Src/main.c) (buscar `fTareaIMU`).
- **Mi documento original:** [`../docs/Ejercicio3_FreeRTOS.pdf`](../docs/Ejercicio3_FreeRTOS.pdf).

Compila sin errores en STM32CubeIDE. No está probado en hardware.

## Contexto: opción II (solo para tenerlo en cuenta en la III)

El Filtro de Kalman Extendido (EKF) es el corazón de la navegación inercial de un cohete: su trabajo es combinar de forma matemática y estadística las lecturas de los sensores (acelerómetros, giróscopos, barómetro, GPS) para estimar en tiempo real la posición, velocidad y orientación exactas del vehículo.

El filtro de Kalman es un estimador estadístico óptimo porque utiliza una matriz de covarianza (P) para saber cuánto debe confiar en cada sensor en función de su ruido estimado.
- Las ecuaciones del filtro asumen que el ruido del sensor sigue una distribución normal (gaussiana).
- Cuando un sensor llega a su límite físico y satura, deja de medir la realidad y se convierte en un valor plano y constante (el techo del sensor). El modelo estadístico del filtro se rompe, porque un valor saturado ya no tiene «ruido normal»: tiene un error sistemático gigantesco. El filtro calcula mal su ganancia de Kalman y pierde la capacidad de corregir errores correctamente.

Por eso la tarea de estimación descarta las muestras saturadas, y por eso existe una tarea para el acelerómetro de alta g.

## Conceptos

- **FreeRTOS:** son archivos de C que se instalan en mi proyecto de CubeIDE y que permiten hacer varios bucles (tareas) a la vez.
- **Scheduler (planificador):** administra el tiempo de CPU para cada tarea. Determina qué tarea debe estar en ejecución en un momento dado.
- **Despachador:** cede el control de la CPU a una cierta tarea en el momento adecuado.
- **Tarea (*thread*):** es como un miniprograma independiente dentro del microcontrolador. Cada tarea tiene su propia función con su bucle infinito `for(;;)`, y el planificador decide a cuál le da un ratito de CPU. Las tareas pueden ser cooperativas (cada una tiene su hueco) o apropiativas (el despachador guarda el contexto de ejecución y lo reemplaza por el de la nueva tarea).
- **`USE_PREEMPTION` (enabled):** es el interruptor que activa la planificación preventiva (*preemptive scheduling*) en el sistema operativo en tiempo real, para que unas tareas dominen sobre otras. Asegura que las tareas con plazos estrictos (*deadlines* cortos), como leer una IMU o calcular estados de vuelo, no se queden bloqueadas detrás de tareas secundarias que tarden más en ejecutarse.
- **Prioridad (y *preemption*):** si hay dos tareas listas para correr, el sistema ejecuta la que tenga mayor prioridad. Si entra una tarea muy urgente (como leer la IMU), interrumpe a la que estaba corriendo y toma el control inmediatamente.
- **Mutex (exclusión mutua):** hace que una tarea pida la «llave» del bus I2C, haga su lectura y la devuelva para que otra la use.
- **Cola (*queue*):** cola de espera tipo FIFO (*first in, first out*): el primero que llega es el primero que se atiende.
- **Thread flag (semáforo binario):** a diferencia de la cola, que transporta datos, esto es una señal de aviso sin datos. Es la que usa la interrupción.
- **Event flags (banderas de eventos):** son como un panel con varios interruptores. Permiten que varias tareas sepan en qué fase de vuelo está el cohete (despegue, motor encendido, apogeo, caída…).
- **`osDelay` y `osDelayUntil` frente a `HAL_Delay`:** `HAL_Delay(10)` mantiene al procesador atrapado en un bucle vacío, gastando ciclos y tiempo de CPU. `osDelayUntil` (en la API nativa, `vTaskDelayUntil`) le dice al sistema operativo: «a esta tarea no la despiertes hasta dentro de exactamente 10 milisegundos».
  - **Liberación de la CPU:** durante ese tiempo de espera, FreeRTOS aprovecha para ejecutar otras tareas (telemetría, control, registro en la flash).
  - **Determinismo:** las tareas de mayor prioridad (como la lectura de la IMU mediante la interrupción del pin físico) pueden interrumpir al instante a las de menor prioridad.
- **Sin RTOS (*bare-metal*):** si se comenta la línea que arranca el kernel, el sistema operativo desaparece de la ecuación. El microcontrolador se olvida de las tareas, las prioridades y el planificador, y se limita a ejecutar el código de forma estrictamente lineal dentro del `while(1)`, con retardos bloqueantes como `HAL_Delay()`. Con un RTOS, dos tareas pueden atenderse a la vez incluso con una diferencia de 1 ms.

## Configuración en CubeMX

1. **System Core → SYS → Timebase Source → TIM6.** FreeRTOS usa SysTick para su reloj; si la HAL también lo usa, chocan.
2. **Middleware → FREERTOS → Interface: CMSIS_V2.** Las tareas se crean con `osThreadNew()`; en CMSIS_V1 era `osThreadDef()`.
3. **Parámetros:**
   - `TOTAL_HEAP_SIZE` = 32 768 bytes (hay 1 MB de RAM).
   - `USE_PREEMPTION` = Enabled.
   - `CHECK_FOR_STACK_OVERFLOW` = 2, para detectar desbordamientos de pila (robustez).
4. **Tareas:** las de la tabla siguiente. La pila es de 512 palabras, salvo el filtro, que lleva 1024 porque usa matrices.
5. **Colas, mutex y event flags:** en las pestañas *Queues*, *Mutexes* y *Events*. Al generar el código, CubeMX crea los *handles* globales (`qSensoresHandle`, `mtxI2C1Handle`…), listos para usar en las tareas.
6. **NVIC:** las interrupciones que llaman a funciones de FreeRTOS deben tener prioridad numérica ≥ 5 (`configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY`). Las EXTI de los sensores están en 5.

Con FreeRTOS, `main()` llama a `osKernelStart()` y no vuelve: la lectura de sensores pasa del bucle de `main.c` a sus tareas.

## a) Tareas y prioridades

| Tarea | Función | Frecuencia | Prioridad | Por qué esa prioridad |
|---|---|---|---|---|
| `tIMU` | `fTareaIMU` | 1 kHz, despertada por la interrupción de dato listo (PE6) | Realtime | El plazo más corto del sistema: si pierde una muestra, la integración inercial se degrada. Su trabajo es corto (una lectura SPI de 14 bytes). |
| `tAltaG` | `fTareaAltaG` | 1 kHz durante la propulsión; 100 Hz después | High7 | Solo importa en el empuje, donde la IMU satura. Mismo ritmo que la IMU, pero menos crítica fuera del empuje. |
| `tEventos` | `fTareaEventos` | 100 Hz | High | Detecta despegue, apagado y apogeo, y dispara las cargas de recuperación. Llegar tarde al apogeo = paracaídas tarde = pérdida del cohete. |
| `tEstimacion` | `fTareaEstimacion` | 200 Hz | AboveNormal | El filtro de Kalman. Es lo que más CPU gasta (~16 Mciclos/s): si fuera más alta, robaría tiempo a la IMU y a los eventos. |
| `tBaro` | `fTareaBaro` | 50 Hz | Normal | Lento por naturaleza (10 ms por conversión). Deja de servir por encima de ~30 km. |
| `tMag` | `fTareaMag` | 100 Hz | Normal | Corrección de guiñada: lenta y tolerante a retrasos. |
| `tGNSS` | `fTareaGNSS` | 10 Hz (NMEA o UBX por UART con DMA) | Normal | Ayuda intermitente: se bloquea en el ascenso (COCOM). Que llegue tarde no rompe nada. |
| `tRegistro` | `fTareaRegistro` | 200 Hz (vacía la cola a la flash NOR por bloques) | BelowNormal | Que no se pierdan datos importa, pero la cola absorbe los retrasos. Es la que más tarda (escritura en flash), así que no puede estar por encima del control. |
| `tAerofreno` | `fTareaAerofreno` | 50 Hz, por CAN | BelowNormal | Control de apogeo: necesita la estimación, pero un retraso de unos ms no es crítico. |
| `tTelemetria` | `fTareaTelemetria` | 10 Hz | Low | Útil para tierra; nada en vuelo depende de ella. |
| `tSalud` | `fTareaSalud` | 1 Hz | Low | Batería (INA226), temperaturas y estado de los sensores. Refresca el watchdog (IWDG) solo si todas las tareas críticas han dado señales de vida. |
| `tZumbador` | `fTareaZumbador` | según el evento | Low | Avisos sonoros en rampa y en la búsqueda. Lo último en importancia. |

**Criterio:** asigno prioridades según el plazo y la consecuencia de fallar. Arriba va lo más urgente y crítico para salvar la misión (IMU y eventos); abajo, lo que solo sirve en tierra (telemetría y zumbador).

## Arquitectura

```
 EXTI PE6 ──flag──► tIMU ──┐
                 tAltaG ───┤                     ┌──► qRegistro ──► tRegistro ──► flash NOR
 tBaro ─(mutex I2C)────────┼──► qSensores ──► tEstimacion ──► qEstado ──┬──► tEventos ──► cargas
 tMag ─────────────────────┤                                            ├──► tAerofreno ──► CAN
 tGNSS ────────────────────┘                                            └──► tTelemetria ──► radio
 tSalud ─(mutex I2C)─ INA226                                tEventos ──evFase──► todas
```

**1. Bloque de entradas y sensores (adquisición)**
- **La regla de oro de la IMU (`tIMU` a 1 kHz):** el pin PE6 genera una interrupción cuando hay un dato listo. Como regla de diseño, la interrupción no hace trabajo pesado: solo activa un *thread flag* que despierta al instante a la tarea `tIMU`, y así se evita la degradación de la navegación inercial.
- **Gestión de buses con mutex:** sensores como el barómetro (`tBaro`), el de salud (`tSalud`, con el INA226) o el acelerómetro de alta g (`tAltaG`) comparten buses físicos (I2C o SPI). Para evitar la corrupción de datos y la inversión de prioridad, se usan mutex con herencia de prioridad (`mtxI2C1`, `mtxSPI2`).

**2. Bloque de procesamiento central (el núcleo del sistema)**
- **El embudo de datos (`qSensores`):** todas las tareas de sensores vuelcan sus lecturas en una cola FIFO (`muestra_t`, 32 elementos). Actúa como un búfer que absorbe picos de tráfico antes de que lleguen al procesador.
- **El filtro de Kalman (`tEstimacion` a 200 Hz):** es el corazón matemático. Procesa los datos y genera un estado unificado (`qEstado`) que distribuye la altitud y la velocidad estimadas. Aunque el filtro consume mucha CPU, deliberadamente no tiene la máxima prioridad: si la tuviera, robaría ciclos vitales a la IMU. Su prioridad es intermedia (AboveNormal).
- **Fases de vuelo (`evFase`):** mediante *event flags*, se comunican a todo el software los cambios críticos de estado (despegue, apagado, apogeo), para que cada tarea adapte su comportamiento.

**3. Bloque de acciones y salidas (seguridad y telemetría)**
- **Tareas críticas de seguridad (`tEventos` y `tAerofreno`):** monitorizan continuamente el apogeo y los tiempos de la misión. Fallar aquí, o llegar tarde, significa perder el cohete.
- **La caja negra (`tRegistro` a 200 Hz):** todas las tareas escriben sus trazas en una cola grande (`qRegistro`, 64 elementos). Una tarea de baja prioridad la vacía poco a poco, escribiendo por bloques en la memoria flash NOR externa, para que la escritura lenta no bloquee el control del cohete.

**Principios del diseño**
- **Prioridades basadas en consecuencias:** según el plazo y lo que cuesta fallar.
- **`osDelayUntil`:** ninguna tarea periódica usa retardos bloqueantes (`HAL_Delay`); todas usan retardos absolutos, para no acumular deriva temporal.
- **Salud y watchdog:** `tSalud` (1 Hz) verifica voltajes y temperaturas, y solo refresca el watchdog del hardware si todas las tareas críticas han demostrado que siguen vivas.

## b) Esqueletos de las tareas

Cada `fTarea…` de `main.c` tiene un comentario de cabecera que dice qué hace, a qué frecuencia, cómo se despierta, qué recibe y qué envía, su prioridad y qué pasa si falla. Además, tres tareas tienen la lógica de comunicación implementada:

| Paso | Dónde | Qué hace |
|---|---|---|
| **A** | `USER CODE BEGIN PD` | `#define FLAG_IMU_DRDY 0x0001U`: el aviso de la ISR de PE6 a `tIMU`. |
| **B** | `USER CODE BEGIN 4` | `HAL_GPIO_EXTI_Callback`: la interrupción solo avisa (`osThreadFlagsSet`). La lectura SPI la hace `tIMU`, que es una tarea y puede esperar al bus. |
| **C** | `fTareaIMU` | `osThreadFlagsWait` duerme la tarea sin gastar CPU hasta que la interrupción la despierta (con un timeout de 5 ms). Lee la IMU y envía la muestra a `qSensores` con `osMessageQueuePut` y timeout 0: si el filtro va retrasado y la cola está llena, la IMU no se bloquea; esa muestra se pierde. |
| **D** | `fTareaBaro` | Toma `mtxI2C1` (el I2C1 lo comparte con `tSalud`), lee el MS5607, suelta el mutex siempre y publica la muestra. `osDelayUntil` mantiene los 50 Hz exactos, sin acumular deriva. |
| **E** | `fTareaEstimacion` | `osMessageQueueGet` duerme la tarea hasta que llega una muestra: es el patrón productor-consumidor (los sensores producen y el filtro consume). Publica el estado en `qEstado`. |

Los mensajes de las colas son `muestra_t`, `estado_t` y `registro_t`, definidos en `USER CODE BEGIN PTD`.

## Limitaciones conocidas

- **`ms5607_read()` espera la conversión con `HAL_Delay`,** que con un RTOS bloquea la CPU unos 20 ms. La mejora es cambiarlo por `osDelay`, que duerme la tarea. Es lo primero que cambiaría.
- **La marca de tiempo se toma del tick del sistema** (resolución de 1 ms). El siguiente paso es usar TIM2 a 1 MHz, en microsegundos.
- **Sobra la tarea `Task2`,** la que CubeMX crea por defecto; no forma parte del diseño.
- **No está probado en hardware.**
