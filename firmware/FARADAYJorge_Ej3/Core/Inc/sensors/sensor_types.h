/*
 * sensor_types.h
 *
 * Tipos comunes a todos los drivers de sensores.
 * Va en su propio archivo porque lo incluyen todos: si estuviera dentro de un
 * driver concreto, los demás dependerían de ese driver sin motivo.
 */
#ifndef INC_SENSORS_SENSOR_TYPES_H_
#define INC_SENSORS_SENSOR_TYPES_H_

#include <stdint.h>

/* Resultado de cualquier función de un driver. Nunca se bloquea: se devuelve un código. */
typedef enum {
  SENS_OK = 0,        /* todo bien */
  SENS_ERR_BUS,       /* la transacción SPI/I2C falló (timeout, NACK, bus ocupado) */
  SENS_ERR_ID,        /* el sensor contesta, pero no es quien esperábamos (o no contesta nada) */
  SENS_ERR_TIMEOUT,   /* el sensor no tuvo el dato listo a tiempo */
  SENS_ERR_CRC        /* datos internos corruptos (p. ej. la PROM del MS5607) */
} sens_status_t;

#endif /* INC_SENSORS_SENSOR_TYPES_H_ */
