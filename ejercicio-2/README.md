# Ejercicio 2 — Selección e integración de sensores

## a) Sensores y modelos

No empecé por una lista de sensores, sino por lo que el ordenador de vuelo tiene que hacer: **estimar el estado** del cohete, **detectar eventos**, **vigilar su propia salud** y **registrar y comunicar**. De cada necesidad sale un sensor, y de los sensores salen los buses que le pido al micro (ejercicio 1).

Lo que condiciona la elección es el perfil de vuelo:
- Mach ~5,2: el GNSS comercial se bloquea por los límites COCOM.
- Más de 100 km de apogeo: el barómetro deja de servir por encima de unos 30 km.
- Decenas de g en el empuje.
- Giro rápido tras el apagado del motor.
- Fuselaje de carbono, opaco a RF.

### Estimar el estado (entradas del filtro de Kalman)

| Sensor | Modelo | Bus | Por qué |
|---|---|---|---|
| IMU de 6 ejes | **ICM-42686-P** | SPI1 | Llega a ±32 g y ±4000 °/s, el doble que el ICM-42688-P habitual en cohetería, así que satura menos en el empuje. Es el sensor central: va solo en su bus. |
| Acelerómetro de alta g | **H3LIS200DL** (±200 g) | SPI2 | Cubre la combustión, donde la IMU satura. Es de 8 bits: no aporta precisión, evita perder el dato. |
| Giróscopo de alto rango | **ADXRS649** (±20 000 °/s) | ADC | Casi todas las IMU MEMS topan en ±2000 °/s (unas 333 rpm). Si el cohete gira más tras el apagado, sin este sensor pierdo la actitud. |
| Magnetómetro | **RM3100** | SPI2 | Ancla la guiñada cuando no hay GNSS. Lo prefiero al MMC5983MA porque deriva menos con la temperatura. |
| Barómetro | **MS5607** (×2) | I²C1 | Es el estándar en cohetería y sirve por debajo de ~30 km. El segundo va en la electrónica redundante. |
| GNSS | u-blox de alta dinámica (modo *Airborne*) | UART | Da una ayuda intermitente al filtro, no la referencia: durante el ascenso se bloquea. |

### Detectar eventos

| Sensor | Bus | Por qué |
|---|---|---|
| Continuidad de las cerillas (×4) | ADC | Antes del vuelo dice si la cerilla está conectada; después, si ha disparado. Son dos canales por evento (drogue y principal), porque la recuperación es redundante. |
| Breakwire o microinterruptor de separación (×2) | GPIO | Distingue «he disparado la carga» de «se ha separado de verdad». |
| Interruptor de armado externo | GPIO | Requisito de seguridad: el sistema se arma en rampa sin abrir el cohete. |
| Posición del aerofreno y corriente del servo | ADC | Cierran el lazo del aerofreno y detectan un atasco. |

### Vigilar la salud del sistema

| Sensor | Modelo | Bus | Por qué |
|---|---|---|---|
| Monitor de batería | **INA226** (×2) | I²C1 | Cuenta culombios. Una LiPo mantiene la tensión casi plana hasta el final, así que tras 6 h en rampa la tensión sola engaña. Lleva uno por batería (vuelo y recuperación). |
| Respaldo de la tensión | divisor + ADC (×2) | ADC | No depende del I²C. |
| Temperatura de las baterías | NTC (×2) | ADC | Por seguridad de las LiPo y porque su capacidad cae con el frío. |
| Temperatura de la electrónica | LM75B o el sensor interno | I²C1 | Comprueba el rango de −40 a 85 °C. |

Para registrar y comunicar:
- **Flash NOR por QSPI** dimensionada para 18,4 MB; descarto la microSD por la vibración.
- **Radio Matek mR900-30** a 868 MHz.
- **TCXO** y el **PPS del GNSS** como base de tiempo.
- **Bus CAN** hacia la bahía del aerofreno.

Además, la recuperación redundante va en una **electrónica comercial independiente** (la competición la exige), y hay un **localizador** con su propia batería.

El inventario completo, con la justificación de cada cantidad y la derivación a buses, está en [`../matriz/data/sensors.csv`](../matriz/data/sensors.csv) y se ve en la sección 2 de la matriz.

## b) Inicialización y lectura

El código está en el mismo proyecto del ejercicio 1, como pide el enunciado:

```
firmware/FARADAYJorge/Core/
├── Inc/sensors/          cabeceras
└── Src/sensors/
    ├── bus.c             capa común SPI / I²C
    ├── icm42686.c        IMU               (SPI1)
    ├── h3lis200dl.c      alta g            (SPI2)
    ├── rm3100.c          magnetómetro      (SPI2)
    ├── ms5607.c          barómetro         (I²C1)
    ├── ina226.c          monitor batería   (I²C1, dos unidades)
    └── sensors.c         inicializa y lee todos
```

En `main.c` solo se añaden tres cosas, siempre dentro de los bloques `USER CODE` para que CubeMX no las borre al regenerar:
1. La llamada a `sensors_init()` al arrancar, que imprime por consola el estado de cada sensor.
2. La llamada a `sensors_read_all()` en el bucle principal.
3. La redirección de `printf` a USART3.

### Cómo está organizado

- **`bus.c`** encapsula la HAL: selecciona y libera el chip-select, pone el bit de lectura de SPI (bit 7), desplaza la dirección I²C (`addr << 1`) y aplica timeouts. Ningún driver llama a la HAL directamente.
- **Cada driver sigue el mismo patrón:** comprueba el registro de identificación del sensor, hace un reset, configura el rango y la frecuencia, y lee convirtiendo a unidades físicas.
- **Ninguna función se bloquea.** Todas devuelven un código de error (`SENS_OK`, `SENS_ERR_BUS`, `SENS_ERR_ID`, `SENS_ERR_TIMEOUT`, `SENS_ERR_CRC`), y las esperas tienen un límite de tiempo.
- **Si un sensor falla, `sensors.c` lo marca y sigue** con los demás: un sensor caído no debe dejar colgado el ordenador de vuelo.

### Detalles de cada sensor

- **ICM-42686-P:** lee los 14 bytes en una sola ráfaga, para que los seis ejes sean de la misma muestra. Fondo de escala máximo (±32 g, ±4000 °/s) a 1 kHz.
- **H3LIS200DL:** ±200 g, con *Block Data Update*. Cada eje es un byte con signo.
- **RM3100:** pide una medida, espera el bit de dato listo con timeout y lee 24 bits por eje, extendiendo el signo a 32 bits.
- **MS5607:** lee la PROM de calibración y comprueba su CRC4. Después aplica la compensación de primer y segundo orden de la ficha, en enteros de 64 bits. La de segundo orden importa porque en altura hace frío.
- **INA226:** un mismo driver sirve para las dos unidades. Calcula el registro de calibración a partir del shunt y de la corriente máxima.

### Estado

- **Compila** sin errores ni avisos en STM32CubeIDE (GCC 14).
- **No está probado en hardware**, porque no tengo la placa.
- **Los registros y valores de identificación** están marcados `VERIFICAR` en el código, a la espera de contrastarlos con cada ficha técnica.
- **Valores de ejemplo:** las direcciones I²C de los INA226, el valor del shunt y la dirección del MS5607 dependen de la placa (`sensors.c`, `ms5607.c`).
- **Sin driver todavía:** los sensores analógicos (giróscopo ADXRS649, continuidad, divisores y NTC). El ADC ya está configurado con sus 11 canales; falta el código de lectura por DMA.
- **Siguiente paso:** leer la IMU cuando llega su interrupción de dato listo y repartir el trabajo en tareas de FreeRTOS. Así el barómetro no bloquea 20 ms esperando su conversión.
