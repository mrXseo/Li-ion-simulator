# ui/setups/cyclic_profile_setup.py
from typing import Optional, List
import random
import dearpygui.dearpygui as dpg

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from core.elements.generators.cyclic_profile_generator import CyclicProfileGenerator


class CyclicProfileSetup(BlankSetup):
    def __init__(self, setup_tag: str, generator: Optional[CyclicProfileGenerator] = None):
        super().__init__(setup_tag)
        self.generator = generator

    def _generate_random_profile(self) -> List[float]:
        return [random.uniform(-2.0, 2.0) for _ in range(20)]

    def _on_generate_click(self):
        if self.generator:
            new_profile = self._generate_random_profile()
            self.generator.set_profile(new_profile)

    def get_setup(self) -> UINode:
        if self.generator is None:
            raise ValueError("CyclicProfileGenerator not set")

        gen_btn = UINode(
            name="GenerateProfileBtn",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Generate Random Profile",
            callback=self._on_generate_click
        )

        plot_widget = HistoryPlotWidget(
            tag=f"{self.tag}_plot",
            simulation_object=self.generator,
            data_keys={self.generator.output_key: "Profile Value"},
            title="Cyclic Profile Output",
            height=300,
            width=600,
            window_size=200
        )
        plot_node = widget_to_node("Plot", plot_widget)

        group = UINode(
            name=f"{self.tag}_group",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=False
        )
        group.add_children(gen_btn)
        group.add_children(plot_node)

        return group