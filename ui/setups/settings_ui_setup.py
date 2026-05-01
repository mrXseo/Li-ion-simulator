# ui/setups/settings_ui_setup.py
import json
import dearpygui.dearpygui as dpg
from pathlib import Path

from .blank_setup import BlankSetup
from ..tools.tree import UINode, TreeTypes
from apps.utils.config import AppContext
from apps.base_simulation_app import BaseSimulationApp

class SettingsUISetup(BlankSetup):
    def __init__(self, setup_tag: str, app : BaseSimulationApp):
        super().__init__(setup_tag)
        self.app : BaseSimulationApp = app
        self.restart_warning_tag = None
        self.selected_path = None
        self.right_panel_col_tag = None     # тег контейнера правой панели
        self.edit_widgets = {}              # {param_name: widget_tag}
        self.param_status_tags = {}         # {param_name: indicator_tag}
        self.tree_leaf_tags = []
        self.current_data = {}
        self.original_data = {}             # исходные значения из файла
        self.unsaved_warning_tag = None     # плашка о несохранённых изменениях

    def get_setup(self) -> UINode:
        # Главный контейнер – горизонтальная группа
        main_group = UINode(
            name=f"{self.tag}_main",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=True
        )

        # Левая панель: child_window с деревом
        left_panel = UINode(
            name=f"{self.tag}_left_panel",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_child_window,
            width=250,
            height=-1
        )
        main_group.add_children(left_panel)

        # Строим дерево в левой панели
        self._build_tree(left_panel)

        # Правая панель: child_window с текстом
        right_panel = UINode(
            name=f"{self.tag}_right_panel",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_child_window,
            width=-1,
            height=-1
        )
        main_group.add_children(right_panel)

        right_panel_col = UINode(
            name=f"{self.tag}_right_panel_col",
            tree_type=TreeTypes.DPG_COMPLEX_COMPONENT,
            init_func=dpg.add_group,
            horizontal=False
        )
        right_panel.add_children(right_panel_col)

        self.right_panel_col_tag = None
        def capture_right_tag(tag):
            self.right_panel_col_tag = tag
        right_panel_col.build_func = capture_right_tag

        placeholder = UINode(
            name=f"{self.tag}_placeholder",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_text,
            default_value="Choice object in tree (left panel)"
        )
        right_panel_col.add_children(placeholder)

        return main_group

    def _build_tree(self, parent_node: UINode):
        """Строит дерево конфигурируемых объектов в левой панели."""
        # Добавляем корневой узел "App" для главного settings.json
        app_node = UINode(
            name=f"{self.tag}_tree_app",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_tree_node,
            label="App",
            default_open=True
        )
        parent_node.add_children(app_node)

        # Добавляем внутрь selectable для настроек приложения
        app_settings_leaf = UINode(
            name=f"{self.tag}_leaf_App",
            tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
            init_func=dpg.add_selectable,
            label="Application settings",
            callback=self._on_tree_select,
            user_data="App"
        )
        def capture_leaf_tag(tag):
            self.tree_leaf_tags.append(tag)
        app_settings_leaf.build_func = capture_leaf_tag
        app_node.add_children(app_settings_leaf)

        # Получаем все объекты с load_settings=True
        objects = AppContext.get_configurable_objects()
        # Группируем по иерархии
        tree = {}
        for obj, path in objects:
            parts = path.split('@')
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = obj

        # Рекурсивно создаём узлы
        self._add_tree_nodes(app_node, tree, "")

    def _add_tree_nodes(self, parent_ui: UINode, tree: dict, current_path: str):
        """Рекурсивно добавляет узлы дерева."""
        for name, value in tree.items():
            path = f"{current_path}@{name}" if current_path else name
            if isinstance(value, dict):
                # Промежуточный узел
                node = UINode(
                    name=f"{self.tag}_tree_{path}",
                    tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                    init_func=dpg.add_tree_node,
                    label=name,
                    default_open=True
                )
                parent_ui.add_children(node)
                self._add_tree_nodes(node, value, path)
            else:
                # Лист – объект
                leaf = UINode(
                    name=f"{self.tag}_leaf_{path}",
                    tree_type=TreeTypes.DPG_SIMPLE_COMPONENT,
                    init_func=dpg.add_selectable,
                    label=name,
                    callback= self._on_tree_select,
                    user_data=path
                )
                def capture_leaf_tag(tag):
                    self.tree_leaf_tags.append(tag)
                leaf.build_func = capture_leaf_tag
                parent_ui.add_children(leaf)

    def _on_tree_select(self, sender, app_data, user_data):
        path = user_data
        for tag in self.tree_leaf_tags:
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, False)
        # Выделяем текущий
        dpg.set_value(sender, True)
        # Загружаем конфигурацию
        self._load_config(path)

    def _load_config(self, path: str):
        self.selected_path = path
        # Загружаем данные
        if path == "App":
            data = self.app.load_settings()
        else:
            config_file = self.app.settings_path / f"{path}.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}

        self.current_data = data.copy()
        self.original_data = data.copy()

        # Очищаем правую панель и строим редактор
        if self.right_panel_col_tag:
            dpg.delete_item(self.right_panel_col_tag, children_only=True)
            self.edit_widgets.clear()
            self.param_status_tags.clear()

        dpg.add_text(f"Edit: {path}", parent=self.right_panel_col_tag)

        for key, value in data.items():
            # Создаём горизонтальную группу для индикатора + виджета
            with dpg.group(horizontal=True, parent=self.right_panel_col_tag) as row_group:
                # Цветной индикатор (зелёный по умолчанию)
                indicator = dpg.add_text("|", color=[0, 255, 0])
                self.param_status_tags[key] = indicator
                if isinstance(value, bool):
                    tag = dpg.add_checkbox(label=key, default_value=value, parent=row_group,
                                        callback=self._on_edit, user_data=key)
                elif isinstance(value, (int, float)):
                    tag = dpg.add_input_float(label=key, default_value=float(value), parent=row_group,
                                            callback=self._on_edit, user_data=key, width=200)
                elif isinstance(value, str) or value is None:
                    tag = dpg.add_input_text(label=key, default_value=str(value) if value else "", parent=row_group,
                                            callback=self._on_edit, user_data=key, width=200)
                else:
                    tag = dpg.add_text(f"{key}: {value}", parent=row_group)
                if isinstance(value, (bool, int, float, str)) or value is None:
                    self.edit_widgets[key] = tag

        # Кнопки Save и Reload
        with dpg.group(horizontal=True, parent=self.right_panel_col_tag):
            dpg.add_button(label="Save", callback=self._save_current)
            dpg.add_button(label="Reload", callback=lambda: self._load_config(path))

        # Плашка перезапуска, если требуется
        if self.app._pending_restart:
            self.restart_warning_tag = dpg.add_text(
                "For uses edited parameters the application needs to be restarted",
                color=[255, 200, 0],
                parent=self.right_panel_col_tag
            )
        # Плашка несохранённых изменений (пока скрыта)
        self.unsaved_warning_tag = None

    def _on_edit(self, sender, app_data, user_data):
        key = user_data
        self.current_data[key] = app_data

        # Меняем цвет индикатора
        indicator = self.param_status_tags.get(key)
        if indicator and dpg.does_item_exist(indicator):
            original = self.original_data.get(key)
            if app_data == original:
                dpg.configure_item(indicator, color=[0, 255, 0])   # зелёный
            else:
                dpg.configure_item(indicator, color=[255, 255, 0]) # жёлтый

        # Проверяем, есть ли в целом несохранённые изменения
        self._update_unsaved_warning()

    def _update_unsaved_warning(self):
        # Сравниваем current_data с original_data
        has_changes = any(
            self.current_data.get(k) != self.original_data.get(k)
            for k in self.edit_widgets.keys()
        )
        if has_changes:
            if not self.unsaved_warning_tag or not dpg.does_item_exist(self.unsaved_warning_tag):
                self.unsaved_warning_tag = dpg.add_text(
                    "You have unsaved changes",
                    color=[255, 0, 0],
                    parent=self.right_panel_col_tag
                )
        else:
            if self.unsaved_warning_tag and dpg.does_item_exist(self.unsaved_warning_tag):
                dpg.delete_item(self.unsaved_warning_tag)
                self.unsaved_warning_tag = None

    def _save_current(self):
        """Сохраняет self.current_data в JSON и применяет к объекту (если возможно)."""
        if not self.selected_path:
            return
        # Собираем актуальные данные из виджетов
        data = {}
        for key, tag in self.edit_widgets.items():
            data[key] = dpg.get_value(tag)

        # Сохраняем в файл
        if self.selected_path == "App":
            self.app.save_settings(data)
        else:
            config_file = self.app.settings_path / f"{self.selected_path}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        # Применяем к объекту, если он существует
        obj = AppContext.get_object(self.selected_path)
        if obj and hasattr(obj, 'set_parameters'):
            obj.set_parameters(**data)
        elif obj and hasattr(obj, 'set_value') and 'value' in data:
            obj.set_value(data['value'])

        # После сохранения обновляем original_data и сбрасываем индикаторы
        self.original_data = data.copy()
        for key, tag in self.edit_widgets.items():
            indicator = self.param_status_tags.get(key)
            if indicator and dpg.does_item_exist(indicator):
                dpg.configure_item(indicator, color=[0, 255, 0])

        # Убираем плашку несохранённых изменений
        if self.unsaved_warning_tag and dpg.does_item_exist(self.unsaved_warning_tag):
            dpg.delete_item(self.unsaved_warning_tag)
            self.unsaved_warning_tag = None

        # Устанавливаем флаг необходимости перезапуска
        self.app.notify_restart_required()

        # Показываем плашку сразу после сохранения
        if not hasattr(self, 'restart_warning_tag') or not dpg.does_item_exist(self.restart_warning_tag):
            self.restart_warning_tag = dpg.add_text(
                "For uses edited parameters the application needs to be restarted",
                color=[255, 200, 0],
                parent=self.right_panel_col_tag
            )