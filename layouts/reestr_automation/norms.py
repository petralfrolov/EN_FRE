"""
Логика покраски ячеек по нормам питательности для вкладки 'Автоматизация реестра'.
"""

import pandas as pd
import logging

from .constants import NORM_SHEETS, FILL_MAP, INDICATOR_TO_DFCOL

logger = logging.getLogger(__name__)


def _to_float(s: str):
    """Преобразует строку в float, заменяя запятую на точку."""
    s = s.strip().replace(",", ".")
    return float(s)


def value_in_expr(val: float, expr: str) -> bool:
    """
    Проверка: попадает ли val в диапазон, заданный строкой expr.
    Поддерживаем: '<20', '≤2', '>6', '20-35', '6.9-8', '6,9-8'
    """
    if expr is None:
        return False
    expr = str(expr).strip()
    if not expr:
        return False

    expr = expr.replace(" ", "")

    # Диапазон A-B
    if "-" in expr:
        parts = expr.replace("–", "-").split("-")
        if len(parts) != 2:
            return False
        try:
            low = _to_float(parts[0])
            high = _to_float(parts[1])
        except ValueError:
            return False
        return (val >= low) and (val <= high)

    # Односторонние
    if expr.startswith("<=") or expr.startswith("≤"):
        num = _to_float(expr.lstrip("<=").lstrip("≤"))
        return val <= num
    if expr.startswith("<"):
        num = _to_float(expr.lstrip("<"))
        return val < num
    if expr.startswith(">=") or expr.startswith("≥"):
        num = _to_float(expr.lstrip(">=").lstrip("≥"))
        return val >= num
    if expr.startswith(">"):
        num = _to_float(expr.lstrip(">"))
        return val > num

    # Просто число
    try:
        num = _to_float(expr)
        return val == num
    except ValueError:
        return False


def get_norm_sheet_for_row(culture_name: str, feed_name: str) -> str | None:
    """
    Определяем, какой лист границ использовать по строке.
    """
    c = (str(culture_name) if pd.notna(culture_name) else "").strip().lower()
    f = (str(feed_name) if pd.notna(feed_name) else "").strip().lower()

    if "вико-овес" in c or "вико овес" in c:
        return "вико-овес"

    if "клевер" in c and "тимофеев" in c:
        return "клевер-тимофеевка"

    if "люцерн" in c or "люцерн" in f:
        if "сенаж" in f:
            return "сенаж люцерновый"

    if "силос" in f:
        return "силос"

    return None


def load_norm_rules(sheet_name: str):
    """
    Читает лист с границами и возвращает словарь правил.
    """
    # Импорт здесь, чтобы избежать циклической зависимости
    from .render import get_user_reestr_norm_path

    norm_path = get_user_reestr_norm_path()
    try:
        df_norm = pd.read_excel(norm_path, sheet_name=sheet_name)
    except Exception:
        return {}

    cols = [c.lower() for c in df_norm.columns]
    try:
        idx_pok = cols.index("показатель")
    except ValueError:
        return {}

    col_err_low = df_norm.columns[idx_pok + 1]
    col_below = df_norm.columns[idx_pok + 2]
    col_norm = df_norm.columns[idx_pok + 3]
    col_above = df_norm.columns[idx_pok + 4]
    col_err_high = df_norm.columns[idx_pok + 5]

    rules = {}
    for _, row in df_norm.iterrows():
        ind = row["Показатель"]
        if pd.isna(ind):
            continue
        ind = str(ind).strip()
        rules[ind] = {
            "error_low": row.get(col_err_low),
            "below": row.get(col_below),
            "norm": row.get(col_norm),
            "above": row.get(col_above),
            "error_high": row.get(col_err_high),
        }

    return rules


def load_all_norm_rules():
    """Загружает правила для всех листов."""
    rules_by_sheet = {}
    for sheet in NORM_SHEETS:
        try:
            rules_by_sheet[sheet] = load_norm_rules(sheet)
        except Exception:
            pass
    return rules_by_sheet


def get_category_for_value(val, row_rules: dict):
    """
    Определяет категорию значения по правилам.
    """
    if val is None:
        return None
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None

    order = ["error_low", "below", "norm", "above", "error_high"]
    for cat in order:
        expr = row_rules.get(cat)
        if value_in_expr(v, expr):
            return cat
    return None


def colorize_new_rows(ws, df_new, start_excel_row, norm_rules_by_sheet):
    """
    Красит ячейки в новых строках согласно нормам.
    """
    cult_col = "Культура"
    feed_col = "Вид корма"

    header_row_idx = 2
    headers = [c.value for c in ws[header_row_idx]]

    dfcol_to_idx = {}
    for col_name in df_new.columns:
        if col_name in headers:
            dfcol_to_idx[col_name] = headers.index(col_name) + 1

    for i, (_, row) in enumerate(df_new.iterrows()):
        excel_row = start_excel_row + i

        culture = row.get(cult_col)
        feed = row.get(feed_col)

        norm_sheet = get_norm_sheet_for_row(culture, feed)
        if norm_sheet is None:
            continue

        norm_rules = norm_rules_by_sheet.get(norm_sheet)
        if not norm_rules:
            continue

        for indicator, df_col in INDICATOR_TO_DFCOL.items():
            if indicator not in norm_rules:
                continue
            if df_col not in df_new.columns:
                continue
            if df_col not in dfcol_to_idx:
                continue

            col_idx_xl = dfcol_to_idx[df_col]
            cell = ws.cell(row=excel_row, column=col_idx_xl)
            val = cell.value

            cat = get_category_for_value(val, norm_rules[indicator])
            if cat and cat in FILL_MAP:
                cell.fill = FILL_MAP[cat]


def style_preview_df(df: pd.DataFrame):
    """
    Применяет покраску к DataFrame для предпросмотра основных кормов.
    Возвращает Styler объект.
    """
    # Цвета для стилей (CSS)
    color_map = {
        "error_low": "background-color: #FFC7CE",   # красный
        "error_high": "background-color: #FFC7CE",
        "below": "background-color: #FFEB9C",       # жёлтый
        "above": "background-color: #FFEB9C",
        "norm": "background-color: #C6EFCE",        # зелёный
    }

    # Загружаем правила
    try:
        norm_rules_by_sheet = load_all_norm_rules()
    except Exception:
        return df.style

    def style_row(row):
        """Стилизует одну строку."""
        styles = [""] * len(row)

        culture = row.get("Культура")
        feed = row.get("Вид корма")
        norm_sheet = get_norm_sheet_for_row(culture, feed)

        if norm_sheet is None:
            return styles

        norm_rules = norm_rules_by_sheet.get(norm_sheet)
        if not norm_rules:
            return styles

        for indicator, df_col in INDICATOR_TO_DFCOL.items():
            if indicator not in norm_rules:
                continue
            if df_col not in row.index:
                continue

            val = row[df_col]
            cat = get_category_for_value(val, norm_rules[indicator])

            if cat and cat in color_map:
                col_idx = row.index.get_loc(df_col)
                styles[col_idx] = color_map[cat]

        return styles

    return df.style.apply(style_row, axis=1)
