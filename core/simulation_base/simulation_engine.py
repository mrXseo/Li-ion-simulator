# core/simulation_engine.py
# -*- coding: utf-8 -*-
"""
Модуль движка симуляции.

Обеспечивает последовательное выполнение фреймов для зарегистрированных
объектов симуляции с автоматической коррекцией временнóй синхронизации
при межобъектных запросах.
"""

from __future__ import annotations
from typing import Dict, Optional, List, Any, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from .simulation_object import SimulationObject

class SimulationEngine:
    """
    Движок симуляции.

    Управляет порядком выполнения объектов, хранит их числовые идентификаторы,
    отслеживает текущий индекс выполняемого объекта и предоставляет механизм
    получения скорректированных по времени результатов других объектов.

    Атрибуты:
        _objects (Dict[int, SimulationObject]): отображение ID → объект.
        _order (List[int]): порядок выполнения ID объектов.
        _index_of (Dict[int, int]): отображение ID → позиция в _order.
        _current_index (int): индекс выполняемого в данный момент объекта
                              в _order (-1, если ни один не выполняется).
        _frames_count (int): общее количество завершённых фреймов.
    """

    def __init__(self) -> None:
        """Инициализирует пустой движок."""
        self._objects: Dict[int, SimulationObject] = {}
        self._order: List[int] = []
        self._index_of: Dict[int, int] = {}
        self._current_index: int = -1
        self._frames_count: int = 0
        self.dt : float = 1
        self.total_time : float = 0

    def register(self, obj: SimulationObject) -> int:
        """
        Регистрирует объект симуляции в движке.

        Args:
            obj (SimulationObject): объект, наследуемый от SimulationObject.

        Returns:
            int: уникальный числовой идентификатор объекта.

        Note:
            Обычно вызывается автоматически в конструкторе SimulationObject.
        """
        obj_id = len(self._objects)
        self._objects[obj_id] = obj
        self._order.append(obj_id)
        self._index_of[obj_id] = len(self._order) - 1
        return obj_id

    def get_result(self, target_id: int, tail_len: int = 1) -> Optional[Dict[str, Any]]:
        """
        Возвращает результат целевого объекта с учётом порядка выполнения.

        Если целевой объект уже выполнился в текущем фрейме (его позиция <=
        текущей позиции), то его история уже содержит результат этого фрейма.
        Чтобы получить данные за ПРЕДЫДУЩИЙ фрейм симуляции, метод автоматически
        увеличивает tail_len на 1. В противном случае tail_len остаётся без
        изменений.

        Args:
            target_id (int): ID целевого объекта.
            tail_len (int): количество фреймов от конца очереди (1 – последний,
                            2 – предпоследний, …). По умолчанию 1.

        Returns:
            Optional[Dict[str, Any]]: словарь с результатами фрейма или None,
            если объект не найден или запрошенный фрейм отсутствует.

        Raises:
            Warning: если скорректированный tail_len больше длины истории.
        """
        target_obj = self._objects.get(target_id)
        if target_obj is None:
            return None

        target_pos = self._index_of.get(target_id)
        if target_pos is None:
            return None

        # Автокоррекция tail_len в зависимости от порядка выполнения
        if target_pos <= self._current_index:
            adjusted_tail = tail_len + 1
        else:
            adjusted_tail = tail_len

        result = target_obj._get_frame_result(adjusted_tail)
        if result is None and adjusted_tail > 1:
            warnings.warn(
                f"Запрошен tail_len={tail_len} (скорректирован={adjusted_tail}) "
                f"для объекта {target_id}, но длина истории = {target_obj.history_length}"
            )
        return result

    def step_frame(self) -> None:
        """
        Выполняет один полный фрейм симуляции.

        Последовательно вызывает метод solve_frame() для всех зарегистрированных
        объектов в порядке их регистрации. После завершения всех объектов
        увеличивает счётчик фреймов.
        """
        for idx, obj_id in enumerate(self._order):
            self._current_index = idx
            obj = self._objects[obj_id]
            obj.solve_frame()
        self._frames_count += 1
        self._current_index = -1

    def step_frames(self, n: int = 1):
        for _ in range(n):
            # существующий код step_frame()
            self.step_frame()
            self.total_time += self.dt

    @property
    def frame_number(self) -> int:
        """
        int: количество полностью завершённых фреймов.
        """
        return self._frames_count

    def reset(self) -> None:
        """
        Полный сброс движка и всех зарегистрированных объектов.

        Вызывает reset_state() и clear_history() для каждого объекта,
        обнуляет счётчик фреймов и сбрасывает текущий индекс.
        """
        for obj in self._objects.values():
            obj.reset_state()
            obj.clear_history()
        self._frames_count = 0
        self._current_index = -1