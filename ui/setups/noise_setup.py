# ui/setups/noise_setup.py
from typing import Optional
import dearpygui.dearpygui as dpg

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from ..widgets.history_histogram_widget import HistoryPlotHistogramWidget
from ..widgets.noise_distribution_widget import NoiseDistributionWidget
from core.elements.generators.noise_generator import NoiseGenerator


class NoiseSetup(BlankSetup):
    """
    Сетап для настройки и визуализации шума.
    Возвращает корневой UINode, содержащий все виджеты и элементы управления.
    """

    def __init__(self, setup_tag: str, noise_generator: Optional[NoiseGenerator] = None):
        super().__init__(setup_tag)
        self.noise_generator = noise_generator

    def set_noise_generator(self, noise_generator: NoiseGenerator) -> None:
        self.noise_generator = noise_generator

    def get_setup(self) -> UINode:
        if self.noise_generator is None:
            raise ValueError("Noise generator is not set in NoiseSetup")

        # ----- Создаём виджеты -----
        plot_widget = HistoryPlotWidget(
            tag=f"{self.tag}_noise_plot",
            simulation_object=self.noise_generator,
            data_keys={
                self.noise_generator.output_key:"noise",
                self.noise_generator.output_key+self.noise_generator.bias_name:"bias",
                self.noise_generator.output_key+self.noise_generator.sigma_name:"sigma",
                },
            #y_keys=["I_noise"],
            title="Noise History",
            height=400,
            width=800,
            window_size=500
        )

        dist_widget = NoiseDistributionWidget(
            tag=f"{self.tag}_noise_dist",
            noise_generator=self.noise_generator,
            sigma_range=(0.0, 2.0),
            bias_range=(-2.0, 2.0),
            width=350,
            height=250
        )

        hist_widget = HistoryPlotHistogramWidget(
            tag=f"{self.tag}_noise_hist",
            history_plot_widget=plot_widget,
            data_key="I_noise",
            eps=0.1,
            eps_range=(0.01, 0.5),
            height=250,
            width=400,
            title="Real Noise Distribution"
        )

        # ----- Преобразуем виджеты в узлы -----
        node_plot = widget_to_node("NoisePlot", plot_widget)
        node_dist = widget_to_node("NoiseDist", dist_widget)
        node_hist = widget_to_node("NoiseHist", hist_widget)

        # ----- Создаём дополнительные элементы DPG -----
        text_current = UINode(
            name="TextCurrentNoise",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text,
            default_value="Current noise: ---"
        )
        # Функция обновления текста текущего шума
        def update_current_text():
            val = self.noise_generator.current_noise
            text = f"Current noise: {val:.4f}" if val is not None else "Current noise: ---"
            dpg.set_value(text_current.tag, text)
        text_current.update_func = update_current_text

        # Горизонтальная группа для текста
        h_layer_text = UINode(
            name="HorizontalText",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )
        h_layer_text.add_children(text_current)

        # Разделители
        sep1 = UINode(
            name="Separator1",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_separator
        )
        sep2 = UINode(
            name="Separator2",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_separator
        )

        # Горизонтальный слой для графика истории (он один, но для единообразия кладём в группу)
        h_layer_plot = UINode(
            name="HorizontalPlot",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )
        h_layer_plot.add_children(node_plot)

        # Горизонтальный слой для гистограммы и распределения
        h_layer_hist_dist = UINode(
            name="HorizontalHistDist",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )
        h_layer_hist_dist.add_children(node_hist)
        h_layer_hist_dist.add_children(node_dist)

        # ----- Собираем всё в контейнер (child_window) -----
        noise_window = UINode(
            name=f"{self.tag}_NoiseWindow",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_child_window,
            label="Noise Analysis",
            width=0,
            height=0
        )
        noise_window.add_children(h_layer_text)
        noise_window.add_children(sep1)
        noise_window.add_children(h_layer_plot)
        noise_window.add_children(sep2)
        noise_window.add_children(h_layer_hist_dist)

        return noise_window