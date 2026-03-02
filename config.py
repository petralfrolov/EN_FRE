"""
Конфигурация приложения EN_FRE (Реестр кормов).
Отдельное Streamlit-приложение для автоматизации и визуализации реестра кормов.
"""

from pathlib import Path

# --- UI ---
PAGE_TITLE = "Реестр кормов"
FONT = 16

# --- Базовые директории ---
# Корень данного приложения
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Данные хранятся в основном приложении EN_FAE
# Укажите абсолютный путь к папке с данными EN_FAE
EN_FAE_DIR = Path(r"d:\Python\EN_FAE1")

# --- Файлы данных ---
EXCEL_FILE_PATH = str(DATA_DIR / "Реестр_кормов_append.xlsx")
REESTR_NORM_FILE_PATH = str(DATA_DIR / "Границы_питательности.xlsx")
REESTR_CODEBOOK_FILE_PATH = str(DATA_DIR / "Кодировка.xlsx")

# --- База данных (общая с EN_FAE) ---
DB_PATH = str(EN_FAE_DIR / "users.db")
