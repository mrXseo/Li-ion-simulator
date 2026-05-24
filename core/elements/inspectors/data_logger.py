# core/elements/inspectors/data_logger.py
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from ...simulation_base.simulation_object import Inspector, SimulationObject
from ...simulation_base.simulation_engine import SimulationEngine


class DataLogger(Inspector):
    def __init__(
        self,
        simulation_engine: SimulationEngine,
        records_path: Path,
        targets: Dict[str, SimulationObject],
        filename: Optional[str] = None,
        auto_flush: bool = True,
        flush_interval: int = 100,
        enabled: bool = False,
        **kwargs
    ):
        super().__init__(simulation_engine, **kwargs)
        self.records_path = records_path
        self.filename = filename or f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.filepath = self.records_path / self.filename
        self.filepath.parent.mkdir(parents=True, exist_ok=True)  # создаёт подпапки
        self.targets = targets
        self.auto_flush = auto_flush
        self.flush_interval = flush_interval
        self.enabled = enabled

        self._buffer: List[Dict[str, Any]] = []
        self._written_rows = 0
        self._saved_rows = 0
        self._frame_counter = 0

        # Флаги для управления заголовком
        self._header_written = False
        self._fieldnames = None

        self.records_path.mkdir(parents=True, exist_ok=True)

    def start(self):
        self.enabled = True

    def stop(self):
        self.enabled = False

    def toggle(self):
        self.enabled = not self.enabled

    def flush(self):
        """Сбрасывает буфер в файл, формируя заголовок один раз по полному набору ключей."""
        if not self._buffer:
            return

        if not self._header_written:
            # Собираем все уникальные ключи из всех строк буфера
            all_fields = set()
            for row in self._buffer:
                all_fields.update(row.keys())
            # Упорядочиваем: frame всегда первый, остальные по алфавиту
            ordered_fields = ['frame'] + sorted([f for f in all_fields if f != 'frame'])
            self._fieldnames = ordered_fields
            self._header_written = True

            # Открываем файл на запись (перезаписываем, если существовал пустой)
            with open(self.filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self._fieldnames, restval='', extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self._buffer)
        else:
            # Дописываем данные с уже известными полями
            with open(self.filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self._fieldnames, restval='', extrasaction='ignore')
                writer.writerows(self._buffer)

        self._saved_rows += len(self._buffer)
        self._buffer.clear()

    def _solve_frame(self):
        if not self.enabled:
            return

        self._frame_counter += 1
        row = {'frame': self._frame_counter}

        for alias, obj in self.targets.items():
            # используем штатный метод движка, чтобы получить актуальный результат
            res = obj.get_frame_result(tail_len=1)
            if res:
                for key, value in res.items():
                    col_name = f"{alias}.{key}"
                    row[col_name] = value

        self._buffer.append(row)
        self._written_rows += 1

        if self.auto_flush and len(self._buffer) >= self.flush_interval:
            self.flush()

    @property
    def unsaved_rows(self):
        return self._written_rows - self._saved_rows

    def reset_state(self):
        pass