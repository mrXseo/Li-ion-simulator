# ui/widgets/history_histogram_widget.py
# -*- coding: utf-8 -*-
"""
Виджет для отображения гистограммы квантованных значений из истории.
Зависит от HistoryPlotWidget для синхронизации оси X и получения данных.
"""

from __future__ import annotations
from typing import Optional, List, Tuple, TypeAlias, Dict
from collections import Counter

import dearpygui.dearpygui as dpg

from .base_widget import BaseWidget
from .history_plot_widget import HistoryPlotWidget

class HistoryPlotHistogramWidget(BaseWidget):
    """
    Гистограмма значений из истории с квантованием.

    Отображает частоты уникальных значений (после квантования с шагом eps)
    в виде столбчатой диаграммы. Ось X синхронизируется с осью Y связанного
    HistoryPlotWidget для согласованного отображения диапазона.
    """

    def __init__(
        self,
        tag: str,
        history_plot_widget: Optional[HistoryPlotWidget] = None,
        data_key: Optional[str] = None,
        eps: float = 0.1,
        eps_range: Tuple[float, float] = (0.01, 1.0),
        height: int = 250,
        width: int = 400,
        title: str = "Noise Histogram",
        **kwargs
    ) -> None:
        """
        Инициализирует виджет гистограммы.

        Args:
            tag (str): уникальный идентификатор виджета.
            history_plot_widget (HistoryPlotWidget): связанный виджет графика истории.
            data_key (Optional[str]): ключ данных для анализа (если None, берётся первый из history_plot_widget.y_keys).
            eps (float): начальный шаг квантования.
            eps_range (Tuple[float, float]): диапазон допустимых значений eps для слайдера.
            height (int): высота графика.
            width (int): ширина виджета.
            title (str): заголовок.
            **kwargs: дополнительные параметры (передаются в set_configure).
        """
        # Специфичные параметры
        self.history_plot_widget: Optional[HistoryPlotWidget] = history_plot_widget
        self.data_key: Optional[str] = data_key
        self.eps: float = eps
        self.eps_range: Tuple[float, float] = eps_range
        self.height: int = height
        self.width: int = width
        self.title: str = title

        # Теги внутренних элементов
        self.plot_tag: str = f"{tag}_hist_plot"
        self.xaxis_tag: str = f"{tag}_hist_xaxis"
        self.yaxis_tag: str = f"{tag}_hist_yaxis"
        self.bar_series_tag: str = f"{tag}_hist_bars"
        self.eps_slider_tag: str = f"{tag}_eps_slider"

        # Родительский конструктор (установит tag, simulation_object и вызовет set_configure)
        super().__init__(tag, simulation_object=None, **kwargs)

        # Если history_plot_widget не None, берём simulation_object из него
        if self.history_plot_widget is not None:
            self.simulation_object = self.history_plot_widget.simulation_object

    def set_configure(self, **kwargs) -> None:
        """
        Обновляет параметры виджета с валидацией.
        """
        if "history_plot_widget" in kwargs:
            self.history_plot_widget = kwargs["history_plot_widget"]
            if self.history_plot_widget is not None:
                self.simulation_object = self.history_plot_widget.simulation_object
        if "data_key" in kwargs:
            self.data_key = kwargs["data_key"]
        if "eps" in kwargs:
            self.eps = kwargs["eps"]
        if "eps_range" in kwargs:
            self.eps_range = kwargs["eps_range"]
        if "height" in kwargs:
            self.height = kwargs["height"]
        if "width" in kwargs:
            self.width = kwargs["width"]
        if "title" in kwargs:
            self.title = kwargs["title"]
        super().set_configure(**kwargs)

    def _quantize(self, value: float) -> float:
        """Округление до ближайшего кратного eps."""
        if self.eps <= 0:
            return value
        return round(value / self.eps) * self.eps

    def _compute_histogram(self, data: List[float]) -> Tuple[List[float], List[int]]:
        """
        Возвращает (уровни, частоты) для квантованных значений.
        """
        if not data or self.eps <= 0:
            return [], []
        quantized = [self._quantize(v) for v in data]
        counter = Counter(quantized)
        levels = sorted(counter.keys())
        counts = [counter[lev] for lev in levels]
        return levels, counts

    def _update_histogram(self) -> None:
        """Пересчитывает и обновляет столбчатую диаграмму."""
        if self.history_plot_widget is None:
            dpg.set_value(self.bar_series_tag, [[], []])
            return

        # Получаем данные напрямую из связанного виджета истории
        values = self.history_plot_widget.get_visible_data(self.data_key)
        if not values:
            dpg.set_value(self.bar_series_tag, [[], []])
            # Синхронизация оси X даже при отсутствии данных
            y_limits = dpg.get_axis_limits(self.history_plot_widget.yaxis_tag)
            if y_limits and len(y_limits) == 2:
                dpg.set_axis_limits(self.xaxis_tag, y_limits[0], y_limits[1])
            return

        levels, counts = self._compute_histogram(values)
        dpg.set_value(self.bar_series_tag, [levels, counts])
        dpg.configure_item(self.bar_series_tag, weight=self.eps)

        # Синхронизация оси X с осью Y графика истории
        y_limits = dpg.get_axis_limits(self.history_plot_widget.yaxis_tag)
        if y_limits and len(y_limits) == 2:
            dpg.set_axis_limits(self.xaxis_tag, y_limits[0], y_limits[1])

    def _on_eps_change(self, sender, app_data) -> None:
        """Колбэк изменения значения слайдера eps."""
        self.eps = app_data
        self._update_histogram()

    def init(self, parent_tag: Optional[str] = None) -> None:
        """
        Создаёт все DPG-элементы виджета.
        """
        self.parent_tag = parent_tag

        with dpg.group(tag=self.tag, parent=parent_tag, horizontal=False):
            dpg.add_text(self.title, color=[0, 191, 255])
            dpg.add_text("Quantization step (eps):")
            dpg.add_slider_float(
                tag=self.eps_slider_tag,
                default_value=self.eps,
                min_value=self.eps_range[0],
                max_value=self.eps_range[1],
                width=self.width,
                # Колбэк будет установлен в build()
            )

            with dpg.plot(
                tag=self.plot_tag,
                label="",
                height=self.height,
                width=self.width
            ):
                dpg.add_plot_axis(
                    dpg.mvXAxis,
                    label="Noise value",
                    tag=self.xaxis_tag
                )
                dpg.add_plot_axis(
                    dpg.mvYAxis,
                    label="Frequency",
                    tag=self.yaxis_tag
                )
                dpg.add_bar_series(
                    [], [],
                    label="Histogram",
                    parent=self.yaxis_tag,
                    tag=self.bar_series_tag,
                    weight=self.eps
                )

    def build(self) -> None:
        """
        Настраивает виджет после создания всех элементов.
        """
        # Устанавливаем колбэк слайдера
        dpg.set_item_callback(self.eps_slider_tag, self._on_eps_change)

        # Устанавливаем начальный предел оси Y (высота окна истории)
        if self.history_plot_widget is not None:
            dpg.set_axis_limits(self.yaxis_tag, 0, self.history_plot_widget.window_size)
        else:
            dpg.set_axis_limits(self.yaxis_tag, 0, 1)  # fallback

        # Первоначальное отображение (даже если история пуста, покажет пустой график)
        self._update_histogram()

    def update(self) -> None:
        """
        Периодическое обновление: синхронизация слайдера и пересчёт гистограммы.
        """
        # Синхронизируем слайдер с текущим значением eps (на случай изменения извне)
        current_eps = dpg.get_value(self.eps_slider_tag)
        if current_eps != self.eps:
            dpg.set_value(self.eps_slider_tag, self.eps)

        self._update_histogram()