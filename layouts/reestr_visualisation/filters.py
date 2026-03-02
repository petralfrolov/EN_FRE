"""
Модуль каскадных фильтров для визуализации реестра кормов.

Содержит функции создания текстовых и числовых фильтров
с каскадной логикой (значения зависимых фильтров обновляются
при выборе в родительских).
"""

import streamlit as st
import pandas as pd


# ── Конфигурация фильтров ──────────────────────────────────────

MAIN_FILTERS = ['Регион', 'Хозяйство', 'Год', 'Культура', 'Вид производства', 'Подразделение', 'Кодировка']

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

def create_text_filter(col, cols_container, col_index, filtered_data):
    """Каскадный текстовый multiselect-фильтр."""
    with cols_container[col_index]:
        if len(filtered_data) > 5000:
            unique_vals = (
                filtered_data[col].dropna()
                .value_counts().head(1000).index.tolist()
            )
        else:
            unique_vals = filtered_data[col].dropna().unique().tolist()

        unique_vals = sorted([str(v) for v in unique_vals])

        if not unique_vals:
            return None

        key = f"rv_filter_text_{col}"

        if key in st.session_state:
            valid = [str(v) for v in st.session_state[key] if str(v) in unique_vals]
        else:
            valid = []

        selected = st.multiselect(
            col,
            options=unique_vals,
            default=valid,
            key=key,
            help=f"Уникальных значений: {len(unique_vals)}" if len(unique_vals) > 50 else None,
        )
        return selected if selected else None


def create_int_filter(col, cols_container, col_index, filtered_data, full_df):
    """Каскадный целочисленный фильтр (От / До)."""
    with cols_container[col_index]:
        base_col = full_df[col].dropna()
        base_min = int(base_col.min()) if len(base_col) > 0 else 0
        base_max = int(base_col.max()) if len(base_col) > 0 else 100

        st.markdown(f"**{col}**")

        min_key = f"rv_filter_int_min_{col}"
        max_key = f"rv_filter_int_max_{col}"

        if min_key in st.session_state:
            prev_min = st.session_state[min_key]
            if prev_min < base_min or prev_min > base_max:
                prev_min = base_min
        else:
            prev_min = base_min

        if max_key in st.session_state:
            prev_max = st.session_state[max_key]
            if prev_max < base_min or prev_max > base_max:
                prev_max = base_max
        else:
            prev_max = base_max

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


def create_float_filter(col, cols_container, col_index, filtered_data, full_df):
    """Каскадный дробный фильтр (От / До)."""
    with cols_container[col_index]:
        base_col = full_df[col].dropna()
        base_min = float(base_col.min()) if len(base_col) > 0 else 0.0
        base_max = float(base_col.max()) if len(base_col) > 0 else 100.0

        st.markdown(f"**{col}**")
        range_size = base_max - base_min
        step = max(0.01, range_size / 1000) if range_size > 0 else 0.01

        min_key = f"rv_filter_float_min_{col}"
        max_key = f"rv_filter_float_max_{col}"

        if min_key in st.session_state:
            prev_min = st.session_state[min_key]
            if prev_min < base_min or prev_min > base_max:
                prev_min = base_min
        else:
            prev_min = base_min

        if max_key in st.session_state:
            prev_max = st.session_state[max_key]
            if prev_max < base_min or prev_max > base_max:
                prev_max = base_max
        else:
            prev_max = base_max

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

    int_cols = set()
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
                       'rv_filter_int_min_', 'rv_filter_int_max_',
                       'rv_filter_float_min_', 'rv_filter_float_max_'):
            key = f"{prefix}{col}"
            if key in st.session_state:
                del st.session_state[key]
    st.rerun()
