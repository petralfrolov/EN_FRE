"""
Вкладка «Визуализация реестра кормов».

Загружает Excel-файл реестра из стандартного пути (настройки пользователя),
отображает каскадные фильтры (на основе справочника кодировки),
таблицу данных, графики и статистику.
"""

import streamlit as st
import pandas as pd
import plotly.express as _px

from modules.cascade_discovery import CascadeDiscovery
from modules.codebook import load_codebook
from .data_loading import load_and_clean_sheet, classify_columns
from .filters import (
    FILTER_GROUPS,
    create_year_filter, create_text_filter, create_int_filter, create_float_filter,
    reset_all_filters, fix_filters_automatically,
)
from .charts import (
    build_chart, build_hybrid_chart,
    AXIS_LABELS, SUPPORTS_COLOR, SUPPORTS_TREND, SUPPORTS_AGG,
)

CHART_TYPES = [
    "Столбчатая диаграмма",
    "Линейный график",
    "Точечная диаграмма",
    "Гистограмма",
    "Круговая диаграмма",
    "Ящик с усами",
]

AGG_OPTIONS = ["Среднее", "Сумма", "Медиана", "Количество", "Минимум", "Максимум"]
HYBRID_CHART_TYPES = ["Линия", "Столбцы", "Точки"]

HELPS = {
    "chart_type": "Выберите способ представления данных. Для каждого типа доступны разные параметры.",
    "x_col":      "Столбец для горизонтальной оси / группировки категорий.",
    "y_col":      "Числовой столбец для вертикальной оси / значений.",
    "agg_type":   "Как свернуть несколько строк с одним X в одно значение. "
                  "«Среднее» — среднее арифметическое, «Количество» — число записей и т.д.",
    "color_col":  "Столбец для цветового разделения данных. "
                  "Доступны столбцы с не более чем 50 уникальными значениями.",
    "bar_mode":   "«Накопление» — столбцы складываются; «Без накопления» — рядом.",
    "show_trend": "Добавляет пунктирную линию линейной регрессии (МНК) поверх графика.",
    "hybrid":     "Добавьте несколько метрик для отображения на одном графике.",
    "codebook":   "Фильтр по справочнику кодировки. Сужает строки реестра по смысловым атрибутам.",
}

# Год — имя столбца (может отсутствовать в данных)
_YEAR_COLS = {'год', 'year'}


# ─────────────────────────────────────────────────────────────────
def _safe_str_series(series: pd.Series) -> pd.Series:
    """Безопасное преобразование столбца в строку (убирает .0 у целых чисел)."""
    return series.astype(str).str.replace(r'\.0$', '', regex=True)

def _isin_case_insensitive(series: pd.Series, values: list) -> pd.Series:
    """Проверка вхождения значений в столбец без учета регистра."""
    if not values:
        return pd.Series(True, index=series.index)
    vals_lower = [str(v).lower() for v in values]
    return _safe_str_series(series).str.lower().isin(vals_lower)

def render_reestr_visualisation():
    """Основная функция рендеринга вкладки «Визуализация реестра»."""

    st.subheader("Визуализация реестра кормов")

    # ── Загрузка стороннего реестра ──────────────────────────────
    with st.expander("Загрузить сторонний реестр (опционально)"):
        vis_temp_registry = st.file_uploader(
            "Загрузите Excel-файл реестра для визуализации",
            type=["xlsx", "xls"],
            key="vis_temp_registry_upload",
        )

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
            st.info(f"Используется загруженный файл: **{vis_temp_registry.name}**")
        except Exception as e:
            st.error(f"Ошибка сохранения: {e}")

    if not using_vis_temp:
        if not excel_path:
            st.warning("Путь к реестру не задан. Проверьте настройки.")
            return
        st.info(f"Реестр (база): `{excel_path}`")

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

    # ── Загрузка данных ──────────────────────────────────────────
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

    color_candidates = [c for c in text_cols if df[c].nunique() <= 50]
    for c in numeric_cols:
        if df[c].nunique() <= 50 and c not in color_candidates:
            color_candidates.append(c)

    # ── Каскадный порядок фильтров ───────────────────────────────
    all_available = list(df.columns)
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

    # ── Загрузка справочника кодировки ───────────────────────────
    try:
        geo_map, culture_map, feed_map = load_codebook()
        has_codebook = not geo_map.empty or not culture_map.empty or not feed_map.empty
    except Exception:
        geo_map = pd.DataFrame()
        culture_map = pd.Series(dtype=object)
        feed_map = pd.Series(dtype=object)
        has_codebook = False

    # ══════════════════════════════════════════════════════════════
    # ── ОСНОВНЫЕ ФИЛЬТРЫ (одна строка) ───────────────────────────
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")

    hc1, hc2 = st.columns([4, 1])
    with hc1:
        st.subheader("Фильтры данных")
    with hc2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Сбросить фильтры", key="rv_reset_all",
                     help="Сбросит все фильтры", width='stretch'):
            reset_all_filters(df)

    selected_filters: dict[str, list] = {}
    numeric_filters:  dict[str, tuple] = {}
    processed_cols:   set[str] = set()

    # Найдём столбец «Год» в данных
    year_col = next(
        (c for c in df.columns if c.lower() in _YEAR_COLS and c in integer_cols), None
    )
    # Найдём столбец «Кодировка»
    kod_col = next(
        (c for c in df.columns if c.lower().replace(" ", "") in ("кодировка", "kod")), None
    )

    # Строим список основных фильтров — ВСЕГДА одна строка
    # Порядок: Год | Регион | Хозяйство | Подразделение | Культура | Тип корма | Кодировка
    MAIN_SLOTS = []
    if year_col:
        MAIN_SLOTS.append(("year",      year_col))
    if has_codebook:
        if not geo_map.empty:
            MAIN_SLOTS.append(("cb_region",   "rv_cb_region"))
            MAIN_SLOTS.append(("cb_farm",     "rv_cb_farm"))
            MAIN_SLOTS.append(("cb_div",      "rv_cb_div"))
        if not culture_map.empty:
            MAIN_SLOTS.append(("cb_culture",  "rv_cb_culture"))
        if not feed_map.empty:
            MAIN_SLOTS.append(("cb_feedtype", "rv_cb_feedtype"))
    if kod_col:
        MAIN_SLOTS.append(("kodировка",  kod_col))

    current_filtered = df.copy()

    if MAIN_SLOTS:
        main_ui = st.columns(len(MAIN_SLOTS))

        for slot_idx, (slot_type, slot_data) in enumerate(MAIN_SLOTS):

            # ── Год ──
            if slot_type == "year":
                col_name = slot_data
                processed_cols.add(col_name)
                result = create_year_filter(col_name, main_ui, slot_idx, current_filtered)
                if result:
                    selected_filters[col_name] = result
                    mask = _isin_case_insensitive(current_filtered[col_name], result)
                    current_filtered = current_filtered[mask].copy()

            # ── Кодировочные фильтры ──
            elif slot_type == "cb_region":
                # Каскадно: опции из гео-справочника
                regions = sorted(geo_map["Регион"].dropna().unique().tolist())
                _cb_vals = _cb_multiselect(main_ui[slot_idx], "Регион", regions, "rv_cb_region",
                                           help=HELPS["codebook"])
                if _cb_vals:
                    st.session_state["_rv_cb_region_vals"] = _cb_vals
                    if "Регион" in current_filtered.columns:
                        current_filtered = current_filtered[
                            _isin_case_insensitive(current_filtered["Регион"], _cb_vals)
                        ].copy()
                        selected_filters["Регион"] = _cb_vals
                        processed_cols.add("Регион")
                else:
                    st.session_state["_rv_cb_region_vals"] = None

            elif slot_type == "cb_farm":
                region_vals = st.session_state.get("_rv_cb_region_vals")
                if region_vals and not geo_map.empty:
                    sub_geo = geo_map[geo_map["Регион"].isin(region_vals)]
                    farms = sorted(sub_geo["Хозяйство"].dropna().unique().tolist())
                else:
                    farms = sorted(geo_map["Хозяйство"].dropna().unique().tolist())
                _cb_vals = _cb_multiselect(main_ui[slot_idx], "Хозяйство", farms, "rv_cb_farm")
                if _cb_vals:
                    st.session_state["_rv_cb_farm_vals"] = _cb_vals
                    if "Хозяйство" in current_filtered.columns:
                        current_filtered = current_filtered[
                            _isin_case_insensitive(current_filtered["Хозяйство"], _cb_vals)
                        ].copy()
                        selected_filters["Хозяйство"] = _cb_vals
                        processed_cols.add("Хозяйство")
                else:
                    st.session_state["_rv_cb_farm_vals"] = None

            elif slot_type == "cb_div":
                farm_vals   = st.session_state.get("_rv_cb_farm_vals")
                region_vals = st.session_state.get("_rv_cb_region_vals")
                sub_geo = geo_map
                if farm_vals and not geo_map.empty:
                    sub_geo = geo_map[geo_map["Хозяйство"].isin(farm_vals)]
                elif region_vals and not geo_map.empty:
                    sub_geo = geo_map[geo_map["Регион"].isin(region_vals)]
                divs = sorted(sub_geo["Подразделение"].dropna().unique().tolist())
                _cb_vals = _cb_multiselect(main_ui[slot_idx], "Подразделение", divs, "rv_cb_div")
                if _cb_vals:
                    if "Подразделение" in current_filtered.columns:
                        current_filtered = current_filtered[
                            _isin_case_insensitive(current_filtered["Подразделение"], _cb_vals)
                        ].copy()
                        selected_filters["Подразделение"] = _cb_vals
                        processed_cols.add("Подразделение")

            elif slot_type == "cb_culture":
                cultures = sorted(culture_map.dropna().unique().tolist())
                _cb_vals = _cb_multiselect(main_ui[slot_idx], "Культура", cultures, "rv_cb_culture")
                if _cb_vals:
                    culture_col = next(
                        (c for c in current_filtered.columns if c.lower() == "культура"), None
                    )
                    if culture_col:
                        current_filtered = current_filtered[
                            _isin_case_insensitive(current_filtered[culture_col], _cb_vals)
                        ].copy()
                        selected_filters[culture_col] = _cb_vals
                        processed_cols.add(culture_col)

            elif slot_type == "cb_feedtype":
                feed_types = sorted(feed_map.dropna().unique().tolist())
                _cb_vals = _cb_multiselect(main_ui[slot_idx], "Тип корма", feed_types,
                                           "rv_cb_feedtype")
                if _cb_vals and kod_col and kod_col in current_filtered.columns:
                    matching_codes = {
                        str(code) for code, name in feed_map.items()
                        if str(name).lower() in [str(v).lower() for v in _cb_vals]
                    }
                    def _match_feed(code_val, codes=matching_codes):
                        try:
                            parts = str(code_val).strip().split(".")
                            return len(parts) == 6 and parts[3] in codes
                        except Exception:
                            return False
                    mask = current_filtered[kod_col].apply(_match_feed)
                    current_filtered = current_filtered[mask].copy()

            # ── Кодировка (raw multiselect) ──
            elif slot_type == "kodировка":
                col_name = slot_data
                processed_cols.add(col_name)
                result = create_text_filter(col_name, main_ui, slot_idx, current_filtered)
                if result:
                    selected_filters[col_name] = result
                    mask = _safe_str_series(current_filtered[col_name]).isin([str(v) for v in result])
                    current_filtered = current_filtered[mask].copy()

    # Помечаем основные колонки как обработанные
    for c in ("Регион", "Хозяйство", "Подразделение", "Культура"):
        processed_cols.add(c)

    st.markdown("---")

    # ── CSS для групп фильтров ────────────────────────────────────
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

    # ── Дополнительные фильтры (один коллапс) ────────────────────
    group_sections: dict[str, list] = {}
    for group_name, group_cols_list in FILTER_GROUPS.items():
        available = [c for c in group_cols_list if c in df.columns and c not in processed_cols]
        available_sorted = [c for c in cascade_order if c in available]
        for c in available:
            if c not in available_sorted:
                available_sorted.append(c)
        if available_sorted:
            group_sections[group_name] = available_sorted
            for c in available_sorted:
                processed_cols.add(c)

    remaining = [c for c in text_cols + integer_cols + float_cols if c not in processed_cols]
    remaining_sorted = [c for c in cascade_order if c in remaining]
    for c in remaining:
        if c not in remaining_sorted:
            remaining_sorted.append(c)
    for c in remaining_sorted:
        processed_cols.add(c)

    total_extra = sum(len(v) for v in group_sections.values()) + len(remaining_sorted)
    if total_extra > 0:
        with st.expander(f"Дополнительные фильтры ({total_extra})", expanded=False):
            cf_inner = current_filtered.copy()

            for group_name, gcols in group_sections.items():
                st.markdown(f"**{group_name}**")
                for row_start in range(0, len(gcols), 3):
                    row_ui = st.columns(3)
                    for i in range(3):
                        idx = row_start + i
                        if idx < len(gcols):
                            col = gcols[idx]
                            cf_inner = _apply_filter_cascading(
                                col, row_ui, i, cf_inner, df,
                                text_cols, integer_cols, float_cols,
                                selected_filters, numeric_filters,
                            )
                st.markdown("")

            if remaining_sorted:
                st.markdown("**Прочие**")
                for row_start in range(0, len(remaining_sorted), 3):
                    row_ui = st.columns(3)
                    for i in range(3):
                        idx = row_start + i
                        if idx < len(remaining_sorted):
                            col = remaining_sorted[idx]
                            cf_inner = _apply_filter_cascading(
                                col, row_ui, i, cf_inner, df,
                                text_cols, integer_cols, float_cols,
                                selected_filters, numeric_filters,
                            )

    # ── Применение всех фильтров ──────────────────────────────────
    # Кодировочные фильтры уже учтены через selected_filters (Регион/Хозяйство/Подразделение/Культура)
    # + фильтр Тип корма применён через current_filtered, но нам нужно отразить это в итоге.
    # Используем current_filtered как базу и применяем поверх selected_filters + numeric_filters.
    filtered_df = _validate_and_apply(current_filtered, selected_filters, numeric_filters,
                                      original_len=len(df))

    # ══════════════════════════════════════════════════════════════
    # ── ТАБЛИЦА ДАННЫХ ────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("Таблица данных")
    st.caption(f"Показано {len(filtered_df)} из {len(df)} строк")
    st.dataframe(filtered_df, width='stretch', height=320)

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
                st.dataframe(stats.T, width='stretch')
            else:
                st.info("Нет числовых столбцов для статистики")
        else:
            st.info("Нет числовых столбцов для статистики")

    # ══════════════════════════════════════════════════════════════
    # ── ВИЗУАЛИЗАЦИЯ ─────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("Визуализация данных")

    chart_type = st.selectbox(
        "Тип графика", CHART_TYPES, key="rv_chart_type", help=HELPS["chart_type"],
    )

    is_hybrid = st.checkbox(
        "Гибридный график (несколько метрик)", key="rv_is_hybrid", help=HELPS["hybrid"],
    )

    x_label, y_label = AXIS_LABELS.get(chart_type, ("По горизонтали", "По вертикали"))

    c1, c2 = st.columns(2)
    with c1:
        x_column = st.selectbox(
            x_label or "По горизонтали",
            options=list(df.columns), key="rv_x_col", help=HELPS["x_col"],
        )

    y_column = None
    if not is_hybrid and chart_type != "Гистограмма" and y_label:
        with c2:
            y_column = st.selectbox(
                y_label,
                options=numeric_cols if numeric_cols else list(df.columns),
                key="rv_y_col", help=HELPS["y_col"],
            )

    agg_type = None
    if not is_hybrid and chart_type in SUPPORTS_AGG:
        agg_type = st.selectbox(
            "Агрегация", AGG_OPTIONS, index=0, key="rv_agg_type", help=HELPS["agg_type"],
        )

    color_column = None
    if not is_hybrid and chart_type in SUPPORTS_COLOR:
        color_column = st.selectbox(
            "Цвет / группировка",
            options=["Нет"] + color_candidates,
            key="rv_color_col", help=HELPS["color_col"],
        )

    bar_mode = "stack"
    if chart_type == "Столбчатая диаграмма" and not is_hybrid:
        bm_choice = st.radio(
            "Режим столбцов", ["Накопление", "Без накопления"],
            horizontal=True, key="rv_bar_mode", help=HELPS["bar_mode"],
        )
        bar_mode = "stack" if bm_choice == "Накопление" else "group"
        if bar_mode == "group" and (not color_column or color_column == "Нет"):
            st.info("ℹ️ Режим «Без накопления» работает только при выбранной "
                    "группировке (Цвет / группировка ≠ Нет).")

    show_trend = False
    if not is_hybrid and chart_type in SUPPORTS_TREND:
        show_trend = st.checkbox(
            "Показать линию тренда", key="rv_show_trend", help=HELPS["show_trend"],
        )

    # ── Гибридные метрики ─────────────────────────────────────────
    if is_hybrid:
        st.markdown("#### Метрики")
        st.caption("Добавьте метрики: для каждой выберите столбец, агрегацию и тип.")

        if "rv_hybrid_metrics" not in st.session_state:
            st.session_state["rv_hybrid_metrics"] = [
                {"y": "", "agg": "Среднее", "type": "Линия"}
            ]

        metrics_state = st.session_state["rv_hybrid_metrics"]
        colors_palette = _px.colors.qualitative.Plotly

        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button("➕ Добавить метрику", key="rv_add_metric"):
                metrics_state.append({"y": "", "agg": "Среднее", "type": "Линия"})
                st.rerun()
        with col_clear:
            if st.button("🗑 Очистить всё", key="rv_clear_metrics"):
                st.session_state["rv_hybrid_metrics"] = [
                    {"y": "", "agg": "Среднее", "type": "Линия"}
                ]
                st.rerun()

        to_delete = None
        for i, m in enumerate(metrics_state):
            with st.expander(f"Метрика {i + 1}: {m.get('y', '—')}", expanded=(i == 0)):
                mc1, mc2, mc3, mc4 = st.columns([3, 2, 2, 1])
                with mc1:
                    y_opts = numeric_cols if numeric_cols else list(df.columns)
                    cur_y = m.get("y", "")
                    y_idx = y_opts.index(cur_y) if cur_y in y_opts else 0
                    m["y"] = st.selectbox("Столбец (Y)", y_opts, index=y_idx,
                                          key=f"rv_metric_y_{i}")
                with mc2:
                    cur_agg = m.get("agg", "Среднее")
                    agg_idx = AGG_OPTIONS.index(cur_agg) if cur_agg in AGG_OPTIONS else 0
                    m["agg"] = st.selectbox("Агрегация", AGG_OPTIONS, index=agg_idx,
                                            key=f"rv_metric_agg_{i}")
                with mc3:
                    cur_t = m.get("type", "Линия")
                    t_idx = HYBRID_CHART_TYPES.index(cur_t) if cur_t in HYBRID_CHART_TYPES else 0
                    m["type"] = st.selectbox("Тип", HYBRID_CHART_TYPES, index=t_idx,
                                             key=f"rv_metric_type_{i}")
                with mc4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✖", key=f"rv_del_metric_{i}", help="Удалить метрику"):
                        to_delete = i
                m["color"] = colors_palette[i % len(colors_palette)]

        if to_delete is not None:
            metrics_state.pop(to_delete)
            st.rerun()

        st.session_state["rv_hybrid_metrics"] = metrics_state

        # Галочка Разделить оси y (если выбрано ровно 2 метрики)
        if len(metrics_state) == 2:
            st.checkbox(
                "Разделить оси Y (шкалы слева и справа)",
                value=True,
                key="rv_split_y",
                help="Если выбрано 2 метрики, их можно отобразить на разных осях с разными масштабами."
            )

    # ── Построить ─────────────────────────────────────────────────
    if st.button("📊 Построить график", type="primary", key="rv_build_chart"):
        try:
            if is_hybrid:
                metrics = st.session_state.get("rv_hybrid_metrics", [])
                split_y = st.session_state.get("rv_split_y", True) if len(metrics) == 2 else False
                fig = build_hybrid_chart(
                    filtered_df, x_column,
                    metrics,
                    split_y=split_y
                )
            else:
                fig = build_chart(
                    chart_type, filtered_df, x_column, y_column,
                    color_column, agg_type,
                    bar_mode=bar_mode,
                    show_trend=show_trend,
                )
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


# ── Вспомогательные функции ──────────────────────────────────────

def _cb_multiselect(col_container, label: str, options: list, key: str,
                    help: str | None = None) -> list:
    """Отображает multiselect кодировочного фильтра и возвращает список выбранных значений."""
    with col_container:
        prev_val = st.session_state.get(key, [])
        # Если старый формат (строка от selectbox), конвертируем
        if isinstance(prev_val, str):
            prev_val = [prev_val] if prev_val and prev_val != "Все" else []
        # Убираем значения, которых нет в текущих опциях
        valid = [v for v in prev_val if v in options]
        st.session_state[key] = valid
        return st.multiselect(
            label, options, key=key, help=help,
        )


def _apply_filter_cascading(col, row_cols, i,
                             current_filtered: pd.DataFrame,
                             full_df: pd.DataFrame,
                             text_cols, integer_cols, float_cols,
                             selected_filters, numeric_filters) -> pd.DataFrame:
    """
    Создаёт фильтр, сохраняет выбор и возвращает обновлённый current_filtered.
    Каскадность: каждый следующий фильтр видит данные,
    уже отфильтрованные предыдущими.
    """
    if col in text_cols:
        result = create_text_filter(col, row_cols, i, current_filtered)
        if result:
            selected_filters[col] = result
            mask = _isin_case_insensitive(current_filtered[col], result)
            current_filtered = current_filtered[mask].copy()
    elif col in integer_cols:
        result = create_int_filter(col, row_cols, i, current_filtered, full_df)
        if result:
            numeric_filters[col] = result
            mn, mx = result
            current_filtered = current_filtered[
                (current_filtered[col] >= mn) & (current_filtered[col] <= mx)
            ].copy()
    elif col in float_cols:
        result = create_float_filter(col, row_cols, i, current_filtered, full_df)
        if result:
            numeric_filters[col] = result
            mn, mx = result
            current_filtered = current_filtered[
                (current_filtered[col] >= mn) & (current_filtered[col] <= mx)
            ].copy()
    return current_filtered


def _validate_and_apply(base_df: pd.DataFrame, selected_filters: dict,
                        numeric_filters: dict, original_len: int = None) -> pd.DataFrame:
    """
    Применяет selected_filters + numeric_filters к base_df.
    base_df уже содержит кодировочные фильтры (Регион, Хозяйство и т.д.).
    """
    has_active = bool(selected_filters)
    if not has_active:
        for col, (mn, mx) in numeric_filters.items():
            if col in base_df.columns:
                cd = base_df[col].dropna()
                if len(cd) > 0:
                    if mn != float(cd.min()) or mx != float(cd.max()):
                        has_active = True
                        break

    if not has_active:
        if original_len and len(base_df) < original_len:
            st.success(f"✅ Отфильтровано строк: {len(base_df)} из {original_len}")
        return base_df.copy()

    temp = base_df.copy()
    for col, values in selected_filters.items():
        if values and col in temp.columns:
            temp = temp[_isin_case_insensitive(temp[col], values)]
    for col, (mn, mx) in numeric_filters.items():
        if mn <= mx and col in temp.columns:
            temp = temp[(temp[col] >= mn) & (temp[col] <= mx)]

    total = original_len or len(base_df)

    if len(temp) == 0:
        problematic = []
        problematic_cols = []
        test_df = base_df.copy()
        for col, values in selected_filters.items():
            if values and col in test_df.columns:
                t = test_df[_isin_case_insensitive(test_df[col], values)]
                if len(t) == 0:
                    vals_str = ', '.join(map(str, values[:3]))
                    if len(values) > 3:
                        vals_str += f'… (+{len(values) - 3})'
                    problematic.append(f"**{col}**: {vals_str}")
                    problematic_cols.append(col)
                else:
                    test_df = t
        for col, (mn, mx) in numeric_filters.items():
            if mn <= mx and col in test_df.columns:
                t = test_df[(test_df[col] >= mn) & (test_df[col] <= mx)]
                if len(t) == 0:
                    problematic.append(f"**{col}**: от {mn} до {mx}")
                    problematic_cols.append(col)
                else:
                    test_df = t

        if problematic:
            msg = "⚠️ **Комбинация фильтров не дала результатов.**\n\n**Проблемные:**\n"
            for p in problematic:
                msg += f"- {p}\n"
            st.markdown(msg)
            if st.button("Исправить", key="rv_fix_filters", help="Сбросит проблемные фильтры"):
                fix_filters_automatically(problematic_cols)

        st.error(f"Результат пуст: отфильтровано 0 из {total} строк")
    else:
        st.success(f"✅ Отфильтровано строк: {len(temp)} из {total}")

    return temp
