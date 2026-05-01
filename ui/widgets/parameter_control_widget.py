# ui/widgets/parameter_control_widget.py
# -*- coding: utf-8 -*-
"""
Универсальный виджет для управления параметрами объекта симуляции.
Поддерживает обычные слайдеры и научный ввод с мантиссой/экспонентой.
"""

from __future__ import annotations
import math
from typing import Any, Dict, Optional

import dearpygui.dearpygui as dpg

from .base_widget import BaseWidget
from core.simulation_base.simulation_object import SimulationObject


class ParameterControlWidget(BaseWidget):
    def __init__(
        self,
        tag: str,
        simulation_object: Optional[SimulationObject] = None,
        param_config: Optional[Dict[str, Dict]] = None,
        width: int = 300,
        **kwargs
    ) -> None:
        self.param_config = param_config if param_config is not None else {}
        self.width = width
        self.control_tags: Dict[str, str] = {}      # слайдеры или мантисса
        self.input_tags: Dict[str, str] = {}        # поля ввода (для обычного show_input)
        self.exp_input_tags: Dict[str, str] = {}    # поля ввода экспоненты
        self.set_display_tags: Dict[str, str] = {}  # текст "Set: ..."
        self.now_display_tags: Dict[str, str] = {}  # текст "Now: ..."
        super().__init__(tag, simulation_object, **kwargs)

    def set_configure(self, **kwargs) -> None:
        if 'param_config' in kwargs:
            self.param_config = kwargs['param_config']
        if 'width' in kwargs:
            self.width = kwargs['width']
        super().set_configure(**kwargs)

    def _compute_mantissa_exp(self, value: float) -> tuple[float, int]:
        """Преобразует число в мантиссу (1..10) и экспоненту."""
        if value == 0.0:
            return 0.0, 0
        exp = math.floor(math.log10(abs(value)))
        mantissa = value / (10 ** exp)
        return mantissa, exp

    def _update_scientific_display(self, param_name: str) -> None:
        """Обновляет SetValueDisplay для научного режима."""
        cfg = self.param_config.get(param_name, {})
        mantissa_tag = self.control_tags.get(param_name)
        exp_tag = self.exp_input_tags.get(param_name)
        display_tag = self.set_display_tags.get(param_name)

        if not mantissa_tag or not display_tag:
            return

        mantissa = dpg.get_value(mantissa_tag)
        if exp_tag:
            exp = dpg.get_value(exp_tag)
        else:
            exp = cfg.get('fixed_exponent', 0)

        value = mantissa * (10 ** exp)
        dpg.set_value(display_tag, f"Set: {value:.4e}")

    def _on_mantissa_change(self, sender, app_data, user_data):
        param_name = user_data
        self._update_scientific_display(param_name)
        cfg = self.param_config.get(param_name, {})
        if not cfg.get('lazy', False):
            self._apply_scientific_value(param_name)

    def _on_exponent_change(self, sender, app_data, user_data):
        param_name = user_data
        self._update_scientific_display(param_name)
        cfg = self.param_config.get(param_name, {})
        if not cfg.get('lazy', False):
            self._apply_scientific_value(param_name)

    def _apply_scientific_value(self, param_name: str):
        """Применяет текущее научное значение к объекту."""
        target = self.simulation_object
        if target is None:
            return
        cfg = self.param_config.get(param_name, {})
        mantissa_tag = self.control_tags.get(param_name)
        exp_tag = self.exp_input_tags.get(param_name)
        if not mantissa_tag:
            return
        mantissa = dpg.get_value(mantissa_tag)
        exp = dpg.get_value(exp_tag) if exp_tag else cfg.get('fixed_exponent', 0)
        value = mantissa * (10 ** exp)
        if hasattr(target, 'set_parameters'):
            target.set_parameters(**{param_name: value})
        elif hasattr(target, 'set_value'):
            target.set_value(value)

    def _on_set_clicked(self, sender, app_data, user_data):
        param_name = user_data
        self._apply_scientific_value(param_name)

    def _on_param_change(self, sender, app_data, user_data) -> None:
        """Колбэк изменения обычного параметра (не научного)."""
        param_name = user_data
        value = app_data
        target = self.simulation_object
        if target is None:
            return
        display_tag = self.set_display_tags.get(param_name)
        slider_tag = self.control_tags.get(param_name)
        input_tag = self.input_tags.get(param_name)
        if sender == slider_tag and input_tag and dpg.does_item_exist(input_tag):
            dpg.set_value(input_tag, value)
        elif sender == input_tag and slider_tag and dpg.does_item_exist(slider_tag):
            dpg.set_value(slider_tag, value)

        if hasattr(target, 'set_parameters'):
            target.set_parameters(**{param_name: value})
        elif hasattr(target, 'set_value'):
            target.set_value(value)
        dpg.set_value(display_tag, f"Set: {value:.4e}")

    def init(self, parent_tag: Optional[str] = None) -> None:
        self.parent_tag = parent_tag
        with dpg.group(tag=self.tag, parent=parent_tag, horizontal=False):
            for param_name, cfg in self.param_config.items():
                label = cfg.get('label', str(param_name))
                param_type = cfg.get('type', 'float')
                default = cfg.get('default', 0)
                range_ = cfg.get('range', (0, 1))
                show_input = cfg.get('show_input', False)
                extra_accuracy = cfg.get('extra_accuracy', False)
                lazy = cfg.get('lazy', False)
                use_mantissa = cfg.get('use_mantissa', False)

                with dpg.group(horizontal=False):  # GroupContainer
                    # GroupRow1
                    with dpg.group(horizontal=True):
                        dpg.add_text("ParameterController:", color=[0, 191, 255])
                        dpg.add_text(label)

                    if use_mantissa or extra_accuracy:
                        # === Научный режим ===
                        mantissa_default, exp_default = self._compute_mantissa_exp(default)
                        mantissa_range = cfg.get('mantissa_range', (0.0, 1.0))
                        # Если extra_accuracy=False, используем fixed_exponent (если не задан, то вычисленный)
                        fixed_exponent = cfg.get('fixed_exponent', exp_default)

                        # GroupRow2
                        with dpg.group(horizontal=True):
                            # MantissaSlider (всегда)
                            slider_tag = f"{self.tag}_{param_name}_mantissa"
                            self.control_tags[str(param_name)] = slider_tag
                            dpg.add_slider_float(
                                tag=slider_tag,
                                default_value=mantissa_default,
                                min_value=mantissa_range[0],
                                max_value=mantissa_range[1],
                                width=self.width,
                                callback=self._on_mantissa_change,
                                user_data=str(param_name)
                            )

                            # ExponentInput или текст с фиксированной экспонентой
                            if extra_accuracy:
                                exp_tag = f"{self.tag}_{param_name}_exp"
                                self.exp_input_tags[str(param_name)] = exp_tag
                                dpg.add_input_int(
                                    tag=exp_tag,
                                    default_value=exp_default,
                                    width=80,
                                    callback=self._on_exponent_change,
                                    user_data=str(param_name)
                                )
                            else:
                                # показываем текст с фиксированной экспонентой
                                dpg.add_text(f"e{fixed_exponent}", color=[150, 150, 150])

                            # SetButton (только при lazy)
                            if lazy:
                                dpg.add_button(
                                    label="Set",
                                    callback=self._on_set_clicked,
                                    user_data=str(param_name)
                                )

                            # SetValueDisplay (всегда)
                            set_display_tag = f"{self.tag}_{param_name}_set_display"
                            self.set_display_tags[str(param_name)] = set_display_tag
                            dpg.add_text("", tag=set_display_tag)

                            # NowValueDisplay (только при lazy)
                            if lazy:
                                now_display_tag = f"{self.tag}_{param_name}_now_display"
                                self.now_display_tags[str(param_name)] = now_display_tag
                                dpg.add_text("", tag=now_display_tag, color=[0, 255, 0])
                        # Инициализация отображения
                        self._update_scientific_display(param_name)
                    else:
                        slider_tag = f"{self.tag}_{param_name}_slider"
                        self.control_tags[str(param_name)] = slider_tag
                        with dpg.group(horizontal=True):
                            if param_type == 'float':
                                dpg.add_slider_float(
                                    tag=slider_tag,
                                    default_value=float(default),
                                    min_value=float(range_[0]),
                                    max_value=float(range_[1]),
                                    width=self.width,
                                    callback=self._on_param_change,
                                    user_data=str(param_name)
                                )
                                if show_input:
                                    input_tag = f"{self.tag}_{param_name}_input"
                                    self.input_tags[str(param_name)] = input_tag
                                    dpg.add_input_float(
                                        tag=input_tag,
                                        default_value=float(default),
                                        width=80,
                                        callback=self._on_param_change,
                                        user_data=str(param_name),
                                        step=0.0,
                                        format="%.4e"
                                    )
                            elif param_type == 'int':
                                dpg.add_slider_int(
                                    tag=slider_tag,
                                    default_value=int(default),
                                    min_value=int(range_[0]),
                                    max_value=int(range_[1]),
                                    width=self.width,
                                    callback=self._on_param_change,
                                    user_data=str(param_name)
                                )
                                if show_input:
                                    input_tag = f"{self.tag}_{param_name}_input"
                                    self.input_tags[str(param_name)] = input_tag
                                    dpg.add_input_int(
                                        tag=input_tag,
                                        default_value=int(default),
                                        width=80,
                                        callback=self._on_param_change,
                                        user_data=str(param_name)
                                    )
                            # SetValueDisplay (всегда)
                            set_display_tag = f"{self.tag}_{param_name}_set_display"
                            self.set_display_tags[str(param_name)] = set_display_tag
                            dpg.add_text("Set:", tag=set_display_tag,)
                        self._update_scientific_display(param_name)


    def build(self) -> None:
        pass

    def update(self) -> None:
        """Синхронизация с реальными значениями объекта (для обычных слайдеров)."""
        target = self.simulation_object
        if target is None:
            return
        for param_name, tag in self.control_tags.items():
            cfg = self.param_config.get(param_name, {})
            # Для научного режима с lazy обновляем NowValueDisplay
            if cfg.get('lazy') and self.now_display_tags.get(param_name):
                if hasattr(target, param_name):
                    current_val = getattr(target, param_name)
                else:
                    continue
                now_tag = self.now_display_tags[param_name]
                if dpg.does_item_exist(now_tag):
                    dpg.set_value(now_tag, f"Now: {current_val:.4e}")
                continue

            # Обычный режим: синхронизация слайдера
            if hasattr(target, param_name):
                current_val = getattr(target, param_name)
            else:
                continue
            if cfg.get('type') == 'int':
                current_val = int(current_val)
            if dpg.does_item_exist(tag) and dpg.get_value(tag) != current_val:
                dpg.set_value(tag, current_val)
            # Также синхронизируем поле ввода, если есть
            input_tag = self.input_tags.get(param_name)
            if input_tag and dpg.does_item_exist(input_tag):
                dpg.set_value(input_tag, current_val)