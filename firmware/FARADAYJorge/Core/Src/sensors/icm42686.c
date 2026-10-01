/*
 * icm42686.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Driver de la IMU ICM-42686-P (SPI1, CS en PE3).
 * Todos los registros y valores están marcados VERIFICAR: hay que contrastarlos
 * con la ficha técnica de TDK (mapa de registros, banco 0) y anotar la página.
 */
#include "sensors/icm42686.h"
#include "sensors/bus.h"

/* Dispositivo SPI de la IMU: bus SPI1 y su chip-select. Los nombres de pin los genera
 * CubeMX en main.h a partir de la etiqueta que pusimos en el .ioc ("Chip Select IMU"). */
static const spi_dev_t imu_dev = {
  .hspi    = &hspi1,
  .cs_port = Chip_Select_IMU_GPIO_Port,
  .cs_pin  = Chip_Select_IMU_Pin
};

/* Registros clave (banco 0)                                          VERIFICAR */
#define REG_DEVICE_CFG  0x11   /* bit 0 = SOFT_RESET_CONFIG */
#define REG_TEMP_DATA1  0x1D   /* primero de los 14 bytes de datos */
#define REG_PWR_MGMT0   0x4E   /* encendido de acelerómetro y giróscopo */
#define REG_GYRO_CFG0   0x4F   /* bits 7:5 = fondo de escala, bits 3:0 = ODR */
#define REG_ACCEL_CFG0  0x50   /* bits 7:5 = fondo de escala, bits 3:0 = ODR */
#define REG_WHO_AM_I    0x75
#define VAL_WHO_AM_I    0x44   /* ICM-42686-P. Cuidado: el ICM-42688-P da 0x47 */

/* Valores de configuración                                           VERIFICAR */
#define FS_SEL_MAX      (0x0u << 5)  /* 000: ±4000 °/s en el giróscopo, ±32 g en el acelerómetro */
#define ODR_1KHZ        0x06u        /* 0110: 1 kHz. 0000 es un valor RESERVADO: no dejarlo a 0 */
#define PWR_LN_BOTH     0x0Fu        /* giróscopo y acelerómetro en modo de bajo ruido (LN) */

/* Sensibilidades con esos fondos de escala                           VERIFICAR */
#define ACCEL_LSB_PER_G    1024.0f   /* ±32 g    -> 32768 / 32  */
#define GYRO_LSB_PER_DPS   8.2f      /* ±4000 °/s -> 32768 / 4000 */
#define TEMP_LSB_PER_C     132.48f
#define TEMP_OFFSET_C      25.0f

/* Dos bytes con MSB primero -> entero de 16 bits con signo (complemento a dos). */
static int16_t be16(const uint8_t *p)
{
  return (int16_t)((uint16_t)(p[0] << 8) | p[1]);
}

sens_status_t icm42686_init(void)
{
  uint8_t id = 0;

  /* 1. ¿Está ahí y es quien esperamos? */
  if (spi_read(&imu_dev, REG_WHO_AM_I, &id, 1) != HAL_OK) return SENS_ERR_BUS;
  if (id != VAL_WHO_AM_I) return SENS_ERR_ID;

  /* 2. Reset por software: deja todos los registros en su valor de fábrica */
  if (spi_write(&imu_dev, REG_DEVICE_CFG, 0x01) != HAL_OK) return SENS_ERR_BUS;
  HAL_Delay(2);  /* la ficha pide al menos 1 ms tras el reset */

  /* 3. Confirmar que ha vuelto del reset */
  if (spi_read(&imu_dev, REG_WHO_AM_I, &id, 1) != HAL_OK) return SENS_ERR_BUS;
  if (id != VAL_WHO_AM_I) return SENS_ERR_ID;

  /* 4. Fondos de escala máximos (no saturar en el empuje) y 1 kHz de muestreo */
  if (spi_write(&imu_dev, REG_GYRO_CFG0,  FS_SEL_MAX | ODR_1KHZ) != HAL_OK) return SENS_ERR_BUS;
  if (spi_write(&imu_dev, REG_ACCEL_CFG0, FS_SEL_MAX | ODR_1KHZ) != HAL_OK) return SENS_ERR_BUS;

  /* 5. Encender los dos sensores en modo de bajo ruido */
  if (spi_write(&imu_dev, REG_PWR_MGMT0, PWR_LN_BOTH) != HAL_OK) return SENS_ERR_BUS;
  HAL_Delay(50);  /* el giróscopo tarda unas decenas de ms en dar datos válidos (VERIFICAR) */

  return SENS_OK;
}

sens_status_t icm42686_read(icm42686_data_t *out)
{
  uint8_t buf[14];

  /* Una sola ráfaga de 14 bytes desde TEMP_DATA1: temperatura, 3 aceleraciones y 3 giros
   * salen de la MISMA muestra (coherencia temporal). */
  if (spi_read(&imu_dev, REG_TEMP_DATA1, buf, sizeof buf) != HAL_OK) return SENS_ERR_BUS;

  out->temp_c = be16(&buf[0])  / TEMP_LSB_PER_C + TEMP_OFFSET_C;

  out->ax_g   = be16(&buf[2])  / ACCEL_LSB_PER_G;
  out->ay_g   = be16(&buf[4])  / ACCEL_LSB_PER_G;
  out->az_g   = be16(&buf[6])  / ACCEL_LSB_PER_G;

  out->gx_dps = be16(&buf[8])  / GYRO_LSB_PER_DPS;
  out->gy_dps = be16(&buf[10]) / GYRO_LSB_PER_DPS;
  out->gz_dps = be16(&buf[12]) / GYRO_LSB_PER_DPS;

  return SENS_OK;
}
