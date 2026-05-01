# core/experiments/battery_simulation_setup.py
# -*- coding: utf-8 -*-
"""
Конфигурация симуляции для модели батареи с генераторами тока и температуры.
"""

from typing import Optional, Union
from .simulation_setup import SimulationSetup
from ..simulation_base.simulation_engine import SimulationEngine
from ..elements.generators.constant_generator import ConstantGenerator
from ..elements.generators.cyclic_profile_generator import CyclicProfileGenerator
from ..elements.transformers.battery_thevenin_1rc import BatteryThevenin1RC


class BatterySimulationSetup(SimulationSetup):
    """
    Создаёт и связывает объекты для эксперимента с моделью батареи.

    Атрибуты после build():
        - battery: BatteryThevenin1RC
        - current_gen: ConstantGenerator или CyclicProfileGenerator
        - temp_gen: ConstantGenerator
    """

    def __init__(
        self,
        engine: SimulationEngine,
        current_mode: str = 'constant',
        current_value: float = 1.0,
        current_profile: Optional[list] = None,
        temperature_value: float = 25.0,
        battery_params: Optional[dict] = None
    ):
        """
        Args:
            engine: движок симуляции.
            current_mode: 'constant' или 'cyclic'.
            current_value: значение тока для режима 'constant' (А).
            current_profile: список значений тока для режима 'cyclic'.
            temperature_value: значение температуры (°C).
            battery_params: словарь параметров для BatteryThevenin1RC.
        """
        super().__init__(engine)
        self.current_mode = current_mode
        self.current_value = current_value
        self.current_profile = current_profile
        self.temperature_value = temperature_value
        self.battery_params = battery_params if battery_params is not None else {}

        # Будут установлены в build()
        self.battery: Optional[BatteryThevenin1RC] = None
        self.current_gen: Optional[Union[ConstantGenerator, CyclicProfileGenerator]] = None
        self.temp_gen: Optional[ConstantGenerator] = None

    def build(self) -> None:
        # 1. Генератор температуры (всегда константный)
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
                # Профиль по умолчанию для теста
                profile = [1.0, 0.5, -0.5, 0.0, 1.0] * 5
            self.current_gen = CyclicProfileGenerator(
                self.engine,
                profile=profile,
                output_key="I_load"
            )
        else:
            raise ValueError(f"Unknown current_mode: {self.current_mode}")

        # 3. Модель батареи
        self.battery = BatteryThevenin1RC(
            self.engine,
            **self.battery_params
        )

        # 4. Связывание входов батареи с генераторами
        self.battery.set_input('current', self.current_gen.simulation_id, 'I_load')
        self.battery.set_input('temperature', self.temp_gen.simulation_id, 'T_ambient')

    def get_objects(self):
        return [self.temp_gen, self.current_gen, self.battery]

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