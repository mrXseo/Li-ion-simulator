# ui/widgets/history_plot_widget.py
# -*- coding: utf-8 -*-
"""
Виджет для отображения истории значений из SimulationObject в виде линейного графика.
Поддерживает задание пользовательских легенд для каждой линии.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, TypeAlias, Tuple

import dearpygui.dearpygui as dpg

from .base_widget import BaseWidget
from core.simulation_base.simulation_object import SimulationObject

StrHistoryLegend : TypeAlias = str
StrHistoryKey : TypeAlias = str

class HistoryPlotWidget(BaseWidget):
    """
    Линейный график истории значений.

    Отображает последние `window_size` точек истории для каждого ключа из `data_keys`.
    Ось X показывает «кадры назад» (0 – текущий фрейм, -1 – предыдущий и т.д.).
    """

    def __init__(
        self,
        tag: str,
        simulation_object: Optional[SimulationObject] = None,
        data_keys: Optional[Dict[StrHistoryKey, StrHistoryLegend]] = None,   # {key: legend}
        y_keys: Optional[List[str]] = None,           # устаревший, для обратной совместимости
        title: str = "History",
        height: int = 300,
        width: int = 0,
        window_size: int = 200,
        y_limits: Optional[Tuple[float, float]] = None,
        **kwargs
    ) -> None:
        """
        Инициализирует виджет графика истории.

        Args:
            tag (str): уникальный идентификатор виджета.
            simulation_object (Optional[SimulationObject]): объект с историей.
            data_keys (Optional[Dict[str, str]]): словарь {ключ_данных: легенда}.
                Если None, будет использован y_keys (для совместимости).
            y_keys (Optional[List[str]]): список ключей (устаревший). Если data_keys не задан,
                ключи из y_keys будут использованы как легенды.
            title (str): заголовок графика.
            height (int): высота графика в пикселях.
            width (int): ширина графика (0 – автоматически).
            window_size (int): количество отображаемых последних фреймов.
            **kwargs: дополнительные параметры (передаются в set_configure).
        """
        # Нормализуем data_keys
        if data_keys is not None:
            self.data_keys: Dict[str, str] = data_keys
        elif y_keys is not None:
            # Для обратной совместимости: ключ == легенда
            self.data_keys = {key: key for key in y_keys}
        else:
            self.data_keys = {}

        self.title: str = title
        self.height: int = height
        self.width: int = width
        self.window_size: int = window_size

        # Теги внутренних элементов
        self.plot_tag: str = f"{tag}_plot"
        self.xaxis_tag: str = f"{tag}_xaxis"
        self.yaxis_tag: str = f"{tag}_yaxis"
        self.series_tags: List[str] = [f"{tag}_series_{i}" for i in range(len(self.data_keys))]

        self.y_limits = y_limits

        # Вызов родительского конструктора
        super().__init__(tag, simulation_object, **kwargs)

    @property
    def y_keys(self) -> List[str]:
        """Список ключей данных (для обратной совместимости)."""
        return list(self.data_keys.keys())

    def set_configure(self, **kwargs) -> None:
        """
        Обновляет параметры виджета с валидацией.
        """
        if "data_keys" in kwargs:
            self.data_keys = kwargs["data_keys"]
            self.series_tags = [f"{self.tag}_series_{i}" for i in range(len(self.data_keys))]
        elif "y_keys" in kwargs:
            # Преобразуем старый формат
            y_keys = kwargs["y_keys"]
            self.data_keys = {key: key for key in y_keys}
            self.series_tags = [f"{self.tag}_series_{i}" for i in range(len(self.data_keys))]

        if "title" in kwargs:
            self.title = kwargs["title"]
        if "height" in kwargs:
            self.height = kwargs["height"]
        if "width" in kwargs:
            self.width = kwargs["width"]
        if "window_size" in kwargs:
            self.window_size = kwargs["window_size"]

        super().set_configure(**kwargs)

    def init(self, parent_tag: Optional[str] = None) -> None:
        """
        Создаёт все DPG-элементы виджета.
        """
        self.parent_tag = parent_tag

        with dpg.group(tag=self.tag, parent=parent_tag, horizontal=False):
            with dpg.plot(
                tag=self.plot_tag,
                label=self.title,
                height=self.height,
                width=self.width
            ):
                dpg.add_plot_legend()
                dpg.add_plot_axis(
                    dpg.mvXAxis,
                    label="Frames ago",
                    tag=self.xaxis_tag
                )
                dpg.add_plot_axis(
                    dpg.mvYAxis,
                    label="",
                    tag=self.yaxis_tag
                )
                for idx, (key, legend) in enumerate(self.data_keys.items()):
                    dpg.add_line_series(
                        [], [],
                        label=legend,
                        parent=self.yaxis_tag,
                        tag=self.series_tags[idx]
                    )

        dpg.set_axis_limits(self.xaxis_tag, -self.window_size, 0)
        if self.y_limits is not None:
            dpg.set_axis_limits(self.yaxis_tag, self.y_limits[0], self.y_limits[1])

    def build(self) -> None:
        pass

    def _get_visible_history(self) -> List[Dict[str, Any]]:
        """
        Возвращает список фреймов истории, обрезанный до window_size.
        """
        if self.simulation_object is None:
            return []
        history = self.simulation_object.get_all_history()
        if not history:
            return []
        if len(history) > self.window_size:
            history = history[-self.window_size:]
        return history

    def get_visible_data(self, key: Optional[str] = None) -> List[float]:
        """
        Возвращает список значений, отображаемых в данный момент на графике.

        Args:
            key (Optional[str]): ключ данных (если None, используется первый ключ из self.data_keys).

        Returns:
            List[float]: список значений, соответствующих отображаемому окну истории.
        """
        history = self._get_visible_history()
        if not history:
            return []

        if key is None:
            if not self.data_keys:
                return []
            key = next(iter(self.data_keys.keys()))

        return [frame.get(key, 0.0) for frame in history]

    def update(self) -> None:
        """
        Обновляет данные на графике из истории simulation_object.
        """
        history = self._get_visible_history()
        if not history:
            return

        # Формируем значения X: 0 для последнего фрейма, -1 для предыдущего и т.д.
        x_vals = [-i for i in range(len(history) - 1, -1, -1)]

        # Обновляем каждую серию
        for idx, key in enumerate(self.data_keys.keys()):
            y_vals = [frame.get(key, 0.0) for frame in history]
            dpg.set_value(self.series_tags[idx], [x_vals, y_vals])