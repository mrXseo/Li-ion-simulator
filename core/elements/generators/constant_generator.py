# core/elements/generators/constant_generator.py
# -*- coding: utf-8 -*-
"""
Генератор, выдающий одно и то же значение на всех фреймах и эмулирующий,
что так было всегда (при запросе истории возвращается это же значение).
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TYPE_CHECKING

from ...simulation_base.simulation_object import Generator

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine


class ConstantGenerator(Generator):
    """
    Генератор постоянного значения.

    На каждом фрейме сохраняет в историю одно и то же значение под заданным ключом.
    При запросе истории через get_all_history() возвращает список словарей,
    каждый из которых содержит это значение, эмулируя полную историю.

    Полезен для:
        - задания постоянных параметров (seed, температура, ток покоя);
        - имитации "вечных" констант для зависимых объектов.
    """

    def __init__(
        self,
        simulation_engine: SimulationEngine,
        value: Any = 0.0,
        output_key: str = "constant",
        frame_list_size: int = 1000,
        **kwargs
    ) -> None:
        """
        Args:
            simulation_engine: движок симуляции.
            value: значение, которое будет выдаваться.
            output_key: ключ, под которым значение сохраняется в истории.
            frame_list_size: размер очереди истории.
        """
        super().__init__(simulation_engine, frame_list_size, **kwargs)
        self.value = value
        self.output_key = output_key

    def set_value(self, value: Any) -> None:
        """Изменить выдаваемое значение (начиная со следующего фрейма)."""
        self.value = value

    def _solve_frame(self) -> None:
        # Сохраняем текущее значение
        self._push_result({self.output_key: self.value})

    def reset_state(self) -> None:
        # Нет накапливаемого состояния, сбрасывать нечего
        pass

    # Переопределяем get_all_history, чтобы эмулировать полную историю
    def get_all_history(self) -> list:
        """
        Возвращает список словарей, заполненный значением value,
        даже если реальных фреймов было меньше frame_list_size.
        """
        real_history = super().get_all_history()
        if not real_history:
            # Если история пуста, возвращаем один элемент (для совместимости)
            return [{self.output_key: self.value}]
        # Иначе возвращаем реальную историю (она уже содержит нужные значения)
        return real_history