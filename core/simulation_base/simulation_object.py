# core/simulation_base/simulation_object.py
# -*- coding: utf-8 -*-
"""
Модуль базового класса для всех объектов симуляции.

Предоставляет интерфейс пошагового выполнения (solve_frame), хранение
ограниченной очереди результатов, механизм синхронизированного доступа
к ним через движок, а также унифицированную систему связывания входов
с автоматическим временны́м выравниванием.
"""

from __future__ import annotations
from collections import deque
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from .simulation_engine import SimulationEngine


# --------------------------------------------------------------
# Исключение для управления ретроспективой
# --------------------------------------------------------------
class RetrospectiveAdjustment(Exception):
    """Сигнализирует, что объект не смог получить данные из-за недостаточной истории источника."""
    pass


class SimulationObject:
    """
    Базовый класс для любого компонента симуляции (модель, фильтр, шум и т.д.).

    Каждый объект автоматически регистрируется в движке при создании.
    Объект обязан переопределить методы _solve_frame() и reset_state().

    Атрибуты:
        simulation_engine (SimulationEngine): ссылка на движок симуляции.
        simulation_id (int): уникальный ID, присвоенный движком.
        frame_list_size (int): максимальное количество сохраняемых фреймов.
        _results_history (deque[Dict[str, Any]]): очередь результатов (FIFO).
        _input_rules (Dict[str, Tuple[int, str]]): правила получения входных данных.
        _retrospective_shift (int): личное смещение объекта во времени (в кадрах).
    """

    def __init__(self, simulation_engine: SimulationEngine, frame_list_size: int = 1000, **other_kwargs) -> None:
        self.simulation_engine: SimulationEngine = simulation_engine
        self.simulation_id: int = self.simulation_engine.register(self)

        if frame_list_size <= 0:
            raise ValueError("frame_list_size must be positive")
        self.frame_list_size: int = frame_list_size
        self._results_history: deque[Dict[str, Any]] = deque(maxlen=frame_list_size)

        # Правила получения входов: input_key -> (source_id, output_key)
        self._input_rules: Dict[str, Tuple[int, str]] = dict()
        self._collected_inputs: Dict[str, Any] = dict()

        # Релятивистское личное смещение (0 – настоящее, 1 – один кадр в прошлом, и т.д.)
        self._retrospective_shift: int = 0

    @property
    def retrospective_shift(self):
        return self._retrospective_shift

    # --------------------------------------------------------------
    # Переопределяемые методы
    # --------------------------------------------------------------
    def _solve_frame(self) -> None:
        """
        Выполняет один шаг симуляции (собственная логика объекта).

        Внутри можно использовать self._collected_inputs для доступа к уже полученным данным.
        Обязан вызвать self._push_result() с результатами фрейма.
        """
        raise NotImplementedError("Subclasses must implement _solve_frame()")

    def reset_state(self) -> None:
        """
        Сбрасывает внутреннее состояние объекта (но не историю).
        Должен быть переопределён в наследниках.
        """
        raise NotImplementedError("Subclasses must implement reset_state()")

    # --------------------------------------------------------------
    # Механизм сбора входных данных (с автоматической ретроспективой)
    # --------------------------------------------------------------
    def _collect_inputs(self) -> None:
        """Собирает все входы согласно _input_rules. При неудаче выбрасывает RetrospectiveAdjustment."""
        for input_key in self._input_rules:
            self._collected_inputs[input_key] = self._get_input(input_key, 1)

    def _destruct_inputs(self) -> None:
        """Очищает собранные входы после использования."""
        self._collected_inputs.clear()

    def _get_input(self, input_key: str, tail_len: int = 1) -> Optional[Any]:
        """
        Получает значение входа по заданному правилу с учётом временны́х сдвигов.

        Если объекты ещё не имеют ретроспективных сдвигов (retro==0),
        используется старый механизм движка (с коррекцией порядка выполнения).
        Иначе применяется релятивистская формула:
            effective_tail = max(1, 1 + self._retrospective_shift - source._retrospective_shift)
        """
        rule = self._input_rules.get(input_key)
        if rule is None:
            warnings.warn(f"Input rule for '{input_key}' not set in {self.__class__.__name__}")
            return None
        source_id, output_key = rule
        source_obj = self.simulation_engine._objects.get(source_id)
        if source_obj is None:
            return None

        # Определяем, нужно ли использовать ретроспективную формулу
        use_retro = (self._retrospective_shift > 0) or (source_obj._retrospective_shift > 0)

        if not use_retro:
            # --- Старый механизм: движок гарантирует атомарность ---
            result = self.simulation_engine.get_result(source_id, tail_len)
            if result is None:
                raise RetrospectiveAdjustment()
            return result.get(output_key)
        else:
            # --- Ретроспективная формула ---
            effective_tail = max(1, tail_len + self._retrospective_shift - source_obj._retrospective_shift)
            result = source_obj._get_frame_result(effective_tail)
            if result is None:
                raise RetrospectiveAdjustment()
            return result.get(output_key)

    # --------------------------------------------------------------
    # Управление историей
    # --------------------------------------------------------------
    def _push_result(self, result: Dict[str, Any]) -> None:
        """Сохраняет результат текущего фрейма в историю."""
        self._results_history.append(result)

    def get_frame_result(self, tail_len: int = 1) -> Optional[Dict[str, Any]]:
        """Публичный доступ к результатам (через движок, с коррекцией порядка)."""
        return self.simulation_engine.get_result(self.simulation_id, tail_len)

    @property
    def default(self) -> Dict[str, Any]:
        return dict()

    def _get_frame_result(self, tail_len: int = 1) -> Optional[Dict[str, Any]]:
        """Внутренний прямой доступ к истории (без коррекции)."""
        if tail_len < 1:
            return self.default
        idx = -tail_len
        if abs(idx) > len(self._results_history):
            return None
        return self._results_history[idx]

    def clear_history(self) -> None:
        self._results_history.clear()

    def get_all_history(self) -> List[Dict[str, Any]]:
        return list(self._results_history)

    @property
    def current_result(self) -> Optional[Dict[str, Any]]:
        return self.get_frame_result(1)

    @property
    def history_length(self) -> int:
        return len(self._results_history)

    # --------------------------------------------------------------
    # Публичный интерфейс связывания входов и выполнения шага
    # --------------------------------------------------------------
    def set_input(self, input_key: str, source_id: int, output_key: str) -> None:
        """Устанавливает правило получения входных данных."""
        self._input_rules[input_key] = (source_id, output_key)

    def solve_frame(self) -> None:
        """
        Главный метод, вызываемый движком.
        Пытается выполнить кадр; при неудаче (нехватка истории источников)
        увеличивает личную ретроспективу и пропускает кадр.
        """
        try:
            self._collect_inputs()
            self._solve_frame()
        except RetrospectiveAdjustment:
            # Не все данные доступны – сдвигаемся на кадр в прошлое и пропускаем
            self._retrospective_shift += 1
        finally:
            self._destruct_inputs()


# --------------------------------------------------------------
# Маркерные классы
# --------------------------------------------------------------
class Generator(SimulationObject):
    pass

class Transformator(SimulationObject):
    pass

class Inspector(SimulationObject):
    pass