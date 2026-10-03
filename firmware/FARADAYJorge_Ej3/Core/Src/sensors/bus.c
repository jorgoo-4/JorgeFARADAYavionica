/*
 * bus.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Implementación de la capa común de buses (ver bus.h).
 */
#include "sensors/bus.h"

#define SPI_TIMEOUT_MS 5
#define SPI_READ_BIT   0x80   /* ICM-42686-P, H3LIS200DL y RM3100: bit 7 = 1 significa lectura (VERIFICAR en cada ficha) */

/* ---------------------------------------------------------------- SPI */

/* Lee n bytes empezando en el registro reg.
 * Trama: CS abajo -> [reg | 0x80] -> n bytes de respuesta -> CS arriba. */
HAL_StatusTypeDef spi_read(const spi_dev_t *d, uint8_t reg, uint8_t *buf, uint16_t n)
{
  uint8_t addr = reg | SPI_READ_BIT;
  HAL_GPIO_WritePin(d->cs_port, d->cs_pin, GPIO_PIN_RESET);                     /* 1. selecciono el sensor */
  HAL_StatusTypeDef st = HAL_SPI_Transmit(d->hspi, &addr, 1, SPI_TIMEOUT_MS);  /* 2. le digo qué registro */
  if (st == HAL_OK) st = HAL_SPI_Receive(d->hspi, buf, n, SPI_TIMEOUT_MS);    /* 3. recibo los datos */
  HAL_GPIO_WritePin(d->cs_port, d->cs_pin, GPIO_PIN_SET);                       /* 4. libero SIEMPRE, haya error o no */
  return st;
}

/* Escribe un byte en el registro reg. Trama: CS abajo -> [reg & 0x7F, val] -> CS arriba.
 * Los dos bytes van en una sola transferencia para que no haya hueco entre ellos. */
HAL_StatusTypeDef spi_write(const spi_dev_t *d, uint8_t reg, uint8_t val)
{
  uint8_t tx[2] = { (uint8_t)(reg & 0x7F), val };  /* bit 7 = 0: escritura */
  HAL_GPIO_WritePin(d->cs_port, d->cs_pin, GPIO_PIN_RESET);
  HAL_StatusTypeDef st = HAL_SPI_Transmit(d->hspi, tx, 2, SPI_TIMEOUT_MS);
  HAL_GPIO_WritePin(d->cs_port, d->cs_pin, GPIO_PIN_SET);
  return st;
}

/* ---------------------------------------------------------------- I2C */
/* La HAL quiere la dirección de 7 bits desplazada un bit a la izquierda (el bit 0
 * es el de lectura/escritura y lo pone ella). Es el error más típico con I2C en STM32. */

/* Sensores con mapa de registros (INA226): escribo el número de registro y leo n bytes. */
HAL_StatusTypeDef i2c_read(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t reg, uint8_t *buf, uint16_t n)
{
  return HAL_I2C_Mem_Read(hi2c, (uint16_t)(addr7 << 1), reg, I2C_MEMADD_SIZE_8BIT, buf, n, I2C_TIMEOUT_MS);
}

HAL_StatusTypeDef i2c_write(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t reg, const uint8_t *buf, uint16_t n)
{
  return HAL_I2C_Mem_Write(hi2c, (uint16_t)(addr7 << 1), reg, I2C_MEMADD_SIZE_8BIT, (uint8_t *)buf, n, I2C_TIMEOUT_MS);
}

/* Sensores por comandos (MS5607): no hay registros, se envía un byte de comando... */
HAL_StatusTypeDef i2c_cmd(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t cmd)
{
  return HAL_I2C_Master_Transmit(hi2c, (uint16_t)(addr7 << 1), &cmd, 1, I2C_TIMEOUT_MS);
}

/* ...y luego se leen los bytes de respuesta. */
HAL_StatusTypeDef i2c_recv(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t *buf, uint16_t n)
{
  return HAL_I2C_Master_Receive(hi2c, (uint16_t)(addr7 << 1), buf, n, I2C_TIMEOUT_MS);
}
