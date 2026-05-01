# core/elements/transformers/noise_adder.py
from __future__ import annotations
from typing import Optional, Any, TYPE_CHECKING
from ...simulation_base.simulation_object import Transformator

if TYPE_CHECKING:
    from ...simulation_base.simulation_engine import SimulationEngine

class NoiseAdderTransformator(Transformator):
    """
    Принимает сигнал и шум, выдаёт сумму.
    Входы (ожидаются через set_input):
        - 'signal' : основной сигнал
        - 'noise'  : шум (например, от NoiseGenerator)
    Выход: {'value': signal + noise}
    """
    def __init__(self, simulation_engine: SimulationEngine, output_key: str = "value"):
        super().__init__(simulation_engine)
        self.output_key = output_key

    def solve_frame(self) -> None:
        signal = self._get_input('signal', tail_len=1)
        noise = self._get_input('noise', tail_len=1)
        if signal is None:
            signal = 0.0
        if noise is None:
            noise = 0.0
        result = signal + noise
        self._push_result({self.output_key: result})

    def reset_state(self) -> None:
        pass