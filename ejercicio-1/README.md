# Ejercicio 1 — Selección de microcontrolador y configuración básica

## Contexto de la misión

Antes de desarrollar el contexto de la misión, conviene recordar que superar el récord mundial es algo atípico. A Mach 5,2 (enunciado de estructuras) y a más de 143 km de altura, los componentes típicos de un cohete de competición fallan:
- **El GNSS se bloquea,** ya sea por las restricciones COCOM de altitud o velocidad, o incluso por el efecto Doppler, la temperatura o las vibraciones del lanzamiento.
- **El barómetro deja de medir** aproximadamente a 31 km de altura, cuando ya se ha perdido más del 99 % de la masa de la atmósfera terrestre y los cambios son indistinguibles.
- **La telemetría sufriría problemas,** porque con frecuencias comerciales puedes tener problemas con la altura.

Además hay muchos otros problemas, que se describen a continuación.

Investigamos el caso más parecido que existe, el cohete que sustenta el récord de altura (**Aftershock II**), ya que nos servirá para responder a todas las cuestiones siguientes. Otro buen caso para hacer un poco de ingeniería inversa es el **Meraki III**, cohete estudiantil con récord de velocidad (111 km).

La tabla de condiciones de vuelo → problema real → implicación en la aviónica está en la hoja `FARADAY 1.xlsx` ([`../matriz/data/challenges.csv`](../matriz/data/challenges.csv)), y se ve en la sección 0 de la [matriz](../matriz/).

## a) Elección del microcontrolador

**Elijo el STM32H743ZI (Cortex-M7, LQFP144).** Tiene un segundo muy cerca, el STM32H563ZI, y explico abajo qué haría cambiar la elección.

### Marco de decisión

Voy a definir un marco de decisión para que mi decisión tenga sentido, basándome en el proceso de análisis de decisiones del NASA Systems Engineering Handbook (sección 6.8):
1. Definir los criterios que la misión exige.
2. Identificar alternativas.
3. Analizarlas (matriz de decisión).
4. Elegir.

El orden importa: los umbrales y los pesos se fijan antes de poner a todos los participantes.

**1. Definir los criterios que la misión exige.** El ordenador de vuelo tiene que ser capaz de hacer tres cosas durante la misión: estimar estados, detectar eventos y vigilar su propia salud. Para ello se hace una preselección de sensores y de qué exigencias tienen estos respecto al microprocesador, sobre todo qué buses necesito y cuántos. Esto es ya el ejercicio 2a: ver [`../ejercicio-2/README.md`](../ejercicio-2/README.md#a-sensores-y-modelos).

Para la matriz de decisión:
- **Umbral:** el mínimo para completar la función. Si un candidato no llega, no se puntúa.
- **Peso:** cuánto importa ese criterio frente a los demás.
- **Nota:** lo bien que cada candidato cumple ese criterio, de 1 a 5.

### Cómo llegué a él

No partí de una lista de micros conocidos, sino de los requisitos de la misión (apogeo > 100 km, Mach ~5,2, 754 s de vuelo de referencia y hasta 6 h en rampa):

1. **Requisitos → umbrales.** De la misión salen los mínimos eliminatorios: FPU en hardware, ≥ 3 SPI, ≥ 4 UART, ≥ 2 I²C, ≥ 1 CAN, interfaz para la memoria de registro (QSPI/OctoSPI o SD/MMC), ≥ 12 canales de ADC, ≥ 3 timers con PWM, ≥ 128 kB de RAM, ≥ 256 kB de flash, rango de −40 a 85 °C y encapsulado LQFP (soldable sin horno ni rayos X). El número de buses no lo elegí a ojo: sale del inventario de sensores, sumando además una reserva.
2. **Umbrales → candidatos.** Apliqué esos umbrales a las 1644 referencias del selector paramétrico de ST y quedaron unas 337, repartidas en 10 series. De cada serie tomé un representante, el que tiene placa Nucleo, y añadí dos controles que deben caer: un ESP32-S3 y un STM32F411RE.
3. **Candidatos → puntuación.** Puntué de 1 a 5 nueve criterios. Cada peso sale de la severidad del fallo que el criterio evita multiplicada por su no detectabilidad (cuánto cuesta verlo en tierra).
4. **Sensibilidad.** Comprobé si el ganador cambia al igualar los pesos, al quitar un criterio o al mover cada peso.

Todo está en [`../matriz/`](../matriz/), con los datos en CSV y la justificación de cada número.

### Justificación

| Aspecto | STM32H743ZI | Por qué importa |
|---|---|---|
| **Potencia de cálculo** | Cortex-M7 a 480 MHz, **FPU de doble precisión** | Mi filtro de Kalman (15 estados a 200 Hz) gasta unos 16,2 Mciclos/s: un 3,4 % de la CPU a 480 MHz. La potencia sobra en todos los candidatos; lo que distingue al H743 es la **doble precisión**. En coordenadas ECEF, un `float` solo resuelve 0,5 m, y las covarianzas pueden divergir sin dar ningún aviso. |
| **Memoria** | 2 MB de flash, 1 MB de RAM, **ECC en flash y RAM** | Hay margen de sobra para el filtro y los buffers. El ECC corrige bits alterados en vuelo, un fallo que no se reproduce en el banco. |
| **Periféricos** | 6 SPI, 8 UART, 4 I²C, 2 FDCAN, Quad-SPI dual y SD/MMC, 28 canales de ADC | Pido 3 SPI, 4 UART, 2 I²C, 1 CAN y 12 ADC (con reserva incluida): todos quedan cubiertos con margen. La memoria de registro tiene QSPI y SD/MMC, dos vías. |
| **Consumo** | 270 µA/MHz típico (selector de ST) | **Es su punto débil.** A 480 MHz son unos 130 mA, el peor de los candidatos para las 6 h en rampa. Por eso el proyecto arranca a 75 MHz: así baja a unos 20 mA y el filtro sigue usando solo un 22 % de la CPU. |
| **Temperatura y encapsulado** | −40 a 85 °C, LQFP144 | Cumple el rango industrial y se puede soldar a mano. |
| **Ecosistema** | Nucleo-H743ZI2, HAL y CubeMX maduros | Permite empezar a desarrollar ya. |

### La parte honesta: es un empate técnico

Con mis pesos, el H743ZI saca 86,2/100 y el **H563ZI (Cortex-M33) 82,4**. Por mi propio criterio, menos de 5 puntos de diferencia es un empate técnico:

- **Lo que sostiene al H743 es un solo criterio:** la FPU de doble precisión, que pesa el 23,8 %. Si igualo todos los pesos, gana el H563.
- **El ganador cambia** si la familia de criterios de «fallo silencioso» (precisión numérica y robustez) baja del 40,9 % del peso total. Hoy está en el 53,6 %.
- **El desempate es una decisión de software.** Si el filtro trabaja en un marco local ENU con `float`, la doble precisión deja de ser necesaria, y el H563 gana: consume menos (111 µA/MHz), llega a 125 °C, tiene ECC y es más sencillo de poner en marcha (no hay que gestionar la caché del M7).

Me quedo con el H743 porque prefiero no atarme ahora a un marco local, pero lo presento como lo que es: una decisión que se reabre si el filtro va en ENU.

## b) Proyecto en STM32CubeMX

**Proyecto:** [`../firmware/FARADAYJorge/`](../firmware/FARADAYJorge/), con la configuración en [`FARADAYJorge.ioc`](../firmware/FARADAYJorge/FARADAYJorge.ioc).

- **MCU:** STM32H743ZITx, LQFP144. La placa de desarrollo prevista es la Nucleo-H743ZI2.
- **Toolchain:** STM32CubeIDE. Compila sin errores ni avisos.
- **Para abrirlo:** en STM32CubeIDE, *File → Import → STM32CubeMX/STM32CubeIDE Project* y seleccionar la carpeta.

### Lo que pide el enunciado

| Requisito | Configuración | Detalle |
|---|---|---|
| **Al menos un bus SPI** | **SPI1** (IMU) y **SPI2** (acelerómetro de alta g y magnetómetro) | Master full-duplex en **modo 3**, con chip-select por GPIO (PE3, PE4 y PE5) que arrancan en alto. SPI1 va a 12,5 MHz (la IMU admite 24 MHz). SPI2 va a ~780 kHz, porque el RM3100 no pasa de 1 MHz. La IMU va sola en su bus para que nada le añada latencia. |
| **Al menos un bus I²C** | **I2C1** (barómetro, monitores de batería, temperatura) y **I2C2** (reserva) | Modo estándar. |
| **Configuración para el ST-LINK** | *SYS → Debug = Serial Wire* | SWDIO en PA13 y SWCLK en PA14, reservados. Además, USART3 en PD8/PD9 es el puerto COM virtual del ST-LINK de la Nucleo, que sirve como consola por el mismo USB. |

### Resto de la configuración

- **Reloj:** HSE en *bypass* a 8 MHz (en la Nucleo, el ST-LINK le da el reloj por su salida MCO), PLL a **75 MHz**, regulador LDO y escala de tensión 3.
- **UART:** USART2 (GNSS), USART6 (radio), USART3 (consola) y LPUART1 (reserva).
- **CAN:** FDCAN1 a 500 kbit/s, para el bus que va a la bahía del aerofreno.
- **QUADSPI:** para la flash NOR de registro. El tamaño se fijará cuando elija la memoria.
- **ADC:** ADC1 y ADC2, con 11 canales en total, en modo *scan* y 64,5 ciclos de muestreo. Son para el giróscopo analógico de alto rango, la continuidad de las cerillas, las tensiones de batería y las NTC.
- **Timers:** con base de 1 µs. TIM1 da los 50 Hz del servo, TIM4 los ~2,7 kHz del zumbador y TIM2 (32 bits) captura el PPS del GNSS.
- **GPIO:** líneas de interrupción de los sensores (PE6–PE8), breakwire (PE10 y PE11, flanco de subida y de bajada, con pull-up) y armado (PE12), todas con su EXTI activada en el NVIC.

### Pinout

| Pin | Señal | Uso |
|---|---|---|
| PA13 / PA14 | SWDIO / SWCLK | ST-LINK |
| PA5 / PG9 / PD7 | SPI1 SCK / MISO / MOSI | IMU ICM-42686-P |
| PE3 | GPIO out | CS de la IMU |
| PB13 / PC2_C / PC3_C | SPI2 SCK / MISO / MOSI | H3LIS200DL y RM3100 |
| PE4 / PE5 | GPIO out | CS del H3LIS200DL / CS del RM3100 |
| PE6 / PE7 / PE8 | EXTI | dato listo de los sensores |
| PB6 / PB7 | I2C1 SCL / SDA | MS5607, INA226 ×2, LM75B |
| PF1 / PF0 | I2C2 SCL / SDA | reserva |
| PD5 / PD6 | USART2 TX / RX | GNSS |
| PC6 / PC7 | USART6 TX / RX | radio |
| PD8 / PD9 | USART3 TX / RX | consola (VCP del ST-LINK) |
| PA9 / PA10 | LPUART1 TX / RX | reserva |
| PA12 / PA11 | FDCAN1 TX / RX | bus CAN entre bahías |
| PF10, PB10, PF8, PF9, PF7, PF6 | QUADSPI CLK, NCS, IO0–IO3 | flash NOR |
| PF11, PF13, PF14, PA2, PA3, PA6, PA7, PB1, PC0, PC1, PC4 | ADC1/ADC2 | 11 canales analógicos |
| PA0 | TIM2 CH1 (captura) | PPS del GNSS |
| PE9 | TIM1 CH1 (PWM) | servo |
| PD14 | TIM4 CH3 (PWM) | zumbador |
| PE10 / PE11 | EXTI | breakwire 1 y 2 |
| PE12 | GPIO in | interruptor de armado |
| PH0 / PH1 | RCC OSC IN / OUT | HSE |

<img width="802" height="655" alt="image" src="https://github.com/user-attachments/assets/043e8308-6c94-4587-8095-e142bd3472b3" />


### Notas

- **SPI2 en PC2_C y PC3_C.** En el H743, esos pads pasan por un conmutador analógico. Lo cierro explícitamente en `HAL_MspInit` (`stm32h7xx_hal_msp.c`, dentro de `USER CODE`). Si ya estuviera cerrado, la llamada no cambia nada.
- **Conflictos en la Nucleo-H743ZI2.** En la Nucleo, el PHY de Ethernet usa PA2, PA7, PC1, PC4 y PB13. Para leer bien esos canales analógicos en la Nucleo, hay que abrir los puentes de soldadura del Ethernet. En una placa propia no ocurre.
