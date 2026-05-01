# core/noise_generator.py
# -*- coding: utf-8 -*-
"""
Модуль генератора шума для симуляции датчиков.

Предоставляет класс NoiseGenerator, который наследуется от SimulationObject
и генерирует случайные шумы (гауссовские) с заданными СКО и смещением.
"""

from __future__ import annotations
import random
from typing import Dict, Any, Optional

from ...simulation_base.simulation_engine import SimulationEngine
from ...simulation_base.simulation_object import Generator


class NoiseGenerator(Generator):
    """
    Генератор шума.

    На каждом фрейме генерирует значение шума по указанному закону
    распределения (пока только гауссовское) и сохраняет его в истории.

    Атрибуты:
        noise_type (str): тип шума ('gaussian' – единственный пока).
        sigma (float): среднеквадратическое отклонение (>=0).
        bias (float): систематическая ошибка (смещение).
        output_key (str): ключ, под которым результат будет сохранён
                          в словаре фрейма (например, 'I_noise').

    Результат фрейма:
        {output_key: сгенерированное_значение}
    """

    def __init__(
        self,
        simulation_engine: SimulationEngine,
        sigma: float = 0.0,
        bias: float = 0.0,
        output_key: str = "noise",
        noise_type: str = "gaussian",
        frame_list_size: int = 1000
    ) -> None:
        """
        Инициализирует генератор шума.

        Args:
            simulation_engine (SimulationEngine): движок симуляции.
            sigma (float): СКО шума (неотрицательное).
            bias (float): систематическое смещение.
            output_key (str): ключ для сохранения результата.
            noise_type (str): тип шума ('gaussian').
            frame_list_size (int): размер очереди истории.

        Raises:
            ValueError: если sigma < 0 или noise_type не поддерживается.
        """
        super().__init__(simulation_engine, frame_list_size)

        if sigma < 0.0:
            raise ValueError("sigma must be >= 0")
        self.sigma: float = sigma

        self.bias: float = bias
        self.output_key: str = output_key

        if noise_type != "gaussian":
            raise ValueError("Only 'gaussian' noise type is supported")
        self.noise_type: str = noise_type

        self.sigma_name = "sigma"
        self.bias_name = "bias"

    def solve_frame(self) -> None:
        """
        Генерирует одно значение шума и сохраняет его в историю.

        Для гауссовского шума: value = bias + N(0, sigma^2).
        Результат упаковывается в словарь {output_key: value}.
        """
        if self.noise_type == "gaussian":
            value = self.bias + random.gauss(0.0, self.sigma)
        else:
            # Fallback (никогда не должно сработать из-за проверки в __init__)
            value = 0.0

        frame_idx = len(self._results_history)

        self._push_result(
            {self.output_key: value, 
             self.output_key+self.bias_name: self.bias, 
             self.output_key+self.sigma_name: self.sigma,
             })

    def reset_state(self) -> None:
        """
        Сбрасывает внутреннее состояние генератора.

        Для данного класса нет накапливаемого состояния, поэтому ничего
        не делает. Однако метод переопределён для соответствия интерфейсу.
        """
        # Генератор шума не имеет состояния, кроме параметров,
        # которые не сбрасываются. При необходимости можно сбросить seed,
        # но это нарушит воспроизводимость. Оставляем пустым.
        pass

    def set_parameters(self, sigma: Optional[float] = None, bias: Optional[float] = None) -> None:
        """
        Динамически изменяет параметры шума (без сброса истории).

        Args:
            sigma (float, optional): новое СКО (должно быть >= 0).
            bias (float, optional): новое смещение.

        Raises:
            ValueError: если sigma < 0.
        """
        if sigma is not None:
            if sigma < 0.0:
                raise ValueError("sigma must be >= 0")
            self.sigma = sigma
        if bias is not None:
            self.bias = bias

    def set_output_key(self, new_key: str) -> None:
        """
        Изменяет ключ, под которым сохраняется результат.

        Args:
            new_key (str): новый ключ.
        """
        self.output_key = new_key

    @property
    def current_noise(self) -> Optional[float]:
        """
        Optional[float]: последнее сгенерированное значение шума
                         (или None, если фреймов ещё не было).
        """
        curr = self.current_result
        if curr is None:
            return None
        return curr.get(self.output_key)