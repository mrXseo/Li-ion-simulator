#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор отчёта по CSV-файлу, полученному от DataLogger.

Использование:
    python report_generator.py <путь_к_csv_файлу>
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-darkgrid')

# Количество начальных кадров, которые нужно пропустить (из-за переходных процессов)
SKIP_INITIAL_FRAMES = 5

def normalize_columns(data: dict) -> dict:
    """Преобразует ключи словаря data к стандартному виду с точкой-разделителем."""
    normalized = {}
    prefixes = ['battery', 'ekf', 'meas']
    for col_name, values in data.items():
        new_name = col_name
        for prefix in prefixes:
            if col_name.startswith(prefix) and len(col_name) > len(prefix):
                rest = col_name[len(prefix):]
                new_name = f"{prefix}.{rest}"
                break
        normalized[new_name] = values
    return normalized


def load_and_clean_csv(filepath: str, skip_initial : int = 0) -> dict:
    """Загружает CSV, нормализует имена и удаляет строки с NaN/inf в ключевых полях."""
    try:
        raw = np.genfromtxt(filepath, delimiter=',', names=True, dtype=None, encoding='utf-8')
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        sys.exit(1)

    arrays = {}
    for name in raw.dtype.names:
        col = raw[name]
        if col.dtype.kind in ('f', 'i'):
            arrays[name] = col
        else:
            try:
                arrays[name] = col.astype(float)
            except:
                pass

    data = normalize_columns(arrays)

    if skip_initial > 0:
        first_key = next(iter(data.keys()))
        if len(data[first_key]) > skip_initial:
            for key in data:
                data[key] = data[key][skip_initial:]
            print(f"Отброшено первых {skip_initial} кадров.")
        else:
            print(f"Внимание: данных меньше {skip_initial}, отбрасывание не выполнено.")

    # Список полей, которые нам критически важны для анализа
    required_keys = ['battery.soc', 'ekf.soc_est', 'battery.voltage_terminal', 'meas.V_measured']
    available_keys = [k for k in required_keys if k in data]

    if not available_keys:
        print("Внимание: ни одного из ключевых полей не найдено, очистка не производится.")
        return data

    # Создаём маску для строк, где все доступные ключевые поля конечны
    mask = np.ones(len(data[available_keys[0]]), dtype=bool)
    for key in available_keys:
        col = data[key]
        mask &= np.isfinite(col)

    # Применяем маску ко всем столбцам
    cleaned_data = {}
    for key, col in data.items():
        cleaned_data[key] = col[mask]

    removed = len(data[available_keys[0]]) - len(cleaned_data[available_keys[0]])
    if removed > 0:
        print(f"Удалено строк с NaN/inf: {removed} из {len(data[available_keys[0]])}")

    return cleaned_data


def compute_metrics(soc_true: np.ndarray, soc_est: np.ndarray) -> dict:
    """Вычисляет RMSE, MAE, Max Error для SOC."""
    error = soc_est - soc_true
    # На всякий случай убираем неконечные значения
    valid = np.isfinite(error)
    if not np.any(valid):
        return {'RMSE': np.nan, 'MAE': np.nan, 'MaxError': np.nan}
    error = error[valid]
    rmse = np.sqrt(np.mean(error ** 2))
    mae = np.mean(np.abs(error))
    max_err = np.max(np.abs(error))
    return {'RMSE': rmse, 'MAE': mae, 'MaxError': max_err}


def plot_report(data: dict, output_path: Path):
    """Строит и сохраняет графики с улучшенной визуализацией."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle(f'Отчёт по файлу: {output_path.stem}', fontsize=14)

    # Для очень длинных записей делаем прореживание (децимацию)
    max_points = 10000
    step = 1
    if 'battery.soc' in data and len(data['battery.soc']) > max_points:
        step = len(data['battery.soc']) // max_points

    # График 1: SOC
    ax1 = axes[0, 0]
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        x = np.arange(len(data['battery.soc']))
        ax1.plot(x[::step], data['battery.soc'][::step], label='True SOC', linewidth=2)
        ax1.plot(x[::step], data['ekf.soc_est'][::step], label='EKF SOC', linewidth=2, alpha=0.8)
        ax1.set_ylabel('SOC')
        ax1.set_xlabel('Frame')
        ax1.set_ylim(-0.05, 1.05)
        ax1.legend()
        ax1.grid(True)
    else:
        ax1.text(0.5, 0.5, 'Нет данных SOC', ha='center', va='center')
        ax1.set_title('SOC')

    # График 2: Ошибка SOC
    ax2 = axes[0, 1]
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        error = data['ekf.soc_est'] - data['battery.soc']
        metrics = compute_metrics(data['battery.soc'], data['ekf.soc_est'])
        ax2.plot(x[::step], error[::step], color='red', linewidth=1)
        ax2.set_ylabel('SOC Error')
        ax2.set_xlabel('Frame')
        ax2.grid(True)
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        # Добавляем текст с метриками на график
        textstr = f"RMSE: {metrics['RMSE']:.4f}\nMAE: {metrics['MAE']:.4f}\nMax: {metrics['MaxError']:.4f}"
        ax2.text(0.02, 0.95, textstr, transform=ax2.transAxes, fontsize=10,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    else:
        ax2.text(0.5, 0.5, 'Нет данных ошибки SOC', ha='center', va='center')
        ax2.set_title('SOC Error')

    # График 3: Напряжение
    ax3 = axes[1, 0]
    if 'battery.voltage_terminal' in data and 'meas.V_measured' in data:
        ax3.plot(x[::step], data['battery.voltage_terminal'][::step], label='True Voltage', linewidth=2)
        ax3.plot(x[::step], data['meas.V_measured'][::step], label='Measured Voltage', linewidth=1, alpha=0.7)
        ax3.set_ylabel('Voltage (V)')
        ax3.set_xlabel('Frame')
        ax3.legend()
        ax3.grid(True)
    else:
        ax3.text(0.5, 0.5, 'Нет данных напряжения', ha='center', va='center')
        ax3.set_title('Voltage')

    # График 4: Инновация EKF
    ax4 = axes[1, 1]
    if 'ekf.innovation' in data:
        innov = data['ekf.innovation']
        ax4.plot(x[::step], innov[::step], color='purple', linewidth=1)
        ax4.set_ylabel('Innovation')
        ax4.set_xlabel('Frame')
        ax4.grid(True)
        ax4.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    else:
        ax4.text(0.5, 0.5, 'Нет данных инновации', ha='center', va='center')
        ax4.set_title('EKF Innovation')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"График сохранён: {output_path}")


def main():
    if len(sys.argv) != 2:
        print("Использование: python report_generator.py <путь_к_csv>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Файл не найден: {csv_path}")
        sys.exit(1)

    print(f"Загрузка данных из {csv_path}...")
    data = load_and_clean_csv(csv_path, skip_initial=SKIP_INITIAL_FRAMES)

    print("Найденные колонки после нормализации:", ', '.join(data.keys()))

    # Расчёт метрик для SOC
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        metrics = compute_metrics(data['battery.soc'], data['ekf.soc_est'])
        print("\n--- Метрики оценки SOC ---")
        print(f"RMSE:      {metrics['RMSE']:.6f}")
        print(f"MAE:       {metrics['MAE']:.6f}")
        print(f"Max Error: {metrics['MaxError']:.6f}")
    else:
        print("Пропущен расчёт метрик SOC: не найдены нужные колонки.")

    # Метрики для напряжения (RMSE между истинным и измеренным)
    if 'battery.voltage_terminal' in data and 'meas.V_measured' in data:
        v_true = data['battery.voltage_terminal']
        v_meas = data['meas.V_measured']
        valid = np.isfinite(v_true) & np.isfinite(v_meas)
        if np.any(valid):
            v_rmse = np.sqrt(np.mean((v_meas[valid] - v_true[valid]) ** 2))
            print(f"\n--- Метрика напряжения ---")
            print(f"RMSE (True vs Measured): {v_rmse:.6f} V")
        else:
            print("\nНет конечных данных для расчёта RMSE напряжения.")

    # Генерация графика
    output_png = csv_path.with_suffix('.png')
    plot_report(data, output_png)


if __name__ == "__main__":
    main()