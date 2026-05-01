# _debug.py
"""
Отладочный скрипт для запуска приложений симуляции.
Использование:
    python _debug.py [noise|battery|ekf]
Если аргумент не указан, будет предложен выбор в консоли.
"""

import sys
from apps.base_simulation_app import BaseSimulationApp
from apps.noise_simulation_app import NoiseSimulationApp
from apps.battery_simulation_app import BatterySimulationApp
from apps.ekf_soc_app import EKFSOCApp

APPS = {
    'noise': NoiseSimulationApp,
    'battery': BatterySimulationApp,
    'ekf': EKFSOCApp,
}

def main():
    if len(sys.argv) > 1:
        choice = sys.argv[1].lower()
    else:
        print("Доступные приложения:")
        for key in APPS:
            print(f"  {key}")
        choice = input("Введите имя приложения: ").strip().lower()

    app_class = APPS.get(choice)
    if app_class is None:
        print(f"Неизвестное приложение: {choice}")
        sys.exit(1)

    app : BaseSimulationApp = app_class()
    app.run()

if __name__ == "__main__":
    main()