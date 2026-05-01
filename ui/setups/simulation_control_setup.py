# ui/setups/simulation_control_setup.py
import dearpygui.dearpygui as dpg
from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes
from apps.base_simulation_app import BaseSimulationApp

class SimulationControlSetup(BlankSetup):
    def __init__(self, setup_tag: str, app: BaseSimulationApp):
        super().__init__(setup_tag)
        self.app = app
        self.load_series_tag = f"{setup_tag}_load_series"

    def get_setup(self) -> UINode:
        # Кнопки управления
        step_btn = UINode(
            name="ButtonStep",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Step",
            callback=self.app.step
        )
        start_btn = UINode(
            name="ButtonStart",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Start",
            callback=self.app.start
        )
        pause_btn = UINode(
            name="ButtonPause",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Pause",
            callback=self.app.pause
        )
        reset_btn = UINode(
            name="ButtonReset",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_button,
            label="Reset",
            callback=self.app.reset
        )

        btn_group = UINode(
            name="HorizontalButtons",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )
        btn_group.add_children(step_btn)
        btn_group.add_children(start_btn)
        btn_group.add_children(pause_btn)
        btn_group.add_children(reset_btn)

        # Слайдер скорости симуляции
        speed_slider = UINode(
            name="SpeedSlider",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_slider_float,
            label="Simulation Speed",
            default_value=self.app.simulation_speed,
            min_value=0.1,
            max_value=100.0,
            width=200,
            callback=lambda s, a: setattr(self.app, 'simulation_speed', a),
        )

        # Текстовое поле с текущим модельным временем
        time_text = UINode(
            name="TimeText",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text,
            default_value="Time: 0.0 s"
        )
        def update_time():
            t = self.app.engine.total_time
            dpg.set_value(time_text.tag, f"Time: {t:.2f} s")
        time_text.update_func = update_time

        # График нагрузки — создаётся одной функцией для избежания конфликтов вложенности
        def init_load_plot(tag: str, parent: str, **kwargs):
            with dpg.plot(
                tag=tag,
                label="Simulation Load",
                height=300,
                width=600,
                parent=parent
            ):
                x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Frames ago", tag=f"{tag}_xaxis")
                y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Load (%)", tag=f"{tag}_yaxis")
                dpg.set_axis_limits(y_axis, 0, 100)
                dpg.add_line_series([], [], label="Load %", parent=y_axis, tag=self.load_series_tag)
            return tag

        load_plot = UINode(
            name="LoadPlot",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=init_load_plot
        )

        # Функция обновления данных графика
        def update_load_plot():
            history = self.app.get_load_history()
            if not history:
                return
            
            x_vals = [-i*self.app.ui_refresh_interval for i in range( self.app._load_history_size - 1, -1, -1)]
            y_vals = history
            if len(history) < self.app._load_history_size:
                y_vals = [0]*(self.app._load_history_size-len(history)) + y_vals
            dpg.set_value(self.load_series_tag, [x_vals, y_vals])
            dpg.set_axis_limits(f"{load_plot.tag}_xaxis", -self.app._load_history_in_seconds, 0)

        load_plot.update_func = update_load_plot

        # Собираем всё в основную группу
        group = UINode(
            name=f"{self.tag}_group",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=False
        )
        group.add_children(btn_group)
        group.add_children(speed_slider)
        group.add_children(time_text)
        group.add_children(load_plot)

        return group