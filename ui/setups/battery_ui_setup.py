# ui/setups/battery_ui_setup.py
# -*- coding: utf-8 -*-
"""
UI сетап для эксперимента с моделью батареи.
Использует готовый BatterySimulationSetup для доступа к объектам.
"""

from typing import Optional
import dearpygui.dearpygui as dpg

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from ..widgets.parameter_control_widget import ParameterControlWidget
from core.experiments.battery_simulation_setup import BatterySimulationSetup
from core.elements.generators.constant_generator import ConstantGenerator
from core.elements.generators.cyclic_profile_generator import CyclicProfileGenerator


class BatteryUISetup(BlankSetup):
    """
    Строит UI для управления и визуализации эксперимента с батареей.
    Ожидает, что BatterySimulationSetup уже выполнил build().
    """

    def __init__(self, setup_tag: str, sim_setup: BatterySimulationSetup):
        super().__init__(setup_tag)
        self.sim_setup = sim_setup

    def get_setup(self) -> UINode:
        battery = self.sim_setup.battery
        current_gen = self.sim_setup.current_gen
        temp_gen = self.sim_setup.temp_gen

        if battery is None or current_gen is None or temp_gen is None:
            raise RuntimeError("BatterySimulationSetup.build() must be called before creating UI")

        # ----- Виджеты управления -----
        controls = []

        # Управление током
        if isinstance(current_gen, ConstantGenerator):
            current_control = ParameterControlWidget(
                tag=f"{self.tag}_current_ctrl",
                simulation_object=current_gen,
                param_config={
                    'value': {
                        'type': 'float',
                        'range': (-5.0, 5.0),
                        'default': current_gen.value,
                        'label': 'Current (A)'
                    }
                },
                width=300
            )
            controls.append(widget_to_node("CurrentControl", current_control))
        elif isinstance(current_gen, CyclicProfileGenerator):
            # Для циклического профиля добавим кнопку генерации нового профиля
            # и текстовое поле для отображения текущего профиля (упрощённо)
            # Пока просто кнопка
            def generate_new_profile():
                import random
                new_profile = [random.uniform(-2.0, 2.0) for _ in range(20)]
                self.sim_setup.set_current_profile(new_profile)

            gen_btn = UINode(
                name="GenerateProfileBtn",
                tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                init_func=dpg.add_button,
                label="Generate Random Profile",
                callback=generate_new_profile
            )
            controls.append(gen_btn)

        # Управление температурой (всегда константа)
        temp_control = ParameterControlWidget(
            tag=f"{self.tag}_temp_ctrl",
            simulation_object=temp_gen,
            param_config={
                'value': {
                    'type': 'float',
                    'range': (-10.0, 60.0),
                    'default': temp_gen.value,
                    'label': 'Temperature (°C)'
                }
            },
            width=300
        )
        controls.append(widget_to_node("TempControl", temp_control))

        # Горизонтальная группа для элементов управления
        controls_group = UINode(
            name=f"{self.tag}_controls",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )
        for ctrl in controls:
            controls_group.add_children(ctrl)

        # ----- Графики -----
        voltage_plot = HistoryPlotWidget(
            tag=f"{self.tag}_voltage_plot",
            simulation_object=battery,
            data_keys={
                'voltage_terminal': 'V_term (V)',
                'ocv': 'OCV (V)'
            },
            title="Battery Voltage",
            height=300,
            width=600,
            window_size=200
        )
        voltage_node = widget_to_node("VoltagePlot", voltage_plot)

        soc_plot = HistoryPlotWidget(
            tag=f"{self.tag}_soc_plot",
            simulation_object=battery,
            data_keys={'soc': 'SOC'},
            title="State of Charge",
            height=250,
            width=600,
            window_size=200
        )
        soc_node = widget_to_node("SOCPlot", soc_plot)

        # Можно добавить график тока для наглядности
        current_plot = HistoryPlotWidget(
            tag=f"{self.tag}_current_plot",
            simulation_object=current_gen,
            data_keys={current_gen.output_key: 'Current (A)'},
            title="Load Current",
            height=200,
            width=600,
            window_size=200
        )
        current_plot_node = widget_to_node("CurrentPlot", current_plot)

        # ----- Сборка -----
        main_group = UINode(
            name=f"{self.tag}_main",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=False
        )
        main_group.add_children(controls_group)
        main_group.add_children(voltage_node)
        main_group.add_children(soc_node)
        main_group.add_children(current_plot_node)

        return main_group