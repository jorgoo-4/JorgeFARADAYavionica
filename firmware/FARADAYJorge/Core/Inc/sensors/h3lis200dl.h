/*
 * h3lis200dl.h
 *
 * Acelerómetro de alta g ST H3LIS200DL (±200 g, 8 bits) por SPI2 (CS en PE4).
 * Cubre la fase de empuje, que satura a la IMU (±32 g).
 */
#ifndef INC_SENSORS_H3LIS200DL_H_
#define INC_SENSORS_H3LIS200DL_H_

#include "sensors/sensor_types.h"

typedef struct {
  float ax_g;
  float ay_g;
  float az_g;
} h3lis200dl_data_t;

sens_status_t h3lis200dl_init(void);
sens_status_t h3lis200dl_read(h3lis200dl_data_t *out);

#endif /* INC_SENSORS_H3LIS200DL_H_ */
