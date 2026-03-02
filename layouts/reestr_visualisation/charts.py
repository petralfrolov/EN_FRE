"""
Модуль построения графиков для визуализации реестра кормов.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


AGG_MAP = {
    "Сумма": "sum",
    "Среднее": "mean",
    "Медиана": "median",
    "Количество": "count",
    "Минимум": "min",
    "Максимум": "max",
}


def build_chart(
    chart_type: str,
    filtered_df: pd.DataFrame,
    x_column: str,
    y_column: str | None,
    color_column: str | None,
    aggregation: str | None = None,
) -> go.Figure | None:
    """
    Строит график выбранного типа с опциональной агрегацией.

    Поддерживаемые типы:
        - Столбчатая диаграмма
        - Линейный график
        - Точечная диаграмма
        - Гистограмма
        - Круговая диаграмма

    Returns:
        go.Figure | None — фигура Plotly или None при ошибке.
    """
    color = color_column if color_column and color_column != "Нет" else None

    # ── Агрегация ────────────────────────────────────────────────
    agg_label = ""
    if aggregation and aggregation in AGG_MAP and y_column:
        agg_func = AGG_MAP[aggregation]
        group_cols = [x_column]
        if color:
            group_cols.append(color)
        group_cols = [c for c in group_cols if c in filtered_df.columns]
        if group_cols:
            plot_df = filtered_df.groupby(group_cols, as_index=False).agg(
                {y_column: agg_func}
            )
        else:
            plot_df = filtered_df
        agg_label = f" ({aggregation.lower()})"
    else:
        plot_df = filtered_df

    # ── Графики ──────────────────────────────────────────────────
    if chart_type == "Столбчатая диаграмма":
        fig = px.bar(
            plot_df, x=x_column, y=y_column, color=color,
            title=f"{y_column}{agg_label} по {x_column}",
        )

    elif chart_type == "Линейный график":
        fig = px.line(
            plot_df, x=x_column, y=y_column, color=color,
            title=f"{y_column}{agg_label} по {x_column}",
        )

    elif chart_type == "Точечная диаграмма":
        fig = px.scatter(
            plot_df, x=x_column, y=y_column, color=color,
            title=f"{y_column}{agg_label} по {x_column}",
        )

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
    else:
        return None

    fig.update_layout(height=500, font=dict(size=12))
    return fig
