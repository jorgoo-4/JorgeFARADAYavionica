/*
 * sensors.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Inicializa y lee todos los sensores. Regla de diseño: un sensor que falla NO
 * detiene a los demás. Se apunta su estado y el resto del sistema sigue; el filtro
 * y la telemetría sabrán qué sensores hay disponibles.
 */
#include "sensors/sensors.h"
#include "main.h"

/* Los dos INA226. Direcciones, shunt e I_max dependen del hardware de la placa:
 * los valores de abajo son de EJEMPLO.                     PENDIENTE: fijarlos con el esquema */
static ina226_dev_t bat_vuelo = { .addr7 = 0x40, .r_shunt_ohm = 0.010f, .i_max_a = 5.0f };
static ina226_dev_t bat_recup = { .addr7 = 0x41, .r_shunt_ohm = 0.010f, .i_max_a = 5.0f };

void sensors_init(sensors_health_t *h)
{
  h->imu       = icm42686_init();
  h->hig       = h3lis200dl_init();
  h->mag       = rm3100_init();
  h->baro      = ms5607_init();
  h->bat_vuelo = ina226_init(&bat_vuelo);
  h->bat_recup = ina226_init(&bat_recup);
}

/* Solo se lee un sensor si se inicializó bien; si una lectura falla, se marca su estado. */
void sensors_read_all(sensors_health_t *h, sensors_snapshot_t *s)
{
  s->t_ms = HAL_GetTick();
  if (h->imu       == SENS_OK) h->imu       = icm42686_read(&s->imu);
  if (h->hig       == SENS_OK) h->hig       = h3lis200dl_read(&s->hig);
  if (h->mag       == SENS_OK) h->mag       = rm3100_read(&s->mag);
  if (h->baro      == SENS_OK) h->baro      = ms5607_read(&s->baro);
  if (h->bat_vuelo == SENS_OK) h->bat_vuelo = ina226_read(&bat_vuelo, &s->bat_vuelo);
  if (h->bat_recup == SENS_OK) h->bat_recup = ina226_read(&bat_recup, &s->bat_recup);
}

const char *sens_status_str(sens_status_t st)
{
  switch (st) {
    case SENS_OK:          return "OK";
    case SENS_ERR_BUS:     return "ERROR DE BUS";
    case SENS_ERR_ID:      return "NO RESPONDE / ID INCORRECTO";
    case SENS_ERR_TIMEOUT: return "TIMEOUT";
    case SENS_ERR_CRC:     return "CRC INCORRECTO";
    default:               return "?";
  }
}
