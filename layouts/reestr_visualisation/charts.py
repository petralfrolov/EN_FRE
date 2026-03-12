"""
Модуль построения графиков для визуализации реестра кормов.

Поддерживает:
  - Столбчатая диаграмма (stack / group)
  - Линейный график (с опциональным трендом)
  - Точечная диаграмма / Скаттерограмма (с опциональным трендом)
  - Гистограмма
  - Круговая диаграмма
  - Ящик с усами (Boxplot)
  - Гибридные графики: несколько метрик с разными типами на одной фигуре
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


AGG_MAP = {
    "Среднее":    "mean",
    "Сумма":      "sum",
    "Медиана":    "median",
    "Количество": "count",
    "Минимум":    "min",
    "Максимум":   "max",
}

# Метки осей в зависимости от типа графика
AXIS_LABELS = {
    "Столбчатая диаграмма": ("Категория", "Значение"),
    "Линейный график":       ("Ось X",     "Ось Y"),
    "Точечная диаграмма":    ("Ось X",     "Ось Y"),
    "Гистограмма":           ("Столбец",   None),
    "Круговая диаграмма":    ("Категория", "Значение"),
    "Ящик с усами":          ("Группа",    "Значение"),
}

# Типы, поддерживающие цвет
SUPPORTS_COLOR = {
    "Столбчатая диаграмма", "Линейный график", "Точечная диаграмма", "Ящик с усами"
}

# Типы, поддерживающие тренд
SUPPORTS_TREND = {"Линейный график", "Точечная диаграмма"}

# Типы, поддерживающие агрегацию
SUPPORTS_AGG = {
    "Столбчатая диаграмма", "Линейный график", "Точечная диаграмма", "Круговая диаграмма"
}


def _aggregate(df: pd.DataFrame, x_col: str, y_col: str,
               color_col: str | None, agg: str) -> pd.DataFrame:
    """Агрегирует df по x_col (+ color_col) с функцией agg для y_col."""
    agg_func = AGG_MAP.get(agg, "mean")
    group_cols = [c for c in [x_col, color_col] if c and c in df.columns]
    if not group_cols:
        return df
    return df.groupby(group_cols, as_index=False).agg({y_col: agg_func})


def _add_trend(fig: go.Figure, df: pd.DataFrame,
               x_col: str, y_col: str) -> go.Figure:
    """Добавляет OLS-линию тренда на существующую фигуру."""
    try:
        sub = df[[x_col, y_col]].dropna()
        if not pd.api.types.is_numeric_dtype(sub[x_col]):
            sub[x_col] = pd.factorize(sub[x_col])[0]
        x_vals = sub[x_col].astype(float).values
        y_vals = sub[y_col].astype(float).values
        if len(x_vals) < 2:
            return fig
        coeffs = np.polyfit(x_vals, y_vals, 1)
        x_line = np.linspace(x_vals.min(), x_vals.max(), 200)
        y_line = np.polyval(coeffs, x_line)
        fig.add_trace(go.Scatter(
            x=x_line, y=y_line,
            mode="lines",
            name=f"Тренд ({coeffs[0]:+.3f}x)",
            line=dict(color="red", width=2, dash="dot"),
        ))
    except Exception:
        pass
    return fig


def build_chart(
    chart_type: str,
    filtered_df: pd.DataFrame,
    x_column: str,
    y_column: str | None,
    color_column: str | None,
    aggregation: str | None = None,
    bar_mode: str = "stack",
    show_trend: bool = False,
) -> go.Figure | None:
    """
    Строит одиночный график.

    Parameters
    ----------
    chart_type   : тип графика (ключ из AXIS_LABELS)
    filtered_df  : уже отфильтрованный DataFrame
    x_column     : столбец по X
    y_column     : столбец по Y (None для Гистограммы)
    color_column : столбец группировки (None / "Нет" — без группировки)
    aggregation  : название агрегации из AGG_MAP или None
    bar_mode     : "stack" или "group" (только для Столбчатой)
    show_trend   : рисовать ли тренд (для Линейного / Точечного)
    """
    color = color_column if color_column and color_column != "Нет" else None
    agg_label = f" ({aggregation.lower()})" if aggregation else ""

    # ── Агрегация ─────────────────────────────────────────────────
    if aggregation and y_column and chart_type in SUPPORTS_AGG:
        plot_df = _aggregate(filtered_df, x_column, y_column, color, aggregation)
    else:
        plot_df = filtered_df.copy()

    # Приводим color-столбец к строке, чтобы Plotly считал его категориальным
    # (иначе числовые столбцы вроде «Год» трактуются как непрерывная шкала
    #  и barmode='group' не отображает столбцы рядом)
    if color and color in plot_df.columns:
        plot_df[color] = plot_df[color].astype(str).str.replace(r'\.0$', '', regex=True)

    # ── Графики ───────────────────────────────────────────────────
    fig = None

    if chart_type == "Столбчатая диаграмма":
        fig = px.bar(
            plot_df, x=x_column, y=y_column, color=color,
            barmode=bar_mode,
            title=f"{y_column}{agg_label} по {x_column}",
        )

    elif chart_type == "Линейный график":
        fig = px.line(
            plot_df, x=x_column, y=y_column, color=color,
            title=f"{y_column}{agg_label} по {x_column}",
        )
        if show_trend:
            fig = _add_trend(fig, plot_df, x_column, y_column)

    elif chart_type == "Точечная диаграмма":
        fig = px.scatter(
            plot_df, x=x_column, y=y_column, color=color,
            title=f"{y_column}{agg_label} по {x_column}",
        )
        if show_trend:
            fig = _add_trend(fig, plot_df, x_column, y_column)

    elif chart_type == "Гистограмма":
        if not pd.api.types.is_numeric_dtype(filtered_df[x_column]):
            return None
        fig = px.histogram(
            filtered_df, x=x_column,
            title=f"Распределение {x_column}",
        )

    elif chart_type == "Круговая диаграмма":
        if y_column and pd.api.types.is_numeric_dtype(filtered_df[y_column]):
            agg_func = AGG_MAP.get(aggregation, "sum") if aggregation else "sum"
            grouped = filtered_df.groupby(x_column)[y_column].agg(agg_func).reset_index()
            fig = px.pie(
                grouped, names=x_column, values=y_column,
                title=f"{y_column}{agg_label} по {x_column}",
            )
        else:
            return None

    elif chart_type == "Ящик с усами":
        if not (y_column and pd.api.types.is_numeric_dtype(filtered_df[y_column])):
            return None
        fig = px.box(
            filtered_df, x=x_column, y=y_column, color=color,
            title=f"Boxplot: {y_column} по {x_column}",
            points="outliers",
        )

    if fig is None:
        return None

    fig.update_layout(height=520, font=dict(size=12),
                       **({"barmode": bar_mode} if chart_type == "Столбчатая диаграмма" else {}))
    return fig


from plotly.subplots import make_subplots


def build_hybrid_chart(
    df: pd.DataFrame,
    x_column: str,
    metrics: list[dict],
    split_y: bool = False,
) -> go.Figure | None:
    """
    Строит гибридный график с несколькими метриками на одной фигуре.

    Каждый элемент списка metrics:
        {
          "y":        str,   # имя столбца
          "agg":      str,   # агрегация (ключ AGG_MAP) или None
          "type":     str,   # "Столбцы" | "Линия" | "Точки"
          "color":    str,   # цвет трассы (Plotly color string)
        }
    """
    if not metrics:
        return None

    use_secondary = split_y and len(metrics) == 2
    if use_secondary:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    colors = px.colors.qualitative.Plotly

    for i, m in enumerate(metrics):
        y_col  = m.get("y")
        agg    = m.get("agg")
        g_type = m.get("type", "Линия")
        clr    = m.get("color", colors[i % len(colors)])

        if not y_col or y_col not in df.columns:
            continue

        # Агрегируем
        if agg and agg in AGG_MAP and x_column in df.columns:
            plot_df = _aggregate(df, x_column, y_col, None, agg)
            agg_label = f" ({agg.lower()})"
        else:
            plot_df = df.copy()
            agg_label = ""

        name = f"{y_col}{agg_label}"
        x_vals = plot_df[x_column] if x_column in plot_df.columns else []
        y_vals = plot_df[y_col]    if y_col   in plot_df.columns else []

        secondary = use_secondary and (i == 1)

        if g_type == "Столбцы":
            fig.add_trace(
                go.Bar(x=x_vals, y=y_vals, name=name, marker_color=clr),
                secondary_y=secondary if use_secondary else None
            )
        elif g_type == "Точки":
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=y_vals, name=name,
                    mode="markers",
                    marker=dict(color=clr, size=6)
                ),
                secondary_y=secondary if use_secondary else None
            )
        else:  # Линия
            fig.add_trace(
                go.Scatter(
                    x=x_vals, y=y_vals, name=name,
                    mode="lines+markers",
                    line=dict(color=clr, width=2)
                ),
                secondary_y=secondary if use_secondary else None
            )

    if not fig.data:
        return None

    fig.update_layout(
        height=540,
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        barmode="group",
    )

    if use_secondary:
        # Улучшаем подписи осей для 2х осей
        fig.update_yaxes(title_text=metrics[0]["y"], secondary_y=False)
        fig.update_yaxes(title_text=metrics[1]["y"], secondary_y=True)

    return fig
