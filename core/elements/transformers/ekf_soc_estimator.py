# core/elements/transformers/ekf_soc_estimator.py
# -*- coding: utf-8 -*-
"""
Расширенный фильтр Калмана для оценки SOC и Vc с учётом гистерезиса и температуры.
"""

import numpy as np
from typing import Optional, Dict, Any, TYPE_CHECKING

from ...simulation_base.simulation_object import Transformator
from ...utils.interpolation import bilinear_interp

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine


class EKFSOCEstimator(Transformator):
    """
    Расширенный фильтр Калмана для оценки SOC и Vc по измерениям напряжения и тока.

    Входы (через set_input):
        - 'voltage_measured' : измеренное напряжение (В)
        - 'current'          : ток (А)
        - 'temperature'      : температура (°C), опционально
        - 'hysteresis_dyn'   : динамическая составляющая гистерезиса h (опционально)
        - 'true_soc'         : истинное SOC для расчёта ошибки (опционально)

    Выходы (сохраняются в историю):
        - 'soc_est'     : оценка SOC
        - 'vc_est'      : оценка Vc
        - 'soc_error'   : ошибка оценки (если есть истина)
        - 'innovation'  : невязка измерения
        - 'K_gain'      : норма коэффициента усиления Калмана
    """

    def __init__(self,
                 simulation_engine: 'SimulationEngine',
                 capacity_nom: float = 5.0,
                 Q: Optional[np.ndarray] = None,
                 R: float = 1e-4,
                 P0: Optional[np.ndarray] = None,
                 x0: Optional[np.ndarray] = None,
                 model_params: Optional[Dict[str, Any]] = None,
                 use_hysteresis: bool = False,
                 M: float = 0.02,
                 gamma: float = 50.0,
                 s: float = 0.5,
                 param_tables: Optional[Dict[str, Any]] = None,
                 **kwargs) -> None:
        """
        Args:
            simulation_engine: движок симуляции.
            capacity_nom: номинальная ёмкость, А·ч.
            Q: ковариационная матрица шума процесса (2x2).
            R: дисперсия шума измерения (скаляр).
            P0: начальная ковариационная матрица ошибок (2x2).
            x0: начальный вектор состояния [SOC, Vc].
            model_params: словарь с параметрами модели (R0, R1, C1, ocv_func).
            use_hysteresis: флаг учёта гистерезиса.
            M, gamma, s: параметры гистерезиса.
            param_tables: таблицы для интерполяции параметров от SOC и T.
        """

        Q00 = kwargs.pop('Q00', None)
        Q11 = kwargs.pop('Q11', None)
        P00 = kwargs.pop('P00', None)
        P11 = kwargs.pop('P11', None)

        # Если матрицы не переданы явно, но есть плоские ключи, строим матрицы
        if Q is None and Q00 is not None and Q11 is not None:
            Q = np.diag([float(Q00), float(Q11)])
        if P0 is None and P00 is not None and P11 is not None:
            P0 = np.diag([float(P00), float(P11)])

        super().__init__(simulation_engine, **kwargs)

        # Параметры модели
        self.capacity_nom = capacity_nom

        if Q is not None:
            self.Q = np.array(Q)
            if self.Q.ndim == 1 and len(self.Q) == 2:
                self.Q = np.diag(self.Q)
            elif self.Q.shape != (2, 2):
                self.Q = np.diag([1e-6, 1e-6])
        else:
            self.Q = np.diag([1e-6, 1e-6])

        # R – скаляр
        self.R = float(R) if R is not None else 1e-4

        # Приведение P0 к numpy-матрице 2x2
        if P0 is not None:
            self.P = np.array(P0)
            if self.P.ndim == 1 and len(self.P) == 2:
                self.P = np.diag(self.P)
            elif self.P.shape != (2, 2):
                self.P = np.diag([0.01, 0.1])
        else:
            self.P = np.diag([0.01, 0.1])

        # Вектор состояния x0
        if x0 is not None:
            self.x = np.array(x0)
        else:
            self.x = np.array([1.0, 0.0])

        # Базовые параметры (будут переопределяться из таблиц при необходимости)
        if model_params is None:
            model_params = {}
        self.R0 = model_params.get('R0', 0.01)
        self.R1 = model_params.get('R1', 0.02)
        self.C1 = model_params.get('C1', 1000.0)
        self.ocv_func = model_params.get('ocv_func', self._default_ocv)

        # Гистерезис
        self.use_hysteresis = use_hysteresis
        self.M = M
        self.gamma = gamma
        self.s = s

        # Таблицы параметров
        self.param_tables = param_tables if param_tables is not None else {}
        self.use_tables = bool(self.param_tables)

    def _default_ocv(self, soc: float) -> float:
        """Полином 5-й степени (заглушка)."""
        coeffs = [3.4, 0.7, -0.5, 0.3, -0.1, 0.02]
        return sum(c * (soc ** i) for i, c in enumerate(coeffs))

    def _interpolate_param(self, param_name: str, soc: float, temp: float) -> float:
        """
        Интерполяция параметра по SOC и температуре с использованием билинейной интерполяции.
        """
        if not self.use_tables or param_name not in self.param_tables:
            return getattr(self, param_name)

        soc_grid, temp_grid, values = self.param_tables[param_name]
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

    def solve_frame(self) -> None:
        # Получение входных данных
        V_meas = self._get_input('voltage_measured', tail_len=1)
        I = self._get_input('current', tail_len=1)
        if V_meas is None or I is None:
            return

        T = self._get_input('temperature', tail_len=1) or 25.0
        h_dyn = self._get_input('hysteresis_dyn', tail_len=1) or 0.0

        # Текущая оценка состояния
        soc, Vc = self.x

        # Обновление параметров модели по текущему SOC и температуре
        self._update_params_from_tables(soc, T)

        dt = self.simulation_engine.dt
        Cn = self.capacity_nom * 3600.0  # А·ч -> А·с

        # === Прогноз (predict) ===
        if self.R1 * self.C1 > 0:
            exp_term = np.exp(-dt / (self.R1 * self.C1))
        else:
            exp_term = 0.0

        A = np.array([
            [1.0, 0.0],
            [0.0, exp_term]
        ])
        B = np.array([
            [-dt / Cn],
            [self.R1 * (1.0 - exp_term)]
        ])

        x_pred = A @ self.x + B.flatten() * I
        x_pred[0] = np.clip(x_pred[0], 0.0, 1.0)  # SOC в [0,1]

        P_pred = A @ self.P @ A.T + self.Q

        # === Коррекция (update) ===
        soc_pred, Vc_pred = x_pred

        # Базовое OCV
        ocv = self.ocv_func(soc_pred)

        # Гистерезис
        hyst_instant = 0.0
        if self.use_hysteresis:
            hyst_instant = self.s * self.M * np.sign(I) if I != 0 else 0.0
        h_total = h_dyn + hyst_instant

        # Предсказанное напряжение
        V_pred = ocv + h_total - Vc_pred - self.R0 * I

        # Якобиан H = [dOCV/dSOC, -1]
        eps = 1e-5
        dOCV = (self.ocv_func(soc_pred + eps) - self.ocv_func(soc_pred - eps)) / (2.0 * eps)
        H = np.array([[dOCV, -1.0]])

        innovation = V_meas - V_pred
        S = H @ P_pred @ H.T + self.R
        K = P_pred @ H.T / S  # усиление Калмана (2x1)

        x_new = x_pred + K.flatten() * innovation
        x_new[0] = np.clip(x_new[0], 0.0, 1.0)

        P_new = (np.eye(2) - np.outer(K, H)) @ P_pred
        # Симметризация для численной устойчивости
        P_new = (P_new + P_new.T) / 2.0

        self.x = x_new
        self.P = P_new

        # Ошибка оценки, если есть истинный SOC
        true_soc = self._get_input('true_soc', tail_len=1)
        soc_error = None
        if true_soc is not None:
            soc_error = x_new[0] - true_soc

        result = {
            'soc_est': x_new[0],
            'vc_est': x_new[1],
            'innovation': innovation,
            'K_gain': float(np.linalg.norm(K)),
            'soc_error': soc_error,
            'P00': float(self.P[0, 0]),
            'P11': float(self.P[1, 1])
        }
        self._push_result(result)

    def reset_state(self) -> None:
        """Сброс оценок фильтра к начальным значениям."""
        self.x = np.array([1.0, 0.0])
        self.P = np.diag([0.01, 0.1])

    @property
    def R_val(self):
        return self.R

    @property
    def Q00(self):
        return float(self.Q[0, 0])

    @property
    def Q11(self):
        return float(self.Q[1, 1])

    @property
    def P00(self):
        return float(self.P[0, 0])

    @property
    def P11(self):
        return float(self.P[1, 1])

    def set_parameters(self, **kwargs) -> None:
        """Динамическое изменение параметров фильтра."""
        if 'R' in kwargs:
            self.R = float(kwargs['R'])
        if 'Q00' in kwargs:
            # Убедимся, что Q – numpy-массив
            if not isinstance(self.Q, np.ndarray):
                self.Q = np.array(self.Q)
            self.Q[0, 0] = float(kwargs['Q00'])
        if 'Q11' in kwargs:
            if not isinstance(self.Q, np.ndarray):
                self.Q = np.array(self.Q)
            self.Q[1, 1] = float(kwargs['Q11'])
        if 'P00' in kwargs:
            if not isinstance(self.P, np.ndarray):
                self.P = np.array(self.P)
            self.P[0, 0] = float(kwargs['P00'])
        if 'P11' in kwargs:
            if not isinstance(self.P, np.ndarray):
                self.P = np.array(self.P)
            self.P[1, 1] = float(kwargs['P11'])
        if 'Q_diag' in kwargs:
            q = kwargs['Q_diag']
            if len(q) == 2:
                self.Q = np.diag(q)
        if 'P0_diag' in kwargs:
            p = kwargs['P0_diag']
            if len(p) == 2:
                self.P = np.diag(p)