# Ejercicio 2 — Selección e integración de sensores

## a) Sensores y modelos

El ordenador de vuelo tiene que ser capaz de hacer tres cosas durante la misión: **estimar estados, detectar eventos y vigilar su propia salud**. Para ello se hace una preselección de sensores y de qué exigencias tienen estos respecto al microprocesador (sobre todo qué buses necesito y cuántos). Esta preselección es la entrada del ejercicio 1a.

Estos se seleccionan con una herramienta más sencilla que una matriz, simplemente teniendo en cuenta dos cosas: **la física de vuelo y la arquitectura del microcontrolador**. Son aproximadamente 25 componentes, y a cada uno se le asigna una importancia. Los problemas de vuelo de los que parten (velocidad, altitud, aceleración, régimen transónico, alabeo, magnetismo, estructura de carbono, enlace, duración y memoria) están en la hoja `FARADAY 1.xlsx`, que se ve en la sección 0 de la [matriz](../matriz/).

Los tres más críticos:
- **IMU (Crítico):** es la base de la estimación de estado.
- **Acelerómetro de altas g (×1, Crítico):** las IMU se saturan a 16-32 g en el principio del vuelo.
- **Giróscopo de alto rango (×1, Importante):** evita la saturación si el cohete experimenta un alabeo.

### Inventario completo y por qué cada sensor

Esta es la justificación de cada componente y de su cantidad, tal como está en mi hoja de inventario (`softwareFARADAY 2.xlsx`, hoja *Inventario*, columna «Por qué ese componente y esa cantidad»).

#### Estimar estados (entradas del filtro de Kalman)

| Para qué lo necesito | Componente | Cant. | Bus | Por qué ese componente y esa cantidad |
|---|---|---|---|---|
| Actitud y aceleración en las tres fases del vuelo | IMU 6 ejes ICM-42686-P | 1 | SPI | Descarto el MPU6050, con el que ya he trabajado, por sus limitaciones. Frente al ICM-42688-P, que es el que más usan los equipos de cohetería, el 42686-P dobla los límites programables: ±32 g y ±4.000 °/s, y eso me quita una saturación en la fase de empuje. Pongo una y no dos: la duplicación se exige en EuRoC y en la America Cup, pero aquí no me obliga el reglamento, y entre la electrónica comercial redundante y el resto de sensores ya tengo con qué contrastar la medida. |
| Aceleración durante la combustión sin saturar | Acelerómetro de alta g H3LIS200DL (±200 g) | 1 | SPI | La IMU satura en ±32 g y el empuje da decenas. ST especifica este integrado para detección de choques y vibraciones extremas hasta ±200 g, y aguanta hasta 10.000 g sin destruirse. Es de 8 bits: lo quiero para la fase que satura a la IMU, no para precisión. |
| Velocidad de alabeo tras el apagado sin saturar | Giróscopo de alto rango ADXRS649 (±20.000 °/s) | 1 | ADC | Casi toda IMU MEMS topa en ±2.000 °/s, unas 333 rpm: si el cohete gira más tras el apagado pierdo la actitud justo cuando la necesito. Salida analógica, así que me gasta un canal de ADC y no un bus, y leyéndolo por DMA no me cuesta CPU. |
| Referencia de rumbo (deriva del giróscopo en guiñada) | Magnetómetro 3 ejes RM3100 | 1 | SPI | Sin GNSS ni magnetómetro el error de guiñada crece sin nada que lo ate. Elijo el RM3100 sobre el MMC5983MA porque deriva menos con la temperatura. Lo calibro con la IMU ya montada en su estructura final: el cartucho de CO2 de acero mete error de hierro duro. |
| Altitud por debajo de unos 30 km | Barómetro MS5607 | 2 | I2C | El MS5607 es el estándar de facto en cohetería; el BMP390 va mejor de consumo y de ruido y lo dejo anotado como alternativa. Pongo dos: uno en mi ordenador y otro en la electrónica de recuperación redundante. El segundo no cuelga de mi I2C, pero lo dejo en el inventario porque es el que me da la segunda opinión de apogeo. Por encima de 31 km ninguno de los dos sirve. |
| Temperatura ambiente para la ecuación barométrica y el sesgo del giróscopo | Integrado en el barómetro y en la IMU | 0 | — | No compro nada: ya viene dentro. Pero tengo que usarlo, porque el sesgo del giróscopo deriva con la temperatura y es el error dominante del INS en un vuelo de 12 min. |
| Posición y velocidad absolutas cuando se puede | GNSS de alta dinámica (u-blox, modo Airborne <4 g) | 1 | UART | Se me va a bloquear por los límites COCOM durante el ascenso. Lo trato como una ayuda intermitente del filtro, no como la fuente de verdad. |

#### Detectar eventos

| Para qué lo necesito | Componente | Cant. | Bus | Por qué ese componente y esa cantidad |
|---|---|---|---|---|
| Saber que la carga de recuperación ha disparado de verdad | Medida de continuidad de cerilla (divisor + ADC) | 4 | ADC | 2 canales por evento, drogue y principal, porque EuRoC exige recuperación redundante. Antes del vuelo me dice si la cerilla está conectada; después, si ha disparado. |
| Saber que algo se ha separado FÍSICAMENTE | Breakwire o microinterruptor de separación | 2 | GPIO | El que más se olvida y el que más me habría servido: distingue «he disparado la carga» de «se ha abierto». Un fallo de recuperación por un nudo en la cuerda del principal se ve aquí y no en la continuidad. |
| Armar el sistema desde fuera del cohete en rampa | Interruptor de armado externo / pull-pin | 1 | GPIO | Requisito de seguridad de competición: se arma con el cohete ya en rampa, sin abrirlo. Si no lo preveo en el diseño mecánico, no paso la revisión. |
| Saber en qué posición está realmente el aerofreno | Encoder o potenciómetro de posición | 1 | ADC | Lazo cerrado. Un servo que dice estar a 30° y no lo está me arruina el control de apogeo y no me entero. Va en el nodo de la otra bahía; lo dejo contado en mi ADC hasta que cierre el reparto de bahías. |
| Detectar que el aerofreno se ha atascado | Medida de corriente del servo (shunt o INA) | 1 | ADC | Un pico de corriente sostenido es un atasco. Sin esto, el actuador falla en silencio. Mismo caso que el encoder: nodo del aerofreno, contado aquí por prudencia. |

#### Vigilar la salud del sistema

| Para qué lo necesito | Componente | Cant. | Bus | Por qué ese componente y esa cantidad |
|---|---|---|---|---|
| Cuánta batería queda tras horas en rampa | Monitor de tensión y corriente INA226 | 2 | I2C | Los LiPo descargan en meseta: mantienen la tensión durante casi toda su capacidad y caen en picado al final. Con 6 h en rampa, mirar solo la tensión me diría que la batería está llena hasta cinco minutos antes de apagarse, así que cuento culombios integrando corriente. Uno por batería, vuelo y recuperación. |
| Respaldo analógico del estado de batería | Divisor de tensión a ADC | 2 | ADC | Si se me cae el bus I2C me quedo sin saber la batería. El divisor no depende de ningún bus. |
| Temperatura de la batería (seguridad del LiPo) | Termistor NTC | 2 | ADC | Un LiPo fuera de rango de temperatura es un riesgo, y la capacidad cae con el frío en altura. |
| Temperatura de la electrónica | LM75B o el sensor interno del micro | 1 | I2C | Verifica en vuelo el rango industrial de −40 a 85 °C que he puesto como umbral. |

#### Registrar y comunicar

| Para qué lo necesito | Componente | Cant. | Bus | Por qué ese componente y esa cantidad |
|---|---|---|---|---|
| Guardar el vuelo entero sin quedarme sin sitio | Flash NOR por QSPI | 1 | QSPI | Descarto la microSD: su controladora interna mete latencias impredecibles y el sistema de ficheros FAT32 se corrompe con vibración. La flash NOR la escribo por bloques y con DMA. La dimensiono con el cálculo de la hoja Requisitos: 18,4 MB. El altímetro de respaldo de USC se quedó sin memoria a los 375 s de un vuelo de 754 s. |
| Telemetría en tiempo real | Par de Matek mR900-30 con mLRS, 868 MHz | 1 | UART | La antena va obligatoriamente en una sección de fibra de vidrio o en la ojiva: el carbono es opaco a RF. Con 868 MHz y más de 150 km de enlace tengo que contar con unos 135 dB de pérdidas y con el Doppler. |
| Depurar y volcar datos en tierra | Consola serie | 1 | UART | Una UART dedicada. No la comparto con la radio: cuando falle la radio es cuando querré la consola. |
| Base de tiempo del filtro | TCXO + señal PPS del GNSS | 1 | TIMER | Es el dt de mi Kalman. El PPS entra por captura de timer y me disciplina el reloj. El contador de 32 bits en µs da la vuelta cada 71,6 min, así que en 6 h de rampa da cinco vueltas antes de despegar y lo tengo que gestionar en firmware. |
| Hablar con la bahía del aerofreno | Bus CAN entre bahías | 1 | CAN | Cablear sensores sueltos entre bahías es peor que un bus. Me queda por definir la tabla de mensajes: identificador, contenido, frecuencia y qué hago si ese nodo muere. |
| Avisar de dónde ha caído / estado en rampa | Zumbador | 1 | PWM | Lo agradeceré buscando el cohete en el campo, y me sirve para comprobar el armado en rampa. |
| Mover el aerofreno | Servo | 1 | PWM | Viene del ejercicio de Hardware. Va en el nodo de la otra bahía, no en mi placa. |

#### Independientes (no cuelgan de mi micro)

| Para qué lo necesito | Componente | Cant. | Bus | Por qué ese componente y esa cantidad |
|---|---|---|---|---|
| Recuperación redundante exigida por la competición | Electrónica comercial (p. ej. CATS Vega) con batería propia | 1 | — | Guía de EuRoC 3.3 y 3.4.1: recuperación redundante y al menos una comercial. No es opcional, y además me da un tercer voto de apogeo y datos con los que contrastar los míos. |
| Encontrar el cohete después de aterrizar | Localizador independiente con su propia batería y radio | 1 | — | Si mi ordenador muere, el cohete sigue en algún sitio. Este no depende de nada mío. |

De este inventario sale el número de buses que se le pide al micro: SPI 2 + 1 de reserva, UART 3 + 1, I²C 1 + 1, CAN 1, 11 canales de ADC + 1, PWM 2 + 1. La derivación y la justificación de cada reparto están en la sección 2 de la [matriz](../matriz/) y en [`../matriz/data/bus_rationale.csv`](../matriz/data/bus_rationale.csv).

## b) Inicialización y lectura

El código está en el mismo proyecto del ejercicio 1:

```
firmware/FARADAYJorge/Core/
├── Inc/sensors/          cabeceras
└── Src/sensors/
    ├── sensor_types.h    (en Inc) códigos de error comunes
    ├── bus.c             capa común SPI / I²C
    ├── icm42686.c        IMU               (SPI1)
    ├── h3lis200dl.c      alta g            (SPI2)
    ├── rm3100.c          magnetómetro      (SPI2)
    ├── ms5607.c          barómetro         (I²C1)
    ├── ina226.c          monitor batería   (I²C1, dos unidades)
    └── sensors.c         inicializa y lee todos
```

Compila sin errores ni avisos en STM32CubeIDE. No está probado en hardware. Los valores de registro están marcados `VERIFICAR` en el código, a la espera de contrastarlos con la ficha técnica de cada sensor.

### Qué se ha escrito en el código

#### 1. Estructura por capas

```
main.c                  "quiero los datos de todos los sensores"
   │
sensors.c               inicializa y lee todos; si uno falla, sigue con los demás
   │
icm42686.c  h3lis200dl.c  rm3100.c  ms5607.c  ina226.c     (un driver/sensor)
   │
bus.c                   sabe CÓMO se habla por SPI e I2C (CS, bit de lectura, timeouts)
   │
HAL de ST               mueve los bits por el periférico del micro
```

El `main.c` se regenera, y así distribuido es más práctico por si se cambia algo.

#### 2. `sensor_types.h`

```c
#ifndef INC_SENSORS_SENSOR_TYPES_H_
#define INC_SENSORS_SENSOR_TYPES_H_
...
#endif /* INC_SENSORS_SENSOR_TYPES_H_ */
```

Estas líneas evitan que el contenido del archivo se procese más de una vez si es incluido accidentalmente múltiples veces en un mismo archivo fuente (`.c`).

Con el `enum`, los drivers comunican un código de error y se quedan a la espera:
- `SENS_OK = 0`: la operación se completó con éxito.
- `SENS_ERR_BUS`: hubo un fallo a nivel de comunicación física.
- `SENS_ERR_ID`: el sensor conectado no responde, o el ID leído no coincide con el modelo esperado.
- `SENS_ERR_TIMEOUT`: el sensor tardó más de lo permitido en preparar o entregar los datos solicitados.
- `SENS_ERR_CRC`: los datos internos están corruptos.

#### 3. `bus.h` y `bus.c` (cómo se habla con los sensores)

Son el puente entre mi MCU (usando HAL) y los sensores físicos a través de I2C, SPI, etc.

```c
extern SPI_HandleTypeDef hspi1;
extern SPI_HandleTypeDef hspi2;
extern I2C_HandleTypeDef hi2c1;
```

Esto es para luego usar la variable dentro de otra capa, el sensor concreto.

```c
typedef struct {
  SPI_HandleTypeDef *hspi;
  GPIO_TypeDef      *cs_port;
  uint16_t           cs_pin;
} spi_dev_t;
```

Un dispositivo SPI = qué bus usa + qué pin es su chip-select. Si varios sensores comparten el mismo bus SPI (como el H3LIS y el RM3100), lo único que permite diferenciarlos y hablar con uno u otro es activar su respectivo pin Chip-Select.

En el protocolo SPI, antes de pedir o mandar datos, hay que indicarle al sensor qué registro queremos tocar utilizando el bit 7 de la dirección:
- **Lectura** (`reg | 0x80`): poner en HIGH (operación OR sobre el bit 7). Al final se sube siempre el CS al terminar, para no bloquear el bus.
- **Escritura** (`reg & 0x7F`): poner en LOW (operación AND sobre el bit 7).

Según el sensor, se habla diferente por I2C.

#### 4. IMU (ICM-42686-P)

```c
static int16_t be16(const uint8_t *p) { return (int16_t)((uint16_t)(p[0] << 8) | p[1]); }
```

`static`, porque limitamos el alcance solamente a este archivo `.c`; `int16_t` con signo, ya que experimenta las fuerzas en los dos sentidos.

**La escala.** El conversor analógico-digital interno de la IMU es de 16 bits con signo, cubriendo un rango de −32768 a +32767 cuentas. Si configuras la IMU en un rango de ±32 g, la relación matemática es directa:

```
32768 cuentas / 32 g = 1024 LSB/g
```

Lo mismo aplica para el giróscopo (±4000 °/s), resultando en unas 8,2 cuentas por grado por segundo.

Cuando un sensor digital, de lo que sea, en este caso una IMU, mide algo en el mundo real, toma una señal analógica continua y la divide en «pasos»: 1 LSB equivale exactamente al valor de un paso.

#### 5. H3LIS200DL, acelerómetro de alta g

La IMU principal está configurada en un rango (32 g) para tener mucha precisión en vuelo ordinario. Pero en el despegue hace falta este sensor para no saturar y estropear los cálculos de navegación inercial.

**Estructura y registros (`hig_dev` y `#define`):**
- Configura el bus SPI y el pin de selección de chip (CS).
- Define los registros de control para habilitar los tres ejes, configurar el muestreo a 1 kHz, activar el filtro BDU (evita corrupción de datos al leer) y fijar el rango en ±200 g.
- Especifica los registros de salida (0x29, 0x2B, 0x2D), destacando que no son contiguos.

**Inicialización (`h3lis200dl_init`):**
- Verifica el sensor leyendo el registro WHO_AM_I (espera el valor 0x32).
- Configura CTRL_REG4 para establecer el rango y el BDU.
- Configura CTRL_REG1 para encender el sensor en modo normal a 1 kHz con sus tres ejes activos.

**Lectura de datos (`h3lis200dl_read`):**
- Realiza tres lecturas individuales por SPI, debido a que los registros de los ejes no son consecutivos.
- Convierte cada byte bruto a un entero con signo (`int8_t`).
- Multiplica el valor por el factor de sensibilidad (1,56) para entregar la aceleración final en unidades de gravedad (g).

#### 6. `rm3100.c`: el magnetómetro de 24 bits

- Se utiliza el modo POLL (bajo demanda: el dispositivo maestro solo solicita datos cuando los necesita, no los pide de manera continua).
- **El problema:** el microcontrolador maneja tipos de 8, 16 y 32 bits. Significa que el tamaño físico de sus circuitos internos, como los registros o los buses de datos, está diseñado para procesar bloques de esa cantidad exacta de dígitos binarios de manera simultánea en un solo ciclo de reloj. **Pero el RM3100 entrega el campo magnético en 3 bytes.**

Guardamos la información en un `int32_t`, pero el sensor me entrega 24 bits:
- **Si el número es positivo,** los bits de arriba quedan libres, pero se sigue leyendo bien.
- **Si el número es negativo, hay un problema.**
  - En informática, para saber si un número es negativo, se mira su bit más alto (el último de la izquierda). Si es un 1, es negativo.
  - Como el sensor da 24 bits, ese «bit negativo» cae justo en la posición 24.
  - Al meterlo en la caja de 32 bits, los espacios que sobran por arriba se rellenan con ceros por defecto. El procesador ve esos ceros arriba y piensa equivocadamente: «como los bits de más arriba son ceros, esto es un número positivo gigante» (un valor enorme de más de 8 millones).

**La solución: forzar la «extensión de signo».** Para que el procesador no se equivoque, hay que avisarle de que el número es negativo rellenando los huecos vacíos con unos (1) en lugar de ceros. Eso es lo que hace esa línea de código, en dos pasos:
1. `if (v & 0x800000)`: revisa si el bit 24 es un 1 (es decir, si el sensor dice que el número es negativo).
2. `v |= 0xFF000000`: si descubre que sí es negativo, llena de unos todos los bits de arriba de la caja de 32 bits.

En el momento en que el procesador ve esos unos arriba, entiende la regla matemática (complemento a dos) y dice: «ah, vale, es un número negativo real», dando el valor correcto (por ejemplo, −1500 en lugar de un error absurdo de 8 000 000).

**Código general.** Este archivo implementa el driver SPI para el magnetómetro RM3100, encargado de medir el campo magnético en tres ejes (X, Y, Z) para la navegación del cohete.

- **Estructura y registros (`mag_dev` y `#define`):**
  - Configura la conexión por SPI2 y el pin de selección de chip (CS).
  - Define constantes operativas como los 200 ciclos de muestreo, la ganancia matemática (75 LSB/µT) y un límite de seguridad (timeout) de 20 ms.
- **Traducción de 24 bits (`be24`):**
  - Empaqueta los 3 bytes que entrega el sensor para cada eje en una variable de 32 bits (`int32_t`).
  - Aplica extensión de signo, para asegurar que el microprocesador interprete correctamente los valores negativos.
- **Inicialización (`rm3100_init`):**
  - Verifica la identidad del sensor leyendo el registro de revisión (espera el valor 0x22).
  - Configura los registros de los tres ejes con los 200 ciclos definidos, para fijar la sensibilidad de forma estricta.
- **Lectura de datos (`rm3100_read`):**
  - *Disparo:* envía la orden de medir simultáneamente los tres ejes.
  - *Espera segura:* revisa cíclicamente el registro de estado hasta que los datos están listos (DRDY), usando un timeout para evitar bloqueos si el sensor falla.
  - *Conversión:* lee los 9 bytes en ráfaga, los procesa con la función `be24()` y los divide entre 75,0 para entregar el campo magnético final en microteslas (µT).

#### 7. `ms5607.c`: el barómetro

Este sensor no nos da la presión en pascales ni la temperatura en grados, sino en número bruto (D1 y D2). Además hay seis constantes de calibración (C1-C6). Necesita fórmulas matemáticas complejas, con coeficientes de fábrica, para arrojar datos reales de presión y temperatura.

**1. Funcionamiento sin mapa de registros, y constantes**
- **Dirección I2C** (`MS5607_ADDR = 0x77`): identifica al dispositivo en el bus I2C.
- **Comandos** (`#define`): en lugar de leer o escribir registros fijos, se envían comandos. Son `CMD_RESET`, las órdenes de conversión de alta resolución (`CMD_CONV_D1_4096` para presión y `CMD_CONV_D2_4096` para temperatura) y la orden de lectura de la memoria interna (`CMD_PROM_READ`).
- **La PROM y los coeficientes (C1 a C6):** cada sensor es único de fábrica. El fabricante quema 6 constantes de calibración en una memoria interna (PROM), que se almacenan en el array `C[]`:
  - C1: sensibilidad de presión.
  - C2: offset de presión.
  - C3 y C4: controlan la dependencia térmica de la sensibilidad y el offset.
  - C5 y C6: calibran la lectura de temperatura pura.

**2. Inicialización y validación (`ms5607_init`)**
- **Comprobación de presencia:** verifica que el dispositivo responde en la dirección I2C.
- **Reinicio (reset):** envía el comando de reinicio para que el sensor recargue su PROM interna.
- **Lectura de la PROM:** lee las 8 palabras de 16 bits de la memoria del sensor (los coeficientes de calibración y un campo final para el CRC).
- **Verificación CRC (`crc4`):** valida la integridad de la PROM mediante una función matemática de código de redundancia cíclica. Si un coeficiente estuviera corrupto, la altitud calculada fallaría estrepitosamente sin previo aviso.

**3. Conversión de datos brutos (`convert`)**

El sensor no entrega la presión en pascales ni la temperatura en grados, sino valores crudos llamados D1 (presión) y D2 (temperatura), los cuales varían según la temperatura física del silicio del chip:
1. Envía el comando de conversión para D1 o D2.
2. Espera unos 10 milisegundos (`T_CONV_MS`) a que el conversor ADC interno termine el cálculo de alta resolución.
3. Lee el resultado de 24 bits (`b[0]`, `b[1]`, `b[2]`) y se asegura de que no devuelva cero (lo que indicaría un timeout por leer antes de tiempo).

**4. Compensación matemática y orden superior (`ms5607_read`)**

Una vez obtenidos los datos crudos D1 y D2, se aplican las fórmulas de compensación:
- **Uso de enteros de 64 bits (`int64_t`):** al multiplicar variables como D1 por C1, o al elevar potencias según las notas de aplicación del fabricante, los números intermedios desbordan por completo los límites de 32 bits. El uso de `int64_t` evita que el cálculo se corrompa.
- **Corrección de segundo orden:** a temperaturas bajas (por debajo de 20 °C), el comportamiento del silicio cambia de forma no lineal. Durante el vuelo de un cohete, al atravesar capas atmosféricas muy frías (frecuentemente por debajo de −30 °C o −40 °C), esta corrección es obligatoria; de lo contrario, el error en el cálculo de la altitud barométrica sería de decenas de metros.

Finalmente, la función devuelve la temperatura en grados Celsius y la presión en pascales, listas para la navegación de la aviónica.

#### 8. `ina226.c`: el monitor energético y el conteo de culombios

**El problema de las baterías LiPo:** las baterías de polímero de litio tienen una curva de descarga que es estable el 80 % inicial y de repente cae en picado.

**Cómo funciona el INA226:**
- Se coloca en serie una resistencia de valor ultrapequeño y alta precisión (llamada shunt, por ejemplo de 10 mΩ).
- El chip mide la caída de voltaje infinitesimal que se produce al pasar la corriente a través de esa resistencia (ley de Ohm: V = I · R).
- Mediante el registro de calibración, le dices al chip los parámetros de tu hardware para que él mismo traduzca esa caída de tensión directamente en miliamperios (mA).
- **Integración de corriente (*coulomb counting*):** al conocer la corriente exacta que consume la aviónica segundo a segundo, el software puede integrar esos datos en el tiempo (Q = ∫ I dt). Esto permite calcular con precisión matemática la energía real que le queda a la batería, evitando sorpresas fatales en vuelo.

**1. Estructura y registros clave (`#define`)**
- **Identificación** (`REG_MANUF_ID = 0xFE`): espera el valor fijo 0x5449 (que corresponde a las letras «TI» de Texas Instruments en ASCII) para verificar que el chip está conectado correctamente.
- **Registros de medida:**
  - `REG_BUS_V` (0x02): mide la tensión de la barra (voltaje de la batería), con una escala fija de 1,25 mV por LSB.
  - `REG_CURRENT` (0x04): mide la corriente que atraviesa la resistencia shunt. Al ser un valor con signo (`int16_t`), permite detectar la dirección del flujo.
  - `REG_CALIB` (0x05): registro donde se escribe el valor matemático que le enseña al chip cómo traducir la caída de voltaje del shunt directamente a miliamperios.

**2. Comunicación de 16 bits (`write16` y `read16`)**

Como los registros del INA226 son de 16 bits y utilizan el formato MSB primero (*Most Significant Byte* primero), estas funciones auxiliares se encargan de empaquetar o desempaquetar los bytes para transmitirlos correctamente a través del bus I2C.

**3. Inicialización y calibración del hardware (`ina226_init`)**
- **Comprobación de ID:** lee el registro del fabricante para validar la presencia del sensor.
- **Cálculo de calibración:** utiliza las fórmulas del fabricante para configurar el chip en función del hardware real de la placa:
  - `current_lsb_a`: define la resolución mínima de la corriente (I_max / 32768).
  - `cal`: aplica la fórmula de fábrica (0,00512 / (current_lsb_a · r_shunt_ohm)) para que el INA226 calcule la corriente de forma interna mediante la ley de Ohm.
- **Configuración de muestreo** (`CONFIG_AVG16_CONT`): configura el chip para promediar 16 muestras y realizar conversiones continuas, tanto del shunt como del bus.

**4. Lectura de datos (`ina226_read`) y *coulomb counting***
- Lee el voltaje del bus y lo multiplica por `BUS_V_PER_LSB` para obtener los voltios reales.
- Lee el registro de corriente, lo convierte a un entero con signo (`int16_t`) y lo multiplica por la resolución calculada para obtener los amperios exactos.
- **Utilidad en el cohete:** al conocer la corriente consumida segundo a segundo, el software de la aviónica puede integrar estos datos en el tiempo (*coulomb counting*). Esto permite calcular con precisión matemática cuánta energía real le queda a la batería, evitando sorpresas fatales en pleno vuelo ante la caída abrupta de las LiPo.

#### 9. `sensors.c`

Son módulos fundamentales en el desarrollo de software embebido: la capa de unificación de sensores y su integración en el flujo principal.
- **`sensors_init`:** no se detiene si un sensor falla (no hay `return` a mitad); el fallo se registra en la salud y se continúa.
- **Lectura condicional (`sensors_read_all`):** evalúa dinámicamente qué sensores están operativos. Si un sensor que funcionaba empieza a fallar durante la ejecución, se marca automáticamente como no disponible, para evitar lecturas erróneas.
- **Gestión de datos mediante estructuras clave:**
  - `sensors_health_t`: contiene el estado de salud de cada componente (ideal para enviar por telemetría y saber desde tierra que funciona).
  - `sensors_snapshot_t`: toma una fotografía de los sensores junto a su marca de tiempo (`t_ms`), lista para ser guardada en la memoria flash o consumida por el filtro de Kalman.

#### 10. `main.c`

Todo va dentro de `USER CODE`, para no bloquear el resto de las cosas.
- **Prueba de integración rápida:** en el arranque se ejecuta `sensors_init()`, seguido de un `printf` que muestra en consola el estado de cada sensor. Esto permite verificar el hardware en segundos.
- **Optimización numérica sin `float`:** se imprimen enteros escalados (por ejemplo, mili-g o pascales) para evitar habilitar el soporte de `float` en el `printf` de la librería estándar reducida. Esto ahorra una cantidad considerable de memoria de programa (flash) y de RAM.
- **`HAL_Delay(100)`:** el uso de retardos bloqueantes (`HAL_Delay`) es solo una prueba de concepto inicial. En un entorno de vuelo real no es viable:
  - la IMU exige lecturas a alta frecuencia (1 kHz), guiadas por interrupciones físicas (pines como el PE6);
  - el barómetro no puede bloquear el procesador durante milisegundos esperando una conversión.
  
  La solución definitiva requiere pasar a FreeRTOS (tareas concurrentes) o a una máquina de estados no bloqueante.

### Pendiente

- **Contrastar con la ficha técnica** cada valor marcado `VERIFICAR`.
- **Fijar con el esquema de la placa** las direcciones I²C de los INA226 y del MS5607 y el valor del shunt. En el código hay valores de ejemplo.
- **Escribir el driver de los sensores analógicos:** giróscopo ADXRS649, continuidad, divisores y NTC. El ADC ya está configurado con sus 11 canales.
