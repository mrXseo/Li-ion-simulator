# core/simulation_base/simulation_object.py
# -*- coding: utf-8 -*-
"""
Модуль базового класса для всех объектов симуляции.

Предоставляет интерфейс пошагового выполнения (solve_frame), хранение
ограниченной очереди результатов, механизм синхронизированного доступа
к ним через движок, а также унифицированную систему связывания входов.
"""

from __future__ import annotations
from collections import deque
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from .simulation_engine import SimulationEngine


class SimulationObject:
    """
    Базовый класс для любого компонента симуляции (модель, фильтр, шум и т.д.).

    Каждый объект автоматически регистрируется в движке при создании.
    Объект обязан переопределить методы solve_frame() и reset_state().

    Атрибуты:
        simulation_engine (SimulationEngine): ссылка на движок симуляции.
        simulation_id (int): уникальный ID, присвоенный движком.
        frame_list_size (int): максимальное количество сохраняемых фреймов.
        _results_history (deque[Dict[str, Any]]): очередь результатов (FIFO).
        _input_rules (Dict[str, Tuple[int, str]]): правила получения входных данных.
    """

    def __init__(self, simulation_engine: SimulationEngine, frame_list_size: int = 1000, **other_kwargs) -> None:
        """
        Инициализирует объект симуляции и регистрирует его в движке.

        Args:
            simulation_engine (SimulationEngine): экземпляр движка.
            frame_list_size (int): максимальный размер очереди истории.
                                   Должен быть положительным.

        Raises:
            ValueError: если frame_list_size <= 0.
        """
        self.simulation_engine: SimulationEngine = simulation_engine
        self.simulation_id: int = self.simulation_engine.register(self)

        if frame_list_size <= 0:
            raise ValueError("frame_list_size must be positive")
        self.frame_list_size: int = frame_list_size
        self._results_history: deque[Dict[str, Any]] = deque(maxlen=frame_list_size)

        # Правила получения входов: input_key -> (source_id, output_key)
        self._input_rules: Dict[str, Tuple[int, str]] = {}

    def solve_frame(self) -> None:
        """
        Выполняет один шаг (фрейм) симуляции.

        Должен быть переопределён в наследниках.
        Внутри метода необходимо:
            - Произвести все вычисления на основе текущего состояния и,
              при необходимости, данных других объектов (через
              self._get_input() или self.get_frame_result()).
            - Вызвать self._push_result() с результатами фрейма в виде словаря.

        Raises:
            NotImplementedError: если метод не переопределён.
        """
        raise NotImplementedError("Subclasses must implement solve_frame()")

    def reset_state(self) -> None:
        """
        Сбрасывает внутреннее состояние объекта (но не историю).

        Должен быть переопределён в наследниках.
        Вызывается движком при глобальном сбросе.

        Raises:
            NotImplementedError: если метод не переопределён.
        """
        raise NotImplementedError("Subclasses must implement reset_state()")

    def _push_result(self, result: Dict[str, Any]) -> None:
        """
        Сохраняет результат текущего фрейма в историю.

        Args:
            result (Dict[str, Any]): словарь с данными фрейма.
        """
        self._results_history.append(result)

    def get_frame_result(self, tail_len: int = 1) -> Optional[Dict[str, Any]]:
        """
        Публичный метод получения результата другого объекта или своего
        с автоматической синхронизацией времени через движок.

        В отличие от прямого обращения к истории, этот метод учитывает
        порядок выполнения объектов и корректирует tail_len, чтобы избежать
        использования ещё не вычисленных данных текущего фрейма.

        Args:
            tail_len (int): количество фреймов от конца очереди
                            (1 – последний, 2 – предпоследний, …).

        Returns:
            Optional[Dict[str, Any]]: словарь результата или None, если
            запрошенный фрейм отсутствует.
        """
        return self.simulation_engine.get_result(self.simulation_id, tail_len)

    @property
    def default(self) -> Dict[str, Any]:
        return dict()

    def _get_frame_result(self, tail_len: int = 1) -> Optional[Dict[str, Any]]:
        """
        Внутренний метод прямого доступа к истории (без коррекции).

        Используется только движком для получения данных из другого объекта.
        Не предназначен для вызова из пользовательского кода.

        Args:
            tail_len (int): количество фреймов от конца очереди (1 – последний).

        Returns:
            Optional[Dict[str, Any]]: результат или None, если индекс выходит
            за границы истории.
        """
        if tail_len < 1:
            return self.default
        idx = -tail_len
        if abs(idx) > len(self._results_history):
            return None
        return self._results_history[idx]

    def clear_history(self) -> None:
        """Полностью очищает историю результатов объекта."""
        self._results_history.clear()

    def get_all_history(self) -> List[Dict[str, Any]]:
        """
        Возвращает всю сохранённую историю результатов (от старых к новым).
        """
        return list(self._results_history)

    @property
    def current_result(self) -> Optional[Dict[str, Any]]:
        """
        Optional[Dict[str, Any]]: результат последнего завершённого фрейма
        (синоним get_frame_result(1)).
        """
        return self.get_frame_result(1)

    @property
    def history_length(self) -> int:
        """
        int: текущее количество сохранённых фреймов в истории.
        """
        return len(self._results_history)

    # --------------------------------------------------------------
    # Новый механизм явного связывания входов (для Transformator'ов)
    # --------------------------------------------------------------

    def set_input(self, input_key: str, source_id: int, output_key: str) -> None:
        """
        Устанавливает правило получения входных данных от другого объекта.

        Args:
            input_key (str): имя, под которым вход будет доступен в объекте.
            source_id (int): ID объекта-источника.
            output_key (str): ключ в словаре результатов источника.
        """
        self._input_rules[input_key] = (source_id, output_key)

    def _get_input(self, input_key: str, tail_len: int = 1) -> Optional[Any]:
        """
        Получает значение входа по заданному правилу.

        Args:
            input_key (str): имя входа.
            tail_len (int): смещение от конца истории источника (1 – последний фрейм).

        Returns:
            Optional[Any]: значение из словаря источника по ключу output_key,
                           или None, если данных нет.
        """
        rule = self._input_rules.get(input_key)
        if rule is None:
            warnings.warn(f"Input rule for '{input_key}' not set in {self.__class__.__name__}")
            return None
        source_id, output_key = rule
        result = self.simulation_engine.get_result(source_id, tail_len)
        if result is None:
            return None
        return result.get(output_key)


# --------------------------------------------------------------
# Маркерные классы для классификации объектов по роли
# --------------------------------------------------------------

class Generator(SimulationObject):
    """
    Объект, который только генерирует данные, не потребляя входов от других объектов.
    """
    pass


class Transformator(SimulationObject):
    """
    Объект, принимающий входы от других объектов, преобразующий их и выдающий результаты.
    Обычно использует set_input() и _get_input() для получения данных.
    """
    pass


class Inspector(SimulationObject):
    """
    Объект, который только читает данные других объектов для анализа/логирования,
    не создавая выходов, используемых в симуляции.
    """
    pass