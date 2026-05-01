# core/elements/generators/cyclic_profile_generator.py
# -*- coding: utf-8 -*-
"""
Генератор, циклически проигрывающий заданный массив значений.
"""

from __future__ import annotations
from typing import List, Any, Optional, TYPE_CHECKING

from ...simulation_base.simulation_object import Generator

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine


class CyclicProfileGenerator(Generator):
    """
    Генератор, последовательно выдающий значения из списка.
    По достижении конца списка начинает сначала.
    """

    def __init__(
        self,
        simulation_engine: SimulationEngine,
        profile: List[Any],
        output_key: str = "profile_value",
        frame_list_size: int = 1000,
        **kwargs
    ) -> None:
        """
        Args:
            simulation_engine: движок.
            profile: список значений для последовательного воспроизведения.
            output_key: ключ для сохранения в истории.
        """
        super().__init__(simulation_engine, frame_list_size, **kwargs)
        self.profile = profile
        self.output_key = output_key
        self._index = 0

    def set_profile(self, profile: List[Any]) -> None:
        """Заменить профиль и сбросить позицию в начало."""
        self.profile = profile
        self._index = 0

    def solve_frame(self) -> None:
        if not self.profile:
            value = None
        else:
            value = self.profile[self._index]
            self._index = (self._index + 1) % len(self.profile)

        self._push_result({self.output_key: value})

    def reset_state(self) -> None:
        self._index = 0