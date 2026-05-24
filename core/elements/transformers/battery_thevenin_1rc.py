# core/elements/transformers/battery_thevenin_1rc.py
# -*- coding: utf-8 -*-
"""
Модель литий-ионного аккумулятора: схема Тевенина с одним RC-звеном,
дополненная гистерезисом напряжения разомкнутой цепи и температурной
зависимостью параметров через табличную интерполяцию.
"""

from __future__ import annotations
import math
import numpy as np
from typing import Optional, Dict, Any, Callable, TYPE_CHECKING

from ...simulation_base.simulation_object import Transformator
from ...utils.interpolation import bilinear_interp

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine


class BatteryThevenin1RC(Transformator):
    """
    Модель аккумулятора Тевенина 1-RC с гистерезисом и температурной зависимостью.

    Входы (задаются через set_input и попадают в _collected_inputs):
        - 'current'     : ток нагрузки (А), положительный при разряде.
        - 'temperature' : температура (°C).

    Выходы:
        - 'voltage_terminal' : напряжение на клеммах (В)
        - 'soc'              : степень заряда (0..1)
        - 'vc'               : напряжение на RC-цепи (В)
        - 'ocv'              : OCV с учётом гистерезиса (В)
        - 'hysteresis_dyn'   : динамическая составляющая гистерезиса h
        - 'current'          : ток (продублирован)
        - 'temperature'      : температура (продублирована)
    """

    def __init__(
        self,
        simulation_engine: SimulationEngine,
        capacity_nom: float = 5.0,
        initial_soc: float = 1.0,
        initial_vc: float = 0.0,
        R0: float = 0.01,
        R1: float = 0.02,
        C1: float = 1000.0,
        use_hysteresis: bool = True,
        M: float = 0.02,
        gamma: float = 50.0,
        s: float = 0.5,
        eta_i: float = 1.0,
        ocv_func: Optional[Callable[[float], float]] = None,
        param_tables: Optional[Dict[str, Any]] = None,
        frame_list_size: int = 1000,
        **kwargs
    ) -> None:
        super().__init__(simulation_engine, frame_list_size, **kwargs)

        # Основные параметры
        self.capacity_nom = capacity_nom
        self.R0 = R0
        self.R1 = R1
        self.C1 = C1
        self.eta_i = eta_i
        self.use_hysteresis = use_hysteresis
        self.M = M
        self.gamma = gamma
        self.s = s

        # Внутреннее состояние
        self.soc = initial_soc
        self.vc = initial_vc
        self.h = 0.0                       # динамический гистерезис
        self.sgn_prev = 0                  # знак предыдущего изменения SOC

        # Функция OCV
        if ocv_func is not None:
            self.ocv_func = ocv_func
        else:
            self.ocv_coeffs = [3.4, 0.7, -0.5, 0.3, -0.1, 0.02]
            self.ocv_func = self._default_ocv

        # Таблицы параметров (SOC, Temp) -> значение
        self.param_tables = param_tables if param_tables is not None else {}
        self.use_tables = bool(self.param_tables)

    def _default_ocv(self, soc: float) -> float:
        """Вычисляет OCV по полиному 5-й степени."""
        return sum(c * (soc ** i) for i, c in enumerate(self.ocv_coeffs))

    def _interpolate_param(self, param_name: str, soc: float, temp: float) -> float:
        """
        Интерполяция параметра по SOC и температуре с использованием билинейной интерполяции.
        """
        if not self.use_tables or param_name not in self.param_tables:
            return getattr(self, param_name)

        soc_grid, temp_grid, values = self.param_tables[param_name]
        # Приводим к numpy массивам для совместимости
        return float(bilinear_interp(
            soc, temp,
            np.array(soc_grid), np.array(temp_grid),
            np.array(values)
        ))

    def _update_params_from_tables(self, soc: float, temp: float) -> None:
        """Обновляет R0, R1, C1 по таблицам."""
        if self.use_tables:
            self.R0 = self._interpolate_param('R0', soc, temp)
            self.R1 = self._interpolate_param('R1', soc, temp)
            self.C1 = self._interpolate_param('C1', soc, temp)

    def set_parameters(self, **kwargs) -> None:
        """Динамическое изменение параметров модели."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _update_hysteresis(self, i: float, soc_dot: float, dt: float) -> float:
        """
        Обновляет динамический гистерезис h.
        Возвращает полное напряжение гистерезиса, добавляемое к OCV.
        """
        if not self.use_hysteresis:
            return 0.0

        # Знак изменения SOC
        sgn = 1 if soc_dot > 0 else (-1 if soc_dot < 0 else self.sgn_prev)
        self.sgn_prev = sgn

        # Асимптотическое значение гистерезиса
        M_hyst = self.M if sgn == 1 else -self.M

        # Коэффициент скорости
        kappa = self.gamma * abs(i) / (3600.0 * self.capacity_nom)

        # Обновление h
        exp_term = math.exp(-abs(kappa) * dt)
        self.h = M_hyst - (M_hyst - self.h) * exp_term

        # Мгновенная составляющая
        s_i = self.s * sgn if i != 0 else 0.0

        return self.h + s_i

    def _solve_frame(self) -> None:
        # Получаем данные из собранных входов
        current = self._collected_inputs.get('current')
        if current is None:
            current = 0.0

        temperature = self._collected_inputs.get('temperature')
        if temperature is None:
            temperature = 25.0

        # Обновляем параметры по текущему SOC и температуре
        self._update_params_from_tables(self.soc, temperature)

        dt = self.simulation_engine.dt
        Cn = self.capacity_nom * 3600.0      # А·ч -> А·с

        # Производная SOC
        soc_dot = -self.eta_i * current / Cn

        # Обновление SOC
        soc_new = self.soc + soc_dot * dt
        soc_new = max(0.0, min(1.0, soc_new))

        # Обновление Vc
        tau = self.R1 * self.C1
        if tau > 0:
            exp_term = math.exp(-dt / tau)
            vc_new = self.vc * exp_term + self.R1 * (1.0 - exp_term) * current
        else:
            vc_new = self.R1 * current

        # Гистерезис
        hyst_voltage = self._update_hysteresis(current, soc_dot, dt)

        # Базовое OCV
        ocv_base = self.ocv_func(soc_new)
        ocv_total = ocv_base + hyst_voltage

        # Напряжение на клеммах
        v_terminal = ocv_total - vc_new - self.R0 * current

        # Сохраняем новое состояние
        self.soc = soc_new
        self.vc = vc_new

        result = {
            'voltage_terminal': v_terminal,
            'soc': self.soc,
            'vc': self.vc,
            'ocv': ocv_total,
            'hysteresis_dyn': self.h,
            'current': current,
            'temperature': temperature
        }
        self._push_result(result)

    def reset_state(self) -> None:
        """Сбрасывает SOC, Vc и гистерезис к начальным значениям."""
        self.soc = 1.0
        self.vc = 0.0
        self.h = 0.0
        self.sgn_prev = 0

    @property
    def voltage(self) -> float:
        """Текущее напряжение на клеммах (из последнего фрейма)."""
        res = self.current_result
        return res.get('voltage_terminal', 0.0) if res else 0.0

    @property
    def current_soc(self) -> float:
        """Текущий SOC."""
        return self.soc