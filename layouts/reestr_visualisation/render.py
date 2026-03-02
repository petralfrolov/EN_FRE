"""
Вкладка «Визуализация реестра кормов».

Загружает Excel-файл реестра из стандартного пути (настройки пользователя),
отображает каскадные фильтры, графики, таблицу и статистику.
"""

import streamlit as st
import pandas as pd

from modules.cascade_discovery import CascadeDiscovery
from .data_loading import load_and_clean_sheet, classify_columns
from .filters import (
    MAIN_FILTERS, FILTER_GROUPS,
    create_text_filter, create_int_filter, create_float_filter,
    reset_all_filters, fix_filters_automatically,
)
from .charts import build_chart


# ─────────────────────────────────────────────────────────────────
def render_reestr_visualisation():
    """Основная функция рендеринга вкладки «Визуализация реестра»."""

    st.subheader("Визуализация реестра кормов")

    # ── Загрузка стороннего реестра (опционально) ─────────────────
    with st.expander("Загрузить сторонний реестр (опционально)"):
        vis_temp_registry = st.file_uploader(
            "Загрузите Excel-файл реестра для визуализации",
            type=["xlsx", "xls"],
            key="vis_temp_registry_upload",
        )

    # ── Путь к файлу ─────────────────────────────────────────────
    excel_path = st.session_state.get("current_excel_path")
    using_vis_temp = False

    if vis_temp_registry:
        import os, tempfile
        temp_path = os.path.join(tempfile.gettempdir(), "en_fae_vis_reestr_upload.xlsx")
        try:
            with open(temp_path, "wb") as f:
                f.write(vis_temp_registry.getvalue())
            excel_path = temp_path
            using_vis_temp = True
            st.info(f"Используется загруженный сторонний реестр: **{vis_temp_registry.name}**")
        except Exception as e:
            st.error(f"Ошибка сохранения временного реестра: {e}")

    if not using_vis_temp:
        if not excel_path:
            st.warning("Путь к реестру не задан. Проверьте настройки.")
            return
        st.info(f"Реестр (база): `{excel_path}`")

    # Сброс кеша при смене источника данных
    prev_vis_source = st.session_state.get("rv_source_path")
    if prev_vis_source != excel_path:
        st.session_state["rv_source_path"] = excel_path
        st.session_state["rv_df"] = None
        st.session_state["rv_last_sheet"] = None

    # ── Загрузка листов ──────────────────────────────────────────
    try:
        xl = pd.ExcelFile(excel_path)
        sheet_names = xl.sheet_names
    except Exception as e:
        st.error(f"Не удалось открыть файл реестра: {e}")
        return

    if not sheet_names:
        st.info("Файл не содержит листов.")
        return

    # Инициализация состояния
    st.session_state.setdefault("rv_selected_sheet", sheet_names[0])
    st.session_state.setdefault("rv_df", None)
    st.session_state.setdefault("rv_last_sheet", None)

    selected_sheet = st.selectbox(
        "Выберите лист для анализа",
        sheet_names,
        index=sheet_names.index(st.session_state.rv_selected_sheet)
        if st.session_state.rv_selected_sheet in sheet_names else 0,
        key="rv_sheet_selector",
    )

    if selected_sheet != st.session_state.rv_selected_sheet:
        st.session_state.rv_selected_sheet = selected_sheet
        st.session_state.rv_df = None
        st.session_state.rv_last_sheet = None

    # ── Загрузка данные листа ────────────────────────────────────
    if st.session_state.rv_df is None or st.session_state.rv_last_sheet != selected_sheet:
        df, info_msg = load_and_clean_sheet(excel_path, selected_sheet)
        if df is None:
            st.error(info_msg)
            return
        st.session_state.rv_df = df
        st.session_state.rv_last_sheet = selected_sheet
        st.success(f"✅ {info_msg}")

    df = st.session_state.rv_df.copy()
    text_cols, integer_cols, float_cols = classify_columns(df)
    numeric_cols = integer_cols + float_cols

    # ── Каскадный порядок фильтров ───────────────────────────────
    all_available = []
    for col in MAIN_FILTERS:
        if col in df.columns:
            all_available.append(col)
    for group_cols in FILTER_GROUPS.values():
        for col in group_cols:
            if col in df.columns and col not in all_available:
                all_available.append(col)
    for col in df.columns:
        if col not in all_available:
            all_available.append(col)

    cache_key = f"rv_cascade_order_{selected_sheet}"
    if cache_key in st.session_state:
        cascade_order = st.session_state[cache_key]
    else:
        with st.spinner("Анализ зависимостей фильтров…"):
            try:
                sample_size = min(10_000, len(df))
                df_sample = df.head(sample_size) if sample_size < len(df) else df
                finder = CascadeDiscovery(df_sample, all_available)
                cascade_order = finder.discover_cascade(threshold=0.3)
            except Exception:
                cascade_order = all_available
        st.session_state[cache_key] = cascade_order

    # ── Построение фильтров ──────────────────────────────────────
    st.markdown("---")
    st.subheader("Фильтры данных")

    selected_filters: dict[str, list] = {}
    numeric_filters: dict[str, tuple] = {}
    processed_cols: set[str] = set()

    # Порядок основных фильтров: берем из MAIN_FILTERS, оставляя только доступные
    ordered_main = [c for c in MAIN_FILTERS if c in df.columns]

    # Заголовок + сброс
    hc1, hc2 = st.columns([4, 1])
    with hc1:
        st.markdown("### Основные фильтры")
    with hc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Сбросить все фильтры", key="rv_reset_all",
                      help="Сбросит все фильтры", width='stretch'):
            reset_all_filters(df)

    # ── Основные фильтры ─────────────────────────────────────────
    if ordered_main:
        main_cols_ui = st.columns(len(ordered_main))
        current_filtered = df.copy()
        for idx, col_name in enumerate(ordered_main):
            processed_cols.add(col_name)
            if col_name in text_cols:
                result = create_text_filter(col_name, main_cols_ui, idx, current_filtered)
                if result:
                    selected_filters[col_name] = result
                    mask = current_filtered[col_name].astype(str).isin([str(v) for v in result])
                    current_filtered = current_filtered[mask].copy()
            elif col_name in integer_cols:
                result = create_int_filter(col_name, main_cols_ui, idx, current_filtered, df)
                if result:
                    numeric_filters[col_name] = result
                    mn, mx = result
                    current_filtered = current_filtered[
                        (current_filtered[col_name] >= mn) & (current_filtered[col_name] <= mx)
                    ].copy()
    else:
        current_filtered = df.copy()

    st.markdown("---")

    # ── CSS для группы фильтров ──────────────────────────────────
    st.markdown("""
        <style>
        .streamlit-expanderContent div[data-testid="stSelectbox"] label,
        .streamlit-expanderContent div[data-testid="stMultiSelect"] label,
        .streamlit-expanderContent div[data-testid="stNumberInput"] label,
        .streamlit-expanderContent p,
        .streamlit-expanderContent strong {
            font-size: 1.3rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ── Группы фильтров ──────────────────────────────────────────
    for group_name, group_cols_list in FILTER_GROUPS.items():
        available = [c for c in group_cols_list if c in df.columns and c not in processed_cols]
        available_sorted = [c for c in cascade_order if c in available]
        for c in available:
            if c not in available_sorted:
                available_sorted.append(c)

        if available_sorted:
            with st.expander(group_name, expanded=False):
                for row_start in range(0, len(available_sorted), 3):
                    row_cols = st.columns(3)
                    for i in range(3):
                        idx = row_start + i
                        if idx < len(available_sorted):
                            col = available_sorted[idx]
                            processed_cols.add(col)
                            _apply_filter(col, row_cols, i, current_filtered, df,
                                          text_cols, integer_cols, float_cols,
                                          selected_filters, numeric_filters)

    # ── Прочие фильтры ───────────────────────────────────────────
    remaining = [c for c in text_cols + integer_cols + float_cols if c not in processed_cols]
    remaining_sorted = [c for c in cascade_order if c in remaining]
    for c in remaining:
        if c not in remaining_sorted:
            remaining_sorted.append(c)

    if remaining_sorted:
        with st.expander(f"Прочие фильтры ({len(remaining_sorted)})", expanded=False):
            for row_start in range(0, len(remaining_sorted), 3):
                row_cols = st.columns(3)
                for i in range(3):
                    idx = row_start + i
                    if idx < len(remaining_sorted):
                        col = remaining_sorted[idx]
                        processed_cols.add(col)
                        _apply_filter(col, row_cols, i, current_filtered, df,
                                      text_cols, integer_cols, float_cols,
                                      selected_filters, numeric_filters)

    # ── Применение фильтров и валидация ──────────────────────────
    filtered_df = _validate_and_apply(
        df, selected_filters, numeric_filters
    )

    # ── Визуализация ─────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Визуализация данных")

    chart_type = st.selectbox(
        "Тип графика",
        ["Столбчатая диаграмма", "Линейный график", "Точечная диаграмма",
         "Гистограмма", "Круговая диаграмма"],
        key="rv_chart_type",
    )

    c1, c2 = st.columns(2)
    with c1:
        x_column = st.selectbox("По горизонтали", options=list(df.columns),
                                key="rv_x_col")
    with c2:
        if chart_type != "Гистограмма":
            y_column = st.selectbox("По вертикали",
                                    options=numeric_cols if numeric_cols else list(df.columns),
                                    key="rv_y_col")
        else:
            y_column = None

    agg_type = None
    if chart_type != "Гистограмма":
        agg_type = st.selectbox(
            "Тип агрегации",
            ["Нет", "Сумма", "Среднее", "Медиана", "Количество", "Минимум", "Максимум"],
            key="rv_agg_type",
        )
        if agg_type == "Нет":
            agg_type = None

    color_column = None
    if chart_type in ("Столбчатая диаграмма", "Линейный график", "Точечная диаграмма"):
        color_column = st.selectbox(
            "Столбец для группировки (цвет)",
            options=["Нет"] + text_cols[:10],
            key="rv_color_col",
        )

    if st.button("Построить график", type="primary", key="rv_build_chart"):
        try:
            fig = build_chart(chart_type, filtered_df, x_column, y_column,
                              color_column, agg_type)
            if fig:
                st.session_state["rv_chart_fig"] = fig
            else:
                st.session_state["rv_chart_fig"] = None
                st.warning("Невозможно построить график с выбранными параметрами.")
        except Exception as e:
            st.session_state["rv_chart_fig"] = None
            st.error(f"Ошибка при построении графика: {e}")

    if st.session_state.get("rv_chart_fig"):
        st.plotly_chart(st.session_state["rv_chart_fig"], width='stretch')

    # ── Таблица данных ───────────────────────────────────────────
    st.markdown("---")
    st.subheader("Таблица данных")
    st.dataframe(filtered_df, width='stretch', height=400)

    # ── Статистика ───────────────────────────────────────────────
    with st.expander("Статистика по числовым показателям", expanded=False):
        if numeric_cols:
            avail_numeric = [c for c in numeric_cols if c in filtered_df.columns]
            if avail_numeric:
                stats = filtered_df[avail_numeric].describe()
                stats.index = stats.index.map({
                    'count': 'Количество', 'mean': 'Среднее',
                    'std': 'Станд. отклонение', 'min': 'Минимум',
                    '25%': '25% (квартиль)', '50%': '50% (медиана)',
                    '75%': '75% (квартиль)', 'max': 'Максимум',
                })
                stats_t = stats.T
                fmt = stats_t.copy()
                for col in fmt.columns:
                    if col == 'Количество':
                        fmt[col] = fmt[col].apply(
                            lambda x: f"{int(x)}" if pd.notna(x) else "")
                    else:
                        fmt[col] = fmt[col].apply(
                            lambda x: f"{x:.2f}" if pd.notna(x) and abs(x) < 1000
                            else f"{x:.0f}" if pd.notna(x) else "")
                st.dataframe(fmt, width='stretch')
            else:
                st.info("Нет числовых столбцов для статистики")
        else:
            st.info("Нет числовых столбцов для статистики")


# ── Вспомогательные функции ──────────────────────────────────────

def _apply_filter(col, row_cols, i, options_df, full_df,
                  text_cols, integer_cols, float_cols,
                  selected_filters, numeric_filters):
    """Создаёт фильтр нужного типа и сохраняет выбор. Не мутирует DataFrame."""
    if col in text_cols:
        result = create_text_filter(col, row_cols, i, options_df)
        if result:
            selected_filters[col] = result
    elif col in integer_cols:
        result = create_int_filter(col, row_cols, i, options_df, full_df)
        if result:
            numeric_filters[col] = result
    elif col in float_cols:
        result = create_float_filter(col, row_cols, i, options_df, full_df)
        if result:
            numeric_filters[col] = result


def _validate_and_apply(df, selected_filters, numeric_filters):
    """Валидирует фильтры и возвращает отфильтрованный DataFrame.

    Все фильтры применяются к оригинальному df, чтобы
    очистка любого фильтра корректно расширяла результат.
    """
    # Проверяем, есть ли активные фильтры
    has_active = bool(selected_filters)
    if not has_active:
        for col, (mn, mx) in numeric_filters.items():
            if col in df.columns:
                cd = df[col].dropna()
                if len(cd) > 0:
                    if mn != float(cd.min()) or mx != float(cd.max()):
                        has_active = True
                        break

    if not has_active:
        return df.copy()

    # Применяем ВСЕ фильтры к оригинальному DataFrame
    temp = df.copy()
    for col, values in selected_filters.items():
        if values:
            temp = temp[temp[col].astype(str).isin([str(v) for v in values])]
    for col, (mn, mx) in numeric_filters.items():
        if mn <= mx:
            temp = temp[(temp[col] >= mn) & (temp[col] <= mx)]

    if len(temp) == 0:
        # Диагностика
        problematic = []
        problematic_cols = []
        test_df = df.copy()
        for col, values in selected_filters.items():
            if values:
                t = test_df[test_df[col].astype(str).isin([str(v) for v in values])]
                if len(t) == 0:
                    vals_str = ', '.join(map(str, values[:3]))
                    if len(values) > 3:
                        vals_str += f'… (+{len(values) - 3})'
                    problematic.append(f"**{col}**: {vals_str}")
                    problematic_cols.append(col)
                else:
                    test_df = t
        for col, (mn, mx) in numeric_filters.items():
            if mn <= mx:
                t = test_df[(test_df[col] >= mn) & (test_df[col] <= mx)]
                if len(t) == 0:
                    problematic.append(f"**{col}**: от {mn} до {mx}")
                    problematic_cols.append(col)
                else:
                    test_df = t

        if problematic:
            msg = "⚠️ **Комбинация фильтров не дала результатов.**\n\n"
            msg += "**Проблемные фильтры:**\n"
            for p in problematic:
                msg += f"- {p}\n"
            st.markdown(msg)
            if st.button("Исправить", key="rv_fix_filters",
                         help="Сбросит проблемные фильтры"):
                fix_filters_automatically(problematic_cols)

        st.error(f"Результат пуст: отфильтровано 0 из {len(df)} строк")
    else:
        st.success(
            f"✅ Отфильтровано строк: {len(temp)} из {len(df)}"
        )

    return temp
