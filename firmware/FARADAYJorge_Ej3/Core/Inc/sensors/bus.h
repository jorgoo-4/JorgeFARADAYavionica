/*
 * bus.h
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Capa común de acceso a los buses. Los drivers de sensores no llaman a la HAL
 * directamente: llaman a estas funciones. Así la lógica del CS, el bit de lectura
 * y los timeouts está escrita una sola vez.
 */
#ifndef INC_SENSORS_BUS_H_
#define INC_SENSORS_BUS_H_

#include "main.h"            /* HAL, tipos de la HAL y nombres de los pines de CubeMX */
#include "sensors/sensor_types.h"

/* Los "handles" los crea CubeMX en main.c. Con extern les decimos a los demás
 * archivos que existen y que están definidos en otro sitio. */
extern SPI_HandleTypeDef hspi1;
extern SPI_HandleTypeDef hspi2;
extern I2C_HandleTypeDef hi2c1;

/* Un dispositivo SPI = qué bus usa + qué pin es su chip-select. */
typedef struct {
  SPI_HandleTypeDef *hspi;
  GPIO_TypeDef      *cs_port;
  uint16_t           cs_pin;
} spi_dev_t;

HAL_StatusTypeDef spi_read(const spi_dev_t *d, uint8_t reg, uint8_t *buf, uint16_t n);
HAL_StatusTypeDef spi_write(const spi_dev_t *d, uint8_t reg, uint8_t val);

#define I2C_TIMEOUT_MS 5
HAL_StatusTypeDef i2c_read(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t reg, uint8_t *buf, uint16_t n);
HAL_StatusTypeDef i2c_write(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t reg, const uint8_t *buf, uint16_t n);
HAL_StatusTypeDef i2c_cmd(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t cmd);
HAL_StatusTypeDef i2c_recv(I2C_HandleTypeDef *hi2c, uint8_t addr7, uint8_t *buf, uint16_t n);

#endif /* INC_SENSORS_BUS_H_ */
