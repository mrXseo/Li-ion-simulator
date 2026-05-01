# core/simulation_setup.py
# -*- coding: utf-8 -*-
"""
Базовый класс для конфигурации симуляционного эксперимента.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..simulation_base.simulation_engine import SimulationEngine
    from ..simulation_base.simulation_object import SimulationObject


class SimulationSetup:
    """
    Отвечает за создание объектов симуляции, их связывание и хранение ссылок.
    Конкретные наследники добавляют свои специфичные атрибуты (например, self.battery).
    """

    def __init__(self, engine: SimulationEngine):
        self.engine = engine

    def build(self) -> None:
        """
        Создать и связать все объекты симуляции.
        Должен быть переопределён в наследниках.
        """
        raise NotImplementedError("Subclasses must implement build()")

    def get_objects(self) -> List[SimulationObject]:
        """
        Возвращает список всех созданных объектов (опционально).
        По умолчанию возвращает пустой список.
        """
        return []