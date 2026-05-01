# ui/widgets/noise_distribution_widget.py
# -*- coding: utf-8 -*-
"""
Виджет управления параметрами гауссовского шума и отображения теоретической PDF.
"""

from __future__ import annotations
import math
from typing import Optional, Tuple

import dearpygui.dearpygui as dpg

from .base_widget import BaseWidget
from core.elements.generators.noise_generator import NoiseGenerator


class NoiseDistributionWidget(BaseWidget):
    """
    Виджет для отображения распределения Гаусса и управления параметрами шума.

    Позволяет изменять sigma и bias через ползунки, график PDF обновляется в реальном времени.
    """

    def __init__(
        self,
        tag: str,
        noise_generator: Optional[NoiseGenerator] = None,
        sigma_range: Tuple[float, float] = (0.1, 2.0),
        bias_range: Tuple[float, float] = (-1.0, 1.0),
        width: int = 400,
        height: int = 300,
        **kwargs
    ) -> None:
        """
        Инициализирует виджет распределения.

        Args:
            tag (str): уникальный идентификатор виджета.
            noise_generator (Optional[NoiseGenerator]): генератор шума для управления.
            sigma_range (Tuple[float, float]): диапазон слайдера sigma.
            bias_range (Tuple[float, float]): диапазон слайдера bias.
            width (int): ширина виджета.
            height (int): высота графика.
            **kwargs: дополнительные параметры (передаются в set_configure).
        """
        # Специфичные параметры
        self.noise_gen: Optional[NoiseGenerator] = noise_generator
        self.sigma_range: Tuple[float, float] = sigma_range
        self.bias_range: Tuple[float, float] = bias_range
        self.width: int = width
        self.height: int = height

        # Теги внутренних элементов
        self.sigma_slider_tag: str = f"{tag}_sigma_slider"
        self.bias_slider_tag: str = f"{tag}_bias_slider"
        self.plot_tag: str = f"{tag}_pdf_plot"
        self.xaxis_tag: str = f"{tag}_pdf_xaxis"
        self.yaxis_tag: str = f"{tag}_pdf_yaxis"
        self.series_tag: str = f"{tag}_pdf_series"

        # Вызов родительского конструктора
        super().__init__(tag, simulation_object=noise_generator, **kwargs)

    def set_configure(self, **kwargs) -> None:
        """
        Обновляет параметры виджета с валидацией.
        """
        if "noise_generator" in kwargs:
            self.noise_gen = kwargs["noise_generator"]
            self.simulation_object = self.noise_gen
        if "sigma_range" in kwargs:
            self.sigma_range = kwargs["sigma_range"]
        if "bias_range" in kwargs:
            self.bias_range = kwargs["bias_range"]
        if "width" in kwargs:
            self.width = kwargs["width"]
        if "height" in kwargs:
            self.height = kwargs["height"]
        super().set_configure(**kwargs)

    def _pdf_gaussian(self, x: float, mu: float, sigma: float) -> float:
        """Вычисляет значение PDF нормального распределения."""
        if sigma <= 0:
            return 0.0
        coeff = 1.0 / (sigma * math.sqrt(2.0 * math.pi))
        exponent = -0.5 * ((x - mu) / sigma) ** 2
        return coeff * math.exp(exponent)

    def _update_pdf_plot(self) -> None:
        """Пересчитывает и обновляет график PDF."""
        if self.noise_gen is None:
            dpg.set_value(self.series_tag, [[], []])
            return

        sigma = self.noise_gen.sigma
        bias = self.noise_gen.bias

        # Диапазон X: от bias - 3*sigma до bias + 3*sigma, но не менее +/-1 при малых sigma
        x_min = bias - 3.0 * sigma
        x_max = bias + 3.0 * sigma
        if sigma < 0.2:
            x_min = min(x_min, bias - 1.0)
            x_max = max(x_max, bias + 1.0)

        step = (x_max - x_min) / 200.0
        x_vals = []
        y_vals = []
        x = x_min
        while x <= x_max:
            x_vals.append(x)
            y_vals.append(self._pdf_gaussian(x, bias, sigma))
            x += step

        dpg.set_value(self.series_tag, [x_vals, y_vals])
        dpg.fit_axis_data(self.xaxis_tag)
        dpg.fit_axis_data(self.yaxis_tag)

    def _on_sigma_change(self, sender, app_data) -> None:
        if self.noise_gen is not None:
            self.noise_gen.set_parameters(sigma=app_data)
        self._update_pdf_plot()

    def _on_bias_change(self, sender, app_data) -> None:
        if self.noise_gen is not None:
            self.noise_gen.set_parameters(bias=app_data)
        self._update_pdf_plot()

    def init(self, parent_tag: Optional[str] = None) -> None:
        """
        Создаёт все DPG-элементы виджета.
        """
        self.parent_tag = parent_tag

        with dpg.group(tag=self.tag, parent=parent_tag, horizontal=False):
            dpg.add_text("Noise Distribution Control", color=[0, 191, 255])

            dpg.add_text("Sigma (std dev):")
            dpg.add_slider_float(
                tag=self.sigma_slider_tag,
                default_value=self.noise_gen.sigma if self.noise_gen else 0.5,
                min_value=self.sigma_range[0],
                max_value=self.sigma_range[1],
                width=self.width,
                # Колбэк будет установлен в build()
            )

            dpg.add_text("Bias (mean):")
            dpg.add_slider_float(
                tag=self.bias_slider_tag,
                default_value=self.noise_gen.bias if self.noise_gen else 0.0,
                min_value=self.bias_range[0],
                max_value=self.bias_range[1],
                width=self.width,
                # Колбэк будет установлен в build()
            )

            with dpg.plot(
                tag=self.plot_tag,
                label="Gaussian PDF",
                height=self.height,
                width=self.width
            ):
                dpg.add_plot_axis(
                    dpg.mvXAxis,
                    label="Value",
                    tag=self.xaxis_tag
                )
                dpg.add_plot_axis(
                    dpg.mvYAxis,
                    label="Density",
                    tag=self.yaxis_tag
                )
                dpg.add_line_series(
                    [], [],
                    label="PDF",
                    parent=self.yaxis_tag,
                    tag=self.series_tag
                )

    def build(self) -> None:
        """
        Настраивает виджет после создания всех элементов.
        """
        # Устанавливаем колбэки слайдеров
        dpg.set_item_callback(self.sigma_slider_tag, self._on_sigma_change)
        dpg.set_item_callback(self.bias_slider_tag, self._on_bias_change)

        # Первоначальная отрисовка теоретической кривой
        self._update_pdf_plot()

    def update(self) -> None:
        """
        Периодическое обновление: синхронизация слайдеров с текущими параметрами и перерисовка PDF.
        """
        if self.noise_gen is None:
            return

        # Синхронизируем слайдеры с актуальными значениями из генератора
        current_sigma = self.noise_gen.sigma
        current_bias = self.noise_gen.bias

        if dpg.get_value(self.sigma_slider_tag) != current_sigma:
            dpg.set_value(self.sigma_slider_tag, current_sigma)
        if dpg.get_value(self.bias_slider_tag) != current_bias:
            dpg.set_value(self.bias_slider_tag, current_bias)

        self._update_pdf_plot()