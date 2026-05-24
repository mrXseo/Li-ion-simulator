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
    is_force_reboot_docs = False
    is_force_reboot_settings = False

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
                config_file_annotation = cls.app.settings_path / f"{child_path}[docs].md"
                if config_file.exists():
                    file_params = dict()
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content:
                            file_params = json.loads(content)
                    # Параметры из файла перезаписывают явно переданные
                    kwargs.update(file_params)
                else:
                    with open(config_file, 'w', encoding='utf-8') as f:
                        pass
                if (not config_file_annotation.exists() ) or cls.is_force_reboot_docs:
                    if cls.is_force_reboot_docs:
                        print(f"Документация настроек [{config_file_annotation}] принудительно обновлена")
                    with open(config_file_annotation, 'w', encoding='utf-8') as f:
                        f.write("### internal code annotations:\n")
                        st_annotations : List[str] = list()
                        st_defaults_counters = len(target_cls.__init__.__defaults__) - len(target_cls.__init__.__annotations__)
                        for name, annot in target_cls.__init__.__annotations__.items():
                            if name == "return":
                                continue
                            st_annotations.append(f"*\t name : **{name}**\n\n")
                            st_annotations.append(f"\t typing : **{annot}**\n\n")
                            if st_defaults_counters >= 0:
                                st_annotations.append(f"\t default : **{target_cls.__init__.__defaults__[st_defaults_counters]}**\n\n")
                            st_defaults_counters += 1
                            st_annotations.append("\n")

                        f.writelines(st_annotations)
                        if target_cls.__init__.__doc__:
                            f.write("### internal code doc:\n")
                            f.write(target_cls.__init__.__doc__)
                    
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