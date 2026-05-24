# core/experiments/ekf_simulation_setup.py
# -*- coding: utf-8 -*-
"""
Конфигурация симуляции для тестирования EKF оценки SOC.
Включает истинную модель батареи, генераторы тока/температуры,
генераторы шума, сумматоры шума и сам EKF.
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
    Поддерживает шумы тока, напряжения и температуры.
    """

    def __init__(
        self,
        engine: SimulationEngine,
        records_path: Optional[Path] = None,
        current_mode: str = 'constant',
        current_value: float = 1.0,
        current_profile: Optional[list] = None,
        current_profile_scale: Optional[int] = None,
        current_linear_change: bool = False,
        temperature_mode: str = 'constant',
        temperature_value: float = 25.0,
        temperature_profile: Optional[list] = None,
        temperature_profile_scale: Optional[int] = None,
        temperature_linear_change: bool = False,
        battery_params: Optional[dict] = None,
        voltage_noise_sigma: float = 0.0,
        current_noise_sigma: float = 0.0,
        temp_noise_sigma: float = 0.0,
        ekf_params: Optional[dict] = None
    ):
        """
        Args:
            engine: движок симуляции.
            records_path: путь для сохранения CSV (опционально).
            current_mode: 'constant' или 'cyclic'.
            current_value: значение тока для режима 'constant' (А).
            current_profile: список значений тока для режима 'cyclic'.
            current_profile_scale: количество кадров на одно значение профиля тока.
            temperature_mode: 'constant' или 'cyclic'.
            temperature_value: значение температуры для режима 'constant' (°C).
            temperature_profile: список значений температуры для режима 'cyclic'.
            temperature_profile_scale: количество кадров на одно значение профиля температуры.
            battery_params: словарь параметров для BatteryThevenin1RC.
            voltage_noise_sigma: СКО шума измерения напряжения (В).
            current_noise_sigma: СКО шума измерения тока (А).
            temp_noise_sigma: СКО шума измерения температуры (°C).
            ekf_params: словарь параметров для EKFSOCEstimator.
        """
        super().__init__(engine)
        # Ток
        self.current_mode = current_mode
        self.current_value = current_value
        self.current_profile = current_profile
        self.current_profile_scale = current_profile_scale if current_profile_scale else 1
        self.current_linear_change = current_linear_change

        # Температура
        self.temperature_mode = temperature_mode
        self.temperature_value = temperature_value
        self.temperature_profile = temperature_profile
        self.temperature_profile_scale = temperature_profile_scale if temperature_profile_scale else 1
        self.temperature_linear_change = temperature_linear_change

        self.battery_params = battery_params if battery_params is not None else {}
        self.voltage_noise_sigma = voltage_noise_sigma
        self.current_noise_sigma = current_noise_sigma
        self.temp_noise_sigma = temp_noise_sigma
        self.ekf_params = ekf_params if ekf_params is not None else {}
        self.records_path = records_path

        # Ссылки на создаваемые объекты
        self.battery: Optional[BatteryThevenin1RC] = None
        self.current_gen: Optional[Union[ConstantGenerator, CyclicProfileGenerator]] = None
        self.temp_gen: Optional[Union[ConstantGenerator, CyclicProfileGenerator]] = None
        self.voltage_noise_gen: Optional[NoiseGenerator] = None
        self.current_noise_gen: Optional[NoiseGenerator] = None
        self.temp_noise_gen: Optional[NoiseGenerator] = None
        self.voltage_adder: Optional[NoiseAdderTransformator] = None
        self.current_adder: Optional[NoiseAdderTransformator] = None
        self.temp_adder: Optional[NoiseAdderTransformator] = None
        self.ekf: Optional[EKFSOCEstimator] = None
        self.data_logger: Optional[DataLogger] = None

    def build(self) -> None:
        # ---------- 1. Генератор температуры ----------
        if self.temperature_mode == 'constant':
            self.temp_gen = ConstantGenerator(
                self.engine,
                value=self.temperature_value,
                output_key="T_ambient"
            )
        elif self.temperature_mode == 'cyclic':
            profile = self.temperature_profile
            if profile is None:
                profile = [25.0, 30.0, 20.0]  # профиль по умолчанию
            self.temp_gen = CyclicProfileGenerator(
                self.engine,
                profile=profile,
                output_key="T_ambient",
                profile_scale=self.temperature_profile_scale,
                linear_change=self.temperature_linear_change
            )
        else:
            raise ValueError(f"Unknown temperature_mode: {self.temperature_mode}")

        # ---------- 2. Генератор тока ----------
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
                output_key="I_load",
                profile_scale=self.current_profile_scale,
                linear_change=self.current_linear_change
            )
        else:
            raise ValueError(f"Unknown current_mode: {self.current_mode}")

        # ---------- 3. Истинная модель батареи ----------
        self.battery = AppContext.WithContext(self, BatteryThevenin1RC, "battery")(
            simulation_engine = self.engine,
            param_tables=DEFAULT_PARAM_TABLES,
            **self.battery_params
        )
        # Батарея использует истинные (бесшумные) ток и температуру
        self.battery.set_input('current', self.current_gen.simulation_id, 'I_load')
        self.battery.set_input('temperature', self.temp_gen.simulation_id, 'T_ambient')

        # ---------- 4. Генераторы шума ----------
        self.voltage_noise_gen = NoiseGenerator(
            simulation_engine=self.engine,
            sigma=self.voltage_noise_sigma,
            bias=0.0,
            output_key="V_noise"
        )
        self.current_noise_gen = NoiseGenerator(
            simulation_engine=self.engine,
            sigma=self.current_noise_sigma,
            bias=0.0,
            output_key="I_noise"
        )
        self.temp_noise_gen = NoiseGenerator(
            simulation_engine=self.engine,
            sigma=self.temp_noise_sigma,
            bias=0.0,
            output_key="T_noise"
        )

        # ---------- 5. Сумматоры (истина + шум) ----------
        # Напряжение
        self.voltage_adder = NoiseAdderTransformator(
            simulation_engine=self.engine,
            output_key="V_measured"
        )
        self.voltage_adder.set_input('signal', self.battery.simulation_id, 'voltage_terminal')
        self.voltage_adder.set_input('noise', self.voltage_noise_gen.simulation_id, 'V_noise')

        # Ток
        self.current_adder = NoiseAdderTransformator(
            simulation_engine=self.engine,
            output_key="I_meas"
        )
        self.current_adder.set_input('signal', self.current_gen.simulation_id, 'I_load')
        self.current_adder.set_input('noise', self.current_noise_gen.simulation_id, 'I_noise')

        # Температура
        self.temp_adder = NoiseAdderTransformator(
            simulation_engine=self.engine,
            output_key="T_meas"
        )
        self.temp_adder.set_input('signal', self.temp_gen.simulation_id, 'T_ambient')
        self.temp_adder.set_input('noise', self.temp_noise_gen.simulation_id, 'T_noise')

        # ---------- 6. Расширенный фильтр Калмана ----------
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
            **ekf_params
        )

        # EKF получает ЗАШУМЛЁННЫЕ ток и температуру
        self.ekf.set_input('voltage_measured', self.voltage_adder.simulation_id, 'V_measured')
        self.ekf.set_input('current', self.current_adder.simulation_id, 'I_meas')
        self.ekf.set_input('temperature', self.temp_adder.simulation_id, 'T_meas')
        self.ekf.set_input('true_soc', self.battery.simulation_id, 'soc')
        self.ekf.set_input('hysteresis_dyn', self.battery.simulation_id, 'hysteresis_dyn')

        # ---------- 7. DataLogger ----------
        if self.records_path:
            self.data_logger = AppContext.WithContext(self, DataLogger, "logger")(
                simulation_engine=self.engine,
                records_path=self.records_path,
                targets = {
                    'battery': self.battery,
                    'ekf': self.ekf,
                    'meas_v': self.voltage_adder,
                    'meas_i': self.current_adder,
                    'meas_t': self.temp_adder
                },
                enabled=False
            )

    def get_objects(self):
        """Возвращает список всех объектов симуляции для движка."""
        objs = [
            self.temp_gen,
            self.current_gen,
            self.battery,
            self.voltage_noise_gen,
            self.current_noise_gen,
            self.temp_noise_gen,
            self.voltage_adder,
            self.current_adder,
            self.temp_adder,
            self.ekf
        ]
        if self.data_logger:
            objs.append(self.data_logger)
        return objs

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