# apps/utils/config.py
"""
Система контекстной конфигурации объектов.
Позволяет связывать экземпляры в иерархию и автоматически загружать настройки из JSON.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from ..base_simulation_app import BaseSimulationApp

T = TypeVar('T')


class AppContext:
    """
    Глобальный контекст приложения.
    Хранит ссылку на приложение и реестр созданных объектов с их конфигурационными путями.
    """

    app: Optional[BaseSimulationApp] = None
    _registry: List[Tuple[Any, str, bool]] = []   # (объект, config_path, load_settings)

    @classmethod
    def init(cls, app: BaseSimulationApp) -> None:
        """
        Инициализирует контекст приложения.
        Вызывается один раз при старте приложения.
        """
        cls.app = app
        cls._registry.clear()
        # Убедимся, что папка settings существует
        app.settings_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def WithContext(cls, parent: Any, target_cls: Type[T], keyword: str, load_settings: bool = True):
        """
        Возвращает конструктор, который создаёт объект target_cls,
        автоматически загружая настройки из JSON-файла по пути parent_keyword@keyword.
        Конструктор принимает только именованные аргументы (**kwargs).
        """
        if cls.app is None:
        # Режим прозрачного пропуска – просто возвращаем конструктор класса
            def constructor(**kwargs) -> T:
                return target_cls(**kwargs)
            return constructor
        
        # Штатный режим с загрузкой настроек и регистрацией
        def constructor(**kwargs) -> T:
            if cls.app is None:
                raise RuntimeError("AppContext не инициализирован")

            # 1. Определяем родительский путь из реестра
            parent_path = cls._find_path(parent)

            # 2. Формируем дочерний путь
            if parent_path:
                child_path = f"{parent_path}@{keyword}"
            else:
                child_path = keyword

            if load_settings:
                # 3. Загружаем настройки из файла, если он есть
                config_file = cls.app.settings_path / f"{child_path}.json"
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        file_params = json.load(f)
                    # Параметры из файла перезаписывают явно переданные
                    kwargs.update(file_params)

            # 4. Создаём экземпляр
            obj = target_cls(**kwargs)

            # 5. Регистрируем объект в реестре
            cls._registry.append((obj, child_path, load_settings))

            return obj

        return constructor

    @classmethod
    def _find_path(cls, obj: Any) -> Optional[str]:
        """Находит конфигурационный путь объекта в реестре."""
        for registered_obj, path, load_settings in cls._registry:
            if registered_obj is obj:
                return path
        return None

    @classmethod
    def get_object(cls, path: str) -> Optional[Any]:
        """Возвращает объект по его конфигурационному пути."""
        for obj, p, load_flag in cls._registry:
            if p == path:
                return obj
        return None

    @classmethod
    def get_path(cls, obj: Any) -> Optional[str]:
        """Возвращает конфигурационный путь для зарегистрированного объекта."""
        return cls._find_path(obj)

    @classmethod
    def save_config(cls, obj: Any, data: Dict[str, Any]) -> None:
        """Сохраняет словарь data в JSON-файл, соответствующий объекту."""
        if cls.app is None:
            raise RuntimeError("AppContext не инициализирован")
        path = cls._find_path(obj)
        if path is None:
            raise ValueError("Объект не зарегистрирован в AppContext")
        config_file = cls.app.settings_path / f"{path}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def reload_config(cls, obj: Any) -> None:
        """
        Перезагружает настройки из JSON-файла и применяет их к объекту.
        Объект должен иметь метод set_parameters(**data) или set_value(value).
        """
        if cls.app is None:
            raise RuntimeError("AppContext не инициализирован")
        path = cls._find_path(obj)
        if path is None:
            raise ValueError("Объект не зарегистрирован в AppContext")
        config_file = cls.app.settings_path / f"{path}.json"
        if not config_file.exists():
            return
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if hasattr(obj, 'set_parameters'):
            obj.set_parameters(**data)
        elif hasattr(obj, 'set_value') and 'value' in data:
            obj.set_value(data['value'])
    
    @classmethod
    def destroy(cls) -> None:
        cls.app = None
        cls._registry = list()

    @classmethod
    def get_configurable_objects(cls) -> List[Tuple[Any, str]]:
        """Возвращает список (объект, путь) только для тех, у кого load_settings=True."""
        return [(obj, path) for obj, path, flag in cls._registry if flag]