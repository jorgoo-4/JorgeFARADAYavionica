/*
 * rm3100.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Driver del magnetómetro RM3100 (SPI2, CS en PE5). SPI máx. 1 MHz: por eso SPI2 va a ~780 kHz.
 * Se usa en modo de medida única (POLL): pido una medida, espero a que esté y la leo.
 * Registros y valores: VERIFICAR en la ficha técnica de PNI.
 */
#include "sensors/rm3100.h"
#include "sensors/bus.h"

static const spi_dev_t mag_dev = {
  .hspi    = &hspi2,
  .cs_port = Chip_Select_magnet_metro_GPIO_Port,
  .cs_pin  = Chip_Select_magnet_metro_Pin
};

/* Registros                                                          VERIFICAR */
#define REG_POLL    0x00   /* escribir aquí pide una medida única */
#define REG_CCX_MSB 0x04   /* número de ciclos por eje: X 0x04-0x05, Y 0x06-0x07, Z 0x08-0x09 */
#define REG_MX      0x24   /* 9 bytes: X, Y, Z en 24 bits con signo, MSB primero */
#define REG_STATUS  0x34   /* bit 7 = DRDY (dato listo) */
#define REG_REVID   0x36
#define VAL_REVID   0x22

/* Configuración                                                      VERIFICAR */
#define POLL_XYZ        0x70u   /* bits 4, 5 y 6: medir X, Y y Z */
#define STATUS_DRDY     0x80u
#define CYCLE_COUNT     200u    /* valor de fábrica: compromiso entre ruido y tiempo de medida */
#define LSB_PER_UT      75.0f   /* ganancia con 200 ciclos */
#define MEAS_TIMEOUT_MS 20u     /* margen sobre el tiempo de medida de 3 ejes a 200 ciclos */

/* 3 bytes MSB primero -> entero de 32 bits con signo (el dato es de 24 bits). */
static int32_t be24(const uint8_t *p)
{
  int32_t v = ((int32_t)p[0] << 16) | ((int32_t)p[1] << 8) | p[2];
  if (v & 0x800000) v |= (int32_t)0xFF000000;   /* extensión de signo: si el bit 23 es 1, es negativo */
  return v;
}

sens_status_t rm3100_init(void)
{
  uint8_t rev = 0;
  if (spi_read(&mag_dev, REG_REVID, &rev, 1) != HAL_OK) return SENS_ERR_BUS;
  if (rev != VAL_REVID) return SENS_ERR_ID;

  /* Fijar explícitamente los ciclos de los tres ejes (no fiarse del valor por defecto):
   * la ganancia LSB_PER_UT solo es válida con este número de ciclos. */
  for (uint8_t eje = 0; eje < 3; eje++) {
    uint8_t reg = REG_CCX_MSB + 2 * eje;
    if (spi_write(&mag_dev, reg,     (uint8_t)(CYCLE_COUNT >> 8))   != HAL_OK) return SENS_ERR_BUS;
    if (spi_write(&mag_dev, reg + 1, (uint8_t)(CYCLE_COUNT & 0xFF)) != HAL_OK) return SENS_ERR_BUS;
  }
  return SENS_OK;
}

sens_status_t rm3100_read(rm3100_data_t *out)
{
  /* 1. Pedir una medida de los tres ejes */
  if (spi_write(&mag_dev, REG_POLL, POLL_XYZ) != HAL_OK) return SENS_ERR_BUS;

  /* 2. Esperar a que esté lista, con límite de tiempo: nunca un while sin salida */
  uint32_t t0 = HAL_GetTick();
  uint8_t status = 0;
  do {
    if (spi_read(&mag_dev, REG_STATUS, &status, 1) != HAL_OK) return SENS_ERR_BUS;
    if (HAL_GetTick() - t0 > MEAS_TIMEOUT_MS) return SENS_ERR_TIMEOUT;
  } while (!(status & STATUS_DRDY));

  /* 3. Leer los 9 bytes en ráfaga y convertir */
  uint8_t buf[9];
  if (spi_read(&mag_dev, REG_MX, buf, sizeof buf) != HAL_OK) return SENS_ERR_BUS;
  out->mx_ut = be24(&buf[0]) / LSB_PER_UT;
  out->my_ut = be24(&buf[3]) / LSB_PER_UT;
  out->mz_ut = be24(&buf[6]) / LSB_PER_UT;
  return SENS_OK;
}
