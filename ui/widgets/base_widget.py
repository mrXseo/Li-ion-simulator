# ui/widgets/base_widget.py
# -*- coding: utf-8 -*-
"""
Базовый класс для всех виджетов интерфейса.

Виджеты инкапсулируют логику создания и обновления элементов DearPyGui.
Разделение на init() и build() позволяет сначала создать все элементы,
а затем настроить их с учётом уже существующих зависимостей.
"""

from __future__ import annotations
from typing import Optional, Any

from core.simulation_base.simulation_object import SimulationObject


class BaseWidget:
    """
    Базовый виджет.

    Жизненный цикл:
        1. __init__() – сохранение параметров.
        2. init(parent_tag) – создание DPG-элементов.
        3. build() – пост-настройка (колбэки, начальные пределы осей и т.п.).
        4. update() – периодическое обновление данных (вызывается из главного цикла).
    """

    def __init__(self, tag: str, simulation_object: Optional[SimulationObject] = None, **kwargs) -> None:
        """
        Инициализирует виджет.

        Args:
            tag (str): уникальный идентификатор виджета (будет использован как тег корневого элемента).
            simulation_object (Optional[SimulationObject]): объект симуляции для привязки.
            **kwargs: дополнительные параметры, передаваемые в set_configure.
        """
        self.tag: str = tag
        self.simulation_object: Optional[SimulationObject] = simulation_object
        self.parent_tag: Optional[str] = None

        if kwargs:
            self.set_configure(**kwargs)

    def set_configure(self, **kwargs) -> None:
        """
        Изменяет настройки виджета.

        Может быть переопределён в наследниках для валидации или дополнительной логики.
        По умолчанию обновляет известные атрибуты.
        """
        if "parent_tag" in kwargs:
            self.parent_tag = kwargs["parent_tag"]
        if "tag" in kwargs:
            self.tag = kwargs["tag"]
        if "simulation_object" in kwargs:
            self.simulation_object = kwargs["simulation_object"]

    # Словарь описаний параметров для возможного использования в редакторе свойств
    keyword_description_type = "type"
    keyword_description_text = "text"

    def get_configure_descriptions(self) -> dict:
        """Возвращает метаданные о доступных параметрах конфигурации."""
        return {
            "parent_tag": {
                self.keyword_description_type: str,
                self.keyword_description_text: "тэг dpg родительского элемента"
            },
            "tag": {
                self.keyword_description_type: str,
                self.keyword_description_text: "тэг dpg корневого элемента виджета"
            },
            "simulation_object": {
                self.keyword_description_type: SimulationObject,
                self.keyword_description_text: "элемент симуляции"
            },
        }

    def init(self, parent_tag: Optional[str] = None) -> None:
        """
        Создаёт все DPG-элементы, относящиеся к виджету.

        Должен быть переопределён в наследниках.
        Обычно создаёт корневой контейнер (например, dpg.group) с тегом self.tag
        и родителем parent_tag, а внутри – все дочерние элементы.

        Args:
            parent_tag (Optional[str]): тег родительского контейнера в DPG.
        """
        raise NotImplementedError("Subclasses must implement init()")

    def build(self) -> None:
        """
        Настраивает виджет после создания всех DPG-элементов.

        Может быть переопределён в наследниках.
        Здесь выполняются действия, которые требуют, чтобы все виджеты были уже
        проинициализированы (например, установка колбэков, синхронизация осей,
        начальное заполнение данными теоретических графиков).

        По умолчанию ничего не делает.
        """
        pass

    def update(self) -> None:
        """
        Обновляет содержимое виджета (графики, текстовые поля и т.д.).

        Вызывается периодически (например, по таймеру или после каждого фрейма симуляции)
        для синхронизации с текущим состоянием объекта симуляции.

        Может быть переопределён в наследниках.
        По умолчанию ничего не делает.
        """
        pass