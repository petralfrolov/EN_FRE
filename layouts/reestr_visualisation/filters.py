"""
Модуль каскадных фильтров для визуализации реестра кормов.

Содержит функции создания текстовых и числовых фильтров
с каскадной логикой — значения зависимых фильтров обновляются
при выборе в родительских, включая числовые диапазоны.
"""

import streamlit as st
import pandas as pd


# ── Конфигурация фильтров ──────────────────────────────────────

MAIN_FILTERS = ['Регион', 'Хозяйство', 'Подразделение', 'Год', 'Культура', 'Кодировка']

FILTER_GROUPS = {
    'Базовый состав': [
        '% влажность', '% сухое вещество',
        '% сырой протеин (СП)', '% сырой жир', '% зола',
        '% крахмал', '% Сахар',
    ],
    'Протеин': [
        '% раств. протеина в СП', '% расщепл. в рубце П',
        'Нерасщепляемый протеин', '% КДНСП', '% НДНСП',
    ],
    'Волокна': [
        '% КДК', '% НДК', '% НДК (б/золы)', '% Лигнин',
        '% неструктур. углеводы',
    ],
    'Энергетическая ценность': [
        'От-я ценность корма', 'чистая Э лактации Mj/Kg',
        'Milk Liters/Metric Ton', '% общ. к-во усв. пит. в-в',
        'От-е кочество корма',
    ],
    'Минералы': [
        '% кальций', '% фосфор', '% магний',
        '% калий', '% сера', '% хлор',
    ],
    'Кислоты и ферментация': [
        '% аммиак', '% молочная кислота', '% уксусная кислота',
        '% масляная кислота', 'летучих жирных кислот',
    ],
    'Перевариваемость': [
        'перевар-сть крахмала',
        '% перевариваемость НДК 24ч.',
        'Перевар-ть НДК 30ч.', 'Перевар-ть НДК 120ч.',
        'Перевар-ть НДК 240ч.',
        'непереваримая НДК 30ч.', 'непереваримая НДК 120ч.',
        'не перевар-сть НДК 240ч.', 'скорость перевар-сти/ ч',
    ],
}

# ── Фильтры ─────────────────────────────────────────────────────

def create_year_filter(col: str, cols_container, col_index: int,
                       filtered_data: pd.DataFrame):
    """
    Фильтр года — ДВА выпадающих списка (От / До).
    Опции динамически строятся из отфильтрованных данных.
    """
    with cols_container[col_index]:
        if col not in filtered_data.columns:
            return None

        raw_vals = filtered_data[col].dropna().unique().tolist()
        try:
            year_vals = sorted({int(v) for v in raw_vals})
        except (ValueError, TypeError):
            year_vals = sorted({str(v) for v in raw_vals})

        if not year_vals:
            return None

        options = [str(y) for y in year_vals]

        key_from = f"rv_filter_year_from_{col}"
        key_to   = f"rv_filter_year_to_{col}"

        st.markdown(f"**{col}**")
        fc1, fc2 = st.columns(2)

        # Дефолт: весь диапазон
        prev_from = st.session_state.get(key_from, options[0])
        if prev_from not in options:
            prev_from = options[0]

        prev_to = st.session_state.get(key_to, options[-1])
        if prev_to not in options:
            prev_to = options[-1]

        with fc1:
            chosen_from = st.selectbox(
                "От",
                options=options,
                index=options.index(prev_from),
                key=key_from,
                label_visibility="visible",
            )
        with fc2:
            # Ограничиваем «До» не меньше «От»
            valid_to = [o for o in options if o >= chosen_from]
            if not valid_to:
                valid_to = [options[-1]]
            if prev_to not in valid_to:
                prev_to = valid_to[-1]

            chosen_to = st.selectbox(
                "До",
                options=valid_to,
                index=valid_to.index(prev_to),
                key=key_to,
                label_visibility="visible",
            )

        # Если весь диапазон — не фильтруем
        if chosen_from == options[0] and chosen_to == options[-1]:
            return None

        # Возвращаем список лет в диапазоне [from, to]
        selected_years = [o for o in options if chosen_from <= o <= chosen_to]
        return selected_years if selected_years else None


def create_text_filter(col: str, cols_container, col_index: int,
                       filtered_data: pd.DataFrame,
                       options_override: list | None = None):
    """
    Каскадный текстовый multiselect-фильтр.
    
    options_override: если передан — использует эти варианты вместо данных из df.
    """
    with cols_container[col_index]:
        if options_override is not None:
            unique_vals = [str(v) for v in options_override]
        elif len(filtered_data) > 5000:
            unique_vals = (
                filtered_data[col].dropna()
                .value_counts().head(1000).index.tolist()
            )
            unique_vals = sorted([str(v) for v in unique_vals])
        else:
            unique_vals_raw = filtered_data[col].dropna().unique().tolist()
            # Дедупликация без учета регистра: приводим к Title Case для красоты или оставляем как есть, но группируем
            seen = {}
            for v in unique_vals_raw:
                v_str = str(v).strip()
                v_lower = v_str.lower()
                if v_lower not in seen:
                    seen[v_lower] = v_str
            unique_vals = sorted(seen.values())

        if not unique_vals:
            return None

        key = f"rv_filter_text_{col}"

        # Берём предыдущее значение ТОЛЬКО из session_state, не из default,
        # чтобы не было конфликта «default + session_state».
        prev_val = st.session_state.get(key, [])
        # Фильтруем недопустимые значения (каскад мог сузить список)
        valid = [str(v) for v in prev_val if str(v) in unique_vals]

        # Обновляем session_state перед созданием виджета (без default!)
        st.session_state[key] = valid

        selected = st.multiselect(
            col,
            options=unique_vals,
            key=key,
            help=f"Уникальных значений: {len(unique_vals)}" if len(unique_vals) > 50 else None,
        )
        return selected if selected else None


def create_int_filter(col: str, cols_container, col_index: int,
                      filtered_data: pd.DataFrame, full_df: pd.DataFrame):
    """
    Каскадный целочисленный фильтр (От / До).

    Диапазон «Допустимо» берётся из full_df (абсолютные границы),
    а текущий диапазон по умолчанию — из filtered_data (каскадное сужение).
    """
    with cols_container[col_index]:
        if col not in full_df.columns:
            return None

        base_col  = full_df[col].dropna()
        base_min  = int(base_col.min()) if len(base_col) > 0 else 0
        base_max  = int(base_col.max()) if len(base_col) > 0 else 100

        # Текущие каскадные границы (по отфильтрованным данным)
        cur_col  = filtered_data[col].dropna() if col in filtered_data.columns else base_col
        cur_min  = int(cur_col.min()) if len(cur_col) > 0 else base_min
        cur_max  = int(cur_col.max()) if len(cur_col) > 0 else base_max

        st.markdown(f"**{col}**")

        min_key = f"rv_filter_int_min_{col}"
        max_key = f"rv_filter_int_max_{col}"

        prev_min = st.session_state.get(min_key, cur_min)
        if not (base_min <= prev_min <= base_max):
            prev_min = cur_min

        prev_max = st.session_state.get(max_key, cur_max)
        if not (base_min <= prev_max <= base_max):
            prev_max = cur_max

        # Ограничиваем сохранённые значения текущим каскадным диапазоном
        prev_min = max(int(prev_min), cur_min)
        prev_max = min(int(prev_max), cur_max)
        if prev_min > prev_max:
            prev_min, prev_max = cur_min, cur_max

        min_val = st.number_input("От", min_value=base_min, max_value=base_max,
                                  value=prev_min, step=1, key=min_key)
        max_val = st.number_input("До", min_value=base_min, max_value=base_max,
                                  value=prev_max, step=1, key=max_key)

        if min_val > max_val:
            st.error(f"Ошибка: 'От' ({min_val}) > 'До' ({max_val})")
            return None

        if min_val != base_min or max_val != base_max:
            return (int(min_val), int(max_val))
    return None


def create_float_filter(col: str, cols_container, col_index: int,
                        filtered_data: pd.DataFrame, full_df: pd.DataFrame):
    """
    Каскадный дробный фильтр (От / До).

    Абсолютные границы из full_df, каскадный дефолт из filtered_data.
    """
    with cols_container[col_index]:
        if col not in full_df.columns:
            return None

        base_col  = full_df[col].dropna()
        base_min  = float(base_col.min()) if len(base_col) > 0 else 0.0
        base_max  = float(base_col.max()) if len(base_col) > 0 else 100.0

        cur_col  = filtered_data[col].dropna() if col in filtered_data.columns else base_col
        cur_min  = float(cur_col.min()) if len(cur_col) > 0 else base_min
        cur_max  = float(cur_col.max()) if len(cur_col) > 0 else base_max

        st.markdown(f"**{col}**")
        range_size = base_max - base_min
        step = max(0.01, range_size / 1000) if range_size > 0 else 0.01

        min_key = f"rv_filter_float_min_{col}"
        max_key = f"rv_filter_float_max_{col}"

        prev_min = float(st.session_state.get(min_key, cur_min))
        if not (base_min <= prev_min <= base_max):
            prev_min = cur_min

        prev_max = float(st.session_state.get(max_key, cur_max))
        if not (base_min <= prev_max <= base_max):
            prev_max = cur_max

        prev_min = max(prev_min, cur_min)
        prev_max = min(prev_max, cur_max)
        if prev_min > prev_max:
            prev_min, prev_max = cur_min, cur_max

        min_val = st.number_input("От", min_value=float(base_min), max_value=float(base_max),
                                  value=float(prev_min), step=step, format="%.2f",
                                  key=min_key)
        max_val = st.number_input("До", min_value=float(base_min), max_value=float(base_max),
                                  value=float(prev_max), step=step, format="%.2f",
                                  key=max_key)

        if min_val > max_val:
            st.error(f"Ошибка: 'От' ({min_val:.2f}) > 'До' ({max_val:.2f})")
            return None

        if abs(min_val - base_min) > 0.01 or abs(max_val - base_max) > 0.01:
            return (min_val, max_val)
    return None


# ── Сброс / автоисправление ──────────────────────────────────────

def reset_all_filters(df: pd.DataFrame):
    """Сбрасывает все фильтры вкладки визуализации реестра."""
    for key in list(st.session_state.keys()):
        if key.startswith('rv_filter_text_'):
            st.session_state[key] = []
        elif key.startswith(('rv_cb_region', 'rv_cb_farm', 'rv_cb_div',
                             'rv_cb_culture', 'rv_cb_feedtype')):
            st.session_state[key] = []
        elif key.startswith('_rv_cb_'):
            st.session_state[key] = None
        elif key.startswith(('rv_filter_year_from_', 'rv_filter_year_to_',
                             'rv_codebook_')):
            del st.session_state[key]

    int_cols   = set()
    float_cols = set()
    for key in list(st.session_state.keys()):
        if key.startswith('rv_filter_int_min_'):
            int_cols.add(key.replace('rv_filter_int_min_', ''))
        elif key.startswith('rv_filter_float_min_'):
            float_cols.add(key.replace('rv_filter_float_min_', ''))

    for col_name in int_cols:
        if col_name in df.columns:
            col_data = df[col_name].dropna()
            if len(col_data) > 0:
                st.session_state[f'rv_filter_int_min_{col_name}'] = int(col_data.min())
                st.session_state[f'rv_filter_int_max_{col_name}'] = int(col_data.max())

    for col_name in float_cols:
        if col_name in df.columns:
            col_data = df[col_name].dropna()
            if len(col_data) > 0:
                st.session_state[f'rv_filter_float_min_{col_name}'] = float(col_data.min())
                st.session_state[f'rv_filter_float_max_{col_name}'] = float(col_data.max())

    # Очищаем кэш каскадного порядка
    cache_key = f"rv_cascade_order_{st.session_state.get('rv_selected_sheet', '')}"
    if cache_key in st.session_state:
        del st.session_state[cache_key]

    st.rerun()


def fix_filters_automatically(problematic_cols: list[str]):
    """Сбрасывает указанные проблемные фильтры."""
    for col in problematic_cols:
        for prefix in ('rv_filter_text_',
                       'rv_filter_year_from_', 'rv_filter_year_to_',
                       'rv_filter_int_min_', 'rv_filter_int_max_',
                       'rv_filter_float_min_', 'rv_filter_float_max_'):
            key = f"{prefix}{col}"
            if key in st.session_state:
                del st.session_state[key]
    st.rerun()
