"""
Функции обработки данных для вкладки 'Автоматизация реестра'.
Декодирование кодировок, парсинг лабораторных файлов, объединение RoTap.
"""

import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def decode_code(code_str: str, geo_map, culture_map, feed_map) -> dict:
    """
    Расшифровка строки вида '3637.07.05.02.1.24' в словарь с данными.
    """
    code_str = str(code_str).strip()
    parts = code_str.split(".")

    if len(parts) != 6:
        raise ValueError(f"Неожиданная структура кода: {code_str}")

    sub_code = int(parts[0])
    storage_num = int(parts[1])
    culture_code = int(parts[2])
    feed_code = int(parts[3])
    cut_num = int(parts[4])
    year_code = int(parts[5])
    harvest_year = 2000 + year_code

    geo_row = geo_map.loc[sub_code]
    region = geo_row["Регион"]
    farm = geo_row["Хозяйство"]
    subdivision = geo_row["Подразделение"]

    culture_name = culture_map.loc[culture_code]
    feed_name = feed_map.loc[feed_code]

    return {
        "Регион": region,
        "Хозяйство": farm,
        "Подразделение": subdivision,
        "Номер хранилища": storage_num,
        "Культура": culture_name,
        "Вид корма": feed_name,
        "Номер укоса": cut_num,
        "Год заготовки": harvest_year,
    }


def split_sample_and_code(value):
    """
    Разобрать строку из столбца 'номер образца' на:
    - Номер пробы (до '/')
    - Кодировку (после '/')
    """
    if pd.isna(value):
        return pd.Series({"Номер пробы": None, "Кодировка": None})

    s = str(value).strip()
    if not s:
        return pd.Series({"Номер пробы": None, "Кодировка": None})

    if "/" in s:
        left, right = s.split("/", 1)
        left = left.strip() or None
        right = right.strip() or None
        return pd.Series({"Номер пробы": left, "Кодировка": right})

    if "." in s and s.replace(".", "").isdigit():
        return pd.Series({"Номер пробы": None, "Кодировка": s})

    return pd.Series({"Номер пробы": s, "Кодировка": None})


def add_decoded_columns(df, geo_map, culture_map, feed_map, code_col="Кодировка"):
    """
    По колонке с кодировкой добавляет расшифровку.
    """
    decode_cols = [
        "Регион", "Хозяйство", "Подразделение", "Номер хранилища",
        "Культура", "Вид корма", "Номер укоса", "Год заготовки",
    ]

    col_map_lower = {c.lower(): c for c in df.columns}
    farm_src_col = col_map_lower.get("хозяйство")
    prod_src_col = col_map_lower.get("описание продукта")
    sample_desc_col = col_map_lower.get("описание образца")
    time_src_col = col_map_lower.get("время анализа")

    def _get_harvest_year_from_time(row):
        if not time_src_col:
            return None
        val = row.get(time_src_col)
        if pd.isna(val):
            return None
        dt = pd.to_datetime(val, errors="coerce")
        if pd.isna(dt):
            return None
        return dt.year

    def _extract_code_from_sample_desc(row):
        if not sample_desc_col:
            return None
        val = row.get(sample_desc_col)
        if pd.isna(val):
            return None
        s = str(val)
        if "/" not in s:
            return None
        candidate = s.rsplit("/", 1)[-1].strip()
        return candidate or None

    def _extract_culture_from_sample_desc(row):
        if not sample_desc_col:
            return None
        val = row.get(sample_desc_col)
        if pd.isna(val):
            return None
        s = str(val)
        if "/" in s:
            culture = s.split("/", 1)[0].strip()
        else:
            culture = s.strip()
        return culture or None

    def _process_row(row):
        code = row.get(code_col)
        decoded_info = None
        success = False

        if pd.notna(code) and str(code).strip():
            try:
                decoded_info = decode_code(str(code).strip(), geo_map, culture_map, feed_map)
                success = True
            except Exception:
                success = False

        if not success:
            code_from_desc = _extract_code_from_sample_desc(row)
            if code_from_desc:
                try:
                    decoded_info = decode_code(str(code_from_desc).strip(), geo_map, culture_map, feed_map)
                    success = True
                except Exception:
                    success = False

        year_from_time = _get_harvest_year_from_time(row)

        if success and decoded_info:
            if decoded_info.get("Год заготовки") is None and year_from_time is not None:
                decoded_info["Год заготовки"] = year_from_time
            return pd.Series(decoded_info)

        fallback_data = {col: None for col in decode_cols}

        if farm_src_col and pd.notna(row.get(farm_src_col)):
            fallback_data["Хозяйство"] = row[farm_src_col]

        culture_from_desc = _extract_culture_from_sample_desc(row)
        if culture_from_desc is not None:
            fallback_data["Культура"] = culture_from_desc

        if prod_src_col and pd.notna(row.get(prod_src_col)):
            val = row[prod_src_col]
            if fallback_data["Культура"] is None:
                fallback_data["Культура"] = val
            fallback_data["Вид корма"] = val

        if year_from_time is not None:
            fallback_data["Год заготовки"] = year_from_time

        return pd.Series(fallback_data)

    decoded_df = df.apply(_process_row, axis=1)
    return pd.concat([decoded_df, df], axis=1)


def add_type_column(df_full):
    """Добавляет колонку 'Вид производства'."""
    try:
        vid = df_full['Подразделение'].iloc[0].split(' ')[0]
        df_full.insert(3, "Вид производства", vid)
    except Exception:
        df_full.insert(3, "Вид производства", None)
    return df_full


def read_lab_columns(uploaded_file, usecols="A:AW") -> list[str]:
    """
    Прочитать только заголовки столбцов из загруженного файла.
    Возвращает список имён столбцов.
    """
    try:
        df = pd.read_excel(uploaded_file, usecols=usecols, nrows=0)
        return list(df.columns)
    except Exception as e:
        logger.warning(f"Не удалось прочитать заголовки: {e}")
        return []


def process_lab_file(uploaded_file, feed_type: str, geo_map, culture_map, feed_map, sample_col: str = None) -> pd.DataFrame:
    """
    Обработать один файл лаборатории.
    sample_col — имя столбца с номером образца. Если None, пытается найти автоматически.
    """
    try:
        df = pd.read_excel(uploaded_file, usecols="A:AW")
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        return pd.DataFrame()

    # Если столбец не передан или не найден — фоллбэк
    if sample_col is None or sample_col not in df.columns:
        fallback = "номер образца"
        if fallback not in df.columns:
            candidates = [c for c in df.columns if "образ" in str(c).lower() or "sample" in str(c).lower()]
            if candidates:
                fallback = candidates[0]
            elif len(df.columns) > 1:
                fallback = df.columns[1]
        sample_col = fallback

    if sample_col in df.columns:
        split_df = df[sample_col].apply(split_sample_and_code)
        df_rest = df.drop(columns=[sample_col])
    else:
        split_df = pd.DataFrame(columns=["Номер пробы", "Кодировка"])
        df_rest = df

    df_with_codes = pd.concat([split_df, df_rest], axis=1)
    df_full = add_decoded_columns(df_with_codes, geo_map, culture_map, feed_map, code_col="Кодировка")
    df_full.insert(0, "Тип_листа_реестра", feed_type)
    df_full = add_type_column(df_full)

    return df_full


def process_ro_tap_results(rt_file, geo_map, culture_map, feed_map) -> pd.DataFrame:
    """
    Обработать файл Rezultatyi_Ro_Tap.xlsx.
    """
    rt = pd.read_excel(rt_file)

    if "Кодировка" not in rt.columns:
        st.error("В файле Rezultatyi_Ro_Tap нет столбца 'Кодировка'")
        return pd.DataFrame()

    code_split = rt["Кодировка"].apply(split_sample_and_code)
    rt["Кодировка_чистая"] = code_split["Кодировка"].fillna(
        code_split["Номер пробы"]
    ).astype(str).str.strip()

    sieve_cols = {
        "L": "Сито L",
        "M": "Сито М",
        "S": "Сито S",
    }

    for k, col in sieve_cols.items():
        if col not in rt.columns:
            st.error(f"Не найден столбец '{col}' для сита {k}")
            return pd.DataFrame()

    percent_col = None
    for col in rt.columns:
        low = str(col).lower()
        if "не проплющ" in low or "не проплющенного" in low:
            percent_col = col
            break

    if percent_col is None:
        st.error("Не найден столбец с '% не проплющенного крахмала'")
        return pd.DataFrame()

    rows = []
    for _, r in rt.iterrows():
        code_clean = str(r["Кодировка_чистая"]).strip()
        if not code_clean:
            continue

        for sieve_code, col_name in sieve_cols.items():
            weight = r[col_name]
            if pd.isna(weight):
                continue

            rows.append({
                "Кодировка_чистая": code_clean,
                "Сито_тип": sieve_code,
                "Сито, вес": weight,
                "% непроплющ. Крахмала": r[percent_col],
            })

    return pd.DataFrame(rows)


def process_ro_tap_pair(lab_file, rt_file, geo_map, culture_map, feed_map, sample_col: str = None) -> pd.DataFrame:
    """
    Обработать пару файлов: лабораторный + Rezultatyi_Ro_Tap.
    sample_col — имя столбца с номером образца. Если None, пытается найти автоматически.
    """
    df_lab = pd.read_excel(lab_file, usecols="B:AW")

    # Если столбец не передан или не найден — фоллбэк
    if sample_col is None or sample_col not in df_lab.columns:
        fallback = None
        for col in df_lab.columns:
            low = str(col).lower()
            if ("номер" in low and ("образ" in low or "проб" in low)) or "sample" in low:
                fallback = col
                break
        if fallback is None:
            fallback = df_lab.columns[0]
        sample_col = fallback

    split_df = df_lab[sample_col].apply(split_sample_and_code)
    df_rest = df_lab.drop(columns=[sample_col])
    df_lab = pd.concat([split_df, df_rest], axis=1)

    df_lab["Кодировка_чистая"] = df_lab["Кодировка"].astype(str).str.strip()
    df_lab = add_decoded_columns(df_lab, geo_map, culture_map, feed_map, code_col="Кодировка")

    df_rt = process_ro_tap_results(rt_file, geo_map, culture_map, feed_map)
    if df_rt.empty:
        return pd.DataFrame()

    df_rt["Кодировка_чистая"] = df_rt["Кодировка_чистая"].astype(str).str.strip()
    df_lab["Кодировка_чистая"] = df_lab["Кодировка_чистая"].astype(str).str.strip()

    df_ro_tap = df_lab.merge(
        df_rt,
        on="Кодировка_чистая",
        how="left"
    )

    df_ro_tap.insert(0, "Тип_листа_реестра", "ro_tap")
    df_ro_tap = add_type_column(df_ro_tap)

    return df_ro_tap
