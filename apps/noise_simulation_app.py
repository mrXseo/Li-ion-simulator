# apps/noise_simulation_app.py
# -*- coding: utf-8 -*-
"""
Приложение для тестирования генератора шума.
"""

import dearpygui.dearpygui as dpg

from .base_simulation_app import BaseSimulationApp
from ui.tools.tree import UINode, TreeTypes, widget_to_node
from ui.setups.noise_setup import NoiseSetup
from ui.setups.simulation_control_setup import SimulationControlSetup
from core.elements.generators.noise_generator import NoiseGenerator


class NoiseSimulationApp(BaseSimulationApp):

    @property
    def app_name(self):
        return "noise_generator_app"

    def __init__(self):
        super().__init__()
        self.noise_gen: NoiseGenerator = None

    def setup_simulation(self) -> None:
        self.noise_gen = NoiseGenerator(
            simulation_engine=self.engine,
            sigma=0.5,
            bias=0.1,
            output_key="I_noise",
            frame_list_size=500
        )

    def setup_ui(self) -> None:
        noise_setup = NoiseSetup("NoiseSetup", self.noise_gen)
        noise_node = noise_setup.get_setup()

        # Панель управления
        control_setup = SimulationControlSetup("ControlPanel", self)
        control_node = control_setup.get_setup()

        # Вкладки
        tab_control = UINode(
            name="TabControl",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab,
            label="Control"
        )
        tab_control.add_children(control_node)

        tab_noise = UINode(
            name="TabNoise",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab,
            label="Noise Analysis"
        )
        tab_noise.add_children(noise_node)

        tab_bar = UINode(
            name="MainTabBar",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab_bar,
            label="Tool"
        )
        tab_bar.add_children(tab_control)
        tab_bar.add_children(tab_noise)

        main_win = UINode(
            name="MainWindow",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_window,
            label="Noise Simulator",
            width=1000,
            height=700
        )
        main_win.add_children(tab_bar)

        self.root_node = main_win

    def _get_viewport_title(self) -> str:
        return "Noise Generator Simulator"


if __name__ == "__main__":
    app = NoiseSimulationApp()
    app.run()