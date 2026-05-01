# core/utils/interpolation.py
import numpy as np

def bilinear_interp(x: float, y: float,
                    x_grid: np.ndarray, y_grid: np.ndarray,
                    values: np.ndarray) -> float:
    """
    Билинейная интерполяция по двум координатам.
    
    x, y        - значения SOC (0..1) и температуры (°C)
    x_grid      - одномерный массив узлов сетки SOC
    y_grid      - одномерный массив узлов сетки температуры
    values      - двумерный массив значений размером (len(x_grid), len(y_grid))
    """
    # Поиск индексов
    i = np.searchsorted(x_grid, x) - 1
    j = np.searchsorted(y_grid, y) - 1
    i = max(0, min(i, len(x_grid) - 2))
    j = max(0, min(j, len(y_grid) - 2))

    x1, x2 = x_grid[i], x_grid[i+1]
    y1, y2 = y_grid[j], y_grid[j+1]

    wx = (x - x1) / (x2 - x1) if x2 != x1 else 0.0
    wy = (y - y1) / (y2 - y1) if y2 != y1 else 0.0

    v11 = values[i, j]
    v12 = values[i, j+1]
    v21 = values[i+1, j]
    v22 = values[i+1, j+1]

    v_y1 = v11 + wx * (v21 - v11)
    v_y2 = v12 + wx * (v22 - v12)
    return v_y1 + wy * (v_y2 - v_y1)