# main.py
"""
Использование:
    python main.py [noise|battery|ekf]
Если аргумент не указан, будет предложен выбор в консоли.
"""

import sys
from apps.base_simulation_app import BaseSimulationApp
from apps.noise_simulation_app import NoiseSimulationApp
from apps.battery_simulation_app import BatterySimulationApp
from apps.ekf_soc_app import EKFSOCApp
from apps.utils.config import AppContext

APPS = {
    'noise': NoiseSimulationApp,
    'battery': BatterySimulationApp,
    'ekf': EKFSOCApp,
}

DOCS_REBOOT_COMMAND = {"flags" :["--docs-reboot", "-rbD"], "docs":"для принудительной перезагрузки документации"}
SETTINGS_REBOOT_COMMAND = {"flags" :["--settings-reboot", "-rbS"], "docs":"для сброса всех настроек"}

ALL_FLAGS = set([*DOCS_REBOOT_COMMAND["flags"] ,*SETTINGS_REBOOT_COMMAND["flags"]])

if len(ALL_FLAGS) != len([*DOCS_REBOOT_COMMAND["flags"] ,*SETTINGS_REBOOT_COMMAND["flags"]]):
    print(ALL_FLAGS)
    print([*DOCS_REBOOT_COMMAND["flags"] ,*SETTINGS_REBOOT_COMMAND["flags"]])
    raise RuntimeError("Пересечение вариаций флагов для разных функций")

def main():
    if len(sys.argv) > 1:
        entered = " ".join(sys.argv[1:])
    else:
        print("Доступные приложения:")
        for key in APPS:
            print(f"  {key}")
        print("Доступные флаги настройки:")
        print(("  "+"  ".join(DOCS_REBOOT_COMMAND["flags"])).ljust(50)+"|", DOCS_REBOOT_COMMAND["docs"])
        print(("  "+"  ".join(SETTINGS_REBOOT_COMMAND["flags"])).ljust(50)+"|", SETTINGS_REBOOT_COMMAND["docs"])
        entered = input("Введите имя приложения: ").strip()
    
    entered = list(filter(lambda st: st != "", entered.split(" ")))

    choice = entered[0].lower()
    flags = entered[1:]
    
    app_class = APPS.get(choice)
    if app_class is None:
        print(f"Неизвестное приложение: {choice}")
        sys.exit(1)

    for idx, flag in reversed(list(enumerate(flags.copy()))):
        if flag == "":
            flags.pop(idx)
            continue
        if not flag in ALL_FLAGS:
            print(f"Неизвестный флаг: {flag}")
            sys.exit(1)
    print(flags)
    for flag in flags:
        if flag in DOCS_REBOOT_COMMAND["flags"]:
            print("принудительно обновление документации включено")
            AppContext.is_force_reboot_docs = True
        if flag in SETTINGS_REBOOT_COMMAND["flags"]:
            AppContext.is_force_reboot_settings = True

    app : BaseSimulationApp = app_class()
    app.run()

if __name__ == "__main__":
    main()