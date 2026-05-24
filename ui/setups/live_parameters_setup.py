# ui/setups/live_parameters_setup.py
import dearpygui.dearpygui as dpg
from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes, widget_to_node
from ..widgets.history_plot_widget import HistoryPlotWidget
from ..widgets.parameter_control_widget import ParameterControlWidget

class LiveParametersSetup(BlankSetup):
    def __init__(self, setup_tag: str, battery, current_gen, voltage_adder, temp_gen, ekf,
                 current_adder=None, temp_adder=None,
                 current_noise_gen=None, voltage_noise_gen=None, temp_noise_gen=None,
                 current_control_widget=None,
                 temp_control_widget=None,
                 voltage_noise_control_widget=None,
                 temp_noise_control_widget=None,
                 current_noise_control_widget=None):   # новый слайдер шума тока
        super().__init__(setup_tag)
        self.battery = battery
        self.current_gen = current_gen
        self.voltage_adder = voltage_adder
        self.temp_gen = temp_gen
        self.ekf = ekf
        self.current_adder = current_adder
        self.temp_adder = temp_adder
        self.current_noise_gen = current_noise_gen
        self.voltage_noise_gen = voltage_noise_gen
        self.temp_noise_gen = temp_noise_gen

        # Готовые виджеты управления
        self.current_control_widget = current_control_widget
        self.temp_control_widget = temp_control_widget
        self.voltage_noise_control_widget = voltage_noise_control_widget
        self.temp_noise_control_widget = temp_noise_control_widget
        self.current_noise_control_widget = current_noise_control_widget  # новый

        self._text_tags = {}
        self._plot_widgets = []
        self._capacity_temp = 25.0

    # --------------------------------------------------------------
    # Построение UI
    # --------------------------------------------------------------
    def get_setup(self) -> UINode:
        main_window = UINode(
            name=f"{self.tag}_window",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_child_window,
            width=-1, height=350, border=True,
            label="Live Parameters"
        )

        tab_bar = UINode(
            name=f"{self.tag}_tab_bar",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_tab_bar
        )
        main_window.add_children(tab_bar)

        tabs_info = [
            ("Current", self._create_current_tab_content),
            ("Voltage", self._create_voltage_tab_content),
            ("Temperature", self._create_temperature_tab_content),
            ("Resistance", self._create_resistance_tab_content),
            ("SOC", self._create_soc_tab_content),
        ]

        for name, builder in tabs_info:
            tab_node = UINode(
                name=f"{self.tag}_tab_{name}",
                tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                init_func=dpg.add_tab,
                label=name
            )
            content_nodes = builder()
            for node in content_nodes:
                tab_node.add_children(node)
            tab_bar.add_children(tab_node)

        def update_live_params():
            self.update()
        main_window.update_func = update_live_params

        return main_window

    # --------------------------------------------------------------
    # Вспомогательные элементы
    # --------------------------------------------------------------
    def _make_param_row(self, label: str, key: str, default: str = "N/A") -> UINode:
        row = UINode(
            name=f"{self.tag}_row_{key}",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )
        row.add_children(UINode(
            name=f"{self.tag}_label_{key}", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text, default_value=f"{label}:"
        ))
        value_node = UINode(
            name=f"{self.tag}_value_{key}", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text, default_value=default
        )
        def capture_tag(tag):
            self._text_tags[key] = tag
        value_node.build_func = capture_tag
        row.add_children(value_node)
        return row

    def _make_plot(self, tag_suffix: str, title: str, sim_obj, keys: dict,
                   height=250, width=450, window_size=200) -> UINode:
        plot = HistoryPlotWidget(
            tag=f"{self.tag}_plot_{tag_suffix}",
            simulation_object=sim_obj,
            data_keys=keys,
            title=title,
            height=height,
            width=width,
            window_size=window_size
        )
        self._plot_widgets.append(plot)
        return widget_to_node(f"Plot_{tag_suffix}", plot)

    # --------------------------------------------------------------
    # Содержимое вкладок
    # --------------------------------------------------------------
    def _create_current_tab_content(self):
        nodes = []
        # Слайдер тока
        if self.current_control_widget is not None:
            nodes.append(widget_to_node("CurrentControl", self.current_control_widget))
        # Слайдер шума тока (новый)
        if self.current_noise_control_widget is not None:
            nodes.append(widget_to_node("CurrentNoiseControl", self.current_noise_control_widget))
        nodes += [
            UINode(name=f"{self.tag}_current_header", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                   init_func=dpg.add_text, default_value="Current"),
            self._make_param_row("True", "i_true"),
        ]
        if self.current_adder:
            nodes.append(self._make_param_row("Meas", "i_meas"))
        if self.current_noise_gen:
            nodes.append(self._make_param_row("Noise std", "i_noise_std"))
        nodes.append(self._make_plot("current", "I true", self.current_gen,
                                     {self.current_gen.output_key: "I (A)"}))
        return nodes

    def _create_voltage_tab_content(self):
        nodes = []
        if self.voltage_noise_control_widget is not None:
            nodes.append(widget_to_node("VoltageNoiseControl", self.voltage_noise_control_widget))
        nodes += [
            UINode(name=f"{self.tag}_voltage_header", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                   init_func=dpg.add_text, default_value="Voltage"),
            self._make_param_row("True", "v_true"),
            self._make_param_row("Meas", "v_meas"),
            self._make_param_row("Innovation", "innovation"),
        ]
        if self.voltage_noise_gen:
            nodes.append(self._make_param_row("Noise std", "v_noise_std"))
        nodes.append(self._make_plot("voltage", "V true", self.battery,
                                     {'voltage_terminal': 'V true (V)'}))
        return nodes

    def _create_temperature_tab_content(self):
        nodes = []
        if self.temp_control_widget is not None:
            nodes.append(widget_to_node("TempControl", self.temp_control_widget))
        # Слайдер шума температуры (новый)
        if self.temp_noise_control_widget is not None:
            nodes.append(widget_to_node("TempNoiseControl", self.temp_noise_control_widget))
        nodes += [
            UINode(name=f"{self.tag}_temp_header", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                   init_func=dpg.add_text, default_value="Temperature"),
            self._make_param_row("True", "t_true"),
        ]
        if self.temp_adder:
            nodes.append(self._make_param_row("Meas", "t_meas"))
        if self.temp_noise_gen:
            nodes.append(self._make_param_row("Noise std", "t_noise_std"))
        nodes.append(self._make_plot("temp", "T true", self.temp_gen,
                                     {self.temp_gen.output_key: "T (C)"}))
        return nodes

    def _create_resistance_tab_content(self):
        return [
            UINode(name=f"{self.tag}_res_header", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                   init_func=dpg.add_text, default_value="Resistance"),
            self._make_param_row("R0", "r0"),
            self._make_param_row("R1", "r1"),
            self._make_param_row("C1", "c1"),
        ]

    def _create_soc_tab_content(self):
        cap_node = UINode(
            name=f"{self.tag}_capacity_label",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text,
            default_value="Capacity: -- Ah"
        )
        def capture_cap_tag(tag):
            self._text_tags["capacity"] = tag
        cap_node.build_func = capture_cap_tag

        return [
            UINode(name=f"{self.tag}_soc_header", tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                   init_func=dpg.add_text, default_value="SOC"),
            self._make_param_row("True", "soc_true"),
            self._make_param_row("Est", "soc_est"),
            self._make_param_row("Error", "soc_error"),
            cap_node,
        ]

    # --------------------------------------------------------------
    # Обновление значений
    # --------------------------------------------------------------
    def update(self):
        self._update_current()
        self._update_voltage()
        self._update_temperature()
        self._update_resistance()
        self._update_soc()

    def _set_text(self, key: str, value: str):
        tag = self._text_tags.get(key)
        if tag and dpg.does_item_exist(tag):
            dpg.set_value(tag, value)

    def _update_current(self):
        res = self.current_gen.current_result
        if res:
            self._set_text("i_true", f"{res.get('I_load', 0):.3f} A")
        if self.current_adder:
            res_m = self.current_adder.current_result
            if res_m:
                self._set_text("i_meas", f"{res_m.get('I_meas', 0):.3f} A")
        if self.current_noise_gen:
            self._set_text("i_noise_std", f"{self.current_noise_gen.sigma:.4f} A")

    def _update_voltage(self):
        res_b = self.battery.current_result
        if res_b:
            self._set_text("v_true", f"{res_b.get('voltage_terminal', 0):.4f} V")
        res_m = self.voltage_adder.current_result
        if res_m:
            self._set_text("v_meas", f"{res_m.get('V_measured', 0):.4f} V")
        res_e = self.ekf.current_result
        if res_e:
            self._set_text("innovation", f"{res_e.get('innovation', 0):.4f} V")
        if self.voltage_noise_gen:
            self._set_text("v_noise_std", f"{self.voltage_noise_gen.sigma:.4f} V")

    def _update_temperature(self):
        res = self.temp_gen.current_result
        if res:
            t = res.get('T_ambient', 25.0)
            self._set_text("t_true", f"{t:.1f} C")
            self._capacity_temp = t
        if self.temp_adder:
            res_m = self.temp_adder.current_result
            if res_m:
                self._set_text("t_meas", f"{res_m.get('T_meas', 0):.1f} C")
        if self.temp_noise_gen:
            self._set_text("t_noise_std", f"{self.temp_noise_gen.sigma:.4f} C")

    def _update_resistance(self):
        self._set_text("r0", f"{self.battery.R0:.4f} Ohm")
        self._set_text("r1", f"{self.battery.R1:.4f} Ohm")
        self._set_text("c1", f"{self.battery.C1:.0f} F")

    def _update_soc(self):
        res_b = self.battery.current_result
        if res_b:
            self._set_text("soc_true", f"{res_b.get('soc', 0):.4f}")
        res_e = self.ekf.current_result
        if res_e:
            self._set_text("soc_est", f"{res_e.get('soc_est', 0):.4f}")
            self._set_text("soc_error", f"{res_e.get('soc_error', 0):.4f}")

        # Capacity(T)
        cap_text = f"Capacity: -- Ah"
        res_b = self.battery.current_result
        t = self._capacity_temp
        if res_b:
            t = res_b.get('temperature', t)
        alpha = 0.002
        cap_nom = self.battery.capacity_nom
        cap = cap_nom * (1 + alpha * (t - 25.0))
        cap_text = f"Capacity: {cap:.2f} Ah (T={t:.1f} C)"
        self._set_text("capacity", cap_text)