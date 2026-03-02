"""
Модуль загрузки и очистки Excel-данных для визуализации реестра кормов.

Содержит функции для автоматического определения строки заголовков,
очистки названий столбцов и классификации типов столбцов.
"""

import re
import pandas as pd


def is_likely_header_row(row_index: int, df_raw: pd.DataFrame) -> tuple[bool, int]:
    """
    Проверяет, является ли строка вероятной строкой заголовков.

    Returns:
        (is_header, score) — флаг и числовая «уверенность».
    """
    if row_index >= len(df_raw):
        return False, 0

    row_values = df_raw.iloc[row_index].astype(str).tolist()

    non_empty = [
        str(v).strip() for v in row_values
        if str(v).strip() and str(v).strip() != 'nan'
        and 'Unnamed' not in str(v)
    ]

    if len(non_empty) < 3:
        return False, 0

    text_count = 0
    numeric_count = 0

    for v in non_empty:
        v_str = str(v)
        if any(kw in v_str for kw in ['Среднее', 'Сводный', 'Итого', 'Сумма', 'Всего']):
            continue

        v_clean = v_str.replace('.', '').replace('-', '').replace(':', '') \
                       .replace(',', '').replace(' ', '')
        try:
            float(v_clean)
            numeric_count += 1
        except ValueError:
            if len(v_str.strip()) > 2:
                text_count += 1

    score = text_count

    if row_index + 1 < len(df_raw):
        next_row = df_raw.iloc[row_index + 1]
        next_non_empty = [
            str(v).strip() for v in next_row.astype(str).tolist()
            if str(v).strip() and str(v).strip() != 'nan'
        ]
        if len(next_non_empty) < 2:
            score = 0

    return text_count > numeric_count and text_count >= 3, score


def load_and_clean_sheet(
    file_path: str,
    sheet_name: str,
) -> tuple[pd.DataFrame | None, str]:
    """
    Читает лист Excel, определяет строку заголовков, очищает данные.

    Returns:
        (df, info_message) — очищенный DataFrame и сообщение о результате.
    """
    try:
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    except Exception as e:
        return None, f"Ошибка при чтении листа: {e}"

    # Поиск строки заголовков
    header_row = 1
    best_score = 0
    for i in range(min(15, len(df_raw))):
        is_header, score = is_likely_header_row(i, df_raw)
        if is_header and score > best_score:
            header_row = i
            best_score = score
    if best_score == 0:
        header_row = 1

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
    except Exception as e:
        return None, f"Ошибка при чтении листа: {e}"

    # Очистка названий столбцов
    cleaned_columns = []
    for i, col in enumerate(df.columns):
        col_str = str(col).strip()
        if 'Unnamed' in col_str or col_str in ('', 'nan', 'None'):
            if len(df) > 0 and header_row + 1 < len(df_raw):
                try:
                    first_val = str(df_raw.iloc[header_row + 1, i]).strip()
                    if first_val and first_val not in ('nan', 'None') and 'Unnamed' not in first_val:
                        cleaned_columns.append(first_val)
                    else:
                        cleaned_columns.append(f"Столбец_{i + 1}")
                except Exception:
                    cleaned_columns.append(f"Столбец_{i + 1}")
            else:
                cleaned_columns.append(f"Столбец_{i + 1}")
        else:
            col_str = re.sub(r'\s+', ' ', col_str).strip()
            cleaned_columns.append(col_str)

    df.columns = cleaned_columns

    # Удаляем полностью пустые строки и столбцы
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # Приводим столбцы с object dtype к StringDtype,
    # чтобы избежать ArrowTypeError при сериализации смешанных типов
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("string")

    info = (
        f"Данные загружены. Строк: {len(df)}, "
        f"Столбцов: {len(df.columns)}. "
        f"Заголовки в строке {header_row + 1}"
    )
    return df, info


def classify_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str]]:
    """
    Классифицирует столбцы DataFrame на текстовые, целочисленные и дробные.

    Returns:
        (text_cols, integer_cols, float_cols)
    """
    text_cols: list[str] = []
    integer_cols: list[str] = []
    float_cols: list[str] = []

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            sample = df[col].dropna()
            if len(sample) > 0:
                if pd.api.types.is_integer_dtype(df[col]) or (sample % 1 == 0).all():
                    integer_cols.append(col)
                else:
                    float_cols.append(col)
            else:
                float_cols.append(col)
        else:
            text_cols.append(col)

    return text_cols, integer_cols, float_cols
