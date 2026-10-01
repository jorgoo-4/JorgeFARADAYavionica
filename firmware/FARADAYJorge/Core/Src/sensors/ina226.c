/*
 * ina226.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Driver del monitor de batería INA226 (I2C1). Registros de 16 bits, MSB primero.
 * Registros, escalas y fórmula de calibración: VERIFICAR en la ficha de TI.
 */
#include "sensors/ina226.h"
#include "sensors/bus.h"

/* Registros                                                          VERIFICAR */
#define REG_CONFIG    0x00
#define REG_BUS_V     0x02   /* 1,25 mV por LSB */
#define REG_CURRENT   0x04   /* con signo; escala = current_lsb */
#define REG_CALIB     0x05
#define REG_MANUF_ID  0xFE
#define VAL_MANUF_ID  0x5449 /* "TI" en ASCII */

/* Configuración                                                      VERIFICAR */
#define CONFIG_AVG16_CONT  0x4527u   /* promedio de 16 muestras, conversión continua de shunt y bus */
#define BUS_V_PER_LSB      0.00125f

static sens_status_t write16(uint8_t addr, uint8_t reg, uint16_t v)
{
  uint8_t b[2] = { (uint8_t)(v >> 8), (uint8_t)(v & 0xFF) };   /* MSB primero */
  return i2c_write(&hi2c1, addr, reg, b, 2) == HAL_OK ? SENS_OK : SENS_ERR_BUS;
}

static sens_status_t read16(uint8_t addr, uint8_t reg, uint16_t *v)
{
  uint8_t b[2];
  if (i2c_read(&hi2c1, addr, reg, b, 2) != HAL_OK) return SENS_ERR_BUS;
  *v = (uint16_t)((b[0] << 8) | b[1]);
  return SENS_OK;
}

sens_status_t ina226_init(ina226_dev_t *dev)
{
  uint16_t id = 0;
  if (read16(dev->addr7, REG_MANUF_ID, &id) != SENS_OK) return SENS_ERR_BUS;
  if (id != VAL_MANUF_ID) return SENS_ERR_ID;

  /* Calibración: el chip calcula la corriente él solo a partir de la tensión del shunt.
   *   current_lsb = I_max / 2^15            (resolución de corriente)
   *   CAL         = 0,00512 / (current_lsb · R_shunt)                    VERIFICAR */
  dev->current_lsb_a = dev->i_max_a / 32768.0f;
  uint16_t cal = (uint16_t)(0.00512f / (dev->current_lsb_a * dev->r_shunt_ohm));

  if (write16(dev->addr7, REG_CONFIG, CONFIG_AVG16_CONT) != SENS_OK) return SENS_ERR_BUS;
  if (write16(dev->addr7, REG_CALIB, cal) != SENS_OK) return SENS_ERR_BUS;
  return SENS_OK;
}

sens_status_t ina226_read(const ina226_dev_t *dev, ina226_data_t *out)
{
  uint16_t v, i;
  if (read16(dev->addr7, REG_BUS_V, &v) != SENS_OK) return SENS_ERR_BUS;
  if (read16(dev->addr7, REG_CURRENT, &i) != SENS_OK) return SENS_ERR_BUS;
  out->bus_v     = v * BUS_V_PER_LSB;
  out->current_a = (int16_t)i * dev->current_lsb_a;   /* (int16_t): la corriente puede ser negativa (carga) */
  return SENS_OK;
}
