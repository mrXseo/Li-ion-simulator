#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор отчётов по CSV-файлам, полученным от DataLogger.
Рекурсивно обрабатывает все record.csv в папке envs/ekf_soc_app/records/.
Создаёт для каждого CSV Markdown-отчёт с графиками и метриками.
Для графиков SoC и ошибки используются отдельные фокусы (первые N% данных).
Подписи всех графиков – на русском языке.
Использование:
    python report_generator.py                 # обработать все записи
    python report_generator.py --file <путь>   # обработать один файл
    python report_generator.py --dir <путь>    # обработать все CSV в указанной папке
"""

import sys
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# ==============================================================
# КОНФИГУРАЦИЯ
# ==============================================================
DT = 0.1                     # шаг дискретизации, с
DPI = 200                    # качество графиков
FOCUS_SOC = 0.00100          # доля данных для графика SoC (первые 5%)
FOCUS_ERROR = 0.0010         # доля данных для графика ошибки SoC (первые 5%)
METRICS_LOCATION = 'lower right'  # позиция текстовой врезки с метриками
                                  # варианты: 'upper left', 'upper right', 'lower left', 'lower right'
plt.style.use('seaborn-v0_8-darkgrid')

# --------------------------------------------------------------
# Вспомогательные функции
# --------------------------------------------------------------
def normalize_columns(data: dict) -> dict:
    """Преобразует ключи словаря data к стандартному виду с точкой-разделителем."""
    normalized = {}
    prefixes = ['battery', 'ekf', 'meas_v', 'meas_i', 'meas_t']
    for col_name, values in data.items():
        new_name = col_name
        for prefix in prefixes:
            if col_name.startswith(prefix) and len(col_name) > len(prefix):
                rest = col_name[len(prefix):]
                new_name = f"{prefix}.{rest}"
                break
        normalized[new_name] = values
    return normalized

def load_csv(filepath: Path) -> dict:
    """Загружает CSV, нормализует имена и удаляет строки с NaN/inf."""
    try:
        raw = np.genfromtxt(filepath, delimiter=',', names=True, dtype=None, encoding='utf-8')
    except Exception as e:
        print(f"Ошибка при чтении файла {filepath}: {e}")
        return {}

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

    # Очистка от NaN/inf
    required_keys = ['battery.soc', 'ekf.soc_est', 'battery.voltage_terminal', 'meas_v.V_measured']
    available_keys = [k for k in required_keys if k in data]
    if available_keys:
        mask = np.ones(len(data[available_keys[0]]), dtype=bool)
        for key in available_keys:
            mask &= np.isfinite(data[key])
        cleaned = {k: v[mask] for k, v in data.items()}
        return cleaned
    return data

def compute_metrics(soc_true: np.ndarray, soc_est: np.ndarray) -> dict:
    """Вычисляет метрики ошибки в долях (0–1)."""
    error = soc_est - soc_true
    valid = np.isfinite(error)
    if not np.any(valid):
        return {'RMSE': np.nan, 'MAE': np.nan, 'MaxError': np.nan}
    error = error[valid]
    return {
        'RMSE': np.sqrt(np.mean(error ** 2)),
        'MAE': np.mean(np.abs(error)),
        'MaxError': np.max(np.abs(error))
    }

# --------------------------------------------------------------
# Генераторы графиков (все подписи на русском)
# --------------------------------------------------------------
def plot_voltage(data: dict, output_path: Path, dt: float = DT):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.voltage_terminal' in data and 'meas_v.V_measured' in data:
        x = np.arange(len(data['battery.voltage_terminal'])) * dt
        ax.plot(x, data['battery.voltage_terminal'], label='Истинное напряжение')
        ax.plot(x, data['meas_v.V_measured'], label='Измеренное напряжение', alpha=0.7)
        ax.set_ylabel('Напряжение (В)')
        ax.set_xlabel('Время (с)')
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)

def plot_soc(data: dict, output_path: Path, dt: float = DT, focus_ratio: float = FOCUS_SOC):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        full_len = len(data['battery.soc'])
        if focus_ratio < 1.0:
            limit = max(1, int(full_len * focus_ratio))
            soc_true = data['battery.soc'][:limit]
            soc_est = data['ekf.soc_est'][:limit]
            x = np.arange(limit) * dt
        else:
            soc_true = data['battery.soc']
            soc_est = data['ekf.soc_est']
            x = np.arange(full_len) * dt

        ax.plot(x, soc_true * 100, label='Истинный SoC')
        ax.plot(x, soc_est * 100, label='Оценка EKF')
        ax.set_ylabel('SoC (%)')
        ax.set_xlabel('Время (с)')
        ax.set_ylim(-5, 105)
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)

def plot_soc_error(data: dict, metrics: dict, output_path: Path, dt: float = DT, focus_ratio: float = FOCUS_ERROR, text_location: str = METRICS_LOCATION):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        full_len = len(data['battery.soc'])
        if focus_ratio < 1.0:
            limit = max(1, int(full_len * focus_ratio))
            soc_true = data['battery.soc'][:limit]
            soc_est = data['ekf.soc_est'][:limit]
            x = np.arange(limit) * dt
        else:
            soc_true = data['battery.soc']
            soc_est = data['ekf.soc_est']
            x = np.arange(full_len) * dt

        error = (soc_est - soc_true) * 100  # в процентах
        ax.plot(x, error, color='red', linewidth=1, label='Ошибка SoC')
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax.set_ylabel('Ошибка SoC (%)')
        ax.set_xlabel('Время (с)')
        ax.grid(True)

        # Текстовая врезка с метриками (по всем данным)
        textstr = (f"RMSE: {metrics['RMSE']*100:.4f} %\n"
                   f"MAE:  {metrics['MAE']*100:.4f} %\n"
                   f"Max:  {metrics['MaxError']*100:.4f} %")

        # Выбор позиции врезки
        if text_location == 'upper left':
            x_pos, y_pos = 0.02, 0.95
            ha, va = 'left', 'top'
        elif text_location == 'upper right':
            x_pos, y_pos = 0.98, 0.95
            ha, va = 'right', 'top'
        elif text_location == 'lower left':
            x_pos, y_pos = 0.02, 0.05
            ha, va = 'left', 'bottom'
        elif text_location == 'lower right':
            x_pos, y_pos = 0.98, 0.05
            ha, va = 'right', 'bottom'
        else:
            # fallback
            x_pos, y_pos = 0.02, 0.95
            ha, va = 'left', 'top'

        ax.text(x_pos, y_pos, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment=va, horizontalalignment=ha,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)

def plot_current(data: dict, output_path: Path, dt: float = DT):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.current' in data:
        x = np.arange(len(data['battery.current'])) * dt
        ax.plot(x, data['battery.current'], label='Истинный ток')
        if 'meas_i.I_meas' in data:
            ax.plot(x, data['meas_i.I_meas'], label='Измеренный ток', alpha=0.7)
        ax.set_ylabel('Ток (А)')
        ax.set_xlabel('Время (с)')
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)

def plot_temperature(data: dict, output_path: Path, dt: float = DT):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.temperature' in data:
        x = np.arange(len(data['battery.temperature'])) * dt
        ax.plot(x, data['battery.temperature'], label='Истинная температура')
        if 'meas_t.T_meas' in data:
            ax.plot(x, data['meas_t.T_meas'], label='Измеренная температура', alpha=0.7)
        ax.set_ylabel('Температура (°C)')
        ax.set_xlabel('Время (с)')
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=DPI)
    plt.close(fig)

# --------------------------------------------------------------
# Генерация отчёта для одного CSV
# --------------------------------------------------------------
def generate_report_for_csv(csv_path: Path):
    """Генерирует отчёт для одного CSV-файла в той же папке."""
    output_dir = csv_path.parent
    data = load_csv(csv_path)
    if not data:
        print(f"Нет данных в {csv_path}, пропускаем.")
        return

    print(f"Обработка {csv_path}...")

    # Графики с отдельными фокусами для SoC и ошибки
    plot_voltage(data, output_dir / "voltage.png")
    plot_soc(data, output_dir / "soc.png", focus_ratio=FOCUS_SOC)
    metrics = {}
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        metrics = compute_metrics(data['battery.soc'], data['ekf.soc_est'])
        plot_soc_error(data, metrics, output_dir / "soc_error.png", focus_ratio=FOCUS_ERROR)
    plot_current(data, output_dir / "current.png")
    plot_temperature(data, output_dir / "temperature.png")

    # Markdown-отчёт (на русском)
    md_lines = []
    md_lines.append(f"# Отчёт по симуляции: {csv_path.stem}")
    md_lines.append(f"**Исходный файл:** `{csv_path.name}`")
    md_lines.append("")

    if metrics:
        md_lines.append("## Метрики оценки SoC")
        md_lines.append("| Метрика | Значение (отн. ед.) | Значение (%) |")
        md_lines.append("|---------|---------------------|--------------|")
        md_lines.append(f"| RMSE | {metrics['RMSE']:.6f} | {metrics['RMSE']*100:.4f} % |")
        md_lines.append(f"| MAE  | {metrics['MAE']:.6f} | {metrics['MAE']*100:.4f} % |")
        md_lines.append(f"| Max Error | {metrics['MaxError']:.6f} | {metrics['MaxError']*100:.4f} % |")
        md_lines.append("")

    if 'battery.voltage_terminal' in data and 'meas_v.V_measured' in data:
        v_true = data['battery.voltage_terminal']
        v_meas = data['meas_v.V_measured']
        valid = np.isfinite(v_true) & np.isfinite(v_meas)
        if np.any(valid):
            v_rmse = np.sqrt(np.mean((v_meas[valid] - v_true[valid]) ** 2))
            md_lines.append("## Измерение напряжения")
            md_lines.append(f"RMSE (истинное vs измеренное): {v_rmse:.6f} В")
            md_lines.append("")

    if 'battery.soc' in data:
        frames = len(data['battery.soc'])
        md_lines.append("## Информация об эксперименте")
        md_lines.append(f"Всего кадров: {frames}")
        md_lines.append(f"Длительность: {frames * DT:.1f} с")
        md_lines.append("")

    md_lines.append("## Графики")
    md_lines.append("### Напряжение")
    md_lines.append("![Напряжение](voltage.png)")
    md_lines.append("### Степень заряда (первые {:d}% данных)".format(int(FOCUS_SOC*100)))
    md_lines.append("![SoC](soc.png)")
    if metrics:
        md_lines.append("### Ошибка SoC (первые {:d}% данных)".format(int(FOCUS_ERROR*100)))
        md_lines.append("![Ошибка SoC](soc_error.png)")
    md_lines.append("### Ток")
    md_lines.append("![Ток](current.png)")
    md_lines.append("### Температура")
    md_lines.append("![Температура](temperature.png)")

    report_path = output_dir / "report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
    print(f"Отчёт сохранён: {report_path}")

# --------------------------------------------------------------
# Поиск всех CSV и обработка
# --------------------------------------------------------------
def find_all_csv_records(base_dir: Path) -> list:
    """Рекурсивно находит все файлы record.csv в base_dir."""
    csv_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file == "record.csv":
                csv_files.append(Path(root) / file)
    return csv_files

def process_all_records(base_dir: Path):
    """Обрабатывает все найденные record.csv."""
    csv_files = find_all_csv_records(base_dir)
    if not csv_files:
        print(f"Не найдено ни одного record.csv в {base_dir}")
        return
    print(f"Найдено {len(csv_files)} файлов record.csv")
    for csv_path in csv_files:
        generate_report_for_csv(csv_path)

# --------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------
def main():
    script_dir = Path(__file__).parent
    default_records = script_dir / "envs" / "ekf_soc_app" / "records"

    if len(sys.argv) == 1:
        if default_records.exists():
            process_all_records(default_records)
        else:
            print(f"Папка {default_records} не найдена. Укажите путь.")
            sys.exit(1)
    elif len(sys.argv) == 2:
        arg = sys.argv[1]
        path = Path(arg)
        if path.is_file():
            generate_report_for_csv(path)
        elif path.is_dir():
            process_all_records(path)
        else:
            print(f"Указанный путь не существует: {path}")
            sys.exit(1)
    else:
        print("Использование:")
        print("  python report_generator.py                 # обработать все записи в envs/ekf_soc_app/records/")
        print("  python report_generator.py <путь_к_csv>   # обработать один CSV")
        print("  python report_generator.py <путь_к_папке> # обработать все CSV в указанной папке")
        sys.exit(1)

if __name__ == "__main__":
    main()