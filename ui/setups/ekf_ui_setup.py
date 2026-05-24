# ui/setups/ekf_ui_setup.py
# -*- coding: utf-8 -*-
"""
UI сетап для эксперимента с EKF оценкой SOC.
Использует TabBar'ы для группировки графиков и настроек.
"""

import dearpygui.dearpygui as dpg
from typing import List, Optional, Callable

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from ..widgets.parameter_control_widget import ParameterControlWidget
from core.experiments.ekf_simulation_setup import EKFSimulationSetup
from core.elements.generators.constant_generator import ConstantGenerator
from core.elements.generators.cyclic_profile_generator import CyclicProfileGenerator
from ..widgets.data_logger_widget import DataLoggerWidget

from apps.utils.config import AppContext

class EKFUISetup(BlankSetup):
    def __init__(self, setup_tag: str, sim_setup: EKFSimulationSetup):
        super().__init__(setup_tag)
        self.sim_setup = sim_setup

    # ------------------------------------------------------------------
    # Вспомогательные фабрики UINode (для компактности get_setup)
    # ------------------------------------------------------------------
    @staticmethod
    def _make_group(name: str, horizontal: bool = False,
                    children: Optional[List[UINode]] = None) -> UINode:
        """Создать вертикальную или горизонтальную группу."""
        node = UINode(
            name=name,
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=horizontal
        )
        if children:
            for child in children:
                node.add_children(child)
        return node

    @staticmethod
    def _make_child_window(name: str, children: Optional[List[UINode]] = None,
                           border: bool = True, **kwargs) -> UINode:
        """Создать child_window с автоматическим размером."""
        static_kwargs = {"width":0, "height":0, "border":border}.copy()
        static_kwargs.update(kwargs)
        node = UINode(
            name=name,
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_child_window,
            **static_kwargs
        )
        if children:
            for child in children:
                node.add_children(child)
        return node

    @staticmethod
    def _make_tab_bar(name: str, children: Optional[List[UINode]] = None) -> UINode:
        """Создать TabBar."""
        node = UINode(
            name=name,
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab_bar
        )
        if children:
            for child in children:
                node.add_children(child)
        return node

    @staticmethod
    def _make_tab(name: str, label: str,
                  children: Optional[List[UINode]] = None) -> UINode:
        """Создать вкладку Tab."""
        node = UINode(
            name=name,
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab,
            label=label
        )
        if children:
            for child in children:
                node.add_children(child)
        return node

    @staticmethod
    def _make_text_header(name: str, text: str) -> UINode:
        """Создать заголовок в стиле ParameterControlWidget."""
        return UINode(
            name=name,
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text,
            default_value=text,
            color=[0, 191, 255]
        )

    # ------------------------------------------------------------------
    # Основной метод построения UI
    # ------------------------------------------------------------------
    def get_setup(self) -> UINode:
        battery = self.sim_setup.battery
        current_gen = self.sim_setup.current_gen
        temp_gen = self.sim_setup.temp_gen
        ekf = self.sim_setup.ekf
        voltage_noise_adder = self.sim_setup.voltage_adder
        voltage_noise_gen = self.sim_setup.voltage_noise_gen

        # ----- Графики (создаём как объекты HistoryPlotWidget) -----
        true_soc_plot = HistoryPlotWidget(
            tag=f"{self.tag}_true_soc_plot",
            simulation_object=battery,
            data_keys={'soc': 'True SOC'},
            title="True State of Charge",
            height=250, width=500, window_size=200,
            y_limits=(0.0, 1.0)
        )
        true_soc_node = widget_to_node("TrueSOCPlot", true_soc_plot)

        ekf_soc_plot = HistoryPlotWidget(
            tag=f"{self.tag}_ekf_soc_plot",
            simulation_object=ekf,
            data_keys={'soc_est': 'EKF SOC'},
            title="EKF SOC Estimate",
            height=250, width=500, window_size=200,
            y_limits=(0.0, 1.0)
        )
        ekf_soc_node = widget_to_node("EKFSOCPlot", ekf_soc_plot)

        error_plot = HistoryPlotWidget(
            tag=f"{self.tag}_error_plot",
            simulation_object=ekf,
            data_keys={'soc_error': 'SOC Error'},
            title="SOC Estimation Error",
            height=250, width=500, window_size=200,
            y_limits=(-1.0, 1.0)
        )
        error_node = widget_to_node("ErrorPlot", error_plot)

        cov_plot = HistoryPlotWidget(
            tag=f"{self.tag}_cov_plot",
            simulation_object=ekf,
            data_keys={'P00': 'P00', 'P11': 'P11'},
            title="Covariance Diagonal Elements",
            height=250, width=500, window_size=200
        )
        cov_node = widget_to_node("CovPlot", cov_plot)

        voltage_true_plot = HistoryPlotWidget(
            tag=f"{self.tag}_voltage_true",
            simulation_object=battery,
            data_keys={'voltage_terminal': 'True Voltage'},
            title="Battery Voltage",
            height=200, width=500, window_size=200, y_limits=(0, 6.0)
        )
        voltage_true_node = widget_to_node("TrueVoltagePlot", voltage_true_plot)

        voltage_meas_plot = HistoryPlotWidget(
            tag=f"{self.tag}_voltage_meas",
            simulation_object=voltage_noise_adder,
            data_keys={'V_measured': 'Measured Voltage'},
            title="Measured Voltage",
            height=200, width=500, window_size=200, y_limits=(0, 6.0)
        )
        voltage_meas_node = widget_to_node("MeasVoltagePlot", voltage_meas_plot)

        innov_plot = HistoryPlotWidget(
            tag=f"{self.tag}_innov_plot",
            simulation_object=ekf,
            data_keys={'innovation': 'Innovation'},
            title="EKF Innovation",
            height=150, width=500, window_size=200
        )
        innov_node = widget_to_node("InnovPlot", innov_plot)

        # ----- Live Parameters (с перенесённым управлением) -----
        from .live_parameters_setup import LiveParametersSetup

        # Виджеты управления, которые теперь будут внутри LiveParameters
        current_control = None
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
                width=250
            )
        
        temp_control = None
        if isinstance(temp_gen, ConstantGenerator):
            temp_control = ParameterControlWidget(
                tag=f"{self.tag}_temp_ctrl",
                simulation_object=temp_gen,
                param_config={
                    'value': {
                        'type': 'float',
                        'range': (-10.0, 60.0),
                        'default': temp_gen.value,
                        'label': 'Temperature (C)'
                    }
                },
                width=250
            )

        voltage_noise_control = ParameterControlWidget(
            tag=f"{self.tag}_noise_ctrl",
            simulation_object=voltage_noise_gen,
            param_config={
                'sigma': {
                    'type': 'float',
                    'range': (0.0, 0.1),
                    'default': voltage_noise_gen.sigma,
                    'label': 'Noise Sigma (V)'
                }
            },
            width=250
        )

        # Слайдер шума тока
        current_noise_control = None
        if hasattr(self.sim_setup, 'current_noise_gen') and self.sim_setup.current_noise_gen:
            current_noise_control = ParameterControlWidget(
                tag=f"{self.tag}_current_noise_ctrl",
                simulation_object=self.sim_setup.current_noise_gen,
                param_config={
                    'sigma': {
                        'type': 'float',
                        'range': (0.0, 0.1),
                        'default': self.sim_setup.current_noise_gen.sigma,
                        'label': 'I Noise Sigma (A)'
                    }
                },
                width=250
            )

        # Слайдер шума температуры
        temp_noise_control = None
        if hasattr(self.sim_setup, 'temp_noise_gen') and self.sim_setup.temp_noise_gen:
            temp_noise_control = ParameterControlWidget(
                tag=f"{self.tag}_temp_noise_ctrl",
                simulation_object=self.sim_setup.temp_noise_gen,
                param_config={
                    'sigma': {
                        'type': 'float',
                        'range': (0.0, 10.0),
                        'default': self.sim_setup.temp_noise_gen.sigma,
                        'label': 'T Noise Sigma (C)'
                    }
                },
                width=250
            )

        live_setup = LiveParametersSetup(
            setup_tag=f"{self.tag}_live",
            battery=battery,
            current_gen=current_gen,
            voltage_adder=voltage_noise_adder,
            temp_gen=temp_gen,
            ekf=ekf,
            current_control_widget=current_control,
            temp_control_widget=temp_control,
            voltage_noise_control_widget=voltage_noise_control,
            # Новые параметры
            current_adder=self.sim_setup.current_adder,
            temp_adder=self.sim_setup.temp_adder,
            current_noise_gen=self.sim_setup.current_noise_gen,
            temp_noise_gen=self.sim_setup.temp_noise_gen,
            temp_noise_control_widget=temp_noise_control,   # слайдер шума T
            current_noise_control_widget=current_noise_control  # слайдер шума I
        )
        live_node = live_setup.get_setup()

        # ----- Элементы управления EKF (ковариации) -----
        ekf_controls = []
        ekf_param_configs = [
            ('R', 'Meas. noise R', ekf.R_val, (0, 1)),
            ('Q00', 'Proc. noise Q00 (SOC)', ekf.Q00, (0, 1)),
            ('Q11', 'Proc. noise Q11 (Vc)', ekf.Q11, (0, 1)),
            ('P00', 'Init. cov P00 (SOC)', ekf.P00, (0, 1)),
            ('P11', 'Init. cov P11 (Vc)', ekf.P11, (0, 1)),
        ]
        for name, label, default, rng in ekf_param_configs:
            widget = ParameterControlWidget(
                tag=f"{self.tag}_ekf_{name}",
                simulation_object=ekf,
                param_config={
                    name: {
                        'type': 'float',
                        'default': default,
                        'label': label,
                        'use_mantissa': True,
                        'extra_accuracy': True,
                        'lazy': True,
                        'mantissa_range': (0.0, 10.0),
                        'exp_range': (-6, 2)
                    }
                },
                width=250
            )
            ekf_controls.append(widget_to_node(f"EKF_{name}_Control", widget))
        ekf_settings_group = self._make_group("EKFSettings", horizontal=False, children=ekf_controls)

        # ----- Компоновка строк -----
        # Строка 1: True SOC (слева) | Live Parameters (справа)
        group_row1 = self._make_group("GroupRow1", horizontal=True, children=[
            true_soc_node,
            live_node
        ])

        # Строка 2: EKF SOC (слева) | EKF Settings (справа)
        group_row2 = self._make_group("GroupRow2", horizontal=True, children=[
            ekf_soc_node,
            ekf_settings_group
        ])

        # ----- Сборка первой строки: TabBar с вкладками -----
        models_tab_content = self._make_group("ModelsTabContent", horizontal=False, children=[group_row1, group_row2])
        models_tab = self._make_tab("TabModels", "Models settings", children=[models_tab_content])

        error_tab_content = self._make_child_window("ErrorChildWin", children=[error_node])
        error_tab = self._make_tab("TabError", "Error statistic", children=[error_tab_content])

        cov_tab_content = self._make_child_window("CovChildWin", children=[cov_node])
        cov_tab = self._make_tab("TabCov", "Covariance", children=[cov_tab_content])

        tab_bar_row1 = self._make_tab_bar("TabBarRow1", children=[models_tab, error_tab, cov_tab])
        child_win_row1 = self._make_child_window("ChildWinRow1", children=[tab_bar_row1], height=600)
        row1 = self._make_group("EKFExp_row1", horizontal=True, children=[child_win_row1])

        # ----- Вторая строка: графики Other plots -----
        header_text = self._make_text_header("HeaderOtherPlots", "Other plots")
        plots_tab_bar = self._make_tab_bar("PlotsTabBar", children=[
            self._make_tab("TabTrueV", "True voltage", children=[voltage_true_node]),
            self._make_tab("TabMeasV", "Meas voltage", children=[voltage_meas_node]),
            self._make_tab("TabInnov", "EKF innovation", children=[innov_node])
        ])
        row2_content = self._make_group("Row2Content", horizontal=False, children=[header_text, plots_tab_bar])
        child_win_row2 = self._make_child_window("ChildWinRow2", children=[row2_content])
        row2 = self._make_group("EKFExp_row2", horizontal=True, children=[child_win_row2])

        main_group = self._make_group("EKFExp_main", horizontal=False, children=[row1, row2])
        return main_group