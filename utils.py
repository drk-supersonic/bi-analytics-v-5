"""
Общие утилиты для дашбордов и приложения.
"""
import html as html_module
import re
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from config import RUSSIAN_MONTHS


def ensure_budget_columns(df: Optional[pd.DataFrame]) -> None:
    """Добавляет budget plan / budget fact из русских/альтернативных названий, если их ещё нет."""
    if df is None or not hasattr(df, "columns"):
        return
    if "budget plan" not in df.columns:
        for name in ("Бюджет План", "Бюджет план", "Budget Plan", "budget_plan"):
            if name in df.columns:
                df["budget plan"] = df[name]
                break
    if "budget fact" not in df.columns:
        for name in ("Бюджет Факт", "Бюджет факт", "Budget Fact", "budget_fact"):
            if name in df.columns:
                df["budget fact"] = df[name]
                break


def ensure_date_columns(df: Optional[pd.DataFrame]) -> None:
    """
    Добавляет plan start, plan end, base start, base end из русских названий (sample_project_data_fixed.csv),
    если английских колонок ещё нет. Вызывать перед проверкой дат в дашбордах.
    """
    if df is None or not hasattr(df, "columns"):
        return
    date_mapping = [
        ("plan start", ["Старт План", "План Старт", "Plan Start"]),
        ("plan end", ["Конец План", "План Конец", "Plan End"]),
        ("base start", ["Старт Факт", "Факт Старт", "Base Start"]),
        ("base end", ["Конец Факт", "Факт Конец", "Base End"]),
    ]
    for en_name, ru_names in date_mapping:
        if en_name not in df.columns:
            for ru in ru_names:
                if ru in df.columns:
                    df[en_name] = df[ru].copy()
                    break


def get_russian_month_name(period_val: Any) -> str:
    """Возвращает русское название месяца для Period, Timestamp или строки."""
    if isinstance(period_val, pd.Period):
        if period_val.freqstr == "M" or (getattr(period_val, "freqstr", "") or "").startswith("M"):
            month_num = period_val.month
            return RUSSIAN_MONTHS.get(month_num, period_val.strftime("%B"))
        try:
            month_num = period_val.month
            return RUSSIAN_MONTHS.get(month_num, "")
        except Exception:
            return ""
    elif isinstance(period_val, (int, pd.Timestamp)):
        month_num = period_val.month if hasattr(period_val, "month") else period_val
        return RUSSIAN_MONTHS.get(month_num, "")
    elif isinstance(period_val, str):
        try:
            if "-" in period_val:
                parts = period_val.split("-")
                if len(parts) >= 2:
                    month_num = int(parts[1])
                    return RUSSIAN_MONTHS.get(month_num, "")
        except Exception:
            pass
    return ""


def apply_chart_background(fig):
    """Применяет стандартный фон #12385C к графикам для тёмной темы."""
    fig.update_layout(
        template=None,
        plot_bgcolor="#12385C",
        paper_bgcolor="#12385C",
        font=dict(color="#ffffff"),
        legend=dict(font=dict(color="#ffffff")),
        margin=dict(b=150, l=50, r=50, t=50),
    )
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.1)",
        linecolor="rgba(255, 255, 255, 0.3)",
        tickfont=dict(color="#ffffff", size=8),
        title=dict(font=dict(color="#ffffff")),
        zerolinecolor="rgba(255, 255, 255, 0.3)",
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.1)",
        linecolor="rgba(255, 255, 255, 0.3)",
        tickfont=dict(color="#ffffff"),
        title=dict(font=dict(color="#ffffff")),
        zerolinecolor="rgba(255, 255, 255, 0.3)",
        overwrite=True,
    )
    fig.layout.plot_bgcolor = "#12385C"
    fig.layout.paper_bgcolor = "#12385C"
    current_margin = getattr(fig.layout, "margin", None) if hasattr(fig.layout, "margin") and fig.layout.margin else None
    if current_margin:
        new_bottom = max(getattr(current_margin, "b", 50) or 50, 150)
        new_margin = dict(
            l=getattr(current_margin, "l", 50) or 50,
            r=getattr(current_margin, "r", 50) or 50,
            t=getattr(current_margin, "t", 50) or 50,
            b=new_bottom,
        )
        fig.update_layout(margin=new_margin)
    else:
        fig.update_layout(autosize=True, margin=dict(l=50, r=50, t=50, b=150))
    return fig


# Цвет фона таблиц (как у графиков)
TABLE_BG_COLOR = "#12385C"
TABLE_TEXT_COLOR = "#ffffff"

# Размерность сумм: млн рублей
MILLION = 1_000_000


def format_million_rub(value) -> str:
    """Форматирует сумму в млн руб.: 940346 -> '0.94 млн руб.'"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    try:
        x = float(value) / MILLION
        return f"{x:.2f} млн руб."
    except (TypeError, ValueError):
        return ""


def to_million_rub(value):
    """Возвращает значение в млн руб. (для осей графиков)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value) / MILLION
    except (TypeError, ValueError):
        return None


def style_dataframe_for_dark_theme(
    df: pd.DataFrame,
    days_column: Optional[str] = None,
    finance_deviation_column: Optional[str] = None,
):
    """
    Возвращает Styler с фоном #12385C и белым текстом для st.table.
    - days_column: колонка с днями — красный при > 0, зелёный при == 0.
    - finance_deviation_column: колонка отклонения в финансах — положительное или ноль = красный, отрицательное = зелёный (БДДС/БДР).
    """
    if df is None or df.empty:
        return df
    base = df.style.set_properties(
        **{
            "background-color": TABLE_BG_COLOR,
            "color": TABLE_TEXT_COLOR,
            "font-size": "14px",
        }
    ).set_table_styles(
        [
            {"selector": "th", "props": [("background-color", TABLE_BG_COLOR), ("color", TABLE_TEXT_COLOR), ("border", "1px solid rgba(255,255,255,0.3)")]},
            {"selector": "td", "props": [("background-color", TABLE_BG_COLOR), ("color", TABLE_TEXT_COLOR), ("border", "1px solid rgba(255,255,255,0.2)")]},
            {"selector": "th *, td *", "props": [("color", TABLE_TEXT_COLOR)]},
        ]
    )
    if days_column and days_column in df.columns:
        def _days_cell_color(series):
            result = []
            for v in series:
                num = pd.to_numeric(v, errors="coerce")
                if pd.isna(num):
                    result.append(f"background-color: {TABLE_BG_COLOR}; color: {TABLE_TEXT_COLOR}")
                elif num > 0:
                    result.append("background-color: #c0392b; color: #ffffff")  # красный
                else:
                    result.append("background-color: #27ae60; color: #ffffff")  # зелёный при 0
            return result
        base = base.apply(lambda c: _days_cell_color(c) if c.name == days_column else [""] * len(c), axis=0)
    if finance_deviation_column and finance_deviation_column in df.columns:
        def _finance_cell_color(series):
            result = []
            for v in series:
                num = None
                try:
                    s = str(v).strip().replace(",", ".")
                    if s and s not in ("", "nan", "None"):
                        num = float(s)
                    else:
                        match = re.search(r"-?\d+[.,]?\d*", str(v))
                        if match:
                            num = float(match.group().replace(",", "."))
                except (TypeError, ValueError):
                    match = re.search(r"-?\d+[.,]?\d*", str(v))
                    if match:
                        try:
                            num = float(match.group().replace(",", "."))
                        except (TypeError, ValueError):
                            pass
                if num is None or pd.isna(num):
                    result.append(f"background-color: {TABLE_BG_COLOR}; color: {TABLE_TEXT_COLOR}")
                elif num >= 0:
                    result.append("background-color: #c0392b; color: #ffffff")  # красный — положительное/ноль
                else:
                    result.append("background-color: #27ae60; color: #ffffff")  # зелёный — отрицательное
            return result
        base = base.apply(
            lambda c: _finance_cell_color(c) if c.name == finance_deviation_column else [""] * len(c),
            axis=0,
        )
    return base


def _parse_finance_value(v) -> Optional[float]:
    """Извлекает число из ячейки (например '0.94 млн руб.' или '-1.20')."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        s = str(v).strip().replace(",", ".")
        if s and s not in ("", "nan", "None"):
            return float(s)
    except (TypeError, ValueError):
        pass
    match = re.search(r"-?\d+[.,]?\d*", str(v))
    if match:
        try:
            return float(match.group().replace(",", "."))
        except (TypeError, ValueError):
            pass
    return None


def budget_table_to_html(
    df: pd.DataFrame,
    finance_deviation_column: Optional[str] = None,
) -> str:
    """
    Строит HTML таблицы бюджета с раскраской колонки отклонения:
    положительное или ноль = красный фон, отрицательное = зелёный.
    Гарантированно работает в Streamlit (inline-стили в каждой ячейке).
    """
    if df is None or df.empty:
        return "<p>Нет данных для отображения.</p>"
    wrap_id = "bdt_" + str(id(df))  # уникальный id, чтобы стили не задевали другие таблицы
    parts = [
        f'<div id="{wrap_id}" class="budget-deviation-table-wrap" style="overflow-x: auto; margin: 1em 0;">',
        f'<style>'
        f'#{wrap_id} td.bd-cell-red {{ background-color: {TABLE_BG_COLOR} !important; }} '
        f'#{wrap_id} td.bd-cell-red, #{wrap_id} td.bd-cell-red * {{ color: #c0392b !important; }} '
        f'#{wrap_id} td.bd-cell-green {{ background-color: {TABLE_BG_COLOR} !important; }} '
        f'#{wrap_id} td.bd-cell-green, #{wrap_id} td.bd-cell-green * {{ color: #27ae60 !important; }}'
        f'</style>',
        '<table style="width:100%; border-collapse: collapse; background-color: ',
        TABLE_BG_COLOR,
        "; color: ",
        TABLE_TEXT_COLOR,
        '; font-size: 14px;">',
        "<thead><tr>",
    ]
    for col in df.columns:
        col_esc = html_module.escape(str(col))
        parts.append(
            f'<th style="border: 1px solid rgba(255,255,255,0.3); padding: 8px; background-color: {TABLE_BG_COLOR};">{col_esc}</th>'
        )
    parts.append("</tr></thead><tbody>")
    for _, row in df.iterrows():
        parts.append("<tr>")
        for col in df.columns:
            val = row[col]
            val_str = "" if (val is None or (isinstance(val, float) and pd.isna(val))) else str(val)
            val_esc = html_module.escape(val_str)
            if finance_deviation_column and col == finance_deviation_column:
                num = _parse_finance_value(val)
                if num is not None:
                    cell_class = "bd-cell-red" if num >= 0 else "bd-cell-green"
                    parts.append(
                        f'<td class="{cell_class}" style="border: 1px solid rgba(0,0,0,0.2); padding: 8px; font-weight: bold;"><span>{val_esc}</span></td>'
                    )
                else:
                    # Число не распарсилось — красим по тексту (минус = зелёный) или стиль по умолчанию для пустых
                    s = val_str.strip()
                    if not s:
                        parts.append(
                            f'<td style="border: 1px solid rgba(255,255,255,0.2); padding: 8px; background-color: {TABLE_BG_COLOR}; color: {TABLE_TEXT_COLOR};">{val_esc}</td>'
                        )
                    else:
                        cell_class = "bd-cell-green" if (s.startswith("-") or re.search(r"^-\d", s)) else "bd-cell-red"
                        parts.append(
                            f'<td class="{cell_class}" style="border: 1px solid rgba(0,0,0,0.2); padding: 8px; font-weight: bold;"><span>{val_esc}</span></td>'
                        )
            else:
                parts.append(
                    f'<td style="border: 1px solid rgba(255,255,255,0.2); padding: 8px; background-color: {TABLE_BG_COLOR}; color: {TABLE_TEXT_COLOR};">{val_esc}</td>'
                )
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def render_styled_table_to_html(styler, hide_index: bool = True) -> str:
    """
    Возвращает HTML строку стилизованной таблицы для вывода через st.markdown(..., unsafe_allow_html=True).
    st.table() в Streamlit не всегда применяет стили pandas Styler, поэтому для раскраски ячеек используем HTML.
    """
    if styler is None or (hasattr(styler, "data") and styler.data.empty):
        return "<p>Нет данных для отображения.</p>"
    try:
        html = styler.to_html(index=not hide_index)
        return f'<div style="overflow-x: auto; margin: 1em 0;">{html}</div>'
    except Exception:
        return ""


def get_report_param_value(report_name: str, parameter_key: str, default: Any = None) -> Any:
    """Возвращает значение параметра отчёта из report_params."""
    try:
        from report_params import get_report_parameter
        param = get_report_parameter(report_name, parameter_key)
        if param and param.get("value") is not None:
            return param["value"]
    except ImportError:
        pass
    return default


def apply_default_filters(report_name: str, user_role: str, filter_widgets: dict) -> dict:
    """Применяет фильтры по умолчанию для отчёта и роли."""
    try:
        from filters import get_default_filters
        default_filters = get_default_filters(user_role, report_name)
        for filter_key, default_value in default_filters.items():
            if filter_key in filter_widgets and filter_widgets[filter_key] is None:
                filter_widgets[filter_key] = default_value
            elif filter_key not in filter_widgets:
                filter_widgets[filter_key] = default_value
    except ImportError:
        pass
    return filter_widgets


def format_dataframe_as_html(
    df: Optional[pd.DataFrame],
    conditional_cols: Optional[Dict[str, Dict[str, str]]] = None,
    column_colors: Optional[Dict[str, str]] = None,
) -> str:
    """Форматирует DataFrame в HTML-таблицу для отображения в Streamlit."""
    if df is None or df.empty:
        return "<p>Нет данных для отображения.</p>"
    html_table = (
        "<table style='width:100%; border-collapse: collapse; background-color: #12385C; color: #ffffff;'>"
    )
    html_table += "<thead><tr>"
    for col in df.columns:
        col_escaped = html_module.escape(str(col))
        html_table += f"<th style='border: 1px solid #ffffff; padding: 8px; background-color: rgba(18, 56, 92, 0.95);'>{col_escaped}</th>"
    html_table += "</tr></thead><tbody>"
    for idx, row in df.iterrows():
        html_table += "<tr>"
        for col in df.columns:
            value = row[col]
            is_scalar = pd.api.types.is_scalar(value)
            if conditional_cols and col in conditional_cols:
                cond_config = conditional_cols[col]
                pos_color = cond_config.get("positive_color", "#ff4444")
                neg_color = cond_config.get("negative_color", "#44ff44")
                if is_scalar and not (isinstance(value, (int, float)) and pd.isna(value)):
                    if isinstance(value, (int, float)):
                        color = pos_color if value > 0 else neg_color
                        formatted_value = f"{value:.2f}" if isinstance(value, float) else f"{int(value)}"
                    else:
                        formatted_value = str(value) if value != "" else "0"
                        color = neg_color
                else:
                    formatted_value = "0" if (is_scalar and pd.isna(value)) else str(value)
                    color = neg_color
                formatted_value = html_module.escape(str(formatted_value))
                html_table += f"<td style='border: 1px solid #ffffff; padding: 8px; color: {color}; font-weight: bold;'>{formatted_value}</td>"
            else:
                if isinstance(value, (int, float)) and is_scalar and not pd.isna(value):
                    if "отклонен" in str(col).lower() or "deviation" in str(col).lower():
                        formatted_value = f"{float(value):.2f}"
                    elif isinstance(value, float) and (value % 1 != 0 or abs(value) < 1):
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = f"{int(value)}"
                else:
                    formatted_value = "" if (is_scalar and pd.isna(value)) else str(value)
                formatted_value = html_module.escape(str(formatted_value))
                cell_style = "border: 1px solid #ffffff; padding: 8px;"
                if column_colors and col in column_colors:
                    cell_style += f" color: {column_colors[col]};"
                html_table += f"<td style='{cell_style}'>{formatted_value}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table>"
    return html_table
