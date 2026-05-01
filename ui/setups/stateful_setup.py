# ui/setups/stateful_setup.py
from typing import Optional
import dearpygui.dearpygui as dpg

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from core.elements.generators.stateful_generator import StatefulGenerator


class StatefulSetup(BlankSetup):
    def __init__(self, setup_tag: str, generator: Optional[StatefulGenerator] = None):
        super().__init__(setup_tag)
        self.generator = generator

    def _set_counter(self):
        if self.generator:
            self.generator.update_func = lambda s, f: s + 1
            self.generator.reset_state()

    def _set_sawtooth(self):
        if self.generator:
            self.generator.update_func = lambda s, f: (s + 0.1) % 1.0
            self.generator.reset_state()

    def get_setup(self) -> UINode:
        if self.generator is None:
            raise ValueError("StatefulGenerator not set")

        btn_counter = UINode(
            name="CounterMode",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Counter (+1 each frame)",
            callback=self._set_counter
        )
        btn_saw = UINode(
            name="SawtoothMode",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Sawtooth (0->1, step 0.1)",
            callback=self._set_sawtooth
        )

        plot_widget = HistoryPlotWidget(
            tag=f"{self.tag}_plot",
            simulation_object=self.generator,
            data_keys={self.generator.output_key: "State"},
            title="Stateful Output",
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
        group.add_children(btn_counter)
        group.add_children(btn_saw)
        group.add_children(plot_node)

        return group