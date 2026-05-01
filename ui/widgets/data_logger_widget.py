# ui/widgets/data_logger_widget.py
import dearpygui.dearpygui as dpg
from .base_widget import BaseWidget
from core.elements.inspectors.data_logger import DataLogger


class DataLoggerWidget(BaseWidget):
    def __init__(self, tag: str, data_logger: DataLogger = None, **kwargs):
        super().__init__(tag, simulation_object=data_logger, **kwargs)
        self.data_logger = data_logger
        self.status_text_tag = f"{tag}_status"
        self.written_tag = f"{tag}_written"
        self.saved_tag = f"{tag}_saved"
        self.unsaved_tag = f"{tag}_unsaved"
        self.button_tag = f"{tag}_button"

    def init(self, parent_tag: str = None):
        self.parent_tag = parent_tag
        with dpg.group(tag=self.tag, parent=parent_tag, horizontal=False):
            # Row1: "Recorder | Targets: ..."
            targets_str = ", ".join(self.data_logger.targets.keys()) if self.data_logger else ""
            with dpg.group(horizontal=True):
                dpg.add_text("Recorder |", color=[0, 191, 255])
                dpg.add_text(f"Targets: {targets_str}")

            # Row2: Start/Stop + Flush
            with dpg.group(horizontal=True):
                dpg.add_button(
                    tag=self.button_tag,
                    label="Start" if not (self.data_logger and self.data_logger.enabled) else "Stop",
                    callback=self._on_toggle
                )
                dpg.add_button(label="Flush Now", callback=self._on_flush)

            # Статистика
            dpg.add_text("", tag=self.written_tag, color=[0, 191, 255])
            dpg.add_text("", tag=self.saved_tag, color=[0, 255, 0])
            dpg.add_text("", tag=self.unsaved_tag, color=[255, 255, 0])

        self._update_stats()

    def _on_toggle(self):
        if self.data_logger:
            self.data_logger.toggle()
            label = "Stop" if self.data_logger.enabled else "Start"
            dpg.set_item_label(self.button_tag, label)

    def _on_flush(self):
        if self.data_logger:
            self.data_logger.flush()

    def _update_stats(self):
        if self.data_logger:
            dpg.set_value(self.written_tag, f"Written rows: {self.data_logger._written_rows}")
            dpg.set_value(self.saved_tag, f"Saved rows: {self.data_logger._saved_rows}")
            dpg.set_value(self.unsaved_tag, f"Unsaved rows: {self.data_logger.unsaved_rows}")

    def update(self):
        self._update_stats()