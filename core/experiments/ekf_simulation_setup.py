# core/experiments/ekf_simulation_setup.py
# -*- coding: utf-8 -*-
"""
Конфигурация симуляции для тестирования EKF оценки SOC.
Включает истинную модель батареи, генераторы тока/температуры,
генератор шума, сумматор шума и сам EKF.
"""

from typing import Optional, Union
import numpy as np
from pathlib import Path

from .simulation_setup import SimulationSetup
from ..simulation_base.simulation_engine import SimulationEngine
from ..elements.generators.constant_generator import ConstantGenerator
from ..elements.generators.cyclic_profile_generator import CyclicProfileGenerator
from ..elements.generators.noise_generator import NoiseGenerator
from ..elements.transformers.battery_thevenin_1rc import BatteryThevenin1RC
from ..elements.transformers.noise_adder import NoiseAdderTransformator
from ..elements.transformers.ekf_soc_estimator import EKFSOCEstimator
from ..elements.inspectors.data_logger import DataLogger
from apps.utils.config import AppContext

from ..data.param_tables import DEFAULT_PARAM_TABLES

class EKFSimulationSetup(SimulationSetup):
    """
    Создаёт и связывает объекты для эксперимента с EKF.
    """

    def __init__(
        self,
        engine: SimulationEngine,
        records_path: Optional[Path] = None,
        current_mode: str = 'constant',
        current_value: float = 1.0,
        current_profile: Optional[list] = None,
        temperature_value: float = 25.0,
        battery_params: Optional[dict] = None,
        noise_sigma: float = 0.01,
        noise_bias: float = 0.0,
        ekf_params: Optional[dict] = None
    ):
        """
        Args:
            engine: движок симуляции.
            current_mode: 'constant' или 'cyclic'.
            current_value: значение тока для режима 'constant' (А).
            current_profile: список значений тока для режима 'cyclic'.
            temperature_value: значение температуры (°C).
            battery_params: словарь параметров для BatteryThevenin1RC.
            noise_sigma: СКО шума измерения напряжения.
            noise_bias: смещение шума.
            ekf_params: словарь параметров для EKFSOCEstimator (Q, R, P0, x0).
        """
        super().__init__(engine)
        self.current_mode = current_mode
        self.current_value = current_value
        self.current_profile = current_profile
        self.temperature_value = temperature_value
        self.battery_params = battery_params if battery_params is not None else {}
        self.noise_sigma = noise_sigma
        self.noise_bias = noise_bias
        self.ekf_params = ekf_params if ekf_params is not None else {}
        self.records_path = records_path

        # Ссылки на создаваемые объекты
        self.battery: Optional[BatteryThevenin1RC] = None
        self.current_gen: Optional[Union[ConstantGenerator, CyclicProfileGenerator]] = None
        self.temp_gen: Optional[ConstantGenerator] = None
        self.voltage_noise_gen: Optional[NoiseGenerator] = None
        self.noise_adder: Optional[NoiseAdderTransformator] = None
        self.ekf: Optional[EKFSOCEstimator] = None

    def build(self) -> None:
        # 1. Генератор температуры
        self.temp_gen = ConstantGenerator(
            self.engine,
            value=self.temperature_value,
            output_key="T_ambient"
        )

        # 2. Генератор тока
        if self.current_mode == 'constant':
            self.current_gen = ConstantGenerator(
                self.engine,
                value=self.current_value,
                output_key="I_load"
            )
        elif self.current_mode == 'cyclic':
            profile = self.current_profile
            if profile is None:
                profile = [1.0, 0.5, -0.5, 0.0, 1.0] * 5
            self.current_gen = CyclicProfileGenerator(
                self.engine,
                profile=profile,
                output_key="I_load"
            )
        else:
            raise ValueError(f"Unknown current_mode: {self.current_mode}")

        # 3. Истинная модель батареи
        self.battery = AppContext.WithContext(self, BatteryThevenin1RC, "battery")(
            simulation_engine = self.engine,
            param_tables=DEFAULT_PARAM_TABLES,
            **self.battery_params
        )
        self.battery.set_input('current', self.current_gen.simulation_id, 'I_load')
        self.battery.set_input('temperature', self.temp_gen.simulation_id, 'T_ambient')

        # 4. Генератор шума для напряжения
        self.voltage_noise_gen = NoiseGenerator(
            simulation_engine=self.engine,
            sigma=self.noise_sigma,
            bias=self.noise_bias,
            output_key="V_noise"
        )

        # 5. Сумматор: истинное напряжение + шум
        self.noise_adder = NoiseAdderTransformator(
            simulation_engine=self.engine,
            output_key="V_measured"
        )
        self.noise_adder.set_input('signal', self.battery.simulation_id, 'voltage_terminal')
        self.noise_adder.set_input('noise', self.voltage_noise_gen.simulation_id, 'V_noise')

        # 6. Расширенный фильтр Калмана
        model_params = {
            'R0': self.battery.R0,
            'R1': self.battery.R1,
            'C1': self.battery.C1,
            'ocv_func': self.battery.ocv_func,
            'use_hysteresis': self.battery.use_hysteresis
        }
        ekf_params = {
            'capacity_nom': self.battery.capacity_nom,
            'model_params': model_params,
            'use_hysteresis': self.battery.use_hysteresis,
            'M': self.battery.M,
            'gamma': self.battery.gamma,
            's': self.battery.s
        }
        ekf_params.update(self.ekf_params)
        self.ekf = AppContext.WithContext(self, EKFSOCEstimator, "ekf")(
            simulation_engine=self.engine, 
            param_tables=DEFAULT_PARAM_TABLES,
            **ekf_params)

        if self.records_path:
            self.data_logger = AppContext.WithContext(self, DataLogger, "logger")(
                simulation_engine=self.engine,
                records_path=self.records_path,
                targets = {
                    'battery': self.battery,
                    'ekf': self.ekf,
                    'meas': self.noise_adder   # или 'voltage_meas' для измеренного напряжения
                },
                enabled=False
            )

        # Связываем входы EKF
        self.ekf.set_input('voltage_measured', self.noise_adder.simulation_id, 'V_measured')
        self.ekf.set_input('current', self.current_gen.simulation_id, 'I_load')
        self.ekf.set_input('true_soc', self.battery.simulation_id, 'soc')
        self.ekf.set_input('temperature', self.temp_gen.simulation_id, 'T_ambient')
        self.ekf.set_input('hysteresis_dyn', self.battery.simulation_id, 'hysteresis_dyn')

    def get_objects(self):
        return [
            self.temp_gen,
            self.current_gen,
            self.battery,
            self.voltage_noise_gen,
            self.noise_adder,
            self.ekf
        ]

    def set_current_profile(self, profile: list):
        """Динамически заменить профиль тока (если используется CyclicProfileGenerator)."""
        if isinstance(self.current_gen, CyclicProfileGenerator):
            self.current_gen.set_profile(profile)
        else:
            raise TypeError("Current generator is not cyclic")

    def set_current_value(self, value: float):
        """Изменить значение тока (если используется ConstantGenerator)."""
        if isinstance(self.current_gen, ConstantGenerator):
            self.current_gen.set_value(value)
        else:
            raise TypeError("Current generator is not constant")