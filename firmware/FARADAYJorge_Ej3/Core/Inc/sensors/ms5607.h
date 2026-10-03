/*
 * ms5607.h
 *
 * Barómetro TE MS5607 por I2C1. Altitud barométrica por debajo de ~30 km.
 */
#ifndef INC_SENSORS_MS5607_H_
#define INC_SENSORS_MS5607_H_

#include "sensors/sensor_types.h"

typedef struct {
  float pressure_pa;   /* presión (Pa) */
  float temp_c;        /* temperatura del sensor (°C) */
} ms5607_data_t;

sens_status_t ms5607_init(void);                 /* reset + lectura y comprobación (CRC) de la PROM */
sens_status_t ms5607_read(ms5607_data_t *out);  /* convierte D1 y D2 y aplica la compensación */

#endif /* INC_SENSORS_MS5607_H_ */
