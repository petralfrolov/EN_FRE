"""
Модуль для работы со справочником кодировки реестра (Кодировка.xlsx).
Загрузка справочников, извлечение фильтров, фильтрация кормов по кодировке.
"""

import os
import streamlit as st
import pandas as pd
import logging

import database as db
from config import REESTR_CODEBOOK_FILE_PATH

logger = logging.getLogger(__name__)


def get_user_reestr_codebook_path() -> str:
    """Возвращает путь к файлу кодировки (пользовательский или дефолтный).
    Если пользовательский путь недоступен, возвращает дефолтный.
    """
    username = st.session_state.get("username")
    if username:
        settings = db.get_user_settings(username)
        user_path = settings.get("reestr_codebook_file_path")
        if user_path:
            if os.path.exists(user_path):
                return user_path
            else:
                st.warning(f"⚠️ Путь к файлу кодировки недоступен: '{user_path}'. Используется стандартный.")
    return REESTR_CODEBOOK_FILE_PATH


def load_codebook():
    """Загружает справочники из файла Кодировка.xlsx."""
    codebook_path = get_user_reestr_codebook_path()
    try:
        geo_df = pd.read_excel(codebook_path, sheet_name="География")
        culture_df = pd.read_excel(codebook_path, sheet_name="Номер культуры")
        feed_df = pd.read_excel(codebook_path, sheet_name="Вид корма")

        geo_map = geo_df.set_index("Код")[["Регион", "Хозяйство", "Подразделение"]]
        culture_map = culture_df.set_index("Код")["Наименование"]
        feed_map = feed_df.set_index("Код")["Наименование"]

        return geo_map, culture_map, feed_map
    except Exception as e:
        st.warning(f"Не удалось загрузить справочники: {e}")
        return pd.DataFrame(), pd.Series(dtype=object), pd.Series(dtype=object)


def get_codebook_filter_options():
    """
    Возвращает три списка уникальных значений из справочника:
    (подразделения, культуры, виды_корма).
    Адаптируется к изменениям в файле кодировки.
    """
    geo_map, culture_map, feed_map = load_codebook()

    subdivisions = sorted(geo_map["Подразделение"].dropna().unique().tolist()) if not geo_map.empty else []
    cultures = sorted(culture_map.dropna().unique().tolist()) if not culture_map.empty else []
    feed_types = sorted(feed_map.dropna().unique().tolist()) if not feed_map.empty else []

    return subdivisions, cultures, feed_types


def get_departments() -> list[str]:
    """
    Возвращает список подразделений из справочника Кодировка.xlsx.
    Используется вместо hardcoded DEPARTMENTS во всём приложении.
    """
    geo_map, _, _ = load_codebook()
    if not geo_map.empty:
        return sorted(geo_map["Подразделение"].dropna().unique().tolist())
    return []


def get_colleague_departments(user_department: str) -> list[str]:
    """
    Возвращает все подразделения хозяйства, к которому относится user_department.
    Используется для определения «коллег» пользователя (все подразделения одного хозяйства).
    """
    geo_map, _, _ = load_codebook()
    if geo_map.empty:
        return [user_department]
    # Найти хозяйство пользователя
    user_rows = geo_map[geo_map["Подразделение"] == user_department]
    if user_rows.empty:
        return [user_department]
    farm = user_rows.iloc[0]["Хозяйство"]
    # Все подразделения этого хозяйства
    colleagues = geo_map[geo_map["Хозяйство"] == farm]["Подразделение"].dropna().unique().tolist()
    return sorted(colleagues)


def filter_feed_names_by_codebook(feed_db, subdivision=None, culture=None, feed_kind=None):
    """
    Фильтрует feed_db (DataFrame с колонкой Кодировка) по параметрам из справочника.
    Декодирует Кодировку каждой записи и сравнивает с выбранными фильтрами.
    Возвращает отфильтрованный список имён (индексов).
    """
    if subdivision is None and culture is None and feed_kind is None:
        return sorted(list(feed_db.index))

    geo_map, culture_map, feed_map = load_codebook()

    filtered_names = []
    for feed_id, row in feed_db.iterrows():
        code = row.get("Кодировка")

        # Записи без кодировки: проверяем только по культуре из имени
        if pd.isna(code) or not str(code).strip():
            if subdivision is not None or feed_kind is not None:
                continue  # без кода нельзя определить подразделение/вид корма
            if culture is not None:
                # unique_feed_id = "Подразделение | Культура", проверяем культуру
                parts = str(feed_id).split(" | ", 1)
                feed_culture = parts[1].strip() if len(parts) > 1 else ""
                if feed_culture != culture:
                    continue
            filtered_names.append(feed_id)
            continue

        # Декодируем кодировку
        try:
            parts = str(code).strip().split(".")
            if len(parts) != 6:
                continue

            geo_code = int(parts[0])
            culture_code = int(parts[2])
            feed_code = int(parts[3])

            if subdivision is not None:
                if geo_code in geo_map.index:
                    if geo_map.loc[geo_code, "Подразделение"] != subdivision:
                        continue
                else:
                    continue

            if culture is not None:
                if culture_code in culture_map.index:
                    if culture_map.loc[culture_code] != culture:
                        continue
                else:
                    continue

            if feed_kind is not None:
                if feed_code in feed_map.index:
                    if feed_map.loc[feed_code] != feed_kind:
                        continue
                else:
                    continue

            filtered_names.append(feed_id)
        except (ValueError, KeyError):
            continue

    return sorted(filtered_names)
