# apps/base_simulation_app.py
# -*- coding: utf-8 -*-
"""
Базовый класс для приложений симуляции с использованием DearPyGui.
"""

from __future__ import annotations
import dearpygui.dearpygui as dpg
from typing import List, Callable, Optional

from core.simulation_base.simulation_engine import SimulationEngine
from ui.tools.tree import UINode, TreeParser

from .utils.config import AppContext

import time
from collections import deque
import json
from pathlib import Path
import shutil

class BaseSimulationApp:
    """
    Абстрактное приложение, управляющее жизненным циклом симуляции и GUI.
    Конкретные приложения должны переопределить:
        - setup_simulation()  (создание SimulationSetup и вызов build())
        - setup_ui()          (построение дерева UINode)
    """

    def __init__(self):
        self.engine = SimulationEngine()
        self.simulation_speed: float = 1.0
        self.ui_refresh_interval: float = 0.033
        self.is_running = False
        self.root_node: Optional[UINode] = None
        self.update_funcs: List[Callable] = []
        self._load_history_in_seconds = 10.0
        self._load_history_size = round(self._load_history_in_seconds / self.ui_refresh_interval)
        self._load_history = deque(maxlen=self._load_history_size)
        self._last_ui_time = time.time()
        self._pending_restart = False
        self._autostart = False
        self._duration_frames = 0

    def notify_restart_required(self):
        self._pending_restart = True

    @property
    def app_name(self):
        raise NotImplementedError("forget set app name")

    @property
    def env_path(self) -> Path:
        return Path(__file__).parent.parent / "envs" / self.app_name

    @property
    def records_path(self) -> Path:
        return self.env_path / "records"

    @property
    def logs_path(self) -> Path:
        return self.env_path / "logs"

    @property
    def scenarios_path(self) -> Path:
        return self.env_path / "scenarios"

    @property
    def settings_path(self) -> Path:
        return self.env_path / "settings"

    @property
    def main_settings_file(self) -> Path:
        return self.env_path / "settings.json"

    def setup_environment(self) -> None:
        """Создаёт структуру папок окружения, если они не существуют."""
        self.env_path.mkdir(parents=True, exist_ok=True)
        self.records_path.mkdir(exist_ok=True)
        self.logs_path.mkdir(exist_ok=True)
        self.scenarios_path.mkdir(exist_ok=True)
        self.settings_path.mkdir(exist_ok=True)

    def load_settings(self) -> dict:
        """Загружает основной settings.json. Если файла нет, возвращает пустой словарь."""
        if not self.main_settings_file.exists():
            return {}
        with open(self.main_settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_settings(self, data: dict) -> None:
        """Сохраняет словарь в settings.json."""
        self.main_settings_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.main_settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _apply_main_settings(self, data: dict):
        self.simulation_speed = data.get('speed', 1.0)
        self.engine.dt = data.get('dt', 1.0)
        self._autostart = data.get('autostart', False)
        self._duration_frames = data.get('duration_frames', 0)

    def apply_scenario(self, scenario_name: str) -> None:
        """
        Копирует все JSON-файлы из папки сценария в рабочую папку settings/,
        а также заменяет корневой settings.json, если он есть в сценарии.
        """
        scenario_dir = self.scenarios_path / scenario_name
        if not scenario_dir.exists():
            raise FileNotFoundError(f"Scenario folder not found: {scenario_dir}")

        for file in scenario_dir.iterdir():
            if file.suffix == '.json':
                if file.name == 'settings.json':
                    shutil.copy2(file, self.main_settings_file)
                else:
                    shutil.copy2(file, self.settings_path / file.name)

    def setup_simulation(self) -> None:
        """Создать и настроить объекты симуляции."""
        raise NotImplementedError

    def setup_ui(self) -> None:
        """Построить дерево UI и сохранить его в self.root_node."""
        raise NotImplementedError

    def build_ui(self) -> None:
        """Инициализировать и построить UI из дерева self.root_node."""
        if self.root_node is None:
            raise RuntimeError("UI not configured. Call setup_ui() first.")
        TreeParser.tree_init(self.root_node)
        TreeParser.tree_build(self.root_node)
        dpg.set_primary_window(self.root_node.tag, True)
        self.update_funcs = TreeParser.get_update_list(self.root_node)

    def step(self):
        start_sim = time.time()
        steps = max(1, int(self.simulation_speed * self.ui_refresh_interval / self.engine.dt))
        self.engine.step_frames(steps)
        sim_time = time.time() - start_sim

        now = time.time()
        frame_interval = now - self._last_ui_time
        self._last_ui_time = now
        if frame_interval > 0:
            load = (sim_time / frame_interval) * 100.0
        else:
            load = 0.0
        self._load_history.append(load)

        self._update_ui()
        if self._duration_frames > 0 and self.engine.frame_number >= self._duration_frames:
            self.pause()

    def get_load_history(self) -> List[float]:
        """Возвращает список значений нагрузки (в процентах) за последние кадры."""
        return list(self._load_history)

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._schedule_next()

    def pause(self) -> None:
        self.is_running = False

    def reset(self) -> None:
        self.pause()
        self.engine.reset()
        self._update_ui()

    def _update_ui(self) -> None:
        for update in self.update_funcs:
            update()

    def _schedule_next(self) -> None:
        if not self.is_running:
            return
        next_frame = dpg.get_frame_count() + 1
        dpg.set_frame_callback(next_frame, self._frame_callback)

    def _frame_callback(self):
        if not self.is_running:
            return
        self.step()
        self._schedule_next()

    def run(self) -> None:
        self.setup_environment()

        # 1. Загружаем главные настройки
        main_settings = self.load_settings()

        # 2. Если активирован сценарий, подменяем файлы и перечитываем главные настройки
        if main_settings.get('use_scenario', False):
            scenario_name = main_settings.get('scenario_folder_name', 'default')
            self.apply_scenario(scenario_name)
            main_settings = self.load_settings()   # сценарий мог заменить settings.json

        # 3. Применяем настройки симуляции (dt, speed, autostart, duration_frames)
        self._apply_main_settings(main_settings)

        # 4. Инициализируем AppContext (после того как settings/ окончательно сформирована)
        AppContext.init(self)

        # 5. Графический интерфейс
        dpg.create_context()
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                # --- Основные цвета фона и текста ---
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (255, 255, 255))              # чисто белый фон окон
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (230, 240, 250))              # светло-голубой заголовок
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (200, 220, 240))        # активный заголовок
                dpg.add_theme_color(dpg.mvThemeCol_Text, (40, 40, 50))                    # тёмно-синий, почти чёрный

                # --- Панели и группы ---
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (248, 250, 252))              # очень светлый фон для групп
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (255, 255, 255))              # белый фон всплывающих окон
                dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, (240, 245, 250))            # фон меню

                # --- Кнопки ---
                dpg.add_theme_color(dpg.mvThemeCol_Button, (235, 240, 245))               # кнопка
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (215, 225, 235))        # наведение
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (195, 210, 225))         # нажатие

                # --- Поля ввода, слайдеры ---
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (245, 247, 250))              # поле ввода
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (235, 240, 245))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (225, 230, 240))

                # --- Слайдеры и скроллбары ---
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (240, 242, 245))
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (200, 210, 220))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (180, 200, 220))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (160, 180, 200))

                # --- Вкладки ---
                dpg.add_theme_color(dpg.mvThemeCol_Tab, (245, 248, 250))
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, (230, 240, 250))
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (220, 230, 240))

                # --- Заголовки и границы ---
                dpg.add_theme_color(dpg.mvThemeCol_Border, (200, 210, 220))               # границы элементов
                dpg.add_theme_color(dpg.mvThemeCol_Separator, (200, 210, 220))            # разделители

                # --- Дополнительно для графиков (если используются внутри DPG) ---
                #dpg.add_theme_color(dpg.mvThemeCol_PlotBg, (255, 255, 255))               # фон графика
                dpg.add_theme_color(dpg.mvThemeCol_PlotLines, (50, 80, 120))              # линии графика
                dpg.add_theme_color(dpg.mvThemeCol_PlotLinesHovered, (30, 60, 100))
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, (100, 150, 200))        # гистограммы
                dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, (80, 130, 180))

        dpg.bind_theme(global_theme)

        self.setup_simulation()
        self.setup_ui()
        self.build_ui()

        if self._autostart:
            dpg.set_frame_callback(dpg.get_frame_count() + 5, lambda: self.start())

        dpg.create_viewport(title=self._get_viewport_title(), width=1620, height=780)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

        AppContext.destroy()

    def _get_viewport_title(self) -> str:
        """Возвращает заголовок окна приложения (может быть переопределён)."""
        return "Simulation App"