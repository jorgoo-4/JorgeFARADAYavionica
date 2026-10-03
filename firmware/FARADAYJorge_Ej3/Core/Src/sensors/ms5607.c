/*
 * ms5607.c
 *
 *  Created on: 1 oct 2026
 *      Author: jorge
 *
 * Driver del barómetro MS5607 (I2C1). A diferencia de los otros sensores, no tiene
 * mapa de registros: se le mandan COMANDOS (reset, leer PROM, convertir, leer ADC).
 * Cada unidad sale de fábrica con 6 coeficientes de calibración en su PROM, y la
 * presión real se calcula con ellos. Comandos y fórmulas: VERIFICAR en la ficha de TE
 * y en la nota de aplicación AN520 (CRC).
 */
#include "sensors/ms5607.h"
#include "sensors/bus.h"

/* Dirección I2C: 0x76 si CSB está a nivel alto, 0x77 si está a nivel bajo.
 * Depende de cómo se cablee CSB en la placa.                    VERIFICAR con el esquema */
#define MS5607_ADDR      0x77

/* Comandos                                                           VERIFICAR */
#define CMD_RESET        0x1E
#define CMD_PROM_READ    0xA0    /* + 2·i, i = 0…7 */
#define CMD_CONV_D1_4096 0x48    /* convertir presión con OSR 4096 (máxima resolución) */
#define CMD_CONV_D2_4096 0x58    /* convertir temperatura con OSR 4096 */
#define CMD_ADC_READ     0x00
#define T_CONV_MS        10      /* OSR 4096 tarda ~9 ms: si se lee antes, el ADC devuelve 0 */

static uint16_t C[8];            /* PROM: C[1]…C[6] coeficientes, C[7] lleva el CRC */

/* CRC4 de la PROM según la nota de aplicación AN520.                  VERIFICAR */
static uint8_t crc4(uint16_t prom[8])
{
  uint16_t rem = 0;
  uint16_t crc_read = prom[7];
  prom[7] &= 0xFF00;                       /* el CRC se calcula con sus propios 4 bits a cero */
  for (int cnt = 0; cnt < 16; cnt++) {
    rem ^= (cnt & 1) ? (prom[cnt >> 1] & 0x00FF) : (prom[cnt >> 1] >> 8);
    for (int bit = 8; bit > 0; bit--) {
      rem = (rem & 0x8000) ? (uint16_t)((rem << 1) ^ 0x3000) : (uint16_t)(rem << 1);
    }
  }
  prom[7] = crc_read;                      /* deja la PROM como estaba */
  return (uint8_t)((rem >> 12) & 0x0F);
}

/* Lanza una conversión, espera y lee el resultado de 24 bits. */
static sens_status_t convert(uint8_t cmd, uint32_t *raw)
{
  uint8_t b[3];
  if (i2c_cmd(&hi2c1, MS5607_ADDR, cmd) != HAL_OK) return SENS_ERR_BUS;
  HAL_Delay(T_CONV_MS);
  if (i2c_cmd(&hi2c1, MS5607_ADDR, CMD_ADC_READ) != HAL_OK) return SENS_ERR_BUS;
  if (i2c_recv(&hi2c1, MS5607_ADDR, b, 3) != HAL_OK) return SENS_ERR_BUS;
  *raw = ((uint32_t)b[0] << 16) | ((uint32_t)b[1] << 8) | b[2];
  return (*raw == 0) ? SENS_ERR_TIMEOUT : SENS_OK;   /* 0 = se leyó antes de terminar la conversión */
}

sens_status_t ms5607_init(void)
{
  /* 1. ¿Hay alguien en esa dirección? */
  if (HAL_I2C_IsDeviceReady(&hi2c1, MS5607_ADDR << 1, 3, I2C_TIMEOUT_MS) != HAL_OK) return SENS_ERR_ID;

  /* 2. Reset: recarga la PROM en los registros internos */
  if (i2c_cmd(&hi2c1, MS5607_ADDR, CMD_RESET) != HAL_OK) return SENS_ERR_BUS;
  HAL_Delay(3);

  /* 3. Leer las 8 palabras de 16 bits de la PROM */
  for (uint8_t i = 0; i < 8; i++) {
    uint8_t b[2];
    if (i2c_cmd(&hi2c1, MS5607_ADDR, (uint8_t)(CMD_PROM_READ + 2 * i)) != HAL_OK) return SENS_ERR_BUS;
    if (i2c_recv(&hi2c1, MS5607_ADDR, b, 2) != HAL_OK) return SENS_ERR_BUS;
    C[i] = (uint16_t)((b[0] << 8) | b[1]);
  }

  /* 4. Comprobar el CRC: un coeficiente corrupto daría alturas falsas sin ningún aviso */
  if (crc4(C) != (C[7] & 0x000F)) return SENS_ERR_CRC;
  return SENS_OK;
}

sens_status_t ms5607_read(ms5607_data_t *out)
{
  uint32_t D1, D2;
  sens_status_t st;
  if ((st = convert(CMD_CONV_D1_4096, &D1)) != SENS_OK) return st;   /* presión cruda */
  if ((st = convert(CMD_CONV_D2_4096, &D2)) != SENS_OK) return st;   /* temperatura cruda */

  /* Compensación de primer orden del MS5607 (OJO: la del MS5611 usa otros exponentes). VERIFICAR */
  int64_t dT   = (int64_t)D2 - ((int64_t)C[5] << 8);
  int64_t TEMP = 2000 + (dT * C[6]) / (1LL << 23);                    /* centésimas de °C */
  int64_t OFF  = ((int64_t)C[2] << 17) + ((int64_t)C[4] * dT) / (1LL << 6);
  int64_t SENS = ((int64_t)C[1] << 16) + ((int64_t)C[3] * dT) / (1LL << 7);

  /* Segundo orden: por debajo de 20 °C (en altura siempre) la de primer orden se queda corta. */
  if (TEMP < 2000) {
    int64_t T2    = (dT * dT) / (1LL << 31);
    int64_t d     = TEMP - 2000;
    int64_t OFF2  = 61 * d * d / 16;
    int64_t SENS2 = 2 * d * d;
    if (TEMP < -1500) {
      int64_t e = TEMP + 1500;
      OFF2  += 15 * e * e;
      SENS2 += 8 * e * e;
    }
    TEMP -= T2;
    OFF  -= OFF2;
    SENS -= SENS2;
  }

  int64_t P = (((int64_t)D1 * SENS) / (1LL << 21) - OFF) / (1LL << 15);   /* Pa (centésimas de mbar) */

  out->temp_c      = TEMP / 100.0f;
  out->pressure_pa = (float)P;
  return SENS_OK;
}
