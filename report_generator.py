#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор отчёта по CSV-файлу, полученному от DataLogger.
Создаёт Markdown-отчёт с графиками и метриками.
Использование:
    python report_generator.py <путь_к_csv_файлу>
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

plt.style.use('seaborn-v0_8-darkgrid')
SKIP_INITIAL_FRAMES = 2

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

def load_and_clean_csv(filepath: str, skip_initial: int = 0) -> dict:
    """Загружает CSV, нормализует имена и удаляет строки с NaN/inf."""
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
# Генераторы графиков (сохраняют в ту же папку, что и CSV)
# --------------------------------------------------------------
def plot_voltage(data: dict, output_path: Path):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.voltage_terminal' in data and 'meas_v.V_measured' in data:
        x = np.arange(len(data['battery.voltage_terminal']))
        ax.plot(x, data['battery.voltage_terminal'], label='True Voltage')
        ax.plot(x, data['meas_v.V_measured'], label='Measured Voltage', alpha=0.7)
        ax.set_ylabel('Voltage (V)')
        ax.set_xlabel('Frame')
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

def plot_soc(data: dict, output_path: Path):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        x = np.arange(len(data['battery.soc']))
        ax.plot(x, data['battery.soc'], label='True SOC')
        ax.plot(x, data['ekf.soc_est'], label='EKF SOC')
        ax.set_ylabel('SOC')
        ax.set_xlabel('Frame')
        ax.set_ylim(-0.05, 1.05)
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

def plot_soc_error(data: dict, metrics: dict, output_path: Path):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        x = np.arange(len(data['battery.soc']))
        error = data['ekf.soc_est'] - data['battery.soc']
        ax.plot(x, error, color='red', linewidth=1)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax.set_ylabel('SOC Error')
        ax.set_xlabel('Frame')
        ax.grid(True)
        textstr = f"RMSE: {metrics['RMSE']:.4f}\nMAE: {metrics['MAE']:.4f}\nMax: {metrics['MaxError']:.4f}"
        ax.text(0.02, 0.95, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

def plot_current(data: dict, output_path: Path):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.current' in data:
        x = np.arange(len(data['battery.current']))
        ax.plot(x, data['battery.current'], label='True Current')
        if 'meas_i.I_meas' in data:
            ax.plot(x, data['meas_i.I_meas'], label='Measured Current', alpha=0.7)
        ax.set_ylabel('Current (A)')
        ax.set_xlabel('Frame')
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

def plot_temperature(data: dict, output_path: Path):
    fig, ax = plt.subplots(figsize=(10, 4))
    if 'battery.temperature' in data:
        x = np.arange(len(data['battery.temperature']))
        ax.plot(x, data['battery.temperature'], label='True Temperature')
        if 'meas_t.T_meas' in data:
            ax.plot(x, data['meas_t.T_meas'], label='Measured Temperature', alpha=0.7)
        ax.set_ylabel('Temperature (°C)')
        ax.set_xlabel('Frame')
        ax.legend()
        ax.grid(True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

# --------------------------------------------------------------
# Генерация Markdown-отчёта
# --------------------------------------------------------------
def generate_report(csv_path: Path, output_dir: Path):
    """Основная функция: загружает CSV, строит графики, создаёт отчёт."""
    data = load_and_clean_csv(csv_path, skip_initial=SKIP_INITIAL_FRAMES)
    if not data:
        print("Нет данных для отчёта")
        return

    # Графики
    plot_voltage(data, output_dir / "voltage.png")
    plot_soc(data, output_dir / "soc.png")
    metrics = {}
    if 'battery.soc' in data and 'ekf.soc_est' in data:
        metrics = compute_metrics(data['battery.soc'], data['ekf.soc_est'])
        plot_soc_error(data, metrics, output_dir / "soc_error.png")
    plot_current(data, output_dir / "current.png")
    plot_temperature(data, output_dir / "temperature.png")

    # Markdown-отчёт
    md_lines = []
    md_lines.append(f"# Simulation Report: {csv_path.stem}")
    md_lines.append(f"**Source file:** `{csv_path.name}`")
    md_lines.append("")

    # SOC metrics
    if metrics:
        md_lines.append("## SOC Estimation Metrics")
        md_lines.append("| Metric | Value |")
        md_lines.append("|--------|-------|")
        md_lines.append(f"| RMSE | {metrics['RMSE']:.6f} |")
        md_lines.append(f"| MAE | {metrics['MAE']:.6f} |")
        md_lines.append(f"| Max Error | {metrics['MaxError']:.6f} |")
        md_lines.append("")

    # Voltage metrics
    if 'battery.voltage_terminal' in data and 'meas_v.V_measured' in data:
        v_true = data['battery.voltage_terminal']
        v_meas = data['meas_v.V_measured']
        valid = np.isfinite(v_true) & np.isfinite(v_meas)
        if np.any(valid):
            v_rmse = np.sqrt(np.mean((v_meas[valid] - v_true[valid]) ** 2))
            md_lines.append("## Voltage Measurement")
            md_lines.append(f"RMSE (True vs Measured): {v_rmse:.6f} V")
            md_lines.append("")

    # Длительность и параметры
    if 'battery.soc' in data:
        frames = len(data['battery.soc'])
        # dt из главных настроек мы не знаем, можно вычислить из времени симуляции?
        md_lines.append("## Experiment Info")
        md_lines.append(f"Total frames: {frames}")
        md_lines.append("")

    # Вставка графиков
    md_lines.append("## Plots")
    md_lines.append("### Voltage")
    md_lines.append("![Voltage](voltage.png)")
    md_lines.append("### State of Charge")
    md_lines.append("![SOC](soc.png)")
    if metrics:
        md_lines.append("### SOC Error")
        md_lines.append("![SOC Error](soc_error.png)")
    md_lines.append("### Current")
    md_lines.append("![Current](current.png)")
    md_lines.append("### Temperature")
    md_lines.append("![Temperature](temperature.png)")

    report_path = output_dir / "report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
    print(f"Report saved to {report_path}")

# --------------------------------------------------------------
# Точка входа
# --------------------------------------------------------------
def main():
    if len(sys.argv) != 2:
        print("Использование: python report_generator.py <путь_к_csv>")
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"Файл не найден: {csv_path}")
        sys.exit(1)

    output_dir = csv_path.parent
    generate_report(csv_path, output_dir)

if __name__ == "__main__":
    main()