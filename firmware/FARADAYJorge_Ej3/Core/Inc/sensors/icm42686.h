/*
 * icm42686.h
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * IMU de 6 ejes TDK InvenSense ICM-42686-P por SPI1 (CS en PE3).
 */
#ifndef INC_SENSORS_ICM42686_H_
#define INC_SENSORS_ICM42686_H_

#include "sensors/sensor_types.h"

/* 1. Estructura donde guardamos los datos ya convertidos a unidades físicas */
typedef struct {
  float ax_g;    /* aceleración en X (g) */
  float ay_g;    /* aceleración en Y (g) */
  float az_g;    /* aceleración en Z (g) */
  float gx_dps;  /* velocidad angular en X (grados por segundo) */
  float gy_dps;  /* velocidad angular en Y (grados por segundo) */
  float gz_dps;  /* velocidad angular en Z (grados por segundo) */
  float temp_c;  /* temperatura interna (°C): sirve para compensar la deriva del giróscopo */
} icm42686_data_t;

/* 2. Prototipos de las funciones principales del driver */
sens_status_t icm42686_init(void);                   /* identifica, resetea y configura el sensor */
sens_status_t icm42686_read(icm42686_data_t *out);  /* lee en ráfaga y convierte a unidades físicas */

#endif /* INC_SENSORS_ICM42686_H_ */
