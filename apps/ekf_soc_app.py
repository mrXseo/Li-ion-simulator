# apps/ekf_soc_app.py
from .base_simulation_app import BaseSimulationApp
from ui.setups.ekf_ui_setup import EKFUISetup
from ui.setups.simulation_control_setup import SimulationControlSetup
from core.experiments.ekf_simulation_setup import EKFSimulationSetup
from ui.tools.tree import UINode, TreeTypes, TreeParser, widget_to_node
import dearpygui.dearpygui as dpg
from ui.widgets.data_logger_widget import DataLoggerWidget
from ui.setups.settings_ui_setup import SettingsUISetup

from .utils.config import AppContext

class EKFSOCApp(BaseSimulationApp):

    @property
    def app_name(self):
        return "ekf_soc_app"

    def __init__(self):
        super().__init__()
        self.sim_setup = None

    def setup_simulation(self):
        self.sim_setup : EKFSimulationSetup = \
            AppContext.WithContext(self, EKFSimulationSetup, "simulation_setup", load_settings=True)(
                engine=self.engine,
                current_mode='constant',
                current_value=1.0,
                temperature_value=25.0,
                battery_params={'capacity_nom': 5.0, 'initial_soc': 1.0},
                voltage_noise_sigma=0.0,
                current_noise_sigma=0.0,
                temp_noise_sigma=0.0,
                # ekf_params={'R': 1e-3, 'Q': [[1e-14, 0], [0, 1e-14]]},  # теперь это берётся из JSON
                records_path=self.records_path,
            )

        self.sim_setup.build()

    def setup_ui(self):

        control_setup = SimulationControlSetup(setup_tag="ControlPanel", app = self)
        control_node = control_setup.get_setup()

        ekf_ui = AppContext.WithContext(
            self, EKFUISetup, "simulation_ui_setup", load_settings=False
            )(setup_tag="EKFExp", sim_setup=self.sim_setup)
        ekf_node = ekf_ui.get_setup()

        tab_control = UINode(name="TabControl", tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                             init_func=dpg.add_tab, label="Control")
        tab_control.add_children(control_node)

        tab_ekf = UINode(name="TabEKF", tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                         init_func=dpg.add_tab, label="EKF SOC")
        tab_ekf.add_children(ekf_node)

        # Вкладка Recording
        tab_recording = UINode(name="TabRecording", tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                            init_func=dpg.add_tab, label="Recording")
        data_logger_widget = DataLoggerWidget(tag="MainLogger", data_logger=self.sim_setup.data_logger)
        data_logger_node = widget_to_node("DataLogger", data_logger_widget)
        tab_recording.add_children(data_logger_node)

        settings_ui = SettingsUISetup("SettingsTab", self)
        settings_node = settings_ui.get_setup()
        tab_settings = UINode(name="TabSettings", tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                            init_func=dpg.add_tab, label="Settings")
        tab_settings.add_children(settings_node)
        
        tab_bar = UINode(name="MainTabBar", tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                         init_func=dpg.add_tab_bar)
        tab_bar.add_children(tab_ekf)
        tab_bar.add_children(tab_control)
        tab_bar.add_children(tab_recording)
        tab_bar.add_children(tab_settings)

        main_win = UINode(name="MainWindow", tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
                          init_func=dpg.add_window, label="EKF SOC Estimator",
                          width=1200, height=800)
        main_win.add_children(tab_bar)

        self.root_node = main_win
        print(TreeParser.str_format(self.root_node))

    def _get_viewport_title(self):
        return "EKF SOC Estimation"

if __name__ == "__main__":
    app = EKFSOCApp()
    app.run()