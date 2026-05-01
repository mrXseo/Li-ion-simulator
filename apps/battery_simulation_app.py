# apps/battery_simulation_app.py
# -*- coding: utf-8 -*-
"""
Приложение для симуляции модели батареи.
"""

import dearpygui.dearpygui as dpg

from .base_simulation_app import BaseSimulationApp
from ui.tools.tree import UINode, TreeTypes
from ui.setups.battery_ui_setup import BatteryUISetup
from ui.setups.simulation_control_setup import SimulationControlSetup
from core.experiments.battery_simulation_setup import BatterySimulationSetup


class BatterySimulationApp(BaseSimulationApp):

    @property
    def app_name(self):
        return "battery_app"

    def __init__(self):
        super().__init__()
        self.sim_setup: BatterySimulationSetup = None

    def setup_simulation(self) -> None:
        self.sim_setup = BatterySimulationSetup(
            self.engine,
            current_mode='constant',
            current_value=1.0,
            temperature_value=25.0,
            battery_params={'capacity_nom': 5.0, 'initial_soc': 1.0}
        )
        self.sim_setup.build()

    def setup_ui(self) -> None:
        battery_ui = BatteryUISetup("BatteryExp", self.sim_setup)
        battery_node = battery_ui.get_setup()

        # Панель управления через общий сетап
        control_setup = SimulationControlSetup("ControlPanel", self)
        control_node = control_setup.get_setup()

        # Вкладка Control
        tab_control = UINode(
            name="TabControl",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab,
            label="Control"
        )
        tab_control.add_children(control_node)

        # Вкладка Battery
        tab_battery = UINode(
            name="TabBattery",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab,
            label="Battery"
        )
        tab_battery.add_children(battery_node)

        tab_bar = UINode(
            name="MainTabBar",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab_bar,
            label="Tool"
        )
        tab_bar.add_children(tab_control)
        tab_bar.add_children(tab_battery)

        main_win = UINode(
            name="MainWindow",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_window,
            label="Battery Simulator",
            width=1000,
            height=700
        )
        main_win.add_children(tab_bar)

        self.root_node = main_win

    def _get_viewport_title(self) -> str:
        return "Battery Simulator"


if __name__ == "__main__":
    app = BatterySimulationApp()
    app.run()