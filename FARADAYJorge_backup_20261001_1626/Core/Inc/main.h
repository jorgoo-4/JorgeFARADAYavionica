/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32h7xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

void HAL_TIM_MspPostInit(TIM_HandleTypeDef *htim);

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define Chip_Select_IMU_Pin GPIO_PIN_3
#define Chip_Select_IMU_GPIO_Port GPIOE
#define Chip_Select_aceler_metro_de_altas_g_Pin GPIO_PIN_4
#define Chip_Select_aceler_metro_de_altas_g_GPIO_Port GPIOE
#define Chip_Select_magnet_metro_Pin GPIO_PIN_5
#define Chip_Select_magnet_metro_GPIO_Port GPIOE
#define interrupciones_sensores_Pin GPIO_PIN_6
#define interrupciones_sensores_GPIO_Port GPIOE
#define Reserva_Pin GPIO_PIN_0
#define Reserva_GPIO_Port GPIOF
#define ReservaF1_Pin GPIO_PIN_1
#define ReservaF1_GPIO_Port GPIOF
#define Memoria_Flash_NOR_Pin GPIO_PIN_6
#define Memoria_Flash_NOR_GPIO_Port GPIOF
#define Memoria_Flash_NORF7_Pin GPIO_PIN_7
#define Memoria_Flash_NORF7_GPIO_Port GPIOF
#define Memoria_Flash_NORF8_Pin GPIO_PIN_8
#define Memoria_Flash_NORF8_GPIO_Port GPIOF
#define Memoria_Flash_NORF9_Pin GPIO_PIN_9
#define Memoria_Flash_NORF9_GPIO_Port GPIOF
#define Memoria_Flash_NORF10_Pin GPIO_PIN_10
#define Memoria_Flash_NORF10_GPIO_Port GPIOF
#define H3LIS200DL_y_RM3100_Pin GPIO_PIN_2
#define H3LIS200DL_y_RM3100_GPIO_Port GPIOC
#define H3LIS200DL_y_RM3100C3_Pin GPIO_PIN_3
#define H3LIS200DL_y_RM3100C3_GPIO_Port GPIOC
#define PPS_del_GNSS_Pin GPIO_PIN_0
#define PPS_del_GNSS_GPIO_Port GPIOA
#define IMU_ICM_42686_P_Pin GPIO_PIN_5
#define IMU_ICM_42686_P_GPIO_Port GPIOA
#define interrupciones_sensoresE7_Pin GPIO_PIN_7
#define interrupciones_sensoresE7_GPIO_Port GPIOE
#define interrupciones_sensoresE8_Pin GPIO_PIN_8
#define interrupciones_sensoresE8_GPIO_Port GPIOE
#define servo_a_50_Hz_Pin GPIO_PIN_9
#define servo_a_50_Hz_GPIO_Port GPIOE
#define breakwire_1_Pin GPIO_PIN_10
#define breakwire_1_GPIO_Port GPIOE
#define breakwire_2_Pin GPIO_PIN_11
#define breakwire_2_GPIO_Port GPIOE
#define interruptor_de_armado_Pin GPIO_PIN_12
#define interruptor_de_armado_GPIO_Port GPIOE
#define ST_LINK_Pin GPIO_PIN_11
#define ST_LINK_GPIO_Port GPIOB
#define H3LIS200DL_y_RM3100B13_Pin GPIO_PIN_13
#define H3LIS200DL_y_RM3100B13_GPIO_Port GPIOB
#define ST_LINKD8_Pin GPIO_PIN_8
#define ST_LINKD8_GPIO_Port GPIOD
#define zumbador_a__2_7_kHz_Pin GPIO_PIN_14
#define zumbador_a__2_7_kHz_GPIO_Port GPIOD
#define RADIO_Pin GPIO_PIN_6
#define RADIO_GPIO_Port GPIOC
#define RADIOC7_Pin GPIO_PIN_7
#define RADIOC7_GPIO_Port GPIOC
#define IMU_ICM_42686_PD7_Pin GPIO_PIN_7
#define IMU_ICM_42686_PD7_GPIO_Port GPIOD
#define IMU_ICM_42686_PG9_Pin GPIO_PIN_9
#define IMU_ICM_42686_PG9_GPIO_Port GPIOG
#define Sensores_de_vigilancia_Pin GPIO_PIN_6
#define Sensores_de_vigilancia_GPIO_Port GPIOB
#define Sensores_de_vigilanciaB7_Pin GPIO_PIN_7
#define Sensores_de_vigilanciaB7_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
