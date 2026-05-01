# ui/setups/constant_setup.py
from typing import Optional
import dearpygui.dearpygui as dpg

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from ..widgets.parameter_control_widget import ParameterControlWidget
from core.elements.generators.constant_generator import ConstantGenerator


class ConstantSetup(BlankSetup):
    def __init__(self, setup_tag: str, generator: Optional[ConstantGenerator] = None):
        super().__init__(setup_tag)
        self.generator = generator

    def get_setup(self) -> UINode:
        if self.generator is None:
            raise ValueError("ConstantGenerator not set")

        # Виджет управления параметром
        param_widget = ParameterControlWidget(
            tag=f"{self.tag}_param",
            simulation_object=self.generator,
            param_config={
                'value': {
                    'type': 'float',
                    'range': (-10.0, 10.0),
                    'default': self.generator.value,
                    'label': 'Constant Value'
                }
            },
            width=300
        )
        param_node = widget_to_node("ParamControl", param_widget)

        # График истории
        plot_widget = HistoryPlotWidget(
            tag=f"{self.tag}_plot",
            simulation_object=self.generator,
            data_keys={self.generator.output_key: "Value"},
            title="Constant Output",
            height=300,
            width=600,
            window_size=200
        )
        plot_node = widget_to_node("Plot", plot_widget)

        # Группа
        group = UINode(
            name=f"{self.tag}_group",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=False
        )
        group.add_children(param_node)
        group.add_children(plot_node)

        return group