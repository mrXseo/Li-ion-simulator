# core/elements/generators/stateful_generator.py
# -*- coding: utf-8 -*-
"""
Генератор с внутренним состоянием, изменяющимся по заданному правилу.
Позволяет создавать таймеры, счётчики, пилообразные сигналы и т.п.
"""

from __future__ import annotations
from typing import Callable, Any, Optional, TYPE_CHECKING

from ...simulation_base.simulation_object import Generator

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine


class StatefulGenerator(Generator):
    """
    Генератор с обновлением состояния по пользовательской функции.

    Функция update_func получает текущее состояние и номер фрейма,
    возвращает новое состояние. Состояние сохраняется в историю под ключом output_key.
    """

    def __init__(
        self,
        simulation_engine: SimulationEngine,
        initial_state: Any,
        update_func: Callable[[Any, int], Any],
        output_key: str = "state",
        frame_list_size: int = 1000,
        **kwargs
    ) -> None:
        """
        Args:
            simulation_engine: движок.
            initial_state: начальное состояние.
            update_func: функция (state, frame_index) -> new_state.
            output_key: ключ для сохранения.
        """
        super().__init__(simulation_engine, frame_list_size, **kwargs)
        self._state = initial_state
        self._initial_state = initial_state
        self.update_func = update_func
        self.output_key = output_key
        self._frame_counter = 0

    def solve_frame(self) -> None:
        # Обновляем состояние
        self._state = self.update_func(self._state, self._frame_counter)
        self._frame_counter += 1

        self._push_result({self.output_key: self._state})

    def reset_state(self) -> None:
        self._state = self._initial_state