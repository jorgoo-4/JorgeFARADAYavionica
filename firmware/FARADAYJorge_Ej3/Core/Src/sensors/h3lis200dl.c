/*
 * h3lis200dl.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Driver del acelerómetro de alta g H3LIS200DL (SPI2, CS en PE4).
 * SPI2 está en modo 3 (CPOL alto, CPHA 2.º flanco) porque este sensor lo necesita.
 * Registros y valores: VERIFICAR en la ficha técnica de ST.
 */
#include "sensors/h3lis200dl.h"
#include "sensors/bus.h"

static const spi_dev_t hig_dev = {
  .hspi    = &hspi2,
  .cs_port = Chip_Select_aceler_metro_de_altas_g_GPIO_Port,
  .cs_pin  = Chip_Select_aceler_metro_de_altas_g_Pin
};

/* Registros                                                          VERIFICAR */
#define REG_WHO_AM_I   0x0F
#define VAL_WHO_AM_I   0x32
#define REG_CTRL_REG1  0x20   /* bits 7:5 = modo, bits 4:3 = ODR, bits 2:0 = ejes Z, Y, X activados */
#define REG_CTRL_REG4  0x23   /* bit 7 = BDU, bit 4 = fondo de escala */
#define REG_OUT_X      0x29   /* cada eje es UN byte con signo (es un sensor de 8 bits) */
#define REG_OUT_Y      0x2B
#define REG_OUT_Z      0x2D

/* Configuración                                                      VERIFICAR */
#define CTRL1_NORMAL_1KHZ_XYZ  0x3Fu   /* 001 (normal) | 11 (1000 Hz) | 111 (X, Y y Z) */
#define CTRL4_BDU_200G         0x90u   /* BDU = 1 | FS = 1 (±200 g) */
#define G_PER_DIGIT            1.56f   /* sensibilidad con ±200 g */

sens_status_t h3lis200dl_init(void)
{
  uint8_t id = 0;
  if (spi_read(&hig_dev, REG_WHO_AM_I, &id, 1) != HAL_OK) return SENS_ERR_BUS;
  if (id != VAL_WHO_AM_I) return SENS_ERR_ID;

  /* BDU (Block Data Update): el sensor no cambia un dato mientras lo leemos */
  if (spi_write(&hig_dev, REG_CTRL_REG4, CTRL4_BDU_200G) != HAL_OK) return SENS_ERR_BUS;
  /* Encender: modo normal, 1 kHz, tres ejes */
  if (spi_write(&hig_dev, REG_CTRL_REG1, CTRL1_NORMAL_1KHZ_XYZ) != HAL_OK) return SENS_ERR_BUS;
  return SENS_OK;
}

sens_status_t h3lis200dl_read(h3lis200dl_data_t *out)
{
  uint8_t x, y, z;
  /* Tres lecturas de un byte: los registros de salida no son contiguos (0x29, 0x2B, 0x2D) */
  if (spi_read(&hig_dev, REG_OUT_X, &x, 1) != HAL_OK) return SENS_ERR_BUS;
  if (spi_read(&hig_dev, REG_OUT_Y, &y, 1) != HAL_OK) return SENS_ERR_BUS;
  if (spi_read(&hig_dev, REG_OUT_Z, &z, 1) != HAL_OK) return SENS_ERR_BUS;

  /* (int8_t): el byte viene en complemento a dos, de −128 a +127 */
  out->ax_g = (int8_t)x * G_PER_DIGIT;
  out->ay_g = (int8_t)y * G_PER_DIGIT;
  out->az_g = (int8_t)z * G_PER_DIGIT;
  return SENS_OK;
}
