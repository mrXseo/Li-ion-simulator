# core/elements/generators/cyclic_profile_generator.py
from __future__ import annotations
from typing import List, Any, Optional, TYPE_CHECKING

from ...simulation_base.simulation_object import Generator

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine

class CyclicProfileGenerator(Generator):
    def __init__(
        self,
        simulation_engine: SimulationEngine,
        profile: List[Any],
        profile_scale: int = 1,
        linear_change: bool = False,
        output_key: str = "profile_value",
        frame_list_size: int = 1000,
        **kwargs
    ) -> None:
        super().__init__(simulation_engine, frame_list_size, **kwargs)
        self.profile = profile
        self.output_key = output_key
        self._index = 0
        self.profile_scale = profile_scale
        self.linear_change = linear_change
        self._subindex = 0

    def set_profile(self, profile: List[Any]) -> None:
        self.profile = profile
        self._index = 0
        self._subindex = 0

    def _solve_frame(self) -> None:
        if not self.profile:
            value = None
        else:
            if self.linear_change and len(self.profile) > 1:
                # Текущая и следующая точки профиля (циклически)
                idx0 = self._index
                idx1 = (self._index + 1) % len(self.profile)
                v0 = self.profile[idx0]
                v1 = self.profile[idx1]
                # Доля между v0 и v1 (от 0 до 1)
                t = self._subindex / self.profile_scale
                value = v0 + (v1 - v0) * t
            else:
                value = self.profile[self._index]

            # Продвижение под-индекса и основного индекса
            self._subindex += 1
            if self._subindex >= self.profile_scale:
                self._subindex = 0
                self._index = (self._index + 1) % len(self.profile)

        self._push_result({self.output_key: value})

    def reset_state(self) -> None:
        self._index = 0
        self._subindex = 0