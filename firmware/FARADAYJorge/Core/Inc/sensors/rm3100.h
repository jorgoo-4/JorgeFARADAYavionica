/*
 * rm3100.h
 *
 * Magnetómetro de 3 ejes PNI RM3100 por SPI2 (CS en PE5).
 * Referencia de rumbo (guiñada) cuando no hay GNSS.
 */
#ifndef INC_SENSORS_RM3100_H_
#define INC_SENSORS_RM3100_H_

#include "sensors/sensor_types.h"

typedef struct {
  float mx_ut;   /* campo magnético en X (microtesla) */
  float my_ut;
  float mz_ut;
} rm3100_data_t;

sens_status_t rm3100_init(void);
sens_status_t rm3100_read(rm3100_data_t *out);   /* lanza una medida, espera y lee */

#endif /* INC_SENSORS_RM3100_H_ */
