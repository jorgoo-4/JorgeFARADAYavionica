/*
 * ina226.h
 *
 * Monitor de tensión y corriente TI INA226 por I2C1. Hay dos: batería de vuelo
 * y batería de recuperación. Por eso el driver recibe "qué INA226" como parámetro.
 */
#ifndef INC_SENSORS_INA226_H_
#define INC_SENSORS_INA226_H_

#include "sensors/sensor_types.h"

typedef struct {
  uint8_t addr7;          /* dirección I2C (la fijan las patillas A0 y A1) */
  float   r_shunt_ohm;    /* resistencia shunt de la placa */
  float   i_max_a;        /* corriente máxima esperada: fija la resolución */
  float   current_lsb_a;  /* lo calcula ina226_init() */
} ina226_dev_t;

typedef struct {
  float bus_v;       /* tensión de la batería (V) */
  float current_a;   /* corriente (A); integrándola se cuentan culombios */
} ina226_data_t;

sens_status_t ina226_init(ina226_dev_t *dev);
sens_status_t ina226_read(const ina226_dev_t *dev, ina226_data_t *out);

#endif /* INC_SENSORS_INA226_H_ */
