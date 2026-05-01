# core/elements/generators/parameter_generator.py
# -*- coding: utf-8 -*-
"""
Генератор, записывающий в историю текущее значение параметра,
которое может изменяться извне.
"""

from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING

from ...simulation_base.simulation_object import Generator

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine


class ParameterGenerator(Generator):
    """
    Генератор параметра, изменяемого извне.

    На каждом фрейме сохраняет в историю текущее значение параметра.
    Позволяет динамически менять значение через set_value().
    """

    def __init__(
        self,
        simulation_engine: SimulationEngine,
        initial_value: Any = 0.0,
        output_key: str = "parameter",
        frame_list_size: int = 1000,
        **kwargs
    ) -> None:
        super().__init__(simulation_engine, frame_list_size, **kwargs)
        self._current_value = initial_value
        self.output_key = output_key

    def set_value(self, value: Any) -> None:
        """Установить новое значение параметра."""
        self._current_value = value

    @property
    def current_value(self) -> Any:
        """Текущее значение параметра."""
        return self._current_value

    def solve_frame(self) -> None:
        self._push_result({self.output_key: self._current_value})

    def reset_state(self) -> None:
        # Состояние не сбрасывается, значение остаётся
        pass