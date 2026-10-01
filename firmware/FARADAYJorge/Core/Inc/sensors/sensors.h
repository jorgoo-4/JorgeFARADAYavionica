/*
 * sensors.h
 *
 * Punto único de entrada al subsistema de sensores: main.c (y en el futuro las
 * tareas de FreeRTOS) solo conoce estas funciones, no cada driver por separado.
 */
#ifndef INC_SENSORS_SENSORS_H_
#define INC_SENSORS_SENSORS_H_

#include "sensors/icm42686.h"
#include "sensors/h3lis200dl.h"
#include "sensors/rm3100.h"
#include "sensors/ms5607.h"
#include "sensors/ina226.h"

/* Estado de cada sensor: SENS_OK o el motivo por el que no está disponible. */
typedef struct {
  sens_status_t imu, hig, mag, baro, bat_vuelo, bat_recup;
} sensors_health_t;

/* Última lectura de todos los sensores (una "foto" del estado del cohete). */
typedef struct {
  uint32_t          t_ms;   /* instante de la lectura (HAL_GetTick) */
  icm42686_data_t   imu;
  h3lis200dl_data_t hig;
  rm3100_data_t     mag;
  ms5607_data_t     baro;
  ina226_data_t     bat_vuelo;
  ina226_data_t     bat_recup;
} sensors_snapshot_t;

void sensors_init(sensors_health_t *h);
void sensors_read_all(sensors_health_t *h, sensors_snapshot_t *s);
const char *sens_status_str(sens_status_t st);

#endif /* INC_SENSORS_SENSORS_H_ */
