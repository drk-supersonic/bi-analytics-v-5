"""
Отрисовка дашбордов. Код перенесён из project_visualization_app.py для уменьшения главного файла.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import numpy as np

from config import RUSSIAN_MONTHS
from utils import (
    get_russian_month_name,
    apply_chart_background,
    get_report_param_value,
    apply_default_filters,
    ensure_budget_columns,
    ensure_date_columns,
    style_dataframe_for_dark_theme,
    render_styled_table_to_html,
    budget_table_to_html,
    format_million_rub,
    to_million_rub,
)


def dashboard_deviations_combined(df):
    """Единый отчёт «Динамика отклонений» с табами: по месяцам, динамика, причины."""
    if df is None or not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return
    st.header("📊 Динамика отклонений")
    tab_by_month, tab_dynamics, tab_reasons = st.tabs(
        ["По месяцам", "Динамика отклонений", "Причины отклонений"]
    )
    with tab_by_month:
        dashboard_reasons_of_deviation(df)
    with tab_dynamics:
        dashboard_dynamics_of_deviations(df)
    with tab_reasons:
        dashboard_dynamics_of_reasons(df)


def dashboard_reasons_of_deviation(df):
    # Проверка на None или пустой DataFrame
    if df is None:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    # Проверка, что df является DataFrame и имеет атрибут columns
    if not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    st.header("📋 Динамика отклонений по месяцам")

    # Add CSS to force filters in one row
    st.markdown(
        """
        <style>
        div[data-testid="column"] {
            flex: 1 1 0%;
            min-width: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Helper function to format months
    def format_month(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                month_name = get_russian_month_name(period_val)
                year = period_val.year
                return f"{month_name} {year}"
            except:
                return str(period_val)
        return str(period_val)

    # Все фильтры в один ряд: Проект, Задача, Этап, Причина, Месяц (5 колонок)
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        try:
            has_project_column = "project name" in df.columns
        except (AttributeError, TypeError):
            has_project_column = False

        if has_project_column:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox("Проект", projects, key="reason_project")
        else:
            selected_project = "Все"

    with col2:
        try:
            has_task_column = "task name" in df.columns
        except (AttributeError, TypeError):
            has_task_column = False

        if has_task_column:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox("Задача", tasks, key="reason_task")
        else:
            selected_task = "Все"

    with col3:
        try:
            has_section_column = "section" in df.columns
        except (AttributeError, TypeError):
            has_section_column = False

        if has_section_column:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox("Этап", sections, key="reason_section")
        else:
            selected_section = "Все"

    with col4:
        try:
            has_reason_column = "reason of deviation" in df.columns
        except (AttributeError, TypeError):
            has_reason_column = False

        if has_reason_column:
            reasons = ["Все"] + sorted(
                df["reason of deviation"].dropna().unique().tolist()
            )
            selected_reason = st.selectbox("Причина", reasons, key="reason_filter")
        else:
            selected_reason = "Все"

    with col5:
        available_months = []
        try:
            has_plan_month_column = "plan_month" in df.columns
        except (AttributeError, TypeError):
            has_plan_month_column = False

        if has_plan_month_column:
            unique_months = df["plan_month"].dropna().unique()
            if len(unique_months) > 0:
                month_dict = {format_month(m): m for m in unique_months}
                available_months = sorted(
                    month_dict.keys(), key=lambda x: month_dict[x]
                )
        else:
            try:
                has_plan_end_column = "plan end" in df.columns
            except (AttributeError, TypeError):
                has_plan_end_column = False

            if has_plan_end_column:
                mask = df["plan end"].notna()
                if mask.any():
                    temp_months = df.loc[mask, "plan end"].dt.to_period("M").unique()
                    if len(temp_months) > 0:
                        month_dict = {format_month(m): m for m in temp_months}
                        available_months = sorted(
                            month_dict.keys(), key=lambda x: month_dict[x]
                        )

        if len(available_months) > 0:
            months = ["Все"] + available_months
            selected_month = st.selectbox("Месяц", months, key="reason_month")
        else:
            selected_month = "Все"
            st.selectbox("Месяц", ["Все"], key="reason_month", disabled=True)

    # Apply all filters - fix filtering logic
    filtered_df = df.copy()

    try:
        has_project_col = "project name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_project_col = False

    if selected_project != "Все" and has_project_col:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    try:
        has_reason_col = "reason of deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_reason_col = False

    if selected_reason != "Все" and has_reason_col:
        filtered_df = filtered_df[
            filtered_df["reason of deviation"].astype(str).str.strip()
            == str(selected_reason).strip()
        ]

    try:
        has_task_col = "task name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_task_col = False

    if selected_task != "Все" and has_task_col:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]

    try:
        has_section_col = "section" in filtered_df.columns
    except (AttributeError, TypeError):
        has_section_col = False

    if selected_section != "Все" and has_section_col:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    try:
        has_plan_month_col = "plan_month" in filtered_df.columns
    except (AttributeError, TypeError):
        has_plan_month_col = False

    if selected_month != "Все" and has_plan_month_col:
        # Convert selected month back to Period format for comparison
        def month_to_period(month_str):
            try:
                # Parse "Январь 2025" format (Russian month names)
                parts = month_str.split()
                if len(parts) == 2:
                    month_name, year = parts
                    # Find month number from Russian month name
                    month_num = None
                    for num, russian_name in RUSSIAN_MONTHS.items():
                        if russian_name == month_name:
                            month_num = num
                            break
                    if month_num:
                        return pd.Period(f"{year}-{month_num:02d}", freq="M")
            except:
                pass
            return None

        selected_period = month_to_period(selected_month)
        if selected_period is not None:
            filtered_df = filtered_df[filtered_df["plan_month"] == selected_period]
        else:
            # Fallback: try to match formatted string
            def format_month_for_comparison(period_val):
                if isinstance(period_val, pd.Period):
                    try:
                        month_name = get_russian_month_name(period_val)
                        year = period_val.year
                        return f"{month_name} {year}"
                    except:
                        pass
                return str(period_val)

            filtered_df = filtered_df[
                filtered_df["plan_month"].apply(format_month_for_comparison)
                == selected_month
            ]

    # Filter tasks relevant for "dynamics of deviations": deviation=1/True OR reason of deviation filled
    try:
        has_deviation_col = "deviation" in filtered_df.columns
        has_reason_col = "reason of deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_col = False
        has_reason_col = False

    if has_deviation_col or has_reason_col:
        # Rows with deviation flag = 1/True
        if has_deviation_col:
            deviation_flag = (
                (filtered_df["deviation"] == True)
                | (filtered_df["deviation"] == 1)
                | (filtered_df["deviation"].astype(str).str.lower() == "true")
                | (filtered_df["deviation"].astype(str).str.strip() == "1")
            )
        else:
            deviation_flag = pd.Series(False, index=filtered_df.index)
        # Rows with non-empty reason of deviation (для project_fixed: показываем и при причине)
        if has_reason_col:
            reason_filled = (
                filtered_df["reason of deviation"].notna()
                & (filtered_df["reason of deviation"].astype(str).str.strip() != "")
            )
        else:
            reason_filled = pd.Series(False, index=filtered_df.index)
        filtered_df = filtered_df[deviation_flag | reason_filled]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Summary metrics: всего задач, основная причина отклонения, её процент и количество
    has_reason_col_metric = "reason of deviation" in filtered_df.columns
    main_reason_name = "—"
    main_reason_pct = 0.0
    main_reason_count = 0
    if has_reason_col_metric and not filtered_df.empty:
        reason_counts = filtered_df["reason of deviation"].value_counts()
        if not reason_counts.empty:
            main_reason_name = str(reason_counts.index[0]).strip() or "—"
            main_reason_count = int(reason_counts.iloc[0])
            total_tasks = len(filtered_df)
            main_reason_pct = (main_reason_count / total_tasks * 100) if total_tasks else 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего задач с отклонениями", len(filtered_df))
    with col2:
        st.metric("Основная причина отклонения", main_reason_name[:50] + ("…" if len(main_reason_name) > 50 else ""))
    with col3:
        col3_value = f"{main_reason_pct:.1f}% ({main_reason_count})" if (has_reason_col_metric and main_reason_count > 0) else "—"
        st.metric("Доля основной причины", col3_value)

    # Reasons breakdown
    try:
        has_reason_col_breakdown = "reason of deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_reason_col_breakdown = False

    if has_reason_col_breakdown:
        st.subheader("Распределение по причинам")
        reason_counts = filtered_df["reason of deviation"].value_counts().reset_index()
        reason_counts.columns = ["Причина", "Количество"]

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                reason_counts,
                x="Причина",
                y="Количество",
                title="Количество задач по причинам",
                labels={
                    "Причина": "Причина отклонения",
                    "Количество": "Количество задач",
                },
                text="Количество",
            )
            fig.update_xaxes(tickangle=-45)
            fig.update_traces(
                textposition="outside", textfont=dict(size=14, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                reason_counts,
                values="Количество",
                names="Причина",
                title="Причины отклонений",
            )
            fig.update_traces(
                textinfo="label+value+percent",
                texttemplate="%{label}<br>%{value}<br>(%{percent:.0%})",
                textposition="inside",
                textfont=dict(size=12, color="white"),
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Detailed table — названия колонок на русском, дни: красный если > 0, зелёный если 0
    with st.expander("📊 Просмотр детальных данных"):
        display_cols = [
            "project name",
            "task name",
            "section",
            "deviation in days",
            "reason of deviation",
        ]

        try:
            has_plan_end_col = "plan end" in filtered_df.columns
        except (AttributeError, TypeError):
            has_plan_end_col = False

        if has_plan_end_col:
            display_cols.insert(-1, "plan end")

        try:
            has_base_end_col = "base end" in filtered_df.columns
        except (AttributeError, TypeError):
            has_base_end_col = False

        if has_base_end_col:
            display_cols.insert(-1, "base end")

        available_cols = [col for col in display_cols if col in filtered_df.columns]
        display_df = filtered_df[available_cols].copy()
        # Русские названия колонок
        col_ru = {
            "project name": "Проект",
            "task name": "Задача",
            "section": "Раздел",
            "deviation in days": "Отклонений в днях",
            "reason of deviation": "Причина отклонений",
            "plan end": "Конец плана",
            "base end": "Конец факт",
        }
        display_df = display_df.rename(columns={c: col_ru[c] for c in display_df.columns if c in col_ru})
        if "Отклонений в днях" in display_df.columns:
            display_df["Отклонений в днях"] = display_df["Отклонений в днях"].apply(
                lambda x: int(round(float(x), 0)) if pd.notna(x) and str(x).strip() != "" else x
            )
        def _date_only(val):
            if pd.isna(val):
                return "Н/Д"
            if hasattr(val, "strftime"):
                return val.strftime("%d.%m.%Y")
            try:
                dt = pd.to_datetime(val, errors="coerce", dayfirst=True)
                return dt.strftime("%d.%m.%Y") if pd.notna(dt) else str(val)
            except Exception:
                return str(val)
        for date_col in ("Конец плана", "Конец факт"):
            if date_col in display_df.columns:
                display_df[date_col] = display_df[date_col].apply(_date_only)
        st.table(style_dataframe_for_dark_theme(display_df, days_column="Отклонений в днях"))


# ==================== DASHBOARD 2: Dynamics of Deviations ====================
def dashboard_dynamics_of_deviations(df):
    st.header("📈 Динамика отклонений")

    col1, col2, col3 = st.columns(3)

    with col1:
        period_type = st.selectbox(
            "Группировать по",
            ["День", "Месяц", "Квартал", "Год"],
            key="dynamics_period",
        )
        period_map = {
            "День": "Day",
            "Месяц": "Month",
            "Квартал": "Quarter",
            "Год": "Year",
        }
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="dynamics_project"
            )
        else:
            selected_project = "Все"

    with col3:
        if "reason of deviation" in df.columns:
            reasons = ["Все"] + sorted(
                df["reason of deviation"].dropna().unique().tolist()
            )
            selected_reason = st.selectbox(
                "Фильтр по причине", reasons, key="dynamics_reason"
            )
        else:
            selected_reason = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_reason != "Все" and "reason of deviation" in df.columns:
        filtered_df = filtered_df[
            filtered_df["reason of deviation"].astype(str).str.strip()
            == str(selected_reason).strip()
        ]

    # Filter tasks: deviation=1/True OR reason of deviation filled
    if "deviation" in filtered_df.columns:
        deviation_flag = (
            (filtered_df["deviation"] == True)
            | (filtered_df["deviation"] == 1)
            | (filtered_df["deviation"].astype(str).str.lower() == "true")
            | (filtered_df["deviation"].astype(str).str.strip() == "1")
        )
    else:
        deviation_flag = pd.Series(False, index=filtered_df.index)
    if "reason of deviation" in filtered_df.columns:
        reason_filled = (
            filtered_df["reason of deviation"].notna()
            & (filtered_df["reason of deviation"].astype(str).str.strip() != "")
        )
    else:
        reason_filled = pd.Series(False, index=filtered_df.index)
    filtered_df = filtered_df[deviation_flag | reason_filled]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Extract period from plan end dates
    if period_type_en == "Day":
        # Use date (day level)
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[mask, "plan end"].dt.date
            period_label = "День"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по дням.")
            return
    elif period_type_en == "Month":
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("M")
            period_label = "Месяц"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по месяцам.")
            return
    elif period_type_en == "Quarter":
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Q")
            period_label = "Квартал"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по кварталам.")
            return
    else:  # Year
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Y")
            period_label = "Год"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по годам.")
            return

    # Filter out rows without period data
    filtered_df = filtered_df[filtered_df["period"].notna()]

    if filtered_df.empty:
        st.info("Нет данных с указанными периодами.")
        return

    # Convert deviation in days to numeric
    if "deviation in days" in filtered_df.columns:
        filtered_df["deviation in days"] = pd.to_numeric(
            filtered_df["deviation in days"], errors="coerce"
        )

    # Group by project, period, and reason - count deviation days
    group_cols = ["period"]
    if "project name" in filtered_df.columns:
        group_cols.append("project name")
    if "reason of deviation" in filtered_df.columns:
        group_cols.append("reason of deviation")

    # Aggregate: count tasks and sum deviation days
    # For average: sum deviation days / number of tasks (grouped by project if project is in group)
    agg_dict = {"deviation": "count"}  # Count tasks
    if "deviation in days" in filtered_df.columns:
        agg_dict["deviation in days"] = "sum"  # Sum deviation days

    grouped_data = filtered_df.groupby(group_cols).agg(agg_dict).reset_index()

    # Ensure period column is preserved as Period type if possible
    # After groupby, Period objects might be converted, so we need to handle this
    if "period" in grouped_data.columns:
        # Try to preserve Period type or convert back if needed
        try:
            # Check if period values are still Period objects
            if isinstance(grouped_data["period"].iloc[0], pd.Period):
                # Period objects are preserved, good
                pass
            else:
                # Try to convert back to Period if they're strings
                try:
                    # Try to convert string representations back to Period
                    def try_convert_to_period(val):
                        if isinstance(val, pd.Period):
                            return val
                        if isinstance(val, str) and "-" in val:
                            try:
                                parts = val.split("-")
                                if len(parts) >= 2:
                                    year = int(parts[0])
                                    month = int(parts[1])
                                    return pd.Period(f"{year}-{month:02d}", freq="M")
                            except:
                                pass
                        return val

                    grouped_data["period"] = grouped_data["period"].apply(
                        try_convert_to_period
                    )
                except:
                    pass
        except:
            pass

    # Calculate average: sum of deviation days / number of tasks
    if "deviation in days" in filtered_df.columns:
        # Rename columns
        if "deviation in days" in grouped_data.columns:
            grouped_data = grouped_data.rename(
                columns={
                    "deviation": "Количество задач",
                    "deviation in days": "Всего дней отклонений",
                }
            )
        else:
            grouped_data = grouped_data.rename(
                columns={"deviation": "Количество задач"}
            )
            grouped_data["Всего дней отклонений"] = 0

        # Calculate average: sum / count of tasks
        grouped_data["Среднее дней отклонений"] = (
            grouped_data["Всего дней отклонений"] / grouped_data["Количество задач"]
        ).round(0)
    else:
        grouped_data = grouped_data.rename(columns={"deviation": "Количество задач"})
        grouped_data["Всего дней отклонений"] = 0
        grouped_data["Среднее дней отклонений"] = 0

    # Format period for display - convert to readable format
    def format_period(period_val):
        if pd.isna(period_val):
            return "Н/Д"

        # Try to convert to Period if it's a string representation
        period_obj = None
        if isinstance(period_val, pd.Period):
            period_obj = period_val
        elif isinstance(period_val, str):
            # Try to parse string like "2025-01" or "2025-01-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = int(parts[0])
                        month = int(parts[1])
                        # Try to create Period object
                        try:
                            period_obj = pd.Period(f"{year}-{month:02d}", freq="M")
                        except:
                            # If that fails, try to parse as date and convert
                            try:
                                date_obj = pd.to_datetime(period_val)
                                period_obj = date_obj.to_period("M")
                            except:
                                pass
            except:
                pass

        # If we have a Period object, format it
        if period_obj is not None:
            try:
                if period_obj.freqstr == "M" or period_obj.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_obj)
                    year = period_obj.year
                    if month_name:
                        return f"{month_name} {year}"
                elif period_obj.freqstr == "Q" or period_obj.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_obj.quarter} {period_obj.year}"
                elif period_obj.freqstr == "Y" or period_obj.freqstr == "A-DEC":  # Year
                    return str(period_obj.year)
                else:
                    month_name = get_russian_month_name(period_obj)
                    year = period_obj.year
                    if month_name:
                        return f"{month_name} {year}"
            except:
                pass

        # If it's still a Period object (original), try direct formatting
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    if month_name:
                        return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
            except:
                pass

        # Try parsing as string
        period_str = str(period_val)
        try:
            if "-" in period_str:
                parts = period_str.split("-")
                if len(parts) >= 2:
                    year = parts[0]
                    month = parts[1]
                    # Remove any extra characters
                    month = month.split()[0] if " " in month else month
                    try:
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
                    except:
                        pass
        except:
            pass

        # If it's a date, format it
        try:
            if isinstance(period_val, (pd.Timestamp, datetime)):
                return period_val.strftime("%d.%m.%Y")
        except:
            pass

        return period_str

    grouped_data["period"] = grouped_data["period"].apply(format_period)

    # Visualizations
    if len(group_cols) == 1:  # Only period
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                grouped_data,
                x="period",
                y="Количество задач",
                title=f"Количество задач с отклонениями по {period_label.lower()}",
                labels={"period": period_label, "Количество задач": "Количество задач"},
                text="Количество задач",
            )
            fig.update_xaxes(tickangle=-45)
            fig.update_traces(
                textposition="outside", textfont=dict(size=14, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if grouped_data["Всего дней отклонений"].sum() > 0:
                grouped_data = grouped_data.copy()
                grouped_data["_дни_текст"] = grouped_data["Всего дней отклонений"].apply(
                    lambda x: f"{int(round(x, 0))}" if pd.notna(x) else ""
                )
                fig = px.line(
                    grouped_data,
                    x="period",
                    y="Всего дней отклонений",
                    title=f"Всего дней отклонений по {period_label.lower()}",
                    markers=True,
                    text="_дни_текст",
                )
                fig.update_xaxes(tickangle=-45)
                fig.update_traces(textposition="top center", textfont=dict(color="white"))
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Нет данных по дням отклонений.")
    else:  # Grouped by project and/or reason
        # Show by project if project is in group
        if "project name" in group_cols:
            st.subheader("По проектам")
            # If reason is also in group_cols, aggregate by period and project only (sum across reasons)
            if "reason of deviation" in group_cols:
                project_data = (
                    grouped_data.groupby(["period", "project name"])
                    .agg({"Всего дней отклонений": "sum", "Количество задач": "sum"})
                    .reset_index()
                )
            else:
                project_data = grouped_data

            project_data = project_data.copy()
            project_data["_дни_текст"] = project_data["Всего дней отклонений"].apply(
                lambda x: f"{int(round(x, 0))}" if pd.notna(x) else ""
            )
            fig = px.bar(
                project_data,
                x="period",
                y="Всего дней отклонений",
                color="project name",
                title="Дни отклонений по периоду",
                labels={"period": "", "Всего дней отклонений": "Дни отклонений"},
                text="_дни_текст",
            )
            # Set barmode to 'group' to group bars by period
            fig.update_layout(barmode="group")
            fig.update_xaxes(tickangle=-45, title_text="")
            # Update traces to ensure horizontal text orientation
            fig.update_traces(
                textposition="outside", textfont=dict(size=14, color="white")
            )
            # Explicitly set textangle to 0 for all traces to ensure horizontal text
            # In Plotly, textangle is set per trace
            for i, trace in enumerate(fig.data):
                # Update trace with textangle=0 to ensure horizontal text
                fig.data[i].update(textangle=0)
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

        # Show by reason if reason is in group
        if "reason of deviation" in group_cols:
            st.subheader("По причинам")
            # Агрегируем данные по периоду и причинам (один столбец за месяц с секторами по причинам)
            if "project name" in group_cols:
                # Сначала суммируем по проектам и причинам, затем по периодам
                reason_data = (
                    grouped_data.groupby(["period", "reason of deviation"])
                    .agg({"Всего дней отклонений": "sum", "Количество задач": "sum"})
                    .reset_index()
                )
            else:
                reason_data = grouped_data

            # Вычисляем суммарные значения по каждому периоду для отображения над столбцами
            period_totals = (
                reason_data.groupby("period")["Всего дней отклонений"]
                .sum()
                .reset_index()
            )

            reason_data = reason_data.copy()
            reason_data["_дни_текст"] = reason_data["Всего дней отклонений"].apply(
                lambda x: f"{int(round(x, 0))}" if pd.notna(x) else ""
            )
            fig = px.bar(
                reason_data,
                x="period",
                y="Всего дней отклонений",
                color="reason of deviation",
                title="Дни отклонений по периоду и причинам",
                labels={"period": "", "Всего дней отклонений": "Дни отклонений"},
                text="_дни_текст",
            )
            # Используем накопление (stack) для отображения секторов причин в одном столбце
            fig.update_layout(barmode="stack")
            fig.update_xaxes(tickangle=-45, title_text="")
            # Убираем текст внутри столбцов, так как итоговые значения выводятся над столбцами через аннотации
            fig.update_traces(
                textposition="none", textfont=dict(size=12, color="white")
            )
            # Explicitly set textangle to 0 for all traces to ensure horizontal text
            # In Plotly, textangle is set per trace
            for i, trace in enumerate(fig.data):
                # Update trace with textangle=0 to ensure horizontal text
                fig.data[i].update(textangle=0)

            # Добавляем суммарные значения над столбцами
            annotations = []
            for idx, row in period_totals.iterrows():
                period = row["period"]
                total = row["Всего дней отклонений"]
                # Для положительных значений - над столбцом (от верхней точки)
                # Для отрицательных значений - над столбцом (от верхней точки, которая находится внизу на y=0)
                if total >= 0:
                    # Положительное значение: аннотация над столбцом
                    y_coord = total
                    y_anchor = "bottom"
                    y_shift = (
                        20  # Фиксированное расстояние 20px от верхней точки столбца
                    )
                else:
                    # Отрицательное значение: аннотация над столбцом (который идет вниз)
                    # Верхняя точка отрицательного столбца находится на y=0, нижняя - на y=total
                    y_coord = 0  # Позиционируем относительно верхней точки (y=0)
                    y_anchor = "bottom"
                    y_shift = (
                        20  # Фиксированное расстояние 20px от верхней точки столбца
                    )

                annotations.append(
                    dict(
                        x=period,
                        y=y_coord,
                        text=f"{int(round(total, 0))}",
                        showarrow=False,
                        xanchor="center",
                        yanchor=y_anchor,
                        yshift=y_shift,
                        font=dict(size=14, color="white", weight="bold"),
                    )
                )
            fig.update_layout(annotations=annotations)

            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Summary table
    # If project is in group, show summary grouped by project overall (aggregate across all periods)
    if "project name" in group_cols:
        # Create project-level summary (aggregate across all periods, not by day/period)
        project_summary_cols = ["project name"]
        if "reason of deviation" in group_cols:
            project_summary_cols.append("reason of deviation")

        # Получаем доступные периоды из grouped_data для фильтра
        available_periods = []
        if "period" in grouped_data.columns:
            available_periods = sorted(
                grouped_data["period"].dropna().unique().tolist()
            )

        st.subheader(
            f"Сводная таблица (группировка: {', '.join(project_summary_cols)})"
        )

        # Добавляем селекторы для фильтрации таблицы
        filter_cols = st.columns(3)
        filtered_df_for_summary = filtered_df.copy()

        with filter_cols[0]:
            if "project name" in filtered_df_for_summary.columns:
                available_projects = ["Все"] + sorted(
                    filtered_df_for_summary["project name"].dropna().unique().tolist()
                )
                selected_project_filter = st.selectbox(
                    "Фильтр по проекту",
                    available_projects,
                    key="summary_project_filter",
                )
                if selected_project_filter != "Все":
                    filtered_df_for_summary = filtered_df_for_summary[
                        filtered_df_for_summary["project name"]
                        == selected_project_filter
                    ]

        with filter_cols[1]:
            if "reason of deviation" in filtered_df_for_summary.columns:
                available_reasons = ["Все"] + sorted(
                    filtered_df_for_summary["reason of deviation"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                selected_reason_filter = st.selectbox(
                    "Фильтр по причине отклонения",
                    available_reasons,
                    key="summary_reason_filter",
                )
                if selected_reason_filter != "Все":
                    filtered_df_for_summary = filtered_df_for_summary[
                        filtered_df_for_summary["reason of deviation"]
                        == selected_reason_filter
                    ]

        with filter_cols[2]:
            # Фильтр по периоду
            period_options = ["Весь период"] + available_periods
            selected_period_filter = st.selectbox(
                "Фильтр по периоду", period_options, key="summary_period_filter"
            )

            # Применяем фильтр по периоду
            if (
                selected_period_filter != "Весь период"
                and "period" in filtered_df_for_summary.columns
            ):
                # Фильтруем по отформатированному периоду
                if "plan end" in filtered_df_for_summary.columns:
                    # Создаем временную колонку с отформатированными периодами для фильтрации
                    filtered_df_for_summary = filtered_df_for_summary.copy()
                    mask = filtered_df_for_summary["plan end"].notna()
                    if period_type_en == "Month":
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.to_period(
                                "M"
                            )
                        )
                    elif period_type_en == "Quarter":
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.to_period(
                                "Q"
                            )
                        )
                    elif period_type_en == "Year":
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.to_period(
                                "Y"
                            )
                        )
                    else:
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.date
                        )

                    # Форматируем периоды для сравнения
                    filtered_df_for_summary.loc[mask, "temp_period_formatted"] = (
                        filtered_df_for_summary.loc[mask, "temp_period"].apply(
                            format_period
                        )
                    )
                    # Фильтруем по выбранному периоду
                    period_mask = (
                        filtered_df_for_summary["temp_period_formatted"]
                        == selected_period_filter
                    )
                    filtered_df_for_summary = filtered_df_for_summary[period_mask]
                    # Удаляем временные колонки
                    filtered_df_for_summary = filtered_df_for_summary.drop(
                        columns=["temp_period", "temp_period_formatted"],
                        errors="ignore",
                    )

        # Aggregate by project (and reason if present) - sum across selected periods
        project_summary = (
            filtered_df_for_summary.groupby(project_summary_cols)
            .agg(
                {
                    "deviation": "count",  # Count tasks
                    "deviation in days": (
                        "sum"
                        if "deviation in days" in filtered_df_for_summary.columns
                        else "count"
                    ),
                }
            )
            .reset_index()
        )

        # Rename columns
        period_col_name = (
            f"Дни отклонений ({selected_period_filter})"
            if selected_period_filter != "Весь период"
            else "Всего дней отклонений"
        )
        col_ru_summary = {
            "deviation": "Количество отклонений",
            "deviation in days": period_col_name,
            "project name": "Проект",
            "reason of deviation": "Причина отклонений",
        }
        project_summary = project_summary.rename(
            columns={c: col_ru_summary[c] for c in project_summary.columns if c in col_ru_summary}
        )

        # Если нет данных по дням отклонений, добавляем нулевую колонку
        if period_col_name not in project_summary.columns:
            project_summary[period_col_name] = 0

        # Sort by total deviation days (descending)
        if period_col_name in project_summary.columns:
            project_summary = project_summary.sort_values(
                period_col_name, ascending=False
            )

        # Строка "Итого": для колонок группировки (после переименования — Проект, Причина отклонений)
        total_row = {}
        for col in project_summary.columns:
            if col in ("Проект", "Причина отклонений"):
                total_row[col] = "Итого"
            elif col == "Количество отклонений":
                total_row[col] = round(project_summary[col].sum(), 0)
            elif col == period_col_name:
                total_row[col] = round(project_summary[col].sum(), 0)
            else:
                total_row[col] = ""

        # Создаем DataFrame для строки "Итого"
        total_df = pd.DataFrame([total_row])
        # Объединяем с основным DataFrame
        project_summary = pd.concat([project_summary, total_df], ignore_index=True)

        # Отображение дней целыми числами (без дробной части)
        if period_col_name in project_summary.columns:
            def _fmt_days(x):
                if pd.isna(x): return x
                if str(x).strip() == "Итого": return x
                try: return round(float(x), 0)
                except (TypeError, ValueError): return x
            project_summary[period_col_name] = project_summary[period_col_name].apply(_fmt_days)

        st.table(style_dataframe_for_dark_theme(project_summary))
    else:
        # No project in group, show regular summary by period (только количество, без дней)
        group_desc = [period_label] + [c for c in group_cols if c != "period"]
        st.subheader(f"Сводная таблица (группировка: {', '.join(group_desc)})")
        table_cols = ["period", "Количество задач"]
        table_cols.extend([c for c in grouped_data.columns if c not in ("period", "Количество задач", "Всего дней отклонений", "Среднее дней отклонений")])
        display_grouped = grouped_data[[c for c in table_cols if c in grouped_data.columns]].copy()
        display_grouped = display_grouped.rename(columns={
            "period": "Период",
            "project name": "Проект",
            "reason of deviation": "Причина отклонений",
        })
        st.table(style_dataframe_for_dark_theme(display_grouped))


# ==================== DASHBOARD 3: Plan/Fact Dates for Tasks ====================
def dashboard_plan_fact_dates(df):
    st.header("📅 Отклонение текущего срока от базового плана")

    # Helper function to find columns by partial match
    def find_column(df, possible_names):
        """Find column by possible names"""
        for col in df.columns:
            # Normalize column name: remove newlines, extra spaces, normalize case
            col_normalized = str(col).replace("\n", " ").replace("\r", " ").strip()
            col_lower = col_normalized.lower()

            for name in possible_names:
                name_lower = name.lower().strip()
                # Exact match (case insensitive)
                if name_lower == col_lower:
                    return col
                # Substring match
                if name_lower in col_lower or col_lower in name_lower:
                    return col
                # Check if all key words from name are in column
                name_words = [w for w in name_lower.split() if len(w) > 2]
                if name_words and all(word in col_lower for word in name_words):
                    return col
        return None

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="dates_project"
            )
        else:
            selected_project = "Все"

    with col2:
        if "task name" in df.columns:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox("Фильтр по лоту", tasks, key="dates_task")
        else:
            selected_task = "Все"

    with col3:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="dates_section"
            )
        else:
            selected_section = "Все"

    with col4:
        pass

    # Apply filters - fix filtering
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_task != "Все" and "task name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    ensure_date_columns(filtered_df)
    # Prepare data for visualization - compare plan and fact dates
    # First, ensure all dates are datetime objects
    date_cols = ["plan start", "plan end", "base start", "base end"]
    for col in date_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_datetime(
                filtered_df[col], errors="coerce", dayfirst=True
            )

    missing_date_cols = [col for col in date_cols if col not in filtered_df.columns]
    if missing_date_cols:
        st.warning(f"Отсутствуют необходимые колонки с датами: {', '.join(missing_date_cols)}")
        return

    # Filter to rows that have at least plan OR fact dates (not necessarily both)
    has_plan_dates = filtered_df["plan start"].notna() & filtered_df["plan end"].notna()
    has_fact_dates = filtered_df["base start"].notna() & filtered_df["base end"].notna()
    has_any_dates = has_plan_dates | has_fact_dates
    filtered_df = filtered_df[has_any_dates]

    if filtered_df.empty:
        st.info("Нет задач с плановыми или фактическими датами для выбранных фильтров.")
        return

    # Calculate date differences for tasks that have both plan and fact
    filtered_df["plan_start_diff"] = None
    filtered_df["plan_end_diff"] = None
    filtered_df["total_diff_days"] = 0

    both_dates_mask = has_plan_dates & has_fact_dates
    if both_dates_mask.any():
        # Дни с дробной частью (total_seconds / 86400)
        filtered_df.loc[both_dates_mask, "plan_start_diff"] = (
            filtered_df.loc[both_dates_mask, "base start"]
            - filtered_df.loc[both_dates_mask, "plan start"]
        ).dt.total_seconds() / 86400
        filtered_df.loc[both_dates_mask, "plan_end_diff"] = (
            filtered_df.loc[both_dates_mask, "base end"]
            - filtered_df.loc[both_dates_mask, "plan end"]
        ).dt.total_seconds() / 86400
        filtered_df.loc[both_dates_mask, "total_diff_days"] = filtered_df.loc[
            both_dates_mask, "plan_end_diff"
        ].abs()

    # Sort by task name (alphabetically) for consistent display
    filtered_df = filtered_df.sort_values("task name", ascending=True)

    plan_start_col = "plan start" if "plan start" in filtered_df.columns else find_column(filtered_df, ["Старт План", "План Старт"])
    plan_end_col = "plan end" if "plan end" in filtered_df.columns else find_column(filtered_df, ["Конец План", "План Конец"])
    base_start_col = "base start" if "base start" in filtered_df.columns else find_column(filtered_df, ["Старт Факт", "Факт Старт"])
    base_end_col = "base end" if "base end" in filtered_df.columns else find_column(filtered_df, ["Конец Факт", "Факт Конец"])
    if not all([plan_start_col, plan_end_col, base_start_col, base_end_col]):
        st.warning("Не найдены колонки с датами (план/факт).")
        return

    # Prepare data for Gantt chart - compare plan vs fact
    viz_data = []
    for idx, row in filtered_df.iterrows():
        task_name = row.get("task name", "Неизвестно")
        project_name = row.get("project name", "Неизвестно")

        plan_start = row.get(plan_start_col)
        plan_end = row.get(plan_end_col)
        base_start = row.get(base_start_col)
        base_end = row.get(base_end_col)
        diff_days = row.get("total_diff_days", 0)

        # Add plan dates
        if pd.notna(plan_start) and pd.notna(plan_end):
            viz_data.append(
                {
                    "Task": f"{task_name} ({project_name})",
                    "Task_Original": task_name,
                    "Project": project_name,
                    "Start": plan_start,
                    "End": plan_end,
                    "Type": "План",
                    "Duration": (plan_end - plan_start).total_seconds() / 86400,
                    "Diff_Days": diff_days,
                }
            )

        # Add fact dates
        if pd.notna(base_start) and pd.notna(base_end):
            viz_data.append(
                {
                    "Task": f"{task_name} ({project_name})",
                    "Task_Original": task_name,
                    "Project": project_name,
                    "Start": base_start,
                    "End": base_end,
                    "Type": "Факт",
                    "Duration": (base_end - base_start).total_seconds() / 86400,
                    "Diff_Days": diff_days,
                }
            )

    if not viz_data:
        st.info("Нет валидных данных по датам.")
        return

    viz_df = pd.DataFrame(viz_data)

    # Sort tasks by difference (largest first) - maintain order from filtered_df
    task_order = filtered_df.sort_values("total_diff_days", ascending=False)[
        "task name"
    ].tolist()
    # Create a mapping for sorting
    task_order_map = {task: idx for idx, task in enumerate(task_order)}
    viz_df["sort_order"] = viz_df["Task_Original"].map(task_order_map).fillna(999)
    viz_df = viz_df.sort_values("sort_order")

    # Gantt chart - use proper timeline visualization with plotly express
    # Get unique tasks in sorted order (by task name)
    unique_tasks = filtered_df["task name"].unique().tolist()

    # Prepare data for bar chart - plan and fact side by side for each task
    # If "Все" projects selected, show all tasks from all projects
    bar_data = []
    for task_name in unique_tasks:
        task_rows = filtered_df[filtered_df["task name"] == task_name]
        if task_rows.empty:
            continue

        # If "Все" projects, show each task for each project separately
        if selected_project == "Все":
            for _, row in task_rows.iterrows():
                project_name = row.get("project name", "Неизвестно")
                display_name = f"{task_name} ({project_name})"
                diff_days = row.get("total_diff_days", 0)

                plan_start = row.get("plan start")
                plan_end = row.get("plan end")
                base_start = row.get("base start")
                base_end = row.get("base end")

                # Этап (section) для оси X
                section_name = row.get("section", "—")
                if pd.isna(section_name) or str(section_name).strip() == "":
                    section_name = "—"

                # Add plan entry
                if pd.notna(plan_start) and pd.notna(plan_end):
                    bar_data.append(
                        {
                            "Задача": display_name,
                            "Этап": section_name,
                            "Тип": "План",
                            "Дата начала": plan_start,
                            "Дата окончания": plan_end,
                            "Длительность": (plan_end - plan_start).total_seconds() / 86400,
                            "Отклонение": diff_days,
                        }
                    )

                # Add fact entry
                if pd.notna(base_start) and pd.notna(base_end):
                    bar_data.append(
                        {
                            "Задача": display_name,
                            "Этап": section_name,
                            "Тип": "Факт",
                            "Дата начала": base_start,
                            "Дата окончания": base_end,
                            "Длительность": (base_end - base_start).total_seconds() / 86400,
                            "Отклонение": diff_days,
                        }
                    )
        else:
            # If specific project selected, show only that project's tasks
            row = task_rows.iloc[0]
            project_name = row.get("project name", "Неизвестно")
            display_name = f"{task_name} ({project_name})"
            diff_days = row.get("total_diff_days", 0)
            section_name = row.get("section", "—")
            if pd.isna(section_name) or str(section_name).strip() == "":
                section_name = "—"

            plan_start = row.get("plan start")
            plan_end = row.get("plan end")
            base_start = row.get("base start")
            base_end = row.get("base end")

            # Add plan entry
            if pd.notna(plan_start) and pd.notna(plan_end):
                bar_data.append(
                    {
                        "Задача": display_name,
                        "Этап": section_name,
                        "Тип": "План",
                        "Дата начала": plan_start,
                        "Дата окончания": plan_end,
                        "Длительность": (plan_end - plan_start).total_seconds() / 86400,
                        "Отклонение": diff_days,
                    }
                )

            # Add fact entry
            if pd.notna(base_start) and pd.notna(base_end):
                bar_data.append(
                    {
                        "Задача": display_name,
                        "Этап": section_name,
                        "Тип": "Факт",
                        "Дата начала": base_start,
                        "Дата окончания": base_end,
                        "Длительность": (base_end - base_start).total_seconds() / 86400,
                        "Отклонение": diff_days,
                    }
                )

    bar_df = pd.DataFrame(bar_data)

    if bar_df.empty:
        st.info("Нет данных для отображения графика.")
    else:
        # График по этапам: ось X = этап, ось Y = отклонение (дней)
        if "Этап" in bar_df.columns:
            section_dev = (
                bar_df.drop_duplicates(subset=["Задача"])[["Этап", "Отклонение"]]
                .groupby("Этап", as_index=False)["Отклонение"]
                .max()
            )
            if not section_dev.empty:
                fig_section = go.Figure()
                fig_section.add_trace(
                    go.Bar(
                        x=section_dev["Этап"],
                        y=section_dev["Отклонение"],
                        text=section_dev["Отклонение"].apply(
                            lambda v: f"{int(round(v, 0))}" if pd.notna(v) else ""
                        ),
                        textposition="inside",
                        textfont=dict(size=12, color="white"),
                        marker_color="#2E86AB",
                        name="Отклонение (дней)",
                    )
                )
                fig_section.update_layout(
                    title="Отклонение текущего срока от базового плана по этапам",
                    xaxis_title="Этап",
                    yaxis_title="Отклонение (дней)",
                    height=max(400, len(section_dev) * 50),
                    showlegend=False,
                )
                fig_section = apply_chart_background(fig_section)
                st.plotly_chart(fig_section, use_container_width=True)

        # Checkbox to show/hide completion percentage
        show_completion = st.checkbox(
            "Показать процент выполнения",
            value=False,
            key="show_completion_percent_dates",
        )

        # Calculate completion percentage if needed
        if show_completion:
            # Calculate completion percentage for each task
            for idx, row in bar_df.iterrows():
                if row["Тип"] == "План" and row["Длительность"] > 0:
                    # Find corresponding fact entry
                    fact_row = bar_df[
                        (bar_df["Задача"] == row["Задача"]) & (bar_df["Тип"] == "Факт")
                    ]
                    if not fact_row.empty:
                        fact_duration = fact_row.iloc[0]["Длительность"]
                        plan_duration = row["Длительность"]
                        if plan_duration > 0:
                            # Percentage = (fact / plan) * 100
                            completion_pct = (fact_duration / plan_duration) * 100
                            completion_pct_str = f"{completion_pct:.1f}%"
                            bar_df.loc[idx, "Процент выполнения"] = completion_pct_str
                            # Также сохраняем процент для соответствующей фактической записи
                            fact_idx = fact_row.index[0]
                            bar_df.loc[fact_idx, "Процент выполнения"] = (
                                completion_pct_str
                            )
                        else:
                            bar_df.loc[idx, "Процент выполнения"] = "Н/Д"
                    else:
                        bar_df.loc[idx, "Процент выполнения"] = "Н/Д"
                elif (
                    row["Тип"] == "Факт" and "Процент выполнения" not in bar_df.columns
                ):
                    bar_df.loc[idx, "Процент выполнения"] = ""

        # Sort tasks by start date (earliest first)
        if not bar_df.empty:
            # Get unique tasks and sort by earliest start date
            task_start_dates = (
                bar_df.groupby("Задача")["Дата начала"].min().sort_values()
            )
            task_order = {task: idx for idx, task in enumerate(task_start_dates.index)}
            bar_df["sort_order"] = bar_df["Задача"].map(task_order)
            bar_df = bar_df.sort_values(["sort_order", "Тип"], ascending=[True, True])
            bar_df = bar_df.drop("sort_order", axis=1)
            bar_df = bar_df.reset_index(drop=True)

        # График «План/факт по этапам»: ось Y — названия этапов и задача (без План/Факт в подписи)
        plan_df = bar_df[bar_df["Тип"] == "План"].copy()
        fact_df = bar_df[bar_df["Тип"] == "Факт"].copy()
        def _y_label(row):
            stage = row.get("Этап", "—")
            if pd.isna(stage) or str(stage).strip() == "":
                stage = "—"
            return f"{stage} — {row['Задача']}"

        # По оси Y только этап и задача (названия этапов); План и Факт — два столбца в одной строке
        plan_df["_y"] = plan_df.apply(_y_label, axis=1)
        fact_df["_y"] = fact_df.apply(_y_label, axis=1)
        all_y = list(plan_df["_y"].dropna().unique()) + list(fact_df["_y"].dropna().unique())
        seen = set()
        unique_tasks_sorted = []
        for y in all_y:
            if y not in seen:
                seen.add(y)
                unique_tasks_sorted.append(y)
        def _sort_key(s):
            parts = s.split(" — ", 2)
            stage = parts[0] if len(parts) > 0 else ""
            task = parts[1] if len(parts) > 1 else ""
            return (stage, task)
        unique_tasks_sorted = sorted(unique_tasks_sorted, key=_sort_key)

        fig_gantt = go.Figure()

        # План — отдельный столбец; при «Показать процент выполнения» показываем только Факт
        if not show_completion and not plan_df.empty:
            plan_tasks = []
            plan_starts = []
            plan_ends = []
            plan_texts = []
            for idx, row in plan_df.iterrows():
                start_date = row["Дата начала"]
                end_date = row["Дата окончания"]
                if pd.notna(start_date) and pd.notna(end_date):
                    plan_tasks.append(row["_y"])
                    plan_starts.append(start_date)
                    plan_ends.append(end_date)
                    plan_texts.append(end_date.strftime("%d.%m.%Y"))
            if plan_tasks:
                fig_gantt.add_trace(
                    go.Bar(
                        x=plan_ends,
                        base=plan_starts,
                        y=plan_tasks,
                        orientation="h",
                        name="План",
                        marker_color="#2E86AB",
                        text=plan_texts,
                        textposition="outside",
                        textfont=dict(size=11, color="white"),
                        hovertemplate="<b>%{y}</b><br>Начало: %{base|%d.%m.%Y}<br>Окончание: %{x|%d.%m.%Y}<br><extra></extra>",
                    )
                )

        if not fact_df.empty:
            fact_tasks = []
            fact_starts = []
            fact_ends = []
            fact_texts = []
            for idx, row in fact_df.iterrows():
                start_date = row["Дата начала"]
                end_date = row["Дата окончания"]
                if pd.notna(start_date) and pd.notna(end_date):
                    fact_tasks.append(row["_y"])
                    fact_starts.append(start_date)
                    fact_ends.append(end_date)
                    end_date_str = end_date.strftime("%d.%m.%Y")
                    if show_completion and "Процент выполнения" in row and pd.notna(row.get("Процент выполнения")) and row["Процент выполнения"] != "":
                        fact_texts.append(f"{end_date_str} ({row['Процент выполнения']})")
                    else:
                        fact_texts.append(end_date_str)
            if fact_tasks:
                fig_gantt.add_trace(
                    go.Bar(
                        x=fact_ends,
                        base=fact_starts,
                        y=fact_tasks,
                        orientation="h",
                        name="Факт",
                        marker_color="#FF6347",
                        text=fact_texts,
                        textposition="outside",
                        textfont=dict(size=11, color="white"),
                        hovertemplate="<b>%{y}</b><br>Начало: %{base|%d.%m.%Y}<br>Окончание: %{x|%d.%m.%Y}<br><extra></extra>",
                    )
                )

        fig_gantt.update_layout(
            title="План/факт по этапам",
            xaxis_title="Дата",
            yaxis_title="Этапы",
            height=max(600, len(unique_tasks_sorted) * 45),
            barmode="group",  # План и Факт — два столбца в одной строке (название этапа — задача)
            hovermode="closest",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(type="date", tickformat="%d.%m.%Y"),
            yaxis=dict(categoryorder="array", categoryarray=list(reversed(unique_tasks_sorted))),
        )
        fig_gantt = apply_chart_background(fig_gantt)
        st.plotly_chart(fig_gantt, use_container_width=True)

    # Форматирование даты для отображения
    def format_date_display(date_val):
        if pd.isna(date_val):
            return "Н/Д"
        if isinstance(date_val, pd.Timestamp):
            return date_val.strftime("%d.%m.%Y")
        try:
            dt = pd.to_datetime(date_val, errors="coerce", dayfirst=True)
            if pd.notna(dt):
                return dt.strftime("%d.%m.%Y")
        except:
            pass
        return str(date_val) if date_val else "Н/Д"

    # Селектор задачи для метрик окончания проекта (только при выборе конкретного проекта)
    selected_task_for_metrics = None
    if (
        selected_project != "Все"
        and "task name" in df.columns
        and "project name" in df.columns
    ):
        # Получаем список задач выбранного проекта
        project_tasks = df[
            df["project name"].astype(str).str.strip() == str(selected_project).strip()
        ]
        if not project_tasks.empty:
            available_tasks = sorted(
                project_tasks["task name"].dropna().unique().tolist()
            )
            if available_tasks:
                # По умолчанию используем "Разрешение на ввод в эксплуатацию", если она есть
                default_task = (
                    "Разрешение на ввод в эксплуатацию"
                    if "Разрешение на ввод в эксплуатацию" in available_tasks
                    else available_tasks[0]
                )
                selected_task_for_metrics = st.selectbox(
                    "Задача для расчета окончания проекта",
                    available_tasks,
                    index=(
                        available_tasks.index(default_task)
                        if default_task in available_tasks
                        else 0
                    ),
                    key="task_for_project_end_metrics",
                )

    # Найти задачу для метрик (либо выбранную через селектор, либо "Разрешение на ввод в эксплуатацию" по умолчанию)
    task_name_to_find = (
        selected_task_for_metrics
        if selected_task_for_metrics
        else "Разрешение на ввод в эксплуатацию"
    )
    task_row = None

    if "task name" in df.columns:
        # Ищем задачу в исходных данных (не в отфильтрованных)
        task_mask = df["task name"].astype(str).str.strip() == task_name_to_find.strip()
        if task_mask.any():
            # Если выбран конкретный проект, ищем задачу только в этом проекте
            if selected_project != "Все" and "project name" in df.columns:
                project_mask = (
                    df["project name"].astype(str).str.strip()
                    == str(selected_project).strip()
                )
                task_row = df[task_mask & project_mask]
                if not task_row.empty:
                    task_row = task_row.iloc[0]
            else:
                task_row = df[task_mask].iloc[0]

    # Add comparison metrics
    col1, col2, col3 = st.columns(3)

    # Максимальное отклонение (дней) - отклонение факта от плана для выбранной задачи
    with col1:
        if task_row is not None:
            # Преобразуем даты в datetime если нужно
            plan_end = task_row.get("plan end")
            base_end = task_row.get("base end")

            if pd.notna(plan_end):
                plan_end = pd.to_datetime(plan_end, errors="coerce", dayfirst=True)
            if pd.notna(base_end):
                base_end = pd.to_datetime(base_end, errors="coerce", dayfirst=True)

            if pd.notna(plan_end) and pd.notna(base_end):
                deviation_days = (base_end - plan_end).total_seconds() / 86400
                deviation_str = f"{int(round(deviation_days, 0))}"

                # Цвет: отрицательное = зеленый, положительное = красный
                # Используем delta_color="inverse": отрицательные значения = зеленый, положительные = красный
                st.metric(
                    "Максимальное отклонение (дней)",
                    deviation_str,
                    delta=f"{int(round(deviation_days, 0))}",
                    delta_color="inverse",
                )
            else:
                st.metric("Максимальное отклонение (дней)", "Н/Д")
        else:
            st.metric("Максимальное отклонение (дней)", "Н/Д")

    # План окончания проекта - дата из задачи "Разрешение на ввод в эксплуатацию"
    with col2:
        if task_row is not None:
            plan_end = task_row.get("plan end")
            if pd.notna(plan_end):
                plan_end = pd.to_datetime(plan_end, errors="coerce", dayfirst=True)
                plan_end_str = format_date_display(plan_end)
            else:
                plan_end_str = "Н/Д"
            st.metric("План окончания проекта", plan_end_str)
        else:
            st.metric("План окончания проекта", "Н/Д")

    # Факт окончания проекта - дата из задачи "Разрешение на ввод в эксплуатацию"
    with col3:
        if task_row is not None:
            base_end = task_row.get("base end")
            if pd.notna(base_end):
                base_end = pd.to_datetime(base_end, errors="coerce", dayfirst=True)
                fact_end_str = format_date_display(base_end)
            else:
                fact_end_str = "Н/Д"
            st.metric("Факт окончания проекта", fact_end_str)
        else:
            st.metric("Факт окончания проекта", "Н/Д")

    # Добавляем разделитель и аналогичные метрики для задачи "Разрешение на строительство"
    st.markdown("---")
    col1_construction, col2_construction, col3_construction = st.columns(3)

    # Найти задачу "Разрешение на строительство"
    task_name_construction = "Разрешение на строительство"
    task_row_construction = None

    if "task name" in df.columns:
        # Ищем задачу в исходных данных (не в отфильтрованных)
        task_mask_construction = (
            df["task name"].astype(str).str.strip() == task_name_construction.strip()
        )
        if task_mask_construction.any():
            task_row_construction = df[task_mask_construction].iloc[0]

    # Максимальное отклонение (дней) - отклонение факта от плана для задачи "Разрешение на строительство"
    with col1_construction:
        if task_row_construction is not None:
            # Преобразуем даты в datetime если нужно
            plan_end_construction = task_row_construction.get("plan end")
            base_end_construction = task_row_construction.get("base end")

            if pd.notna(plan_end_construction):
                plan_end_construction = pd.to_datetime(
                    plan_end_construction, errors="coerce", dayfirst=True
                )
            if pd.notna(base_end_construction):
                base_end_construction = pd.to_datetime(
                    base_end_construction, errors="coerce", dayfirst=True
                )

            if pd.notna(plan_end_construction) and pd.notna(base_end_construction):
                deviation_days_construction = (
                    base_end_construction - plan_end_construction
                ).total_seconds() / 86400
                deviation_str_construction = f"{int(round(deviation_days_construction, 0))}"

                # Цвет: отрицательное = зеленый, положительное = красный
                # Используем delta_color="inverse": отрицательные значения = зеленый, положительные = красный
                st.metric(
                    "Максимальное отклонение (дней)",
                    deviation_str_construction,
                    delta=f"{int(round(deviation_days_construction, 0))}",
                    delta_color="inverse",
                )
            else:
                st.metric("Максимальное отклонение (дней)", "Н/Д")
        else:
            st.metric("Максимальное отклонение (дней)", "Н/Д")

    # План окончания проекта - дата из задачи "Разрешение на строительство"
    with col2_construction:
        if task_row_construction is not None:
            plan_end_construction = task_row_construction.get("plan end")
            if pd.notna(plan_end_construction):
                plan_end_construction = pd.to_datetime(
                    plan_end_construction, errors="coerce", dayfirst=True
                )
                plan_end_str_construction = format_date_display(plan_end_construction)
            else:
                plan_end_str_construction = "Н/Д"
            st.metric("План окончания проекта", plan_end_str_construction)
        else:
            st.metric("План окончания проекта", "Н/Д")

    # Факт окончания проекта - дата из задачи "Разрешение на строительство"
    with col3_construction:
        if task_row_construction is not None:
            base_end_construction = task_row_construction.get("base end")
            if pd.notna(base_end_construction):
                base_end_construction = pd.to_datetime(
                    base_end_construction, errors="coerce", dayfirst=True
                )
                fact_end_str_construction = format_date_display(base_end_construction)
            else:
                fact_end_str_construction = "Н/Д"
            st.metric("Факт окончания проекта", fact_end_str_construction)
        else:
            st.metric("Факт окончания проекта", "Н/Д")

    # Summary table - format dates properly, sorted by difference
    summary_data = []
    for idx, row in filtered_df.iterrows():
        plan_start = row.get("plan start", pd.NaT)
        plan_end = row.get("plan end", pd.NaT)
        base_start = row.get("base start", pd.NaT)
        base_end = row.get("base end", pd.NaT)
        diff_days = row.get("total_diff_days", 0)
        start_diff = row.get("plan_start_diff", 0)
        end_diff = row.get("plan_end_diff", 0)

        # Format dates for display
        def format_date(date_val):
            if pd.isna(date_val):
                return "Н/Д"
            if isinstance(date_val, pd.Timestamp):
                return date_val.strftime("%d.%m.%Y")
            try:
                dt = pd.to_datetime(date_val, errors="coerce", dayfirst=True)
                if pd.notna(dt):
                    return dt.strftime("%d.%m.%Y")
            except:
                pass
            return str(date_val) if date_val else "Н/Д"

        summary_data.append(
            {
                "Проект": row.get("project name", "Н/Д"),
                "Задача": row.get("task name", "Н/Д"),
                "Раздел": row.get("section", "Н/Д"),
                "План Начало": format_date(plan_start),
                "План Конец": format_date(plan_end),
                "Факт Начало": format_date(base_start),
                "Факт Конец": format_date(base_end),
                "Отклонение начала (дней)": start_diff,
                "Отклонение конца (дней)": end_diff,
            }
        )

    summary_df = pd.DataFrame(summary_data)
    # Convert 'Отклонение конца (дней)' to numeric for proper sorting
    summary_df["Отклонение конца (дней)"] = pd.to_numeric(
        summary_df["Отклонение конца (дней)"], errors="coerce"
    )
    summary_df["Отклонение начала (дней)"] = pd.to_numeric(
        summary_df["Отклонение начала (дней)"], errors="coerce"
    )

    # If "Все" projects selected, add summary column with totals per task
    if selected_project == "Все" and "Задача" in summary_df.columns:
        # Calculate totals per task
        task_totals = (
            summary_df.groupby("Задача")
            .agg({"Отклонение начала (дней)": "sum", "Отклонение конца (дней)": "sum"})
            .reset_index()
        )
        task_totals.columns = [
            "Задача",
            "Сумма отклонения начала (дней)",
            "Сумма отклонения конца (дней)",
        ]

        # Calculate total deviation per task (sum of start and end deviations)
        task_totals["Суммарное отклонение (дней)"] = task_totals[
            "Сумма отклонения начала (дней)"
        ].fillna(0) + task_totals["Сумма отклонения конца (дней)"].fillna(0)

        # Merge totals back to summary_df
        summary_df = summary_df.merge(task_totals, on="Задача", how="left")

        # Reorder columns to put summary columns after deviation columns
        cols = summary_df.columns.tolist()
        # Remove summary columns from their current position
        cols.remove("Сумма отклонения начала (дней)")
        cols.remove("Сумма отклонения конца (дней)")
        cols.remove("Суммарное отклонение (дней)")
        # Add them after deviation columns
        start_idx = cols.index("Отклонение начала (дней)")
        end_idx = cols.index("Отклонение конца (дней)")
        cols.insert(end_idx + 1, "Сумма отклонения начала (дней)")
        cols.insert(end_idx + 2, "Сумма отклонения конца (дней)")
        cols.insert(end_idx + 3, "Суммарное отклонение (дней)")
        summary_df = summary_df[cols]

    # Sort by end date difference (largest first, descending order)
    # Handle NaN values by placing them at the end
    summary_df = summary_df.sort_values(
        "Отклонение конца (дней)", ascending=False, na_position="last"
    )
    # Отображение дней целыми числами (без дробной части)
    for col in ["Отклонение начала (дней)", "Отклонение конца (дней)"]:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].apply(
                lambda x: round(float(x), 0) if pd.notna(x) and str(x).strip() != "" else x
            )
    for col in ["Сумма отклонения начала (дней)", "Сумма отклонения конца (дней)", "Суммарное отклонение (дней)"]:
        if col in summary_df.columns:
            summary_df[col] = summary_df[col].apply(
                lambda x: round(float(x), 0) if pd.notna(x) and str(x).strip() != "" else x
            )
    st.subheader("Детальные даты задач")
    st.table(style_dataframe_for_dark_theme(summary_df))


# ==================== DASHBOARD 4: Deviation Amount by Tasks ====================
def dashboard_deviation_by_tasks_current_month(df):
    # Проверка на None или пустой DataFrame
    if df is None:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    # Проверка, что df является DataFrame и имеет атрибут columns
    if not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    st.header("📊 Значения отклонений от базового плана")
    
    # Helper function to find columns by partial match
    def find_column(df, possible_names):
        """Find column by possible names"""
        for col in df.columns:
            # Normalize column name: remove newlines, extra spaces, normalize case
            col_normalized = str(col).replace("\n", " ").replace("\r", " ").strip()
            col_lower = col_normalized.lower()

            for name in possible_names:
                name_lower = name.lower().strip()
                # Exact match (case insensitive)
                if name_lower == col_lower:
                    return col
                # Substring match
                if name_lower in col_lower or col_lower in name_lower:
                    return col
                # Check if all key words from name are in column
                name_words = [w for w in name_lower.split() if len(w) > 2]
                if name_words and all(word in col_lower for word in name_words):
                    return col
        return None

    # Start with full dataset (all periods, not just current month)
    filtered_df = df.copy()

    # Filters row 1: Project, Task, Section, Block
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Project filter - show all projects from full dataset
        selected_project = "Все"  # Initialize default value
        # Find project column
        project_col = (
            "project name"
            if "project name" in df.columns
            else find_column(df, ["Проект", "project"])
        )
        
        if project_col:
            # Get all unique projects from the full dataset
            all_projects = sorted(df[project_col].dropna().unique().tolist())
            if all_projects:
                projects = ["Все"] + all_projects
                selected_project = st.selectbox(
                    "Фильтр по проекту", projects, key="deviation_tasks_project"
                )
            else:
                st.warning("Проекты не найдены в данных.")
                return
        else:
            st.warning("Поле 'project name' / 'Проект' не найдено в данных.")
            return

    with col2:
        # Task filter - use original df to show all available tasks
        try:
            has_task_column = "task name" in df.columns
        except (AttributeError, TypeError):
            has_task_column = False

        if has_task_column:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox(
                "Фильтр по лоту", tasks, key="deviation_tasks_task"
            )
        else:
            selected_task = "Все"

    with col3:
        # Section filter - use original df to show all available sections
        try:
            has_section_column = "section" in df.columns
        except (AttributeError, TypeError):
            has_section_column = False

        if has_section_column:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="deviation_tasks_section"
            )
        else:
            selected_section = "Все"

    with col4:
        pass

    # Apply project filter
    if selected_project != "Все" and project_col and project_col in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df[project_col].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    # Apply task and section filters
    try:
        has_task_col = "task name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_task_col = False

    if selected_task != "Все" and has_task_col:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]

    try:
        has_section_col = "section" in filtered_df.columns
    except (AttributeError, TypeError):
        has_section_col = False

    if selected_section != "Все" and has_section_col:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Filter tasks: deviation=1/True OR reason of deviation filled
    try:
        has_deviation_col = "deviation" in filtered_df.columns
        has_reason_col = "reason of deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_col = False
        has_reason_col = False

    if has_deviation_col or has_reason_col:
        if has_deviation_col:
            deviation_flag = (
                (filtered_df["deviation"] == True)
                | (filtered_df["deviation"] == 1)
                | (filtered_df["deviation"].astype(str).str.lower() == "true")
                | (filtered_df["deviation"].astype(str).str.strip() == "1")
            )
        else:
            deviation_flag = pd.Series(False, index=filtered_df.index)
        if has_reason_col:
            reason_filled = (
                filtered_df["reason of deviation"].notna()
                & (filtered_df["reason of deviation"].astype(str).str.strip() != "")
            )
        else:
            reason_filled = pd.Series(False, index=filtered_df.index)
        filtered_df = filtered_df[deviation_flag | reason_filled]
    else:
        st.warning("Поле 'deviation' или 'reason of deviation' не найдено в данных.")
        return

    if filtered_df.empty:
        st.info("Отклонения не найдены для выбранных фильтров.")
        return

    # Group by project and task - aggregate across all periods
    # Find task column
    task_col = (
        "task name"
        if "task name" in filtered_df.columns
        else find_column(filtered_df, ["Задача", "task"])
    )
    
    has_task_col = task_col is not None

    if project_col and has_task_col:
        # Convert deviation in days to numeric
        try:
            has_deviation_days_col = "deviation in days" in filtered_df.columns
        except (AttributeError, TypeError):
            has_deviation_days_col = False

        if has_deviation_days_col:
            filtered_df["deviation in days"] = pd.to_numeric(
                filtered_df["deviation in days"], errors="coerce"
            )

        # Подставляем колонки дат из русских названий, если их ещё нет
        ensure_date_columns(filtered_df)
        # Calculate completion percentage if dates are available
        try:
            has_plan_start = "plan start" in filtered_df.columns
            has_plan_end = "plan end" in filtered_df.columns
            has_base_start = "base start" in filtered_df.columns
            has_base_end = "base end" in filtered_df.columns
        except (AttributeError, TypeError):
            has_plan_start = False
            has_plan_end = False
            has_base_start = False
            has_base_end = False

        if has_plan_start and has_plan_end and has_base_start and has_base_end:
            # Convert dates to datetime
            for col in ["plan start", "plan end", "base start", "base end"]:
                filtered_df[col] = pd.to_datetime(
                    filtered_df[col], errors="coerce", dayfirst=True
                )

            # Calculate completion percentage:
            # (Планируемая дата окончания - планируемая дата начала) / (Фактическая дата окончания - фактическая дата начала) * 100
            filtered_df["plan_duration"] = (
                filtered_df["plan end"] - filtered_df["plan start"]
            ).dt.days
            filtered_df["fact_duration"] = (
                filtered_df["base end"] - filtered_df["base start"]
            ).dt.days

            # Calculate percentage: plan_duration / fact_duration * 100
            # Avoid division by zero
            filtered_df["completion_percent"] = (
                filtered_df["plan_duration"]
                / filtered_df["fact_duration"].replace(0, np.nan)
                * 100
            ).fillna(0)
            # Cap at reasonable values (0-200%)
            filtered_df["completion_percent"] = filtered_df["completion_percent"].clip(
                0, 200
            )
        else:
            filtered_df["completion_percent"] = None

        # Determine grouping level based on applied filters
        # Priority: task > section > project
        if selected_task != "Все":
            # If specific task is selected, group by task (only one task will be shown)
            group_by_cols = [project_col, task_col]
            y_column = "Задача"
        elif selected_section != "Все":
            # If section is selected but not task, group by section
            group_by_cols = ["section"]
            y_column = "Раздел"
        elif selected_project != "Все":
            # If project is selected but not task/section, group by project
            group_by_cols = [project_col]
            y_column = "Проект"
        else:
            # If nothing is selected, group by project
            group_by_cols = [project_col]
            y_column = "Проект"

        # Group data based on determined grouping level
        deviations = (
            filtered_df.groupby(group_by_cols)
            .agg(
                {
                    "deviation in days": (
                        "sum" if "deviation in days" in filtered_df.columns else "count"
                    ),
                    "completion_percent": (
                        "mean"
                        if "completion_percent" in filtered_df.columns
                        and filtered_df["completion_percent"].notna().any()
                        else lambda x: None
                    ),
                }
            )
            .reset_index()
        )

        # Set column names based on grouping level
        if len(group_by_cols) == 2:  # project + task
            deviations.columns = [
                "Проект",
                "Задача",
                "Суммарно дней отклонений",
                "Процент выполнения",
            ]
            deviations["Отображение"] = (
                deviations["Задача"] + " (" + deviations["Проект"] + ")"
            )
        elif "section" in group_by_cols:
            deviations.columns = [
                "Раздел",
                "Суммарно дней отклонений",
                "Процент выполнения",
            ]
            deviations["Отображение"] = deviations["Раздел"]
        else:  # project only
            deviations.columns = [
                "Проект",
                "Суммарно дней отклонений",
                "Процент выполнения",
            ]
            deviations["Отображение"] = deviations["Проект"]

        # If completion percent calculation failed, set to None
        if "Процент выполнения" in deviations.columns:
            deviations["Процент выполнения"] = pd.to_numeric(
                deviations["Процент выполнения"], errors="coerce"
            )

        # Sort by deviation amount (descending - largest first)
        deviations = deviations.sort_values("Суммарно дней отклонений", ascending=False)

        if deviations.empty:
            st.info("Нет данных для отображения.")
            return

        # Checkboxes row 2: Top 5 and Completion percentage
        col5, col6 = st.columns(2)

        with col5:
            # Checkbox for Top 5 filter
            show_top5 = st.checkbox(
                "Топ 5 отклонений", value=False, key="show_top5_deviations"
            )

        with col6:
            # Checkbox to show/hide completion percentage
            show_completion = st.checkbox(
                "Показывать процент выполнения",
                value=False,
                key="show_completion_percent",
            )

        # Apply Top 5 filter if enabled
        if show_top5:
            deviations = deviations.head(5)

        # Visualization - horizontal bar chart
        # Format text for display on bars
        text_values = []
        for _, row in deviations.iterrows():
            if show_completion and pd.notna(row.get("Процент выполнения")):
                text_values.append(
                    f"{int(round(row['Суммарно дней отклонений'], 0))} ({row['Процент выполнения']:.1f}%)"
                )
            else:
                text_values.append(f"{int(round(row['Суммарно дней отклонений'], 0))}")

        fig = px.bar(
            deviations,
            x="Суммарно дней отклонений",
            y="Отображение",
            orientation="h",
            title="Отклонения от базового плана",
            labels={
                "Суммарно дней отклонений": "Суммарно дней отклонений",
                "Отображение": y_column,
            },
            text=text_values,
            color_discrete_sequence=["#1f77b4"],  # Blue color for all bars
        )

        # Set category order to show largest values at top (descending order)
        # For horizontal bars, reverse the list so largest is at top
        category_list = deviations["Отображение"].tolist()
        fig.update_layout(
            showlegend=False,
            yaxis=dict(
                categoryorder="array",
                categoryarray=list(
                    reversed(category_list)
                ),  # Reverse to show largest at top
            ),
        )
        fig.update_traces(
            textposition="outside", textfont=dict(size=14, color="white")
        )  # Show text outside bars at the end

        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Additional histogram with detail by section and task
        st.subheader("📊 Детализация отклонений по разделам и задачам")

        # Filter for detail histogram - only by project
        detail_df = df.copy()

        # Apply project filter if selected
        if selected_project != "Все" and project_col and project_col in detail_df.columns:
            detail_df = detail_df[
                detail_df[project_col].astype(str).str.strip()
                == str(selected_project).strip()
            ]

        # Filter only tasks with deviations
        if "deviation" in detail_df.columns:
            deviation_mask = (
                (detail_df["deviation"] == True)
                | (detail_df["deviation"] == 1)
                | (detail_df["deviation"].astype(str).str.lower() == "true")
                | (detail_df["deviation"].astype(str).str.strip() == "1")
            )
            detail_df = detail_df[deviation_mask]

        if detail_df.empty:
            st.info("Нет данных для отображения детализации.")
        else:
            # Convert deviation in days to numeric
            if "deviation in days" in detail_df.columns:
                detail_df["deviation in days"] = pd.to_numeric(
                    detail_df["deviation in days"], errors="coerce"
                )

            # Group by section and task
            if "section" in detail_df.columns and "task name" in detail_df.columns:
                detail_deviations = (
                    detail_df.groupby(["section", "task name"])
                    .agg(
                        {
                            "deviation in days": (
                                "sum"
                                if "deviation in days" in detail_df.columns
                                else "count"
                            )
                        }
                    )
                    .reset_index()
                )

                detail_deviations.columns = [
                    "Раздел",
                    "Задача",
                    "Суммарно дней отклонений",
                ]
                detail_deviations["Отображение"] = (
                    detail_deviations["Задача"]
                    + " ("
                    + detail_deviations["Раздел"]
                    + ")"
                )

                # Не выводить отрицательные значения на графике
                detail_deviations = detail_deviations[
                    detail_deviations["Суммарно дней отклонений"] >= 0
                ]

                # Sort by deviation amount (descending)
                detail_deviations = detail_deviations.sort_values(
                    "Суммарно дней отклонений", ascending=False
                )

                # Create horizontal bar chart (только неотрицательные)
                if detail_deviations.empty:
                    st.info("Нет неотрицательных отклонений для детализации.")
                else:
                    fig_detail = px.bar(
                        detail_deviations,
                        x="Суммарно дней отклонений",
                    y="Отображение",
                    orientation="h",
                    title="Детализация отклонений по разделам и задачам",
                    labels={
                        "Суммарно дней отклонений": "Суммарно дней отклонений",
                        "Отображение": "Задача (Раздел)",
                    },
                    text=detail_deviations["Суммарно дней отклонений"].apply(
                        lambda x: f"{int(round(x, 0))}" if pd.notna(x) else ""
                    ),
                    color_discrete_sequence=["#1f77b4"],
                )

                # Set category order to show largest values at top
                category_list_detail = detail_deviations["Отображение"].tolist()
                fig_detail.update_layout(
                    showlegend=False,
                    yaxis=dict(
                        categoryorder="array",
                        categoryarray=list(reversed(category_list_detail)),
                    ),
                    height=max(
                        400, len(detail_deviations) * 30
                    ),  # Dynamic height based on number of items
                )
                fig_detail.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )

                fig_detail = apply_chart_background(fig_detail)
                st.plotly_chart(fig_detail, use_container_width=True)
            else:
                st.warning("Поля 'section' или 'task name' не найдены для детализации.")
    else:
        st.warning(
            "Необходимые поля 'project name' или 'task name' не найдены в данных."
        )


# ==================== DASHBOARD 5: Dynamics of Reasons by Month ====================
def dashboard_dynamics_of_reasons(df):
    # Проверка на None или пустой DataFrame
    if df is None:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    # Проверка, что df является DataFrame и имеет атрибут columns
    if not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    st.header("📉 Динамика причин отклонений")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="reasons_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        try:
            has_reason_column = "reason of deviation" in df.columns
        except (AttributeError, TypeError):
            has_reason_column = False

        if has_reason_column:
            reasons = ["Все"] + sorted(
                df["reason of deviation"].dropna().unique().tolist()
            )
            selected_reason = st.selectbox(
                "Фильтр по причине", reasons, key="reasons_reason"
            )
        else:
            selected_reason = "Все"

    with col3:
        try:
            has_project_column = "project name" in df.columns
        except (AttributeError, TypeError):
            has_project_column = False

        if has_project_column:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="reasons_project"
            )
        else:
            selected_project = "Все"

    with col4:
        try:
            has_section_column = "section" in df.columns
        except (AttributeError, TypeError):
            has_section_column = False

        if has_section_column:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="reasons_section"
            )
        else:
            selected_section = "Все"

    # View type selector
    view_type = st.selectbox(
        "Вид отображения", ["По причинам", "По месяцам"], key="reasons_view_type"
    )

    # Apply filters - fix filtering
    filtered_df = df.copy()

    try:
        has_reason_col = "reason of deviation" in df.columns
    except (AttributeError, TypeError):
        has_reason_col = False

    if selected_reason != "Все" and has_reason_col:
        filtered_df = filtered_df[
            filtered_df["reason of deviation"].astype(str).str.strip()
            == str(selected_reason).strip()
        ]

    try:
        has_project_col = "project name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_project_col = False

    if selected_project != "Все" and has_project_col:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    try:
        has_section_col = "section" in filtered_df.columns
    except (AttributeError, TypeError):
        has_section_col = False

    if selected_section != "Все" and has_section_col:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Filter tasks: deviation=1/True OR reason of deviation filled
    try:
        has_deviation_col = "deviation" in filtered_df.columns
        has_reason_col = "reason of deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_col = False
        has_reason_col = False

    if has_deviation_col or has_reason_col:
        if has_deviation_col:
            deviation_flag = (
                (filtered_df["deviation"] == True)
                | (filtered_df["deviation"] == 1)
                | (filtered_df["deviation"].astype(str).str.lower() == "true")
                | (filtered_df["deviation"].astype(str).str.strip() == "1")
            )
        else:
            deviation_flag = pd.Series(False, index=filtered_df.index)
        if has_reason_col:
            reason_filled = (
                filtered_df["reason of deviation"].notna()
                & (filtered_df["reason of deviation"].astype(str).str.strip() != "")
            )
        else:
            reason_filled = pd.Series(False, index=filtered_df.index)
        filtered_df = filtered_df[deviation_flag | reason_filled]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Determine period column - use plan_month for month grouping
    try:
        has_plan_end_col = "plan end" in filtered_df.columns
    except (AttributeError, TypeError):
        has_plan_end_col = False

    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
        # If plan_month doesn't exist, try to create it from plan end
        try:
            has_period_col = period_col in filtered_df.columns
        except (AttributeError, TypeError):
            has_period_col = False

        if not has_period_col and has_plan_end_col:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, period_col] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("M")
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
        try:
            has_period_col = period_col in filtered_df.columns
        except (AttributeError, TypeError):
            has_period_col = False

        if not has_period_col and has_plan_end_col:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, period_col] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Q")
    else:
        period_col = "plan_year"
        period_label = "Год"
        try:
            has_period_col = period_col in filtered_df.columns
        except (AttributeError, TypeError):
            has_period_col = False

        if not has_period_col and has_plan_end_col:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, period_col] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Y")

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Group by period and reason - ensure we have both project name and reason
    if "reason of deviation" in filtered_df.columns:
        # Filter out rows without period data
        reason_dynamics = (
            filtered_df[filtered_df[period_col].notna()]
            .groupby([period_col, "reason of deviation"])
            .size()
            .reset_index(name="Количество")
        )

        # Format period for display
        def format_period(period_val):
            if pd.isna(period_val):
                return "Н/Д"
            if isinstance(period_val, pd.Period):
                try:
                    if period_val.freqstr == "M" or period_val.freqstr.startswith(
                        "M"
                    ):  # Month
                        month_name = get_russian_month_name(period_val)
                        year = period_val.year
                        return f"{month_name} {year}"
                    elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                        "Q"
                    ):  # Quarter
                        return f"Q{period_val.quarter} {period_val.year}"
                    elif (
                        period_val.freqstr == "Y" or period_val.freqstr == "A-DEC"
                    ):  # Year
                        return str(period_val.year)
                    else:
                        month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                except:
                    # Try parsing as string
                    period_str = str(period_val)
                    try:
                        if "-" in period_str:
                            parts = period_str.split("-")
                            if len(parts) >= 2:
                                year = parts[0]
                                month = parts[1]
                                month_num = int(month)
                                month_name = RUSSIAN_MONTHS.get(month_num, "")
                                if month_name:
                                    return f"{month_name} {year}"
                    except:
                        pass
                    return str(period_val)
            elif isinstance(period_val, str):
                # Try parsing string like "2025-01"
                try:
                    if "-" in period_val:
                        parts = period_val.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
            return str(period_val)

        reason_dynamics[period_col] = reason_dynamics[period_col].apply(format_period)

        # Aggregate again after formatting to handle potential duplicates from formatting
        reason_dynamics = (
            reason_dynamics.groupby([period_col, "reason of deviation"])["Количество"]
            .sum()
            .reset_index()
        )

        # Checkbox to show/hide trend line
        show_trend = st.checkbox(
            "Показывать линию тренда", value=False, key="show_trend_line"
        )

        # Build visualization based on view type
        if view_type == "По причинам":
            # View 1: By reasons - reason on X-axis, count on Y-axis
            # Group by reason and sum across all periods
            reason_summary = (
                reason_dynamics.groupby("reason of deviation")["Количество"]
                .sum()
                .reset_index()
            )
            reason_summary = reason_summary.sort_values("Количество", ascending=False)

            # Visualization - vertical bar chart with reasons on X-axis
            fig = px.bar(
                reason_summary,
                x="reason of deviation",
                y="Количество",
                title="Динамика причин отклонений по причинам",
                labels={
                    "reason of deviation": "Причина отклонения",
                    "Количество": "Количество отклонений",
                },
                text="Количество",
                color_discrete_sequence=["#1f77b4"],
            )
            fig.update_xaxes(tickangle=-45)
            fig.update_traces(
                textposition="outside", textfont=dict(size=12, color="white")
            )
        else:
            # View 2: By months - month on X-axis, count on Y-axis, reasons as colors (stacked)
            # If "Все" projects selected, show aggregated view (one column per period)
            if selected_project == "Все":
                # For chart: group only by period (sum all reasons)
                chart_data = (
                    reason_dynamics.groupby(period_col)["Количество"]
                    .sum()
                    .reset_index()
                )
                chart_data["reason of deviation"] = (
                    "Все проекты"  # Dummy column for consistency
                )

                # Visualization - vertical bar chart with single column per period
                fig = px.bar(
                    chart_data,
                    x=period_col,
                    y="Количество",
                    title="Динамика причин отклонений по периодам",
                    labels={
                        period_col: period_label,
                        "Количество": "Количество отклонений",
                    },
                    text="Количество",
                    color_discrete_sequence=["#1f77b4"],  # Single color for all bars
                )
            else:
                # Visualization - vertical bar chart with stacked reasons
                # Use period_col for x-axis and reason for color (legend)
                # Use stacked mode to show all reasons in one column per period
                fig = px.bar(
                    reason_dynamics,
                    x=period_col,
                    y="Количество",
                    color="reason of deviation",
                    title="Динамика причин отклонений по периодам",
                    labels={
                        period_col: period_label,
                        "reason of deviation": "Причина отклонения",
                        "Количество": "Количество отклонений",
                    },
                    text="Количество",
                    barmode="stack",  # Stacked bars: all reasons in one column per period
                )
        # Update layout based on view type
        if view_type == "По причинам":
            # For "По причинам" view, no additional annotations needed
            pass
        else:
            # For "По месяцам" view, add annotations and trend line
            fig.update_xaxes(tickangle=-45)
            # Show values inside bars for each reason - horizontal text (same as other charts)
            fig.update_traces(
                textposition="inside", textfont=dict(size=12, color="white")
            )
            # Set text angle to horizontal (0 degrees) for inside bar labels - same as other charts
            for i, trace in enumerate(fig.data):
                fig.data[i].update(textangle=0)

            # Add total values above bars and trend line
            if selected_project == "Все":
                # For "Все проекты": use chart_data for annotations and trend
                total_by_period = (
                    chart_data.groupby(period_col)["Количество"].sum().reset_index()
                )
                periods = sorted(chart_data[period_col].unique())
                max_y_value = chart_data["Количество"].max()
            else:
                # Calculate total deviations per period for annotations
                total_by_period = (
                    reason_dynamics.groupby(period_col)["Количество"]
                    .sum()
                    .reset_index()
                )
                total_by_period_dict = dict(
                    zip(total_by_period[period_col], total_by_period["Количество"])
                )
                periods = sorted(reason_dynamics[period_col].unique())
                max_y_value = reason_dynamics["Количество"].max()

                # Add annotations for individual project view
                for period in periods:
                    total = total_by_period_dict.get(period, 0)
                    if total > 0:
                        # Get all bars for this period to find max height
                        period_bars = reason_dynamics[
                            reason_dynamics[period_col] == period
                        ]
                        if not period_bars.empty:
                            # Find the maximum height among all bars in this period group
                            max_bar_height = period_bars["Количество"].max()

                            # Calculate offset
                            if max_y_value > 0:
                                y_offset = max_y_value * 0.10
                            else:
                                y_offset = max_bar_height * 0.10

                            # Position annotation
                            x_position = period
                            y_position = max_bar_height + y_offset

                            fig.add_annotation(
                                x=x_position,
                                y=y_position,
                                text=f"<b>{int(round(total, 0))}</b>",
                                showarrow=False,
                                font=dict(size=14, color="white"),
                                xanchor="center",
                                yanchor="bottom",
                                bgcolor="rgba(0,0,0,0.5)",
                                xshift=10,
                            )

            # Add trend line if checkbox is checked
            if show_trend:
                # Calculate overall trend across all reasons (sum by period)
                total_by_period_sorted = total_by_period.sort_values(period_col)
                if len(total_by_period_sorted) > 1:
                    # Use period values as x positions
                    x_positions = total_by_period_sorted[period_col].tolist()
                    y_values = total_by_period_sorted["Количество"].values

                    # Create numeric x values for trend calculation (for fitting)
                    x_numeric = range(len(y_values))

                    # Calculate linear trend
                    z = np.polyfit(x_numeric, y_values, 1)
                    p = np.poly1d(z)
                    trend_y = p(x_numeric)

                    # Add single trend line across all data
                    fig.add_trace(
                        go.Scatter(
                            x=x_positions,
                            y=trend_y,
                            mode="lines",
                            name="Линия тренда",
                            line=dict(dash="dash", width=3, color="white"),
                            showlegend=True,
                            hoverinfo="skip",
                        )
                    )

        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Summary table - always show by reason (summarized values)
        # Group by reason and sum across all periods
        summary_by_reason = (
            reason_dynamics.groupby("reason of deviation")["Количество"]
            .sum()
            .reset_index()
        )
        summary_by_reason.columns = ["Причина отклонения", "Суммарное количество"]
        summary_by_reason = summary_by_reason.sort_values(
            "Суммарное количество", ascending=False
        )

        st.subheader(f"Сводная таблица по {period_label.lower()}")
        st.table(style_dataframe_for_dark_theme(summary_by_reason))
    else:
        st.warning("Столбец 'reason of deviation' не найден в данных.")


# ==================== DASHBOARD 6: Budget Plan/Fact/Reserve by Project by Period ====================
def dashboard_budget_by_period(df):
    st.header("💰 БДДС")
    st.caption("Вид отображения: по месяцам или накопительно.")

    # Filters row 1: Period and Project
    col1, col2 = st.columns(2)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_project"
            )
        else:
            selected_project = "Все"

    # Filters row 2: Task, Section
    col3, col4 = st.columns(2)

    with col3:
        if "task name" in df.columns:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox("Фильтр по лоту", tasks, key="budget_task")
        else:
            selected_task = "Все"

    with col4:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_section"
            )
        else:
            selected_section = "Все"

    # Filters row 3: Block
    col6 = st.columns(1)[0]
    with col6:
        pass

    # Filters row 4: View type (в фрагменте — без полного перезапуска) and Hide adjusted budget
    col7, col8 = st.columns(2)
    with col8:
        hide_adjusted = st.checkbox(
            "Скрыть скорректированный бюджет",
            value=True,
            key="budget_period_hide_adjusted",
        )

    # Filters row 5: Hide deviation
    col9, col10 = st.columns(2)

    with col9:
        hide_reserve = st.checkbox(
            "Скрыть отклонение", value=True, key="budget_period_hide_reserve"
        )

    # Apply filters - fix filtering
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_task != "Все" and "task name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns (нормализуем русские названия)
    ensure_budget_columns(filtered_df)
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine adjusted budget column name
    adjusted_budget_col = None
    if "budget adjusted" in filtered_df.columns:
        adjusted_budget_col = "budget adjusted"
    elif "adjusted budget" in filtered_df.columns:
        adjusted_budget_col = "adjusted budget"

    # Determine period column and ensure it exists (create from plan end if missing)
    ensure_date_columns(filtered_df)
    if "plan end" in filtered_df.columns:
        plan_end = pd.to_datetime(filtered_df["plan end"], errors="coerce")
        mask = plan_end.notna()
        if mask.any():
            if "plan_month" not in filtered_df.columns:
                filtered_df.loc[mask, "plan_month"] = plan_end.loc[mask].dt.to_period("M")
            if "plan_quarter" not in filtered_df.columns:
                filtered_df.loc[mask, "plan_quarter"] = plan_end.loc[mask].dt.to_period("Q")
            if "plan_year" not in filtered_df.columns:
                filtered_df.loc[mask, "plan_year"] = plan_end.loc[mask].dt.to_period("Y")

    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден. Убедитесь, что в данных есть колонка дат (например, «Конец План» / plan end).")
        return

    # Отклонение = факт - план (положительное — перерасход, красный; отрицательное — экономия, зелёный)
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget fact"] - filtered_df["budget plan"]
    )

    # Convert adjusted budget to numeric if it exists
    if adjusted_budget_col:
        filtered_df[adjusted_budget_col] = pd.to_numeric(
            filtered_df[adjusted_budget_col], errors="coerce"
        )

    # Колонка для группировки по лотам (лот = section или колонка "лот"/"lot")
    lot_col = "лот" if "лот" in filtered_df.columns else ("lot" if "lot" in filtered_df.columns else "section")
    if lot_col not in filtered_df.columns:
        lot_col = "section"  # fallback для группировки по лотам

    # Format period for display (общая для обоих табов)
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    tab_period, tab_lot = st.tabs(["По периодам", "По лотам"])

    with tab_period:
        # Group by period and project
        agg_dict = {"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"}
        if adjusted_budget_col:
            agg_dict[adjusted_budget_col] = "sum"

        budget_summary = (
            filtered_df.groupby([period_col, "project name"]).agg(agg_dict).reset_index()
        )

        # Store original period values for sorting before formatting
        budget_summary["period_original"] = budget_summary[period_col]
        budget_summary[period_col] = budget_summary[period_col].apply(format_period_display)

        @st.fragment
        def _budget_period_chart():
            view_type = st.selectbox(
                "Вид отображения", ["По месяцам", "Накопительно"], key="budget_period_view"
            )
            if selected_project != "Все":
                project_data = budget_summary[
                    budget_summary["project name"] == selected_project
                ].copy()
            else:
                agg_dict_all = {
                    "budget plan": "sum",
                    "budget fact": "sum",
                    "reserve budget": "sum",
                    "period_original": "first",
                }
                if adjusted_budget_col:
                    agg_dict_all[adjusted_budget_col] = "sum"
                project_data = (
                    budget_summary.groupby(period_col).agg(agg_dict_all).reset_index()
                )
            if project_data["period_original"].dtype == "object":
                try:
                    project_data["period_sort"] = project_data["period_original"].apply(
                        lambda x: (
                            x if isinstance(x, pd.Period)
                            else (pd.Period(str(x), freq=period_type_en[0]) if pd.notna(x) else None)
                        )
                    )
                    project_data = project_data.sort_values("period_sort").copy()
                    project_data = project_data.drop("period_sort", axis=1)
                except Exception:
                    project_data = project_data.sort_values("period_original").copy()
            else:
                project_data = project_data.sort_values("period_original").copy()
            if view_type == "Накопительно":
                project_data["budget plan"] = project_data["budget plan"].cumsum()
                project_data["budget fact"] = project_data["budget fact"].cumsum()
                project_data["reserve budget"] = project_data["reserve budget"].cumsum()
                if adjusted_budget_col and adjusted_budget_col in project_data.columns:
                    project_data[adjusted_budget_col] = project_data[adjusted_budget_col].cumsum()
                title_suffix = " (накопительно)"
            else:
                title_suffix = ""
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=project_data[period_col],
                    y=project_data["budget plan"].div(1e6),
                    name="Бюджет План",
                    marker_color="#2E86AB",
                    text=project_data["budget plan"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=14, color="white"),
                    customdata=project_data["budget plan"].apply(format_million_rub),
                    hovertemplate="<b>%{x}</b><br>Бюджет План: %{customdata}<br><extra></extra>",
                )
            )
            fig.add_trace(
                go.Bar(
                    x=project_data[period_col],
                    y=project_data["budget fact"].div(1e6),
                    name="Бюджет Факт",
                    marker_color="#A23B72",
                    text=project_data["budget fact"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=14, color="white"),
                    customdata=project_data["budget fact"].apply(format_million_rub),
                    hovertemplate="<b>%{x}</b><br>Бюджет Факт: %{customdata}<br><extra></extra>",
                )
            )
            if not hide_reserve:
                dev_vals = project_data["reserve budget"].div(1e6)
                dev_colors = ["#e74c3c" if v >= 0 else "#27ae60" for v in project_data["reserve budget"]]
                fig.add_trace(
                    go.Bar(
                        x=project_data[period_col],
                        y=dev_vals,
                        name="Отклонение",
                        marker_color=dev_colors,
                        text=project_data["reserve budget"].apply(format_million_rub),
                        textposition="outside",
                        textfont=dict(size=14, color="white"),
                        customdata=project_data["reserve budget"].apply(format_million_rub),
                        hovertemplate="<b>%{x}</b><br>Отклонение: %{customdata}<br><extra></extra>",
                    )
                )
            if (
                adjusted_budget_col
                and adjusted_budget_col in project_data.columns
                and not hide_adjusted
            ):
                fig.add_trace(
                    go.Bar(
                        x=project_data[period_col],
                        y=project_data[adjusted_budget_col].div(1e6),
                        name="Скорректированный бюджет",
                        marker_color="#F18F01",
                        text=project_data[adjusted_budget_col].apply(format_million_rub),
                        textposition="outside",
                        textfont=dict(size=14, color="white"),
                        customdata=project_data[adjusted_budget_col].apply(format_million_rub),
                        hovertemplate="<b>%{x}</b><br>Скорректированный бюджет: %{customdata}<br><extra></extra>",
                    )
                )
            fig.update_layout(
                title=f"БДДС{title_suffix}",
                xaxis_title=period_label,
                yaxis_title="млн руб.",
                barmode="group",
                xaxis=dict(tickangle=-45),
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

        _budget_period_chart()

        # Summary table — суммы в млн руб.
        st.subheader(f"Сводка бюджета по {period_label.lower()}")
        table_display = budget_summary.drop(columns=["period_original"], errors="ignore").copy()
        budget_cols_table = ["budget plan", "budget fact", "reserve budget"]
        if adjusted_budget_col and adjusted_budget_col in table_display.columns:
            budget_cols_table = budget_cols_table + [adjusted_budget_col]
        for col in budget_cols_table:
            if col in table_display.columns:
                table_display[col] = (table_display[col] / 1e6).round(2).apply(
                    lambda x: f"{float(x):.2f} млн руб." if pd.notna(x) else ""
                )
        table_display = table_display.rename(columns={
            "budget plan": "Бюджет План, млн руб.",
            "budget fact": "Бюджет Факт, млн руб.",
            "reserve budget": "Отклонение, млн руб.",
            **({adjusted_budget_col: "Скорр. бюджет, млн руб."} if adjusted_budget_col and adjusted_budget_col in table_display.columns else {}),
        })
        if period_col in table_display.columns:
            table_display = table_display.rename(columns={period_col: period_label})
        st.markdown(
            budget_table_to_html(table_display, finance_deviation_column="Отклонение, млн руб."),
            unsafe_allow_html=True,
        )

    with tab_lot:
        # По лотам: группировка по периоду и лоту (section / лот / lot)
        if lot_col not in filtered_df.columns:
            st.info("Нет колонки для группировки по лотам (section / лот).")
        else:
            agg_dict_lot = {"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"}
            budget_summary_lot = (
                filtered_df.groupby([period_col, lot_col]).agg(agg_dict_lot).reset_index()
            )
            budget_summary_lot["period_original"] = budget_summary_lot[period_col]
            budget_summary_lot[period_col] = budget_summary_lot[period_col].apply(format_period_display)

            hide_reserve_lot = st.checkbox(
                "Скрыть отклонение", value=True, key="budget_lot_hide_reserve"
            )
            # По лотам: ось Y = этапы (лоты), ось X = млн руб.
            lot_chart_data = (
                budget_summary_lot.groupby(lot_col)
                .agg({"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"})
                .reset_index()
            )
            lot_chart_data = lot_chart_data.sort_values("budget plan", ascending=True)
            fig_lot = go.Figure()
            fig_lot.add_trace(
                go.Bar(
                    y=lot_chart_data[lot_col],
                    x=lot_chart_data["budget plan"].div(1e6),
                    name="Бюджет План",
                    marker_color="#2E86AB",
                    text=lot_chart_data["budget plan"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=18, color="white"),
                    orientation="h",
                )
            )
            fig_lot.add_trace(
                go.Bar(
                    y=lot_chart_data[lot_col],
                    x=lot_chart_data["budget fact"].div(1e6),
                    name="Бюджет Факт",
                    marker_color="#A23B72",
                    text=lot_chart_data["budget fact"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=18, color="white"),
                    orientation="h",
                )
            )
            if not hide_reserve_lot:
                dev_colors_lot = ["#e74c3c" if v >= 0 else "#27ae60" for v in lot_chart_data["reserve budget"]]
                fig_lot.add_trace(
                    go.Bar(
                        y=lot_chart_data[lot_col],
                        x=lot_chart_data["reserve budget"].div(1e6),
                        name="Отклонение",
                        marker_color=dev_colors_lot,
                        text=lot_chart_data["reserve budget"].apply(format_million_rub),
                        textposition="outside",
                        textfont=dict(size=18, color="white"),
                        orientation="h",
                    )
                )
            fig_lot.update_layout(
                title=dict(text="План/факт/отклонение по лотам", font=dict(size=24)),
                xaxis_title="млн руб.",
                yaxis_title="Этапы",
                barmode="group",
                xaxis=dict(tickangle=0, tickfont=dict(size=16)),
                yaxis=dict(tickfont=dict(size=16), categoryorder="trace"),
                legend=dict(font=dict(size=18)),
                height=max(400, len(lot_chart_data) * 44),
            )
            fig_lot = apply_chart_background(fig_lot)
            st.plotly_chart(fig_lot, use_container_width=True)

            st.subheader("Сводка бюджета по лотам")
            table_lot = budget_summary_lot.drop(columns=["period_original"], errors="ignore").copy()
            for col in ["budget plan", "budget fact", "reserve budget"]:
                if col in table_lot.columns:
                    table_lot[col] = (table_lot[col] / 1e6).round(2).apply(
                        lambda x: f"{float(x):.2f} млн руб." if pd.notna(x) else ""
                    )
            rename_cols = {
                "budget plan": "Бюджет План, млн руб.",
                "budget fact": "Бюджет Факт, млн руб.",
                "reserve budget": "Отклонение, млн руб.",
            }
            if lot_col in table_lot.columns:
                rename_cols[lot_col] = "Лот"
            table_lot = table_lot.rename(columns=rename_cols)
            st.markdown(
                budget_table_to_html(table_lot, finance_deviation_column="Отклонение, млн руб."),
                unsafe_allow_html=True,
            )


# ==================== DASHBOARD 6.5: Budget Cumulative ====================
def dashboard_budget_cumulative(df):
    st.header("💰 БДДС накопительно")

    # Filters row 1: Period and Project
    col1, col2 = st.columns(2)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_cum_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_cum_project"
            )
        else:
            selected_project = "Все"

    # Filters row 2: Task and Section
    col3, col4 = st.columns(2)

    with col3:
        # Task filter
        if "task name" in df.columns:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox(
                "Фильтр по лоту", tasks, key="budget_cum_task"
            )
        else:
            selected_task = "Все"

    with col4:
        # Section filter (блоки)
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_cum_section"
            )
        else:
            selected_section = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_task != "Все" and "task name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns (нормализуем русские названия)
    ensure_budget_columns(filtered_df)
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine adjusted budget column name
    adjusted_budget_col = None
    if "budget adjusted" in filtered_df.columns:
        adjusted_budget_col = "budget adjusted"
    elif "adjusted budget" in filtered_df.columns:
        adjusted_budget_col = "adjusted budget"

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Convert to numeric
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    if adjusted_budget_col:
        filtered_df[adjusted_budget_col] = pd.to_numeric(
            filtered_df[adjusted_budget_col], errors="coerce"
        )

    # Group by period and project
    agg_dict = {"budget plan": "sum", "budget fact": "sum"}
    if adjusted_budget_col:
        agg_dict[adjusted_budget_col] = "sum"

    budget_summary = (
        filtered_df.groupby([period_col, "project name"]).agg(agg_dict).reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    budget_summary[period_col] = budget_summary[period_col].apply(format_period_display)

    # Aggregate data
    if selected_project != "Все":
        project_data = budget_summary[
            budget_summary["project name"] == selected_project
        ]
    else:
        agg_dict_all = {"budget plan": "sum", "budget fact": "sum"}
        if adjusted_budget_col:
            agg_dict_all[adjusted_budget_col] = "sum"
        project_data = (
            budget_summary.groupby(period_col).agg(agg_dict_all).reset_index()
        )

    # Sort data by period to ensure correct cumulative calculation
    project_data_sorted = project_data.sort_values(period_col).copy()

    # Calculate cumulative sums
    project_data_sorted["budget plan_cum"] = project_data_sorted["budget plan"].cumsum()
    project_data_sorted["budget fact_cum"] = project_data_sorted["budget fact"].cumsum()
    if adjusted_budget_col and adjusted_budget_col in project_data_sorted.columns:
        project_data_sorted[f"{adjusted_budget_col}_cum"] = project_data_sorted[
            adjusted_budget_col
        ].cumsum()

    # Create cumulative chart (в млн руб., два знака после запятой)
    fig_cum = go.Figure()
    fig_cum.add_trace(
        go.Bar(
            x=project_data_sorted[period_col],
            y=project_data_sorted["budget plan_cum"].div(1e6),
            name="Бюджет План (накопительно)",
            marker_color="#2E86AB",
            text=project_data_sorted["budget plan_cum"].apply(format_million_rub),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )
    fig_cum.add_trace(
        go.Bar(
            x=project_data_sorted[period_col],
            y=project_data_sorted["budget fact_cum"].div(1e6),
            name="Бюджет Факт (накопительно)",
            marker_color="#A23B72",
            text=project_data_sorted["budget fact_cum"].apply(format_million_rub),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Add adjusted budget cumulative if available
    if adjusted_budget_col and adjusted_budget_col in project_data_sorted.columns:
        fig_cum.add_trace(
            go.Bar(
                x=project_data_sorted[period_col],
                y=project_data_sorted[f"{adjusted_budget_col}_cum"].div(1e6),
                name="Скорректированный бюджет (накопительно)",
                marker_color="#F18F01",
                text=project_data_sorted[f"{adjusted_budget_col}_cum"].apply(format_million_rub),
                textposition="outside",
                textfont=dict(size=14, color="white"),
            )
        )

    fig_cum.update_layout(
        title="БДДС накопительно",
        xaxis_title=period_label,
        yaxis_title="млн руб.",
        barmode="group",
        xaxis=dict(tickangle=-45),
    )
    fig_cum = apply_chart_background(fig_cum)
    st.plotly_chart(fig_cum, use_container_width=True)

    # Summary table with cumulative data (млн руб., два знака после запятой)
    st.subheader(f"Сводка бюджета (накопительно) по {period_label.lower()}")
    summary_cum = project_data_sorted[
        [period_col, "budget plan_cum", "budget fact_cum"]
    ].copy()
    if (
        adjusted_budget_col
        and f"{adjusted_budget_col}_cum" in project_data_sorted.columns
    ):
        summary_cum[f"{adjusted_budget_col}_cum"] = project_data_sorted[
            f"{adjusted_budget_col}_cum"
        ]
    # Переводим в млн руб. и форматируем с двумя знаками
    summary_cum["budget plan_cum"] = (summary_cum["budget plan_cum"] / 1e6).round(2)
    summary_cum["budget fact_cum"] = (summary_cum["budget fact_cum"] / 1e6).round(2)
    if adjusted_budget_col and f"{adjusted_budget_col}_cum" in summary_cum.columns:
        summary_cum[f"{adjusted_budget_col}_cum"] = (summary_cum[f"{adjusted_budget_col}_cum"] / 1e6).round(2)
    for c in ["budget plan_cum", "budget fact_cum"] + ([f"{adjusted_budget_col}_cum"] if adjusted_budget_col and f"{adjusted_budget_col}_cum" in summary_cum.columns else []):
        if c in summary_cum.columns:
            summary_cum[c] = summary_cum[c].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "")
    summary_cum.columns = [
        period_label,
        "Бюджет План (накопительно), млн руб.",
        "Бюджет Факт (накопительно), млн руб.",
    ] + (
        ["Скорр. бюджет (накопительно), млн руб."]
        if adjusted_budget_col
        and f"{adjusted_budget_col}_cum" in project_data_sorted.columns
        else []
    )
    st.table(style_dataframe_for_dark_theme(summary_cum))


# ==================== DASHBOARD 7: Budget Plan/Fact/Reserve by Section by Period ====================
def dashboard_budget_by_section(df):
    st.header("💰 БДДС по лотам")
    st.caption("Вид отображения: по месяцам или накопительно.")

    col1, col2, col3 = st.columns(3)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_section_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_section"
            )
        else:
            selected_section = "Все"

    with col3:
        pass

    # Apply filters
    filtered_df = df.copy()
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns (нормализуем русские названия)
    ensure_budget_columns(filtered_df)
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Отклонение = факт - план (положительное — перерасход, красный; отрицательное — экономия, зелёный)
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget fact"] - filtered_df["budget plan"]
    )

    # Group by period and section
    budget_summary = (
        filtered_df.groupby([period_col, "section"])
        .agg({"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"})
        .reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    # Store original period values for sorting before formatting
    budget_summary["period_original"] = budget_summary[period_col]
    budget_summary[period_col] = budget_summary[period_col].apply(format_period_display)

    # Checkbox to hide/show deviation
    hide_reserve = st.checkbox(
        "Скрыть отклонение", value=True, key="budget_section_hide_reserve"
    )

    @st.fragment
    def _budget_section_chart():
        if selected_section != "Все":
            section_data = budget_summary[
                budget_summary["section"] == selected_section
            ].copy()
            if section_data["period_original"].dtype == "object":
                try:
                    section_data["period_sort"] = section_data["period_original"].apply(
                        lambda x: (
                            x if isinstance(x, pd.Period)
                            else (pd.Period(str(x), freq=period_type_en[0]) if pd.notna(x) else None)
                        )
                    )
                    section_data = section_data.sort_values("period_sort").copy()
                    section_data = section_data.drop("period_sort", axis=1)
                except Exception:
                    section_data = section_data.sort_values("period_original").copy()
            else:
                section_data = section_data.sort_values("period_original").copy()
            view_type = st.selectbox(
                "Вид отображения", ["По месяцам", "Накопительно"], key="budget_section_view"
            )
            if view_type == "Накопительно":
                section_data = section_data.copy()
                section_data["budget plan"] = section_data["budget plan"].cumsum()
                section_data["budget fact"] = section_data["budget fact"].cumsum()
                section_data["reserve budget"] = section_data["reserve budget"].cumsum()
                title_suffix = " (накопительно)"
            else:
                title_suffix = ""
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=section_data[period_col],
                    y=section_data["budget plan"].div(1e6),
                    name="Бюджет План",
                    marker_color="#2E86AB",
                    text=section_data["budget plan"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=18, color="white"),
                )
            )
            fig.add_trace(
                go.Bar(
                    x=section_data[period_col],
                    y=section_data["budget fact"].div(1e6),
                    name="Бюджет Факт",
                    marker_color="#A23B72",
                    text=section_data["budget fact"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=18, color="white"),
                )
            )
            if not hide_reserve:
                dev_colors_sec = ["#e74c3c" if v >= 0 else "#27ae60" for v in section_data["reserve budget"]]
                fig.add_trace(
                    go.Bar(
                        x=section_data[period_col],
                        y=section_data["reserve budget"].div(1e6),
                        name="Отклонение",
                        marker_color=dev_colors_sec,
                        text=section_data["reserve budget"].apply(format_million_rub),
                        textposition="outside",
                        textfont=dict(size=18, color="white"),
                    )
                )
            fig.update_layout(
                title=dict(text=f"План/факт/отклонение по лотам{title_suffix}", font=dict(size=24)),
                xaxis_title=dict(text=period_label, font=dict(size=20)),
                yaxis_title=dict(text="млн руб.", font=dict(size=20)),
                barmode="group",
                xaxis=dict(tickangle=0, tickfont=dict(size=16)),
                yaxis=dict(tickfont=dict(size=16)),
                legend=dict(font=dict(size=18)),
                height=600,
            )
        else:
            # Все этапы: ось Y = этапы, ось X = млн руб.
            section_chart_data = (
                budget_summary.groupby("section")
                .agg({"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"})
                .reset_index()
            )
            section_chart_data = section_chart_data.sort_values("budget plan", ascending=True)
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    y=section_chart_data["section"],
                    x=section_chart_data["budget plan"].div(1e6),
                    name="Бюджет План",
                    marker_color="#2E86AB",
                    text=section_chart_data["budget plan"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=18, color="white"),
                    orientation="h",
                )
            )
            fig.add_trace(
                go.Bar(
                    y=section_chart_data["section"],
                    x=section_chart_data["budget fact"].div(1e6),
                    name="Бюджет Факт",
                    marker_color="#A23B72",
                    text=section_chart_data["budget fact"].apply(format_million_rub),
                    textposition="outside",
                    textfont=dict(size=18, color="white"),
                    orientation="h",
                )
            )
            if not hide_reserve:
                dev_colors_sec = ["#e74c3c" if v >= 0 else "#27ae60" for v in section_chart_data["reserve budget"]]
                fig.add_trace(
                    go.Bar(
                        y=section_chart_data["section"],
                        x=section_chart_data["reserve budget"].div(1e6),
                        name="Отклонение",
                        marker_color=dev_colors_sec,
                        text=section_chart_data["reserve budget"].apply(format_million_rub),
                        textposition="outside",
                        textfont=dict(size=18, color="white"),
                        orientation="h",
                    )
                )
            fig.update_layout(
                title=dict(text="План/факт/отклонение по лотам", font=dict(size=24)),
                xaxis_title=dict(text="млн руб.", font=dict(size=20)),
                yaxis_title=dict(text="Этапы", font=dict(size=20)),
                barmode="group",
                xaxis=dict(tickangle=0, tickfont=dict(size=16)),
                yaxis=dict(tickfont=dict(size=16), categoryorder="trace order"),
                legend=dict(font=dict(size=18)),
                height=max(400, len(section_chart_data) * 44),
            )
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

    _budget_section_chart()

    # Summary table — в млн руб., два знака после запятой
    st.subheader("Сводка бюджета по периоду")
    table_section = budget_summary.drop(columns=["period_original"], errors="ignore").copy()
    for col in ["budget plan", "budget fact", "reserve budget"]:
        if col in table_section.columns:
            table_section[col] = (table_section[col] / 1e6).round(2).apply(
                lambda x: f"{float(x):.2f} млн руб." if pd.notna(x) else ""
            )
    table_section = table_section.rename(columns={
        "budget plan": "Бюджет План, млн руб.",
        "budget fact": "Бюджет Факт, млн руб.",
        "reserve budget": "Отклонение, млн руб.",
    })
    st.markdown(
        budget_table_to_html(table_section, finance_deviation_column="Отклонение, млн руб."),
        unsafe_allow_html=True,
    )


# ==================== DASHBOARD: БДР (бюджет доходов и расходов) ====================
def dashboard_bdr(df):
    """
    БДР — бюджет доходов и расходов.
    Доходы и расходы берутся из колонок (доход/доходы/revenue, расход/расходы/expense)
    или из budget plan / budget fact: план = доходы, факт = расходы.
    Результат (сальдо) = Доходы - Расходы.
    """
    st.header("💰 БДР")

    if df is None or not hasattr(df, "columns") or df.empty:
        st.warning("⚠️ Нет данных для отображения. Загрузите данные проекта.")
        return

    # Определяем колонки для доходов и расходов
    def find_col(df, variants):
        for v in variants:
            for c in df.columns:
                if str(c).strip().lower() == v.lower() or v.lower() in str(c).lower():
                    return c
        return None

    revenue_col = find_col(
        df,
        ["доходы", "доход", "revenue", "income", "Бюджет План", "budget plan"],
    )
    expense_col = find_col(
        df,
        ["расходы", "расход", "expense", "Бюджет Факт", "budget fact"],
    )
    ensure_budget_columns(df)
    if revenue_col is None and "budget plan" in df.columns:
        revenue_col = "budget plan"
    if expense_col is None and "budget fact" in df.columns:
        expense_col = "budget fact"

    if revenue_col is None or expense_col is None:
        st.warning(
            "Для отчёта БДР нужны столбцы доходов и расходов "
            "(например «Доходы»/«Расходы» или «Бюджет План»/«Бюджет Факт»)."
        )
        return

    # Фильтры — в одном стиле с БДДС: строка 1 — Группировать по, Фильтр по проекту; строка 2 — Фильтр по лоту, Фильтр по этапу
    st.caption("Доходы и расходы по периоду.")

    col1, col2 = st.columns(2)
    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="bdr_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")
    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="bdr_project"
            )
        else:
            selected_project = "Все"

    col3, col4 = st.columns(2)
    with col3:
        # Фильтр по лоту: task name или лот/section (как в БДДС)
        if "task name" in df.columns:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox("Фильтр по лоту", tasks, key="bdr_task")
        else:
            bdr_lot_col = "лот" if "лот" in df.columns else ("lot" if "lot" in df.columns else "section")
            if bdr_lot_col in df.columns:
                bdr_lots = ["Все"] + sorted(df[bdr_lot_col].dropna().astype(str).unique().tolist())
                selected_task = st.selectbox("Фильтр по лоту", bdr_lots, key="bdr_lot")
            else:
                selected_task = "Все"
    with col4:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="bdr_section"
            )
        else:
            selected_section = "Все"

    # Период
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in df.columns:
        st.warning(f"Столбец периода «{period_col}» не найден. Добавьте даты в данные.")
        return

    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_task != "Все" and "task name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]
    bdr_lot_col = "лот" if "лот" in df.columns else ("lot" if "lot" in df.columns else "section")
    if selected_task != "Все" and "task name" not in filtered_df.columns and bdr_lot_col in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df[bdr_lot_col].astype(str).str.strip()
            == str(selected_task).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    filtered_df["_revenue"] = pd.to_numeric(filtered_df[revenue_col], errors="coerce")
    filtered_df["_expense"] = pd.to_numeric(filtered_df[expense_col], errors="coerce")
    filtered_df["_result"] = filtered_df["_revenue"] - filtered_df["_expense"]

    agg_dict = {"_revenue": "sum", "_expense": "sum", "_result": "sum"}
    bdr_summary = (
        filtered_df.groupby(period_col).agg(agg_dict).reset_index()
    )
    bdr_summary = bdr_summary.rename(
        columns={"_revenue": "Доходы", "_expense": "Расходы", "_result": "Результат (сальдо)"}
    )

    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if getattr(period_val, "freqstr", "") and ("M" in str(period_val.freqstr) or str(period_val.freqstr).startswith("M")):
                    return f"{get_russian_month_name(period_val)} {period_val.year}"
                if getattr(period_val, "freqstr", "") and "Q" in str(period_val.freqstr):
                    return f"Q{period_val.quarter} {period_val.year}"
                return str(period_val)
            except Exception:
                return str(period_val)
        return str(period_val)

    bdr_summary["period_display"] = bdr_summary[period_col].apply(format_period_display)

    @st.fragment
    def _bdr_chart():
        view_type = st.selectbox(
            "Вид отображения", ["По месяцам", "Накопительно"], key="bdr_view"
        )
        chart_df = bdr_summary.copy()
        if view_type == "Накопительно":
            chart_df["Доходы"] = chart_df["Доходы"].cumsum()
            chart_df["Расходы"] = chart_df["Расходы"].cumsum()
            chart_df["Результат (сальдо)"] = chart_df["Результат (сальдо)"].cumsum()
            title_suffix = " (накопительно)"
        else:
            title_suffix = ""
        fig = go.Figure()
        x_vals = chart_df["period_display"]
        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=chart_df["Доходы"].div(1e6),
                name="Доходы",
                marker_color="#2E86AB",
                text=chart_df["Доходы"].apply(format_million_rub),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )
        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=chart_df["Расходы"].div(1e6),
                name="Расходы",
                marker_color="#A23B72",
                text=chart_df["Расходы"].apply(format_million_rub),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )
        fig.add_trace(
            go.Bar(
                x=x_vals,
                y=chart_df["Результат (сальдо)"].div(1e6),
                name="Результат (сальдо)",
                marker_color="#06A77D",
                text=chart_df["Результат (сальдо)"].apply(format_million_rub),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )
        fig.update_layout(
            title=f"БДР — доходы и расходы{title_suffix}",
            xaxis_title=period_label,
            yaxis_title="млн руб.",
            barmode="group",
            xaxis=dict(tickangle=-45),
        )
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

    _bdr_chart()

    st.subheader("Сводка БДР по периоду")
    display_df = bdr_summary[
        [c for c in ["period_display", "Доходы", "Расходы", "Результат (сальдо)"] if c in bdr_summary.columns]
    ].copy()
    display_df = display_df.rename(columns={"period_display": period_label})
    for col in ["Доходы", "Расходы", "Результат (сальдо)"]:
        if col in display_df.columns:
            display_df[col] = (display_df[col] / 1e6).round(2).apply(
                lambda x: f"{float(x):.2f} млн руб." if pd.notna(x) else ""
            )
    display_df = display_df.rename(columns={
        "Доходы": "Доходы, млн руб.",
        "Расходы": "Расходы, млн руб.",
        "Результат (сальдо)": "Результат (сальдо), млн руб.",
    })
    st.markdown(
        budget_table_to_html(display_df, finance_deviation_column="Результат (сальдо), млн руб."),
        unsafe_allow_html=True,
    )


# ==================== DASHBOARD 8.6: RD Delay Chart ====================
def dashboard_rd_delay(df):
    st.subheader("⏱️ Просрочка выдачи РД")

    # Find column names (they might have different formats)
    # Try to find columns by partial name matching
    def find_column(df, possible_names):
        """Find column by possible names"""
        for col in df.columns:
            # Normalize column name: remove newlines, extra spaces, normalize case
            col_normalized = str(col).replace("\n", " ").replace("\r", " ").strip()
            col_lower = col_normalized.lower()

            for name in possible_names:
                name_lower = name.lower().strip()
                # Exact match (case insensitive)
                if name_lower == col_lower:
                    return col
                # Substring match
                if name_lower in col_lower or col_lower in name_lower:
                    return col
                # Check if all key words from name are in column
                name_words = [w for w in name_lower.split() if len(w) > 2]
                if name_words and all(word in col_lower for word in name_words):
                    return col

        # Special handling for RD count column with key words
        if any(
            "разделов" in n.lower() and "рд" in n.lower() and "договор" in n.lower()
            for n in possible_names
        ):
            for col in df.columns:
                col_lower = str(col).lower().replace("\n", " ").replace("\r", " ")
                key_words = ["разделов", "рд", "договор", "количество"]
                if all(word in col_lower for word in key_words if len(word) > 3):
                    return col

        return None

    # Find required columns
    # Column for Y-axis: "Отклонение разделов РД" (exact match from CSV file)
    # This is column 17 in the CSV file (after header row)
    rd_deviation_col = None

    # First try exact match
    if "Отклонение разделов РД" in df.columns:
        rd_deviation_col = "Отклонение разделов РД"
    else:
        # Try with find_column function for variations
        rd_deviation_col = find_column(
            df,
            [
                "Отклонение разделов РД",
                "Отклонение разделов рд",
                "отклонение разделов рд",
                "Отклон. Количества разделов РД",
                "Отклонение количества разделов РД",
                "Отклон. разделов РД",
                "Отклонение разделов РД по Договору",
            ],
        )

        # Special handling: if not found, try to find by key words
        if not rd_deviation_col:
            for col in df.columns:
                col_lower = str(col).lower().replace("\n", " ").replace("\r", " ")
                key_words = ["отклон", "раздел", "рд"]
                if all(word in col_lower for word in key_words if len(word) > 3):
                    rd_deviation_col = col
                    break

    if not rd_deviation_col:
        st.warning("⚠️ Колонка 'Отклонение разделов РД' не найдена.")
        return

    # Find required columns
    plan_start_col = (
        "plan start"
        if "plan start" in df.columns
        else find_column(df, ["Старт План", "План Старт"])
    )
    project_col = (
        "project name"
        if "project name" in df.columns
        else find_column(df, ["Проект", "project"])
    )
    section_col = (
        "section" if "section" in df.columns else find_column(df, ["Раздел", "section"])
    )
    task_col = (
        "task name"
        if "task name" in df.columns
        else find_column(df, ["Задача", "task"])
    )

    # Check if required columns exist
    missing_cols = []
    if not project_col or project_col not in df.columns:
        missing_cols.append("Проект (project name)")
    if not section_col or section_col not in df.columns:
        missing_cols.append("Раздел (section)")
    if not task_col or task_col not in df.columns:
        missing_cols.append("Задача (task name)")

    if missing_cols:
        st.warning(f"⚠️ Отсутствуют необходимые колонки: {', '.join(missing_cols)}")
        st.info("Пожалуйста, убедитесь, что файл содержит все необходимые колонки.")
        return

    # Add filters
    st.subheader("Фильтры")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # Project filter
    with filter_col1:
        try:
            projects = ["Все"] + sorted(df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="rd_delay_project"
            )
        except Exception as e:
            st.error(f"Ошибка при загрузке списка проектов: {str(e)}")
            return

    # Section filter
    with filter_col2:
        try:
            sections = ["Все"] + sorted(df[section_col].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="rd_delay_section"
            )
        except Exception as e:
            st.error(f"Ошибка при загрузке списка разделов: {str(e)}")
            return

    # Apply filters
    filtered_df = df.copy()

    if selected_project != "Все":
        filtered_df = filtered_df[
            filtered_df[project_col].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    if selected_section != "Все":
        filtered_df = filtered_df[
            filtered_df[section_col].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Prepare data for "Просрочка выдачи РД"
    # X-axis: "Задача" (each task is a separate bar)
    # Y-axis: "Отклонение разделов РД" (deviation values)
    try:
        # Convert "Отклонение разделов РД" to numeric - handle comma as decimal separator
        # First, get the raw column values
        rd_deviation_raw = filtered_df[rd_deviation_col].copy()

        # Convert to string, handling NaN properly
        rd_deviation_str = rd_deviation_raw.astype(str)

        # Replace various representations of empty/NaN values with empty string
        rd_deviation_str = rd_deviation_str.replace(
            ["nan", "None", "NaN", "NaT", "<NA>", "None"], ""
        )

        # Strip whitespace
        rd_deviation_str = rd_deviation_str.str.strip()

        # Replace comma with dot for decimal separator FIRST (European format: 6,00 -> 6.00)
        rd_deviation_str = rd_deviation_str.str.replace(",", ".", regex=False)

        # Now replace empty strings with '0' AFTER comma replacement
        rd_deviation_str = rd_deviation_str.replace("", "0")

        # Convert to numeric - this handles most cases
        filtered_df["rd_deviation_numeric"] = pd.to_numeric(
            rd_deviation_str, errors="coerce"
        ).fillna(0)

        # Determine grouping mode: if section is selected, show tasks; otherwise group by project
        show_by_tasks = selected_section != "Все"

        if show_by_tasks:
            # Prepare data for chart - each task is a separate bar
            # Create label combining section and task for better readability
            if section_col and section_col in filtered_df.columns:
                filtered_df["Задача_полная"] = (
                    filtered_df[section_col].astype(str)
                    + " | "
                    + filtered_df[task_col].astype(str)
                )
            else:
                filtered_df["Задача_полная"] = filtered_df[task_col].astype(str)

            chart_data = filtered_df[
                [task_col, "Задача_полная", "rd_deviation_numeric"]
            ].copy()
            chart_data.columns = ["Задача", "Задача_полная", "Отклонение разделов РД"]

            # Sort by deviation value (descending) to show largest deviations first
            chart_data = chart_data.sort_values(
                "Отклонение разделов РД", ascending=False
            )
            y_column = "Задача_полная"
            y_title = "Задача"
        else:
            # Group by project and sum deviations
            if project_col and project_col in filtered_df.columns:
                chart_data = (
                    filtered_df.groupby(project_col)
                    .agg({"rd_deviation_numeric": "sum"})
                    .reset_index()
                )
                chart_data.columns = ["Проект", "Отклонение разделов РД"]

                # Sort by deviation value (descending)
                chart_data = chart_data.sort_values(
                    "Отклонение разделов РД", ascending=False
                )
                y_column = "Проект"
                y_title = "Проект"
            else:
                st.info("Нет данных для построения графика.")
                return

        if chart_data.empty:
            st.info("Нет данных для построения графика.")
            return

        # Format text values for display on bars (same approach as "Отклонение от базового плана")
        text_values = []
        for _, row in chart_data.iterrows():
            val = row["Отклонение разделов РД"]
            if pd.notna(val):
                text_values.append(f"{int(round(val, 0))}")
            else:
                text_values.append("")

        # Create horizontal bar chart
        fig = px.bar(
            chart_data,
            x="Отклонение разделов РД",
            y=y_column,
            orientation="h",
            title="Просрочка выдачи РД",
            labels={
                y_column: y_title,
                "Отклонение разделов РД": "Отклонение разделов РД",
            },
            text=text_values,
            color_discrete_sequence=["#2E86AB"],  # Single color for all bars
        )

        # Format text labels (same as "Отклонение от базового плана")
        fig.update_traces(
            textposition="outside",
            textfont=dict(size=14, color="white"),
            marker=dict(line=dict(width=1, color="white")),
            showlegend=False,  # Hide legend
        )

        # Add vertical line at 0 to separate positive and negative deviations (without annotation)
        fig.add_vline(x=0, line_dash="dash", line_color="gray")

        # Set category order to show largest values at top (descending order)
        # For horizontal bars, reverse the list so largest is at top
        category_list = chart_data[y_column].tolist()
        fig.update_layout(
            xaxis_title="Отклонение разделов РД",
            yaxis_title=y_title,
            height=max(
                600, len(chart_data) * 40
            ),  # Adjust height based on number of items
            showlegend=False,
            yaxis=dict(
                tickangle=0,  # Horizontal labels
                categoryorder="array",
                categoryarray=list(
                    reversed(category_list)
                ),  # Reverse to show largest at top
            ),
            bargap=0.1,  # Reduce gap between bars to make them appear larger
        )

        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Summary table
        st.subheader("Сводка по просрочке")
        # Show appropriate columns based on grouping mode
        if show_by_tasks:
            summary_table = chart_data[
                ["Задача_полная", "Отклонение разделов РД"]
            ].copy()
            summary_table.columns = ["Задача", "Отклонение разделов РД"]
        else:
            summary_table = chart_data[["Проект", "Отклонение разделов РД"]].copy()
        if "Отклонение разделов РД" in summary_table.columns:
            summary_table["Отклонение разделов РД"] = summary_table["Отклонение разделов РД"].apply(
                lambda x: int(round(float(x), 0)) if pd.notna(x) else ""
            )
        st.table(style_dataframe_for_dark_theme(summary_table))

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_deviation = chart_data["Отклонение разделов РД"].sum()
            st.metric(
                "Сумма отклонений",
                f"{total_deviation:,.0f}" if pd.notna(total_deviation) else "Н/Д",
            )
        with col2:
            positive_deviation = chart_data[chart_data["Отклонение разделов РД"] > 0][
                "Отклонение разделов РД"
            ].sum()
            st.metric(
                "Положительные отклонения",
                f"{positive_deviation:,.0f}" if pd.notna(positive_deviation) else "0",
            )
        with col3:
            negative_deviation = chart_data[chart_data["Отклонение разделов РД"] < 0][
                "Отклонение разделов РД"
            ].sum()
            st.metric(
                "Отрицательные отклонения",
                f"{negative_deviation:,.0f}" if pd.notna(negative_deviation) else "0",
            )

    except Exception as e:
        st.error(f"Ошибка при построении графика 'Просрочка выдачи РД': {str(e)}")


# ==================== DASHBOARD 8.6.5: Technique Visualization ====================
def dashboard_technique(df):
    st.header("🔧 Аналитика по технике")

    # Get technique data from session state
    technique_df = st.session_state.get("technique_data", None)

    if technique_df is None or technique_df.empty:
        st.warning(
            "⚠️ Для отображения аналитики по технике необходимо загрузить файл с данными о технике."
        )
        st.info(
            "📋 Ожидаемые колонки: Проект, Контрагент, Период, План, Среднее за месяц или Среднее за неделю, 1–5 неделя, Дельта, Дельта (%)"
        )
        return

    # Данные для круговых и иных диаграмм берутся только из загруженного файла (session technique_data)
    st.caption("📁 Данные из загруженного файла с данными о технике.")

    # Create working copy
    work_df = technique_df.copy()

    # Helper function to find columns by partial match (handles encoding issues)
    def find_column_by_partial(df, possible_names):
        """Find column by possible names (exact or partial match)"""
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for name in possible_names:
                name_lower = str(name).lower().strip()
                if (
                    name_lower == col_lower
                    or name_lower in col_lower
                    or col_lower in name_lower
                ):
                    return col
        return None

    # sample_resources_data.csv: Проект, Контрагент, Период, План, Среднее за месяц, 1–5 неделя, Дельта, Дельта (%)
    # Use Russian column names directly

    # Check required columns - Контрагент is essential
    if "Контрагент" not in work_df.columns:
        # Try to find contractor column by partial match
        contractor_col = find_column_by_partial(
            work_df,
            [
                "Контрагент",
                "контрагент",
                "Подразделение",
                "подразделение",
                "contractor",
            ],
        )
        if contractor_col:
            work_df["Контрагент"] = work_df[contractor_col]
        else:
            st.error(f"❌ Отсутствует необходимая колонка 'Контрагент'")
            st.info(f"Доступные колонки: {', '.join(work_df.columns)}")
            return

    # Find week columns dynamically - also try partial match
    week_columns = []
    for week_num in range(1, 6):
        week_col = f"{week_num} неделя"
        if week_col in work_df.columns:
            week_columns.append(week_col)
        else:
            # Try to find by partial match
            found_col = find_column_by_partial(
                work_df,
                [
                    week_col,
                    f"{week_num} недел",
                    f"недел {week_num}",
                    f"week {week_num}",
                ],
            )
            if found_col:
                week_columns.append(found_col)

    # Check if we have any data
    if work_df.empty:
        st.warning("⚠️ Данные пусты после обработки.")
        return

    # Process numeric columns
    # Process План
    if "План" in work_df.columns:
        work_df["План_numeric"] = pd.to_numeric(
            work_df["План"].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        work_df["План_numeric"] = 0

    # Process week columns - convert to numeric, handle empty strings
    for week_col in week_columns:
        work_df[f"{week_col}_numeric"] = pd.to_numeric(
            work_df[week_col]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", "")
            .replace("", "0"),
            errors="coerce",
        ).fillna(0)

    # Факт: sample_resources_data.csv — «Среднее за месяц»; sample_technique_data.csv — «Среднее за неделю»
    if "Среднее за месяц" in work_df.columns:
        work_df["Среднее_за_месяц_numeric"] = pd.to_numeric(
            work_df["Среднее за месяц"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        work_df["week_sum"] = work_df["Среднее_за_месяц_numeric"]
    elif "Среднее за неделю" in work_df.columns:
        work_df["Среднее_за_неделю_numeric"] = pd.to_numeric(
            work_df["Среднее за неделю"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        work_df["week_sum"] = work_df["Среднее_за_неделю_numeric"]
    elif week_columns:
        week_numeric_cols = [f"{col}_numeric" for col in week_columns]
        work_df["week_sum"] = work_df[week_numeric_cols].sum(axis=1)
    else:
        work_df["week_sum"] = 0

    # Process Дельта (Delta) if available - try to find column by partial match
    delta_col = None
    if "Дельта" in work_df.columns:
        delta_col = "Дельта"
    else:
        delta_col = find_column_by_partial(
            work_df, ["Дельта", "дельта", "delta", "Delta", "Дельта (без %)"]
        )

    if delta_col and delta_col in work_df.columns:
        work_df["Дельта_numeric"] = pd.to_numeric(
            work_df[delta_col].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        # Calculate delta as plan - fact (week_sum)
        work_df["Дельта_numeric"] = work_df["План_numeric"] - work_df["week_sum"]

    # Process Дельта (%) (Delta %) if available - extract numeric value from percentage string
    # Try to find column by partial match
    delta_pct_col = None
    if "Дельта (%)" in work_df.columns:
        delta_pct_col = "Дельта (%)"
    else:
        delta_pct_col = find_column_by_partial(
            work_df,
            [
                "Дельта (%)",
                "Дельта %",
                "дельта (%)",
                "дельта %",
                "Delta %",
                "delta %",
                "Дельта(%)",
                "Дельта%",
            ],
        )

    if delta_pct_col and delta_pct_col in work_df.columns:

        def extract_percentage(value):
            """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
            if pd.isna(value):
                return 0
            # If already numeric, return as is
            if isinstance(value, (int, float)):
                return float(value)
            # Otherwise, try to extract from string
            value_str = str(value).strip()
            # Remove % sign and convert to float
            value_str = value_str.replace("%", "").replace(",", ".").replace(" ", "")
            try:
                return float(value_str)
            except:
                return 0

        work_df["Дельта_процент_numeric"] = work_df[delta_pct_col].apply(
            extract_percentage
        )
    else:
        # Calculate delta percentage if we have delta and plan
        work_df["Дельта_процент_numeric"] = 0
        if "Дельта_numeric" in work_df.columns and "План_numeric" in work_df.columns:
            mask = work_df["План_numeric"] != 0
            work_df.loc[mask, "Дельта_процент_numeric"] = (
                work_df.loc[mask, "Дельта_numeric"] / work_df.loc[mask, "План_numeric"]
            ) * 100
        work_df["Дельта_процент_numeric"] = work_df["Дельта_процент_numeric"].fillna(0)

    # Find Проект column
    period_col = None
    if "Период" in work_df.columns:
        period_col = "Период"
    else:
        # Try to find period column by partial match
        period_col = find_column_by_partial(
            work_df, ["Период", "период", "period", "Месяц", "месяц", "month"]
        )

    if period_col:
        # Parse period format like "дек.25" or "декабрь 2025"
        def parse_period(period_val):
            if pd.isna(period_val):
                return None
            period_str = str(period_val).strip()
            # Try to extract year and month
            # Format: "дек.25" -> period="дек.2025"
            # Format: "декабрь 2025" -> period="декабрь 2025"
            if "." in period_str:
                parts = period_str.split(".")
                if len(parts) >= 2:
                    month_part = parts[0].strip()
                    year_part = parts[1].strip()
                    try:
                        year = int(year_part)
                        if year < 100:
                            year = 2000 + year
                        return f"{month_part}.{year}"
                    except:
                        pass
            return period_str

        work_df["period_display"] = work_df[period_col].apply(parse_period)
    else:
        work_df["period_display"] = "Н/Д"

    # Find Проект column
    project_col = None
    if "Проект" in work_df.columns:
        project_col = "Проект"
    else:
        project_col = find_column_by_partial(
            work_df, ["Проект", "проект", "project", "Project"]
        )

    # Filters - project and contractor filters
    col1, col2 = st.columns(2)

    with col1:
        # Project filter - multiselect для выбора нескольких проектов
        if project_col and project_col in work_df.columns:
            all_projects = sorted(work_df[project_col].dropna().unique().tolist())
            selected_projects = st.multiselect(
                "Фильтр по проектам (можно выбрать несколько)",
                all_projects,
                default=all_projects if len(all_projects) <= 3 else all_projects[:3],
                key="technique_projects",
            )
        else:
            selected_projects = []
            st.info("Колонка 'Проект' не найдена")

    with col2:
        # Contractor filter
        if "Контрагент" in work_df.columns:
            contractors = ["Все"] + sorted(
                work_df["Контрагент"].dropna().unique().tolist()
            )
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", contractors, key="technique_contractor"
            )
        else:
            selected_contractor = "Все"
            st.info("Колонка 'Контрагент' не найдена")

    # Apply filters
    filtered_df = work_df.copy()
    if selected_projects and project_col and project_col in filtered_df.columns:
        # Фильтруем по выбранным проектам
        project_mask = (
            filtered_df[project_col]
            .astype(str)
            .str.strip()
            .isin([str(p).strip() for p in selected_projects])
        )
        filtered_df = filtered_df[project_mask]
    if selected_contractor != "Все" and "Контрагент" in filtered_df.columns:
        # Use string comparison with strip to handle whitespace
        filtered_df = filtered_df[
            filtered_df["Контрагент"].astype(str).str.strip()
            == str(selected_contractor).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для отображения с выбранными фильтрами.")
        return

    # Ensure Контрагент column exists and has values
    if (
        "Контрагент" not in filtered_df.columns
        or filtered_df["Контрагент"].isna().all()
    ):
        st.error("❌ Колонка 'Контрагент' отсутствует или пуста после фильтрации.")
        return

    # Remove rows where Контрагент is NaN before grouping
    filtered_df = filtered_df[filtered_df["Контрагент"].notna()].copy()

    if filtered_df.empty:
        st.info("Нет данных с указанными контрагентами после фильтрации.")
        return

    # Определяем список проектов для обработки
    if selected_projects and project_col and project_col in filtered_df.columns:
        projects_to_process = selected_projects
    else:
        # Если проекты не выбраны или колонка не найдена, обрабатываем все проекты
        if project_col and project_col in filtered_df.columns:
            projects_to_process = sorted(
                filtered_df[project_col].dropna().unique().tolist()
            )
        else:
            projects_to_process = ["Все проекты"]

    # Обрабатываем каждый проект отдельно
    for project_name in projects_to_process:
        # Фильтруем данные по проекту
        project_filtered_df = filtered_df.copy()
        if (
            project_col
            and project_col in project_filtered_df.columns
            and project_name != "Все проекты"
        ):
            project_filtered_df = project_filtered_df[
                project_filtered_df[project_col].astype(str).str.strip()
                == str(project_name).strip()
            ]

        if project_filtered_df.empty:
            continue

        # Заголовок для проекта
        if len(projects_to_process) > 1:
            st.markdown("---")
            st.subheader(f"📊 Проект: {project_name}")

        # ========== Chart 1: Pie Chart by Contractor (Delta %) ==========
        st.subheader("📊 Круговая диаграмма: Распределение дельты (%) по контрагентам")

        # Group by Контрагент and aggregate for pie chart (Delta %)
        # Ensure Дельта_процент_numeric exists - check if it was created in work_df
        if "Дельта_процент_numeric" not in project_filtered_df.columns:
            # Try to find Дельта (%) column by partial match
            delta_pct_col = None
            if "Дельта (%)" in project_filtered_df.columns:
                delta_pct_col = "Дельта (%)"
            else:
                delta_pct_col = find_column_by_partial(
                    project_filtered_df,
                    [
                        "Дельта (%)",
                        "Дельта %",
                        "дельта (%)",
                        "дельта %",
                        "Delta %",
                        "delta %",
                        "Дельта(%)",
                        "Дельта%",
                    ],
                )

            if delta_pct_col and delta_pct_col in project_filtered_df.columns:
                # Extract percentage values from the column
                def extract_percentage(value):
                    """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
                    if pd.isna(value):
                        return 0
                    # If already numeric, return as is
                    if isinstance(value, (int, float)):
                        return float(value)
                    # Otherwise, try to extract from string
                    value_str = str(value).strip()
                    # Remove % sign and convert to float
                    value_str = (
                        value_str.replace("%", "").replace(",", ".").replace(" ", "")
                    )
                    try:
                        return float(value_str)
                    except:
                        return 0

                project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                    delta_pct_col
                ].apply(extract_percentage)
            else:
                # Try to calculate from Дельта and План if available
                if (
                    "Дельта_numeric" in project_filtered_df.columns
                    and "План_numeric" in project_filtered_df.columns
                ):
                    project_filtered_df["Дельта_процент_numeric"] = 0
                    mask = project_filtered_df["План_numeric"] != 0
                    project_filtered_df.loc[mask, "Дельта_процент_numeric"] = (
                        project_filtered_df.loc[mask, "Дельта_numeric"]
                        / project_filtered_df.loc[mask, "План_numeric"]
                    ) * 100
                    project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                        "Дельта_процент_numeric"
                    ].fillna(0)
                else:
                    st.error(
                        "❌ Не удалось найти или рассчитать Дельта (%). Отсутствуют необходимые колонки."
                    )
                    st.info(
                        f"Доступные колонки: {', '.join(project_filtered_df.columns)}"
                    )
                    contractor_delta_pct = pd.DataFrame(
                        columns=["Контрагент", "Дельта (%)"]
                    )

        # Group by contractor and aggregate
        if "Дельта_процент_numeric" in project_filtered_df.columns:
            # Check if we have any data before grouping
            if (
                not project_filtered_df.empty
                and "Контрагент" in project_filtered_df.columns
            ):
                contractor_delta_pct = (
                    project_filtered_df.groupby("Контрагент")
                    .agg({"Дельта_процент_numeric": "sum"})  # Sum of delta percentages
                    .reset_index()
                )

                contractor_delta_pct.columns = ["Контрагент", "Дельта (%)"]
            else:
                contractor_delta_pct = pd.DataFrame(
                    columns=["Контрагент", "Дельта (%)"]
                )
        else:
            contractor_delta_pct = pd.DataFrame(columns=["Контрагент", "Дельта (%)"])

        # Check if we have data (внутри цикла по проектам — круговая и столбчатая по каждому проекту)
        if contractor_delta_pct.empty or len(contractor_delta_pct) == 0:
            st.info("Нет данных для отображения круговой диаграммы.")
        else:
            # Ensure Дельта (%) is numeric
            contractor_delta_pct["Дельта (%)"] = pd.to_numeric(
                contractor_delta_pct["Дельта (%)"], errors="coerce"
            ).fillna(0)

            # Check if we have any non-zero values
            total_abs_sum = contractor_delta_pct["Дельта (%)"].abs().sum()

            if total_abs_sum == 0:
                st.info(
                    "Все значения дельты (%) равны нулю. Диаграмма не может быть построена."
                )
            else:
                # Remove only exactly zero values (not small values)
                non_zero_data = contractor_delta_pct[
                    contractor_delta_pct["Дельта (%)"] != 0
                ].copy()

                # Use non-zero data if available
                if not non_zero_data.empty:
                    contractor_delta_pct = non_zero_data

                # Sort by absolute value for better visualization
                contractor_delta_pct = contractor_delta_pct.sort_values(
                    "Дельта (%)", key=abs, ascending=False
                )

                # Create a copy with absolute values for pie chart (pie charts don't support negative values)
                contractor_delta_pct_abs = contractor_delta_pct.copy()
                contractor_delta_pct_abs["Дельта (%)_abs"] = contractor_delta_pct_abs[
                    "Дельта (%)"
                ].abs()

                # Store original values for display
                original_values = contractor_delta_pct_abs["Дельта (%)"].tolist()

                # Create pie chart using absolute values
                fig_pie = px.pie(
                    contractor_delta_pct_abs,
                    values="Дельта (%)_abs",
                    names="Контрагент",
                    title="Распределение дельты (%) по контрагентам",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )

                fig_pie.update_layout(
                    height=600,
                    showlegend=True,
                    legend=dict(
                        orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                    ),
                    title_font_size=16,
                )

                # На круговой диаграмме: подпись с абсолютным значением и процентом (без наведения)
                fig_pie.update_traces(
                    textinfo="label+value+percent",
                    texttemplate="%{label}<br>%{value}<br>(%{percent:.0%})",
                    textposition="inside",
                    textfont=dict(size=12, color="white"),
                    customdata=original_values,
                    hovertemplate="<b>%{label}</b><br>Дельта (%): %{customdata:.0f}%<br>Процент: %{percent}<br><extra></extra>",
                )

                fig_pie = apply_chart_background(fig_pie)
                st.plotly_chart(fig_pie, use_container_width=True)

        # ========== Chart 2: Bar Chart by Contractor (Plan, Average, Delta) ==========
        st.subheader(
            "📊 Столбчатая диаграмма: План, Среднее за месяц, Дельта (группировка по контрагенту)"
        )

        # Group by Контрагент and aggregate
        # Ensure Дельта_numeric exists
        if "Дельта_numeric" not in project_filtered_df.columns:
            # Try to calculate if missing
            if (
                "План_numeric" in project_filtered_df.columns
                and "week_sum" in project_filtered_df.columns
            ):
                project_filtered_df["Дельта_numeric"] = (
                    project_filtered_df["План_numeric"]
                    - project_filtered_df["week_sum"]
                )
            else:
                project_filtered_df["Дельта_numeric"] = 0

        contractor_data = (
            project_filtered_df.groupby("Контрагент")
            .agg(
                {
                    "План_numeric": "sum",  # Sum of plans
                    "week_sum": "sum",  # Sum of weeks = среднее за месяц
                    "Дельта_numeric": "sum",  # Sum of deltas
                }
            )
            .reset_index()
        )

        contractor_data.columns = ["Контрагент", "План", "Среднее за месяц", "Дельта"]

        # Ensure Дельта column has numeric values
        contractor_data["Дельта"] = pd.to_numeric(
            contractor_data["Дельта"], errors="coerce"
        ).fillna(0)

        # Sort by contractor name
        contractor_data = contractor_data.sort_values("Контрагент")

        # Create bar chart
        fig_bar = go.Figure()

        # Add bars for Plan
        fig_bar.add_trace(
            go.Bar(
                name="План",
                x=contractor_data["Контрагент"],
                y=contractor_data["План"],
                marker_color="#3498db",
                text=contractor_data["План"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )

        # Add bars for Average
        fig_bar.add_trace(
            go.Bar(
                name="Среднее за месяц",
                x=contractor_data["Контрагент"],
                y=contractor_data["Среднее за месяц"],
                marker_color="#2ecc71",
                text=contractor_data["Среднее за месяц"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )

        # Add bars for Delta - ensure values are properly formatted
        # Разделяем на положительные и отрицательные значения для разных цветов
        delta_values = contractor_data["Дельта"].fillna(0)
        delta_abs = delta_values.abs()  # Абсолютные значения для отображения

        # Положительные значения дельты (зеленый)
        positive_mask = delta_values > 0
        if positive_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (+)",
                    x=contractor_data.loc[positive_mask, "Контрагент"],
                    y=delta_abs[positive_mask],
                    marker_color="#2ecc71",  # Зеленый для положительных
                    text=delta_abs[positive_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Отрицательные значения дельты (красный)
        negative_mask = delta_values < 0
        if negative_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (-)",
                    x=contractor_data.loc[negative_mask, "Контрагент"],
                    y=delta_abs[negative_mask],
                    marker_color="#e74c3c",  # Красный для отрицательных
                    text=delta_abs[negative_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Нулевые значения (если есть)
        zero_mask = delta_values == 0
        if zero_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (0)",
                    x=contractor_data.loc[zero_mask, "Контрагент"],
                    y=delta_abs[zero_mask],
                    marker_color="#95a5a6",  # Серый для нулевых
                    text=delta_abs[zero_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Update layout
        fig_bar.update_layout(
            title="План, Среднее за месяц и Дельта по контрагентам",
            xaxis_title="Контрагент",
            yaxis_title="Значение",
            barmode="group",
            height=600,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            xaxis=dict(tickangle=-45),
        )

        fig_bar = apply_chart_background(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

        # ========== Chart 3: Pie Chart by Contractor (Plan + Average) ==========
        st.subheader(
            "📊 Круговая диаграмма: Распределение суммы Плана и Среднего за месяц по контрагентам"
        )

        # Group by Контрагент and aggregate for pie chart (Plan + Average)
        contractor_plan_avg = (
            project_filtered_df.groupby("Контрагент")
            .agg(
                {
                    "План_numeric": "sum",  # Sum of plans
                    "week_sum": "sum",  # Sum of weeks = среднее за месяц
                    "Дельта_numeric": "sum",  # Sum of deltas
                }
            )
            .reset_index()
        )

        contractor_plan_avg.columns = [
            "Контрагент",
            "План",
            "Среднее за месяц",
            "Дельта",
        ]

        # Calculate sum of Plan + Average for each contractor
        contractor_plan_avg["Сумма"] = (
            contractor_plan_avg["План"] + contractor_plan_avg["Среднее за месяц"]
        )

        # Calculate доля факта (Среднее за месяц / Сумма * 100) and доля отклонения (Дельта / План * 100)
        contractor_plan_avg["Доля факта (%)"] = 0
        contractor_plan_avg["Доля отклонения (%)"] = 0
        mask_sum = contractor_plan_avg["Сумма"] != 0
        contractor_plan_avg.loc[mask_sum, "Доля факта (%)"] = (
            contractor_plan_avg.loc[mask_sum, "Среднее за месяц"]
            / contractor_plan_avg.loc[mask_sum, "Сумма"]
        ) * 100
        mask_plan = contractor_plan_avg["План"] != 0
        contractor_plan_avg.loc[mask_plan, "Доля отклонения (%)"] = (
            contractor_plan_avg.loc[mask_plan, "Дельта"]
            / contractor_plan_avg.loc[mask_plan, "План"]
        ) * 100

        # Remove zero values for pie chart
        contractor_plan_avg = contractor_plan_avg[
            contractor_plan_avg["Сумма"] != 0
        ].copy()

        if contractor_plan_avg.empty:
            st.info("Нет данных для отображения.")
        else:
            # Sort by sum value for better visualization
            contractor_plan_avg = contractor_plan_avg.sort_values(
                "Сумма", ascending=False
            )

            # Create pie chart
            fig_pie_plan_avg = px.pie(
                contractor_plan_avg,
                values="Сумма",
                names="Контрагент",
                title="Распределение суммы Плана и Среднего за месяц по контрагентам",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )

            fig_pie_plan_avg.update_layout(
                height=600,
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                ),
                title_font_size=16,
            )

            # На круговой диаграмме: абсолютное значение и процент в подписи (без наведения)
            fig_pie_plan_avg.update_traces(
                textinfo="label+value+percent",
                texttemplate="%{label}<br>%{value:,.0f}<br>(%{percent:.0%})",
                textposition="inside",
                textfont=dict(size=12, color="white"),
            )
            # Долю факта и отклонения оставляем в hover
            fig_pie_plan_avg.update_traces(
                customdata=list(
                    zip(
                        contractor_plan_avg["Доля факта (%)"],
                        contractor_plan_avg["Доля отклонения (%)"],
                    )
                ),
                hovertemplate="<b>%{label}</b><br>Сумма: %{value:,.0f}<br>Процент: %{percent}<br>Доля факта: %{customdata[0]:.0f}%<br>Доля отклонения: %{customdata[1]:.0f}%<br><extra></extra>",
            )

            fig_pie_plan_avg = apply_chart_background(fig_pie_plan_avg)
            st.plotly_chart(fig_pie_plan_avg, use_container_width=True)

        # ========== Summary Table ==========
        st.subheader("📋 Сводная таблица по контрагентам")

        # Format numbers for display
        summary_table = contractor_data.copy()
        summary_table["План"] = summary_table["План"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )
        summary_table["Среднее за месяц"] = summary_table["Среднее за месяц"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )
        summary_table["Дельта"] = summary_table["Дельта"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )

        st.table(style_dataframe_for_dark_theme(summary_table))

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            total_plan = contractor_data["План"].sum()
            st.metric("Общий план", f"{int(total_plan)}")

        with col2:
            total_average = contractor_data["Среднее за месяц"].sum()
            st.metric("Общее среднее за месяц", f"{int(total_average)}")

        with col3:
            total_delta = contractor_data["Дельта"].sum()
            st.metric("Общая дельта", f"{int(total_delta)}")


# ==================== DASHBOARD 8.6.7: Workforce Movement ====================
def dashboard_workforce_movement(df):
    st.header("👥 График движения рабочей силы")

    # Get resources and technique data from session state
    resources_df = st.session_state.get("resources_data", None)
    technique_df = st.session_state.get("technique_data", None)

    # Combine both data sources if available
    combined_df = None

    if resources_df is not None and not resources_df.empty:
        combined_df = resources_df.copy()
        combined_df["data_source"] = "Ресурсы"

    if technique_df is not None and not technique_df.empty:
        if combined_df is not None:
            technique_copy = technique_df.copy()
            technique_copy["data_source"] = "Техника"
            # Align columns before concatenation to avoid issues
            # If technique has "Среднее за месяц" but resources has "Среднее за неделю", keep both
            combined_df = pd.concat(
                [combined_df, technique_copy], ignore_index=True, sort=False
            )
        else:
            combined_df = technique_df.copy()
            combined_df["data_source"] = "Техника"

    if combined_df is None or combined_df.empty:
        st.warning(
            "⚠️ Для отображения графика движения рабочей силы необходимо загрузить файл с данными о ресурсах или технике."
        )
        st.info(
            "📋 Ожидаемые колонки: Проект, Контрагент, Период, План, Среднее за месяц (ресурсы) или Среднее за неделю (техника), 1–5 неделя, Дельта, Дельта (%)"
        )
        return

    # Данные для круговых и иных диаграмм берутся только из загруженных файлов (resources_data + technique_data)
    st.caption("📁 Данные из загруженных файлов (ресурсы и/или техника).")

    # Create working copy
    work_df = combined_df.copy()

    # Helper function to find columns by partial match (handles encoding issues)
    def find_column_by_partial(df, possible_names):
        """Find column by possible names (exact or partial match)"""
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for name in possible_names:
                name_lower = str(name).lower().strip()
                if (
                    name_lower == col_lower
                    or name_lower in col_lower
                    or col_lower in name_lower
                ):
                    return col
        return None

    # sample_technique_data.csv: Проект, Контрагент, Период, План, Среднее за неделю, 1–5 неделя, Дельта, Дельта (%)
    # Use Russian column names directly

    # Check required columns - Контрагент is essential
    if "Контрагент" not in work_df.columns:
        # Try to find contractor column by partial match
        contractor_col = find_column_by_partial(
            work_df,
            [
                "Контрагент",
                "контрагент",
                "Подразделение",
                "подразделение",
                "contractor",
            ],
        )
        if contractor_col:
            work_df["Контрагент"] = work_df[contractor_col]
        else:
            st.error(f"❌ Отсутствует необходимая колонка 'Контрагент'")
            st.info(f"Доступные колонки: {', '.join(work_df.columns)}")
            return

    # Find week columns dynamically - also try partial match
    week_columns = []
    for week_num in range(1, 6):
        week_col = f"{week_num} неделя"
        if week_col in work_df.columns:
            week_columns.append(week_col)
        else:
            # Try to find by partial match
            found_col = find_column_by_partial(
                work_df,
                [
                    week_col,
                    f"{week_num} недел",
                    f"недел {week_num}",
                    f"week {week_num}",
                ],
            )
            if found_col:
                week_columns.append(found_col)

    # Check if we have any data
    if work_df.empty:
        st.warning("⚠️ Данные пусты после обработки.")
        return

    # Process numeric columns
    # Process План
    if "План" in work_df.columns:
        work_df["План_numeric"] = pd.to_numeric(
            work_df["План"].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        work_df["План_numeric"] = 0

    # Process week columns - convert to numeric, handle empty strings
    for week_col in week_columns:
        work_df[f"{week_col}_numeric"] = pd.to_numeric(
            work_df[week_col]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", "")
            .replace("", "0"),
            errors="coerce",
        ).fillna(0)

    # Calculate sum of weeks (fact for the month = среднее за месяц)
    # Handle both "Среднее за неделю" (resources) and "Среднее за месяц" (technique)
    if "Среднее за неделю" in work_df.columns:
        # If we have Среднее за неделю (resources), multiply by number of weeks (typically 4-5)
        work_df["Среднее_за_неделю_numeric"] = pd.to_numeric(
            work_df["Среднее за неделю"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        # Calculate week_sum as Среднее за неделю * number of weeks
        num_weeks = len(week_columns) if week_columns else 4
        work_df["week_sum"] = work_df["Среднее_за_неделю_numeric"] * num_weeks
    elif "Среднее за месяц" in work_df.columns:
        # If we have Среднее за месяц (technique), use it directly as week_sum
        work_df["Среднее_за_месяц_numeric"] = pd.to_numeric(
            work_df["Среднее за месяц"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        work_df["week_sum"] = work_df["Среднее_за_месяц_numeric"]
        # Also create Среднее_за_неделю_numeric for consistency (divide by number of weeks)
        num_weeks = len(week_columns) if week_columns else 4
        work_df["Среднее_за_неделю_numeric"] = (
            work_df["week_sum"] / num_weeks if num_weeks > 0 else 0
        )
    elif week_columns:
        # Calculate from week columns if available
        week_numeric_cols = [f"{col}_numeric" for col in week_columns]
        work_df["week_sum"] = work_df[week_numeric_cols].sum(axis=1)
        # Calculate average per week
        num_weeks = len(week_columns) if week_columns else 4
        work_df["Среднее_за_неделю_numeric"] = (
            work_df["week_sum"] / num_weeks if num_weeks > 0 else 0
        )
    else:
        work_df["week_sum"] = 0
        work_df["Среднее_за_неделю_numeric"] = 0

    # Process Дельта (Delta) if available - try to find column by partial match
    delta_col = None
    if "Дельта" in work_df.columns:
        delta_col = "Дельта"
    else:
        delta_col = find_column_by_partial(
            work_df, ["Дельта", "дельта", "delta", "Delta", "Дельта (без %)"]
        )

    if delta_col and delta_col in work_df.columns:
        work_df["Дельта_numeric"] = pd.to_numeric(
            work_df[delta_col].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        # Calculate delta as plan - fact (week_sum)
        work_df["Дельта_numeric"] = work_df["План_numeric"] - work_df["week_sum"]

    # Process Дельта (%) (Delta %) if available - extract numeric value from percentage string
    # Try to find column by partial match
    delta_pct_col = None
    if "Дельта (%)" in work_df.columns:
        delta_pct_col = "Дельта (%)"
    else:
        delta_pct_col = find_column_by_partial(
            work_df,
            [
                "Дельта (%)",
                "Дельта %",
                "дельта (%)",
                "дельта %",
                "Delta %",
                "delta %",
                "Дельта(%)",
                "Дельта%",
            ],
        )

    if delta_pct_col and delta_pct_col in work_df.columns:

        def extract_percentage(value):
            """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
            if pd.isna(value):
                return 0
            # If already numeric, return as is
            if isinstance(value, (int, float)):
                return float(value)
            # Otherwise, try to extract from string
            value_str = str(value).strip()
            # Remove % sign and convert to float
            value_str = value_str.replace("%", "").replace(",", ".").replace(" ", "")
            try:
                return float(value_str)
            except:
                return 0

        work_df["Дельта_процент_numeric"] = work_df[delta_pct_col].apply(
            extract_percentage
        )
    else:
        # Calculate delta percentage if we have delta and plan
        work_df["Дельта_процент_numeric"] = 0
        if "Дельта_numeric" in work_df.columns and "План_numeric" in work_df.columns:
            mask = work_df["План_numeric"] != 0
            work_df.loc[mask, "Дельта_процент_numeric"] = (
                work_df.loc[mask, "Дельта_numeric"] / work_df.loc[mask, "План_numeric"]
            ) * 100
        work_df["Дельта_процент_numeric"] = work_df["Дельта_процент_numeric"].fillna(0)

    # Ensure Среднее_за_неделю_numeric exists (should already be calculated above)
    if "Среднее_за_неделю_numeric" not in work_df.columns:
        # Fallback: calculate from week_sum / number of weeks
        num_weeks = len(week_columns) if week_columns else 4
        work_df["Среднее_за_неделю_numeric"] = (
            work_df["week_sum"] / num_weeks if num_weeks > 0 else 0
        )

    # Find Проект column
    project_col = None
    if "Проект" in work_df.columns:
        project_col = "Проект"
    else:
        project_col = find_column_by_partial(
            work_df, ["Проект", "проект", "project", "Project"]
        )

    # Filters - project and contractor filters
    col1, col2 = st.columns(2)

    with col1:
        # Project filter - multiselect для выбора нескольких проектов
        if project_col and project_col in work_df.columns:
            all_projects = sorted(work_df[project_col].dropna().unique().tolist())
            selected_projects = st.multiselect(
                "Фильтр по проектам (можно выбрать несколько)",
                all_projects,
                default=all_projects if len(all_projects) <= 3 else all_projects[:3],
                key="workforce_projects",
            )
        else:
            selected_projects = []
            st.info("Колонка 'Проект' не найдена")

    with col2:
        # Contractor filter
        if "Контрагент" in work_df.columns:
            contractors = ["Все"] + sorted(
                work_df["Контрагент"].dropna().unique().tolist()
            )
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", contractors, key="workforce_contractor"
            )
        else:
            selected_contractor = "Все"
            st.info("Колонка 'Контрагент' не найдена")

    # Apply filters
    filtered_df = work_df.copy()
    if selected_projects and project_col and project_col in filtered_df.columns:
        # Фильтруем по выбранным проектам
        project_mask = (
            filtered_df[project_col]
            .astype(str)
            .str.strip()
            .isin([str(p).strip() for p in selected_projects])
        )
        filtered_df = filtered_df[project_mask]
    if selected_contractor != "Все" and "Контрагент" in filtered_df.columns:
        # Use string comparison with strip to handle whitespace
        filtered_df = filtered_df[
            filtered_df["Контрагент"].astype(str).str.strip()
            == str(selected_contractor).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для отображения с выбранными фильтрами.")
        return

    # Ensure Контрагент column exists and has values
    if (
        "Контрагент" not in filtered_df.columns
        or filtered_df["Контрагент"].isna().all()
    ):
        st.error("❌ Колонка 'Контрагент' отсутствует или пуста после фильтрации.")
        return

    # Remove rows where Контрагент is NaN before grouping
    filtered_df = filtered_df[filtered_df["Контрагент"].notna()].copy()

    if filtered_df.empty:
        st.info("Нет данных с указанными контрагентами после фильтрации.")
        return

    # Определяем список проектов для обработки
    if selected_projects and project_col and project_col in filtered_df.columns:
        projects_to_process = selected_projects
    else:
        # Если проекты не выбраны или колонка не найдена, обрабатываем все проекты
        if project_col and project_col in filtered_df.columns:
            projects_to_process = sorted(
                filtered_df[project_col].dropna().unique().tolist()
            )
        else:
            projects_to_process = ["Все проекты"]

    # Обрабатываем каждый проект отдельно
    for project_name in projects_to_process:
        # Фильтруем данные по проекту
        project_filtered_df = filtered_df.copy()
        if (
            project_col
            and project_col in project_filtered_df.columns
            and project_name != "Все проекты"
        ):
            project_filtered_df = project_filtered_df[
                project_filtered_df[project_col].astype(str).str.strip()
                == str(project_name).strip()
            ]

        if project_filtered_df.empty:
            continue

        # Заголовок для проекта
        if len(projects_to_process) > 1:
            st.markdown("---")
            st.subheader(f"📊 Проект: {project_name}")

        # ========== Chart 1: Pie Chart by Contractor (Delta %) ==========
        st.subheader("📊 Круговая диаграмма: Распределение дельты (%) по контрагентам")

        # Group by Контрагент and aggregate for pie chart (Delta %)
        # Ensure Дельта_процент_numeric exists - check if it was created in work_df
        if "Дельта_процент_numeric" not in project_filtered_df.columns:
            # Try to find Дельта (%) column by partial match
            delta_pct_col = None
            if "Дельта (%)" in project_filtered_df.columns:
                delta_pct_col = "Дельта (%)"
            else:
                delta_pct_col = find_column_by_partial(
                    project_filtered_df,
                    [
                        "Дельта (%)",
                        "Дельта %",
                        "дельта (%)",
                        "дельта %",
                        "Delta %",
                        "delta %",
                        "Дельта(%)",
                        "Дельта%",
                    ],
                )

            if delta_pct_col and delta_pct_col in project_filtered_df.columns:
                # Extract percentage values from the column
                def extract_percentage(value):
                    """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
                    if pd.isna(value):
                        return 0
                    # If already numeric, return as is
                    if isinstance(value, (int, float)):
                        return float(value)
                    # Otherwise, try to extract from string
                    value_str = str(value).strip()
                    # Remove % sign and convert to float
                    value_str = (
                        value_str.replace("%", "").replace(",", ".").replace(" ", "")
                    )
                    try:
                        return float(value_str)
                    except:
                        return 0

                project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                    delta_pct_col
                ].apply(extract_percentage)
            else:
                # Try to calculate from Дельта and План if available
                if (
                    "Дельта_numeric" in project_filtered_df.columns
                    and "План_numeric" in project_filtered_df.columns
                ):
                    project_filtered_df["Дельта_процент_numeric"] = 0
                    mask = project_filtered_df["План_numeric"] != 0
                    project_filtered_df.loc[mask, "Дельта_процент_numeric"] = (
                        project_filtered_df.loc[mask, "Дельта_numeric"]
                        / project_filtered_df.loc[mask, "План_numeric"]
                    ) * 100
                    project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                        "Дельта_процент_numeric"
                    ].fillna(0)
                else:
                    st.error(
                        "❌ Не удалось найти или рассчитать Дельта (%). Отсутствуют необходимые колонки."
                    )
                    st.info(
                        f"Доступные колонки: {', '.join(project_filtered_df.columns)}"
                    )
                    contractor_delta_pct = pd.DataFrame(
                        columns=["Контрагент", "Дельта (%)"]
                    )

        # Group by contractor and aggregate
        if "Дельта_процент_numeric" in project_filtered_df.columns:
            # Check if we have any data before grouping
            if (
                not project_filtered_df.empty
                and "Контрагент" in project_filtered_df.columns
            ):
                contractor_delta_pct = (
                    project_filtered_df.groupby("Контрагент")
                    .agg({"Дельта_процент_numeric": "sum"})  # Sum of delta percentages
                    .reset_index()
                )

                contractor_delta_pct.columns = ["Контрагент", "Дельта (%)"]
            else:
                contractor_delta_pct = pd.DataFrame(
                    columns=["Контрагент", "Дельта (%)"]
                )
        else:
            contractor_delta_pct = pd.DataFrame(columns=["Контрагент", "Дельта (%)"])

        # Check if we have data (внутри цикла по проектам — круговая и столбчатая по каждому проекту)
        if contractor_delta_pct.empty or len(contractor_delta_pct) == 0:
            st.info("Нет данных для отображения круговой диаграммы.")
        else:
            # Ensure Дельта (%) is numeric
            contractor_delta_pct["Дельта (%)"] = pd.to_numeric(
                contractor_delta_pct["Дельта (%)"], errors="coerce"
            ).fillna(0)

            # Check if we have any non-zero values
            total_abs_sum = contractor_delta_pct["Дельта (%)"].abs().sum()

            if total_abs_sum == 0:
                st.info(
                    "Все значения дельты (%) равны нулю. Диаграмма не может быть построена."
                )
            else:
                # Remove only exactly zero values (not small values)
                non_zero_data = contractor_delta_pct[
                    contractor_delta_pct["Дельта (%)"] != 0
                ].copy()

                # Use non-zero data if available
                if not non_zero_data.empty:
                    contractor_delta_pct = non_zero_data

                # Sort by absolute value for better visualization
                contractor_delta_pct = contractor_delta_pct.sort_values(
                    "Дельта (%)", key=abs, ascending=False
                )

                # Create a copy with absolute values for pie chart (pie charts don't support negative values)
                contractor_delta_pct_abs = contractor_delta_pct.copy()
                contractor_delta_pct_abs["Дельта (%)_abs"] = contractor_delta_pct_abs[
                    "Дельта (%)"
                ].abs()

                # Store original values for display
                original_values = contractor_delta_pct_abs["Дельта (%)"].tolist()

                # Create pie chart using absolute values
                fig_pie = px.pie(
                    contractor_delta_pct_abs,
                    values="Дельта (%)_abs",
                    names="Контрагент",
                    title="Распределение дельты (%) по контрагентам",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                )

                fig_pie.update_layout(
                    height=600,
                    showlegend=True,
                    legend=dict(
                        orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                    ),
                    title_font_size=16,
                )

                # На круговой диаграмме: абсолютное значение и процент в подписи (без наведения)
                fig_pie.update_traces(
                    textinfo="label+value+percent",
                    texttemplate="%{label}<br>%{value}<br>(%{percent:.0%})",
                    textposition="inside",
                    textfont=dict(size=12, color="white"),
                    customdata=original_values,
                    hovertemplate="<b>%{label}</b><br>Дельта (%): %{customdata:.0f}%<br>Процент: %{percent}<br><extra></extra>",
                )

                fig_pie = apply_chart_background(fig_pie)
                st.plotly_chart(fig_pie, use_container_width=True)

        # ========== Chart 2: Bar Chart by Contractor (Plan, Average, Delta) ==========
        st.subheader(
            "📊 Столбчатая диаграмма: План, Среднее за месяц, Дельта (группировка по контрагенту)"
        )

        # Group by Контрагент and aggregate for bar chart
        contractor_data = (
            project_filtered_df.groupby("Контрагент")
            .agg(
                {
                    "План_numeric": "sum",  # Sum of plans
                    "week_sum": "sum",  # Sum of weeks = среднее за месяц
                    "Дельта_numeric": "sum",  # Sum of deltas
                }
            )
            .reset_index()
        )

        contractor_data.columns = ["Контрагент", "План", "Среднее за месяц", "Дельта"]

        # Ensure Дельта column has numeric values
        contractor_data["Дельта"] = pd.to_numeric(
            contractor_data["Дельта"], errors="coerce"
        ).fillna(0)

        # Sort by contractor name
        contractor_data = contractor_data.sort_values("Контрагент")

        # Create bar chart
        fig_bar = go.Figure()

        # Add bars for Plan
        fig_bar.add_trace(
            go.Bar(
                name="План",
                x=contractor_data["Контрагент"],
                y=contractor_data["План"],
                marker_color="#3498db",
                text=contractor_data["План"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )

        # Add bars for Average
        fig_bar.add_trace(
            go.Bar(
                name="Среднее за месяц",
                x=contractor_data["Контрагент"],
                y=contractor_data["Среднее за месяц"],
                marker_color="#2ecc71",
                text=contractor_data["Среднее за месяц"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )

        # Add bars for Delta - ensure values are properly formatted
        # Разделяем на положительные и отрицательные значения для разных цветов
        delta_values = contractor_data["Дельта"].fillna(0)
        delta_abs = delta_values.abs()  # Абсолютные значения для отображения

        # Положительные значения дельты (зеленый)
        positive_mask = delta_values > 0
        if positive_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (+)",
                    x=contractor_data.loc[positive_mask, "Контрагент"],
                    y=delta_abs[positive_mask],
                    marker_color="#2ecc71",  # Зеленый для положительных
                    text=delta_abs[positive_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Отрицательные значения дельты (красный)
        negative_mask = delta_values < 0
        if negative_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (-)",
                    x=contractor_data.loc[negative_mask, "Контрагент"],
                    y=delta_abs[negative_mask],
                    marker_color="#e74c3c",  # Красный для отрицательных
                    text=delta_abs[negative_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Нулевые значения (если есть)
        zero_mask = delta_values == 0
        if zero_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (0)",
                    x=contractor_data.loc[zero_mask, "Контрагент"],
                    y=delta_abs[zero_mask],
                    marker_color="#95a5a6",  # Серый для нулевых
                    text=delta_abs[zero_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Update layout
        fig_bar.update_layout(
            title="План, Среднее за месяц и Дельта по контрагентам",
            xaxis_title="Контрагент",
            yaxis_title="Значение",
            barmode="group",
            height=600,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(tickangle=-45),
        )

        fig_bar = apply_chart_background(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

        # ========== Chart 3: Pie Chart by Contractor (Plan + Average) ==========
        st.subheader(
            "📊 Круговая диаграмма: Распределение суммы Плана и Среднего за месяц по контрагентам"
        )

        # Group by Контрагент and aggregate for pie chart (Plan + Average)
        contractor_plan_avg = (
            project_filtered_df.groupby("Контрагент")
            .agg(
                {
                    "План_numeric": "sum",  # Sum of plans
                    "week_sum": "sum",  # Sum of weeks = среднее за месяц
                    "Дельта_numeric": "sum",  # Sum of deltas
                }
            )
            .reset_index()
        )

        contractor_plan_avg.columns = ["Контрагент", "План", "Среднее за месяц", "Дельта"]

        # Calculate sum of Plan + Average for each contractor
        contractor_plan_avg["Сумма"] = (
            contractor_plan_avg["План"] + contractor_plan_avg["Среднее за месяц"]
        )

        # Calculate доля факта (Среднее за месяц / Сумма * 100) and доля отклонения (Дельта / План * 100)
        contractor_plan_avg["Доля факта (%)"] = 0
        contractor_plan_avg["Доля отклонения (%)"] = 0
        mask_sum = contractor_plan_avg["Сумма"] != 0
        contractor_plan_avg.loc[mask_sum, "Доля факта (%)"] = (
            contractor_plan_avg.loc[mask_sum, "Среднее за месяц"]
            / contractor_plan_avg.loc[mask_sum, "Сумма"]
        ) * 100
        mask_plan = contractor_plan_avg["План"] != 0
        contractor_plan_avg.loc[mask_plan, "Доля отклонения (%)"] = (
            contractor_plan_avg.loc[mask_plan, "Дельта"]
            / contractor_plan_avg.loc[mask_plan, "План"]
        ) * 100

        # Remove zero values for pie chart
        contractor_plan_avg = contractor_plan_avg[contractor_plan_avg["Сумма"] != 0].copy()

        if contractor_plan_avg.empty:
            st.info("Нет данных для отображения.")
        else:
            # Sort by sum value for better visualization
            contractor_plan_avg = contractor_plan_avg.sort_values("Сумма", ascending=False)

            # Create pie chart
            fig_pie_plan_avg = px.pie(
                contractor_plan_avg,
                values="Сумма",
                names="Контрагент",
                title="Распределение суммы Плана и Среднего за месяц по контрагентам",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )

            fig_pie_plan_avg.update_layout(
                height=600,
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                ),
                title_font_size=16,
            )

            # На круговой диаграмме: абсолютное значение и процент в подписи (без наведения)
            fig_pie_plan_avg.update_traces(
                textinfo="label+value+percent",
                texttemplate="%{label}<br>%{value:,.0f}<br>(%{percent:.0%})",
                textposition="inside",
                textfont=dict(size=12, color="white"),
            )
            fig_pie_plan_avg.update_traces(
                customdata=list(
                    zip(
                        contractor_plan_avg["Доля факта (%)"],
                        contractor_plan_avg["Доля отклонения (%)"],
                    )
                ),
                hovertemplate="<b>%{label}</b><br>Сумма: %{value:,.0f}<br>Процент: %{percent}<br>Доля факта: %{customdata[0]:.0f}%<br>Доля отклонения: %{customdata[1]:.0f}%<br><extra></extra>",
            )

            fig_pie_plan_avg = apply_chart_background(fig_pie_plan_avg)
            st.plotly_chart(fig_pie_plan_avg, use_container_width=True)

            # ========== Summary Table ==========
            st.subheader("📋 Сводная таблица по контрагентам")

            # Format numbers for display
            summary_table = contractor_data.copy()
            summary_table["План"] = summary_table["План"].apply(
                lambda x: f"{int(x)}" if pd.notna(x) else "0"
            )
            summary_table["Среднее за месяц"] = summary_table["Среднее за месяц"].apply(
                lambda x: f"{int(x)}" if pd.notna(x) else "0"
            )
            summary_table["Дельта"] = summary_table["Дельта"].apply(
                lambda x: f"{int(x)}" if pd.notna(x) else "0"
            )

            st.table(style_dataframe_for_dark_theme(summary_table))

            # Summary metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                total_plan = contractor_data["План"].sum()
                st.metric("Общий план", f"{int(total_plan)}")

            with col2:
                total_average = contractor_data["Среднее за месяц"].sum()
                st.metric("Общее среднее за месяц", f"{int(total_average)}")

            with col3:
                total_delta = contractor_data["Дельта"].sum()
                st.metric("Общая дельта", f"{int(total_delta)}")


# ==================== DASHBOARD 8.6: SKUD Stroyka ====================
def dashboard_skud_stroyka(df):
    st.header("🏗️ СКУД стройка")

    # Get resources data from session state
    resources_df = st.session_state.get("resources_data", None)

    if resources_df is None or resources_df.empty:
        st.warning(
            "⚠️ Для отображения графика СКУД стройка необходимо загрузить файл с данными о ресурсах."
        )
        st.info(
            "📋 Ожидаемые колонки в файле: Проект, Контрагент, Период, Среднее за неделю или Среднее за месяц"
        )
        return

    # Create working copy
    work_df = resources_df.copy()

    # Helper function to find columns by partial match
    def find_column_by_partial(df, possible_names):
        """Find column by possible names (exact or partial match)"""
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for name in possible_names:
                name_lower = str(name).lower().strip()
                if (
                    name_lower == col_lower
                    or name_lower in col_lower
                    or col_lower in name_lower
                ):
                    return col
        return None

    # Find required columns
    project_col = find_column_by_partial(
        work_df, ["Проект", "проект", "project", "Project"]
    )
    contractor_col = find_column_by_partial(
        work_df,
        ["Контрагент", "контрагент", "Подразделение", "подразделение", "contractor"],
    )
    period_col = find_column_by_partial(
        work_df, ["Период", "период", "period", "Period", "Месяц", "месяц"]
    )

    # Find average column (Среднее за неделю or Среднее за месяц)
    avg_col = None
    if "Среднее за неделю" in work_df.columns:
        avg_col = "Среднее за неделю"
    elif "Среднее за месяц" in work_df.columns:
        avg_col = "Среднее за месяц"
    else:
        avg_col = find_column_by_partial(
            work_df, ["Среднее за неделю", "Среднее за месяц", "среднее", "average"]
        )

    if not avg_col:
        st.error(
            "❌ Не найдена колонка со средним значением (Среднее за неделю или Среднее за месяц)"
        )
        st.info(f"Доступные колонки: {', '.join(work_df.columns)}")
        st.info(f"Количество строк в данных: {len(work_df)}")
        return

    # Process average column to numeric
    work_df["Среднее_numeric"] = pd.to_numeric(
        work_df[avg_col].astype(str).str.replace(",", ".").str.replace(" ", ""),
        errors="coerce",
    )

    # Check if we have any valid numeric values
    if work_df["Среднее_numeric"].isna().all():
        st.error("❌ Все значения в колонке со средним значением не являются числами.")
        st.info(
            f"Примеры значений из колонки '{avg_col}': {work_df[avg_col].head(10).tolist()}"
        )
        return

    # Fill NaN with 0 only for display purposes, but keep track of valid data
    work_df["Среднее_numeric"] = work_df["Среднее_numeric"].fillna(0)

    # Process period column - try to convert to datetime/period
    if period_col and period_col in work_df.columns:
        # Try to parse period as date
        work_df["period_parsed"] = pd.to_datetime(
            work_df[period_col], errors="coerce", dayfirst=True
        )
        # If parsing failed, try to extract month/year from string
        mask = work_df["period_parsed"].isna()
        if mask.any():
            # Try to extract month and year from period string
            def extract_period(val):
                if pd.isna(val):
                    return None
                val_str = str(val)
                # Try patterns like "2025-01", "01.2025", "январь 2025", etc.
                try:
                    # Try YYYY-MM format
                    if "-" in val_str:
                        parts = val_str.split("-")
                        if len(parts) >= 2:
                            year = int(parts[0])
                            month = int(parts[1])
                            return pd.Period(f"{year}-{month:02d}", freq="M")
                    # Try DD.MM.YYYY or MM.YYYY
                    if "." in val_str:
                        parts = val_str.split(".")
                        if len(parts) >= 2:
                            if len(parts) == 3:  # DD.MM.YYYY
                                year = int(parts[2])
                                month = int(parts[1])
                            else:  # MM.YYYY
                                year = int(parts[1])
                                month = int(parts[0])
                            return pd.Period(f"{year}-{month:02d}", freq="M")
                except:
                    pass
                return None

            work_df.loc[mask, "period_parsed"] = work_df.loc[mask, period_col].apply(
                extract_period
            )

        # Convert to Period if possible
        work_df["period_month"] = work_df["period_parsed"].apply(
            lambda x: (
                x.to_period("M")
                if pd.notna(x) and isinstance(x, pd.Timestamp)
                else (x if isinstance(x, pd.Period) else None)
            )
        )
    else:
        work_df["period_month"] = None

    # Filters
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        # Grouping filter
        grouping_options = [
            "По проектам",
            "По контрагентам",
            "По проектам и контрагентам",
            "Без группировки",
        ]
        selected_grouping = st.selectbox(
            "Группировка", grouping_options, key="skud_grouping"
        )

    with col2:
        # Фильтр по периоду от
        if period_col and "period_month" in work_df.columns and work_df["period_month"].notna().any():
            available_months = sorted(
                work_df[work_df["period_month"].notna()]["period_month"].unique()
            )
            month_options = ["Все"] + [str(m) for m in available_months]
            selected_period_from = st.selectbox(
                "Период от", month_options, key="skud_period_from"
            )
        else:
            selected_period_from = st.selectbox(
                "Период от", ["Все"], key="skud_period_from"
            )

    with col3:
        # Фильтр по периоду до
        if period_col and "period_month" in work_df.columns and work_df["period_month"].notna().any():
            available_months = sorted(
                work_df[work_df["period_month"].notna()]["period_month"].unique()
            )
            month_options = ["Все"] + [str(m) for m in available_months]
            selected_period_to = st.selectbox(
                "Период до", month_options, key="skud_period_to"
            )
        else:
            selected_period_to = st.selectbox(
                "Период до", ["Все"], key="skud_period_to"
            )

    with col4:
        # Project filter
        if project_col and project_col in work_df.columns:
            projects = ["Все"] + sorted(work_df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="skud_project"
            )
        else:
            selected_project = st.selectbox(
                "Фильтр по проекту", ["Все"], key="skud_project"
            )

    with col5:
        # Contractor filter
        if contractor_col and contractor_col in work_df.columns:
            contractors = ["Все"] + sorted(
                work_df[contractor_col].dropna().unique().tolist()
            )
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", contractors, key="skud_contractor"
            )
        else:
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", ["Все"], key="skud_contractor"
            )

    # Apply filters
    filtered_df = work_df.copy()

    if selected_project != "Все" and project_col and project_col in filtered_df.columns:
        # More robust filtering - handle NaN values and case-insensitive comparison
        project_mask = (
            filtered_df[project_col].astype(str).str.strip().str.lower()
            == str(selected_project).strip().lower()
        )
        filtered_df = filtered_df[project_mask]

    if (
        selected_contractor != "Все"
        and contractor_col
        and contractor_col in filtered_df.columns
    ):
        # More robust filtering - handle NaN values and case-insensitive comparison
        contractor_mask = (
            filtered_df[contractor_col].astype(str).str.strip().str.lower()
            == str(selected_contractor).strip().lower()
        )
        filtered_df = filtered_df[contractor_mask]

    # Apply period filters
    if (
        "period_month" in filtered_df.columns
        and filtered_df["period_month"].notna().any()
    ):
        if selected_period_from != "Все":
            try:
                period_from = pd.Period(selected_period_from, freq="M")
                filtered_df = filtered_df[filtered_df["period_month"] >= period_from]
            except Exception as e:
                st.warning(f"Ошибка при фильтрации по периоду от: {e}")

        if selected_period_to != "Все":
            try:
                period_to = pd.Period(selected_period_to, freq="M")
                filtered_df = filtered_df[filtered_df["period_month"] <= period_to]
            except Exception as e:
                st.warning(f"Ошибка при фильтрации по периоду до: {e}")

    if filtered_df.empty:
        st.warning("⚠️ Нет данных для отображения с выбранными фильтрами.")
        return

    # Group data based on selected grouping
    group_cols = []
    if (
        selected_grouping == "По проектам"
        and project_col
        and project_col in filtered_df.columns
    ):
        group_cols.append(project_col)
    elif (
        selected_grouping == "По контрагентам"
        and contractor_col
        and contractor_col in filtered_df.columns
    ):
        group_cols.append(contractor_col)
    elif selected_grouping == "По проектам и контрагентам":
        if project_col and project_col in filtered_df.columns:
            group_cols.append(project_col)
        if contractor_col and contractor_col in filtered_df.columns:
            group_cols.append(contractor_col)

    # Always group by period_month for time series (only if not filtering by specific period range)
    # Only add period_month if it has valid (non-NaN) values
    if (
        (selected_period_from == "Все" and selected_period_to == "Все")
        and "period_month" in filtered_df.columns
        and filtered_df["period_month"].notna().any()
    ):
        group_cols.append("period_month")

    if group_cols:
        # Filter out rows where any grouping column is NaN before grouping
        mask = pd.Series([True] * len(filtered_df))
        for col in group_cols:
            if col in filtered_df.columns:
                mask = mask & filtered_df[col].notna()

        if mask.any():
            grouped_data = (
                filtered_df[mask]
                .groupby(group_cols)["Среднее_numeric"]
                .mean()
                .reset_index()
            )
            grouped_data.columns = list(group_cols) + ["Среднее за месяц"]
        else:
            # All grouping columns are NaN, aggregate without grouping
            grouped_data = pd.DataFrame(
                {"Среднее за месяц": [filtered_df["Среднее_numeric"].mean()]}
            )
    else:
        # No grouping, just aggregate by period if available
        if (
            "period_month" in filtered_df.columns
            and filtered_df["period_month"].notna().any()
        ):
            grouped_data = (
                filtered_df.groupby("period_month")["Среднее_numeric"]
                .mean()
                .reset_index()
            )
            grouped_data.columns = ["period_month", "Среднее за месяц"]
        else:
            # No period available, just aggregate all data
            mean_value = filtered_df["Среднее_numeric"].mean()
            if pd.isna(mean_value):
                mean_value = 0
            grouped_data = pd.DataFrame({"Среднее за месяц": [mean_value]})

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                month_name = get_russian_month_name(period_val)
                year = period_val.year
                if month_name:
                    return f"{month_name} {year}"
                return str(period_val)
            except:
                return str(period_val)
        return str(period_val)

    if "period_month" in grouped_data.columns:
        grouped_data["period_display"] = grouped_data["period_month"].apply(
            format_period_display
        )

    # Check if we have data to display
    if grouped_data.empty:
        st.warning("⚠️ Нет данных для отображения после применения фильтров.")
        with st.expander("🔍 Детали проблемы", expanded=True):
            st.write(f"**Исходных строк:** {len(work_df)}")
            st.write(f"**Строк после фильтрации:** {len(filtered_df)}")
            st.write(f"**Строк после группировки:** {len(grouped_data)}")
            st.write(f"**Выбранная группировка:** {selected_grouping}")
            st.write(f"**Колонки для группировки:** {group_cols}")
            st.write(f"**Выбранный проект:** {selected_project}")
            st.write(f"**Выбранный контрагент:** {selected_contractor}")
            st.write(f"**Период от:** {selected_period_from}")
            st.write(f"**Период до:** {selected_period_to}")
            if len(filtered_df) > 0:
                st.write("**Данные после фильтрации (первые 10 строк):**")
                st.table(style_dataframe_for_dark_theme(filtered_df.head(10)))
                if "Среднее_numeric" in filtered_df.columns:
                    st.write(f"**Среднее_numeric в отфильтрованных данных:**")
                    st.write(
                        f"- Не пустых значений: {filtered_df['Среднее_numeric'].notna().sum()}"
                    )
                    st.write(
                        f"- Среднее значение: {filtered_df['Среднее_numeric'].mean():.2f}"
                    )
                    st.write(f"- Сумма: {filtered_df['Среднее_numeric'].sum():.2f}")
            else:
                st.write(
                    "**Проблема:** После применения фильтров не осталось ни одной строки."
                )
                st.write("**Возможные причины:**")
                st.write("- Фильтры слишком строгие")
                st.write("- Данные не соответствуют выбранным фильтрам")
                st.write("- Проблемы с типами данных при сравнении")
        return

    # Check if all values are NaN (but allow zeros - zeros are valid data)
    if "Среднее за месяц" in grouped_data.columns:
        if grouped_data["Среднее за месяц"].isna().all():
            st.warning("⚠️ Все значения среднего равны NaN после группировки.")
            with st.expander("🔍 Детали проблемы", expanded=True):
                st.write(f"**Строк после группировки:** {len(grouped_data)}")
                st.table(style_dataframe_for_dark_theme(grouped_data))
            return

    # Create visualization
    has_period = (
        "period_month" in grouped_data.columns
        or "period_display" in grouped_data.columns
    )

    if selected_grouping == "Без группировки":
        if has_period:
            # Simple line chart with time series
            x_col = (
                "period_display"
                if "period_display" in grouped_data.columns
                else "period_month"
            )
            fig = px.line(
                grouped_data,
                x=x_col,
                y="Среднее за месяц",
                title="Среднее за месяц по людям в динамике",
                labels={x_col: "Месяц", "Среднее за месяц": "Среднее за месяц (чел.)"},
                markers=True,
            )
            fig.update_xaxes(tickangle=-45)
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Single value bar chart
            fig = px.bar(
                grouped_data,
                y="Среднее за месяц",
                title="Среднее за месяц по людям",
                labels={"Среднее за месяц": "Среднее за месяц (чел.)"},
                text="Среднее за месяц",
            )
            fig.update_traces(
                textposition="outside", textfont=dict(size=12, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)
    else:
        # Grouped visualization
        grouping_cols = [col for col in group_cols if col != "period_month"]

        if has_period and len(grouping_cols) > 0:
            # Grouped bar chart with time series
            x_col = (
                "period_display"
                if "period_display" in grouped_data.columns
                else "period_month"
            )
            color_col = grouping_cols[0] if len(grouping_cols) == 1 else None

            if color_col:
                fig = px.bar(
                    grouped_data,
                    x=x_col,
                    y="Среднее за месяц",
                    color=color_col,
                    title="Среднее за месяц по людям в динамике",
                    labels={
                        x_col: "Месяц",
                        "Среднее за месяц": "Среднее за месяц (чел.)",
                    },
                    text="Среднее за месяц",
                )
                fig.update_layout(barmode="group")
                fig.update_xaxes(tickangle=-45)
                fig.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            elif len(grouping_cols) > 1:
                # Multiple grouping columns - use first for color, show others in hover
                fig = px.bar(
                    grouped_data,
                    x=x_col,
                    y="Среднее за месяц",
                    color=grouping_cols[0],
                    title="Среднее за месяц по людям в динамике",
                    labels={
                        x_col: "Месяц",
                        "Среднее за месяц": "Среднее за месяц (чел.)",
                    },
                    text="Среднее за месяц",
                    facet_col=grouping_cols[1] if len(grouping_cols) > 1 else None,
                )
                fig.update_layout(barmode="group")
                fig.update_xaxes(tickangle=-45)
                fig.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            else:
                # Fallback to line chart
                fig = px.line(
                    grouped_data,
                    x=x_col,
                    y="Среднее за месяц",
                    title="Среднее за месяц по людям в динамике",
                    labels={
                        x_col: "Месяц",
                        "Среднее за месяц": "Среднее за месяц (чел.)",
                    },
                    markers=True,
                )
                fig.update_xaxes(tickangle=-45)
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
        elif len(grouping_cols) > 0:
            # Grouped bar chart without time series (single month selected)
            color_col = grouping_cols[0] if len(grouping_cols) == 1 else None
            if color_col:
                fig = px.bar(
                    grouped_data,
                    x=color_col,
                    y="Среднее за месяц",
                    title="Среднее за месяц по людям",
                    labels={"Среднее за месяц": "Среднее за месяц (чел.)"},
                    text="Среднее за месяц",
                )
                fig.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )
                fig.update_xaxes(tickangle=-45)
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Не удалось построить график с выбранной группировкой.")
        else:
            st.info("Не удалось построить график с выбранной группировкой.")

    # Summary table
    if not grouped_data.empty:
        st.subheader("📋 Сводная таблица")
        display_cols = []

        # Add period column only if not filtering by specific period range
        if (selected_period_from == "Все" and selected_period_to == "Все") and (
            "period_display" in grouped_data.columns
            or "period_month" in grouped_data.columns
        ):
            display_cols.append(
                "period_display"
                if "period_display" in grouped_data.columns
                else "period_month"
            )

        # Add grouping columns
        if selected_grouping != "Без группировки":
            for col in group_cols:
                if col != "period_month" and col in grouped_data.columns:
                    display_cols.append(col)

        display_cols.append("Среднее за месяц")

        # Filter to only existing columns
        display_cols = [col for col in display_cols if col in grouped_data.columns]

        summary_table = grouped_data[display_cols].copy()
        summary_table["Среднее за месяц"] = summary_table["Среднее за месяц"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "0"
        )
        st.table(style_dataframe_for_dark_theme(summary_table))


# ==================== DASHBOARD: График движения рабочей силы + СКУД стройка (объединённый) ====================
def dashboard_workforce_and_skud(df):
    """
    Объединённый отчёт: «График движения рабочей силы» и «СКУД стройка» в двух вкладках.
    """
    st.header("👥 График движения рабочей силы / СКУД стройка")
    tab1, tab2 = st.tabs(["График движения рабочей силы", "СКУД стройка"])
    with tab1:
        dashboard_workforce_movement(df)
    with tab2:
        dashboard_skud_stroyka(df)


# ==================== DASHBOARD 8.7: Documentation ====================
def dashboard_documentation(df):
    st.header("📚 Выдача рабочей/проектной документации")

    # Find column names (they might have different formats)
    # Try to find columns by partial name matching
    def find_column(df, possible_names):
        """Find column by possible names"""
        for col in df.columns:
            # Normalize column name: remove newlines, extra spaces, normalize case
            col_normalized = str(col).replace("\n", " ").replace("\r", " ").strip()
            col_lower = col_normalized.lower()

            for name in possible_names:
                name_lower = name.lower().strip()
                # Exact match (case insensitive)
                if name_lower == col_lower:
                    return col
                # Substring match
                if name_lower in col_lower or col_lower in name_lower:
                    return col
                # Check if all key words from name are in column
                name_words = [w for w in name_lower.split() if len(w) > 2]
                if name_words and all(word in col_lower for word in name_words):
                    return col

        # Special handling for RD count column with key words
        if any(
            "разделов" in n.lower() and "рд" in n.lower() and "договор" in n.lower()
            for n in possible_names
        ):
            for col in df.columns:
                col_lower = str(col).lower().replace("\n", " ").replace("\r", " ")
                key_words = ["разделов", "рд", "договор", "количество"]
                if all(word in col_lower for word in key_words if len(word) > 3):
                    return col

        return None

    # Find required columns (sample_project_data_fixed.csv: «РД по Договору», нет «Количество разделов РД по Договору»)
    rd_count_col = find_column(
        df,
        [
            "Количество разделов РД по Договору",
            "Количество разделов РД",
            "РД по Договору",
            "разделов РД",
            "Количетсов разделов РД по Договору",  # Handle typo
            "Количество разделов РД по договору",
        ],
    )

    on_approval_col = find_column(df, ["На согласовании", "согласовании"])
    in_production_col = find_column(
        df, ["Выдано в производство работ", "производство работ", "в производство"]
    )
    plan_start_col = (
        "plan start"
        if "plan start" in df.columns
        else find_column(df, ["Старт План", "План Старт"])
    )
    plan_end_col = (
        "plan end"
        if "plan end" in df.columns
        else find_column(df, ["Конец План", "План Конец"])
    )
    base_start_col = (
        "base start"
        if "base start" in df.columns
        else find_column(df, ["Старт Факт", "Факт Старт"])
    )
    base_end_col = (
        "base end"
        if "base end" in df.columns
        else find_column(df, ["Конец Факт", "Факт Конец"])
    )

    # Check if required columns exist
    missing_cols = []
    if not rd_count_col:
        missing_cols.append("Количество разделов РД по Договору")
    if not on_approval_col:
        missing_cols.append("На согласовании")
    if not in_production_col:
        missing_cols.append("Выдано в производство работ")

    if missing_cols:
        st.warning(f"⚠️ Отсутствуют необходимые колонки: {', '.join(missing_cols)}")
        st.info("Пожалуйста, убедитесь, что файл содержит все необходимые колонки.")
        return

    # Find project column for filtering
    project_col = (
        "project name"
        if "project name" in df.columns
        else find_column(df, ["Проект", "project"])
    )

    # Add filters
    st.subheader("Фильтры")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # Filter by project
    selected_project = "Все"
    if project_col and project_col in df.columns:
        with filter_col1:
            projects = ["Все"] + sorted(df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="doc_project_filter"
            )

    # Filter by date period
    selected_date_start = None
    selected_date_end = None
    if plan_start_col and plan_start_col in df.columns:
        with filter_col2:
            # Convert dates for filtering
            plan_start_str = df[plan_start_col].astype(str)
            df_dates = pd.to_datetime(
                plan_start_str, errors="coerce", dayfirst=True, format="mixed"
            )
            valid_dates = df_dates[df_dates.notna()]

            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                selected_date_start = st.date_input(
                    "Дата начала периода",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="doc_date_start",
                )
                selected_date_end = st.date_input(
                    "Дата окончания периода",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="doc_date_end",
                )

    # Filter by RD status
    with filter_col3:
        rd_status_options = ["Все"]
        if on_approval_col and on_approval_col in df.columns:
            rd_status_options.append("На согласовании")
        if in_production_col and in_production_col in df.columns:
            rd_status_options.append("Выдано в производство работ")

        # Find other status columns
        contractor_col = find_column(df, ["Выдана подрядчику", "подрядчику"])
        rework_col = find_column(df, ["На доработке", "доработке"])

        if contractor_col and contractor_col in df.columns:
            rd_status_options.append("Выдана подрядчику")
        if rework_col and rework_col in df.columns:
            rd_status_options.append("На доработке")

        selected_statuses = st.multiselect(
            "Фильтр по статусу РД",
            options=rd_status_options,
            default=["Все"],
            key="doc_status_filter",
        )

    # Apply filters to data
    filtered_df = df.copy()

    # Apply project filter
    if selected_project != "Все" and project_col and project_col in df.columns:
        filtered_df = filtered_df[
            filtered_df[project_col].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    # Apply date filter
    if (
        selected_date_start
        and selected_date_end
        and plan_start_col
        and plan_start_col in df.columns
    ):
        plan_start_str = filtered_df[plan_start_col].astype(str)
        filtered_df[plan_start_col + "_parsed"] = pd.to_datetime(
            plan_start_str, errors="coerce", dayfirst=True, format="mixed"
        )
        date_mask = (
            filtered_df[plan_start_col + "_parsed"].notna()
            & (filtered_df[plan_start_col + "_parsed"].dt.date >= selected_date_start)
            & (filtered_df[plan_start_col + "_parsed"].dt.date <= selected_date_end)
        )
        filtered_df = filtered_df[date_mask].copy()

    # Apply status filter
    if "Все" not in selected_statuses and selected_statuses:
        status_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)

        if (
            "На согласовании" in selected_statuses
            and on_approval_col
            and on_approval_col in filtered_df.columns
        ):
            on_approval_series = (
                filtered_df[on_approval_col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            on_approval_numeric = pd.to_numeric(
                on_approval_series, errors="coerce"
            ).fillna(0)
            status_mask = status_mask | (on_approval_numeric > 0)

        if (
            "Выдано в производство работ" in selected_statuses
            and in_production_col
            and in_production_col in filtered_df.columns
        ):
            in_production_series = (
                filtered_df[in_production_col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            in_production_numeric = pd.to_numeric(
                in_production_series, errors="coerce"
            ).fillna(0)
            status_mask = status_mask | (in_production_numeric > 0)

        if (
            "Выдана подрядчику" in selected_statuses
            and contractor_col
            and contractor_col in filtered_df.columns
        ):
            contractor_series = (
                filtered_df[contractor_col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            contractor_numeric = pd.to_numeric(
                contractor_series, errors="coerce"
            ).fillna(0)
            status_mask = status_mask | (contractor_numeric > 0)

        if (
            "На доработке" in selected_statuses
            and rework_col
            and rework_col in filtered_df.columns
        ):
            rework_series = (
                filtered_df[rework_col].astype(str).str.replace(",", ".", regex=False)
            )
            rework_numeric = pd.to_numeric(rework_series, errors="coerce").fillna(0)
            status_mask = status_mask | (rework_numeric > 0)

        filtered_df = filtered_df[status_mask].copy()

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Use filtered_df for all subsequent operations
    df = filtered_df

    # Prepare data for pie chart "Исполнение РД"
    # Sum values for "На согласовании" and "Выдано в производство работ"
    try:
        # Convert to numeric, handling comma as decimal separator
        on_approval_series = (
            df[on_approval_col].astype(str).str.replace(",", ".", regex=False)
        )
        on_approval_sum = (
            pd.to_numeric(on_approval_series, errors="coerce").fillna(0).sum()
        )

        in_production_series = (
            df[in_production_col].astype(str).str.replace(",", ".", regex=False)
        )
        in_production_sum = (
            pd.to_numeric(in_production_series, errors="coerce").fillna(0).sum()
        )

        # Create pie chart
        if on_approval_sum > 0 or in_production_sum > 0:
            st.subheader("Исполнение РД")
            # Округляем значения до целых
            pie_data = {
                "На согласовании": int(round(on_approval_sum)),
                "Выдано в производство работ": int(round(in_production_sum)),
            }

            fig_pie = px.pie(
                values=list(pie_data.values()),
                names=list(pie_data.keys()),
                title="Исполнение РД",
                color_discrete_map={
                    "На согласовании": "#2E86AB",
                    "Выдано в производство работ": "#06A77D",
                },
            )
            # На круговой диаграмме: абсолютное значение и процент в подписи (без наведения)
            fig_pie.update_traces(
                textinfo="label+value+percent",
                texttemplate="%{label}<br>%{value}<br>(%{percent:.0%})",
                textposition="inside",
                textfont=dict(size=14, color="white"),
                hovertemplate="<b>%{label}</b><br>Значение: %{value}<br>Процент: %{percent}<br><extra></extra>",
            )

            fig_pie = apply_chart_background(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Нет данных для построения графика 'Исполнение РД'.")
    except Exception as e:
        st.error(f"Ошибка при построении графика 'Исполнение РД': {str(e)}")

    # Prepare data for "Динамика выдачи РД"
    # X-axis: "Старт План" (plan start date)
    # Plan (Y-axis): "РД по Договору" (grouped by "Старт План")
    # Fact (Y-axis): "Выдано в производство работ" (grouped by "Старт План")
    try:
        # Find column for plan data: "РД по Договору"
        rd_plan_col = find_column(
            df, ["РД по Договору", "РД по договору", "рд по договору", "РД по Договору"]
        )

        # Check if required columns exist
        if not plan_start_col or plan_start_col not in df.columns:
            st.warning(
                "⚠️ Для построения графика 'Динамика выдачи РД' необходима колонка 'Старт План' (plan start)."
            )
            return

        if not rd_plan_col or rd_plan_col not in df.columns:
            st.warning(
                "⚠️ Для построения графика 'Динамика выдачи РД' необходима колонка 'РД по Договору'."
            )
            return

        if not in_production_col or in_production_col not in df.columns:
            st.warning(
                "⚠️ Для построения графика 'Динамика выдачи РД' необходима колонка 'Выдано в производство работ'."
            )
            return

        # Convert columns to numeric - handle comma as decimal separator
        # Replace comma with dot for numeric conversion
        # Plan: use "РД по Договору"
        rd_plan_series = df[rd_plan_col].astype(str).str.replace(",", ".", regex=False)
        df["rd_plan_numeric"] = pd.to_numeric(rd_plan_series, errors="coerce").fillna(0)

        # Convert "Выдано в производство работ" to numeric - handle comma as decimal separator
        in_production_series = (
            df[in_production_col].astype(str).str.replace(",", ".", regex=False)
        )
        df["in_production_numeric"] = pd.to_numeric(
            in_production_series, errors="coerce"
        ).fillna(0)

        # Convert dates - handle DD.MM.YYYY format
        # First convert to string, then parse with dayfirst=True
        plan_start_str = df[plan_start_col].astype(str)
        df[plan_start_col] = pd.to_datetime(
            plan_start_str, errors="coerce", dayfirst=True, format="mixed"
        )

        # Prepare data
        # Both Plan and Fact are grouped by plan_start_col (Старт план)
        dynamics_data = []

        # Plan data: group by plan start date, sum "РД по Договору"
        # Always include plan data, even if some values are 0
        plan_mask = df[plan_start_col].notna()
        if plan_mask.any():
            plan_grouped = (
                df[plan_mask]
                .groupby(df[plan_mask][plan_start_col].dt.date)
                .agg({"rd_plan_numeric": "sum"})
                .reset_index()
            )
            plan_grouped.columns = ["Дата", "Количество"]
            plan_grouped["Тип"] = "План"
            # Fill NaN with 0 and ensure all values are numeric
            plan_grouped["Количество"] = plan_grouped["Количество"].fillna(0)
            # Always add plan data, even if all values are 0
            dynamics_data.append(plan_grouped)

        # Fact data: group by plan start date (same as Plan!), sum "Выдано в производство работ"
        fact_mask = df[plan_start_col].notna()  # Use plan_start_col for both!
        if fact_mask.any():
            fact_grouped = (
                df[fact_mask]
                .groupby(df[fact_mask][plan_start_col].dt.date)
                .agg({"in_production_numeric": "sum"})
                .reset_index()
            )
            fact_grouped.columns = ["Дата", "Количество"]
            fact_grouped["Тип"] = "Факт"
            # Fill NaN with 0 and ensure all values are numeric
            fact_grouped["Количество"] = fact_grouped["Количество"].fillna(0)
            # Filter out rows where sum is 0 for fact (only show actual production)
            fact_grouped = fact_grouped[fact_grouped["Количество"] > 0]
            if not fact_grouped.empty:
                dynamics_data.append(fact_grouped)

        # Always show graph if we have plan data, even if fact data is empty
        if dynamics_data:
            st.subheader("Динамика выдачи РД")
            dynamics_df = pd.concat(dynamics_data, ignore_index=True)
            dynamics_df = dynamics_df.sort_values("Дата")

            # Вычисляем накопительные значения для каждого типа отдельно
            dynamics_df["Накопительное_значение"] = 0
            for typ in dynamics_df["Тип"].unique():
                mask = dynamics_df["Тип"] == typ
                dynamics_df.loc[mask, "Накопительное_значение"] = dynamics_df.loc[
                    mask, "Количество"
                ].cumsum()

            # Используем накопительные значения для графика
            dynamics_df["Количество"] = dynamics_df["Накопительное_значение"]

            # Показатели: план по проекту, план/факт/отклонение на текущую дату, прогноз производительности
            plan_df = dynamics_df[dynamics_df["Тип"] == "План"].sort_values("Дата")
            fact_df = dynamics_df[dynamics_df["Тип"] == "Факт"].sort_values("Дата")
            today = date.today()

            plan_total = float(plan_df["Количество"].max()) if not plan_df.empty else 0.0
            plan_to_date = 0.0
            if not plan_df.empty:
                dt_plan = pd.to_datetime(plan_df["Дата"])
                past_plan = plan_df[dt_plan.dt.date <= today]
                plan_to_date = float(past_plan["Количество"].iloc[-1]) if not past_plan.empty else 0.0
            fact_to_date = 0.0
            if not fact_df.empty:
                dt_fact = pd.to_datetime(fact_df["Дата"])
                past_fact = fact_df[dt_fact.dt.date <= today]
                fact_to_date = float(past_fact["Количество"].iloc[-1]) if not past_fact.empty else 0.0
            deviation_to_date = fact_to_date - plan_to_date

            # Прогноз: текущая производительность в неделю и необходимая для выполнения плана
            first_plan_date = plan_df["Дата"].min() if not plan_df.empty else None
            last_plan_date = plan_df["Дата"].max() if not plan_df.empty else None
            if first_plan_date is not None:
                first_d = pd.to_datetime(first_plan_date).date()
            else:
                first_d = today
            if last_plan_date is not None:
                last_d = pd.to_datetime(last_plan_date).date()
            else:
                last_d = today
            weeks_elapsed = max((today - first_d).days / 7.0, 1.0 / 7.0)
            current_productivity = fact_to_date / weeks_elapsed if weeks_elapsed > 0 else 0.0
            remaining_days = (last_d - today).days
            remaining_weeks = max(remaining_days / 7.0, 0.0)
            remaining_to_plan = max(plan_total - fact_to_date, 0.0)
            required_productivity = (remaining_to_plan / remaining_weeks) if remaining_weeks > 0 else float("inf")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("План по проекту", f"{plan_total:,.0f}".replace(",", " "))
            with c2:
                st.metric("План на текущую дату", f"{plan_to_date:,.0f}".replace(",", " "))
            with c3:
                st.metric("Факт на текущую дату", f"{fact_to_date:,.0f}".replace(",", " "))
            with c4:
                st.metric("Отклонение на текущую дату", f"{deviation_to_date:+,.0f}".replace(",", " "))

            st.caption("Прогноз производительности (РД в неделю)")
            p1, p2 = st.columns(2)
            with p1:
                st.metric(
                    "Текущая производительность в неделю",
                    f"{current_productivity:,.1f}".replace(",", " "),
                    help="Факт на текущую дату / число недель с начала плана",
                )
            with p2:
                if remaining_weeks <= 0:
                    st.metric(
                        "Необходимая для выполнения плана",
                        "—",
                        help="Плановый срок завершения уже наступил или прошёл",
                    )
                elif required_productivity == float("inf"):
                    st.metric("Необходимая для выполнения плана", "—", help="Нет оставшегося срока")
                else:
                    st.metric(
                        "Необходимая для выполнения плана",
                        f"{required_productivity:,.1f}".replace(",", " "),
                        help="(План по проекту − Факт на текущую дату) / оставшиеся недели",
                    )

            # Create line chart with text labels always visible
            # Prepare text labels for each data point
            dynamics_df["Текст"] = dynamics_df["Количество"].apply(
                lambda x: f"{x:.0f}" if pd.notna(x) else ""
            )

            fig_dynamics = px.line(
                dynamics_df,
                x="Дата",
                y="Количество",
                color="Тип",
                title="Динамика выдачи РД",
                markers=True,
                labels={"Количество": "Количество", "Дата": "Дата (Старт План)"},
                text="Текст",
            )

            fig_dynamics.update_layout(
                xaxis_title="Дата (Старт План)",
                yaxis_title="Количество",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    title_text="",
                ),
            )
            # Update legend labels to be more descriptive
            fig_dynamics.for_each_trace(
                lambda t: t.update(
                    name=(
                        "План (РД по Договору)"
                        if t.name == "План"
                        else (
                            "Факт (Выдано в производство работ)"
                            if t.name == "Факт"
                            else t.name
                        )
                    )
                )
            )
            # Add text labels and format - ensure text is always visible
            fig_dynamics.update_traces(
                line=dict(width=2),
                marker=dict(size=8),
                mode="lines+markers+text",  # Enable text display mode
                textposition="top center",
                textfont=dict(size=10, color="white"),
            )
            fig_dynamics = apply_chart_background(fig_dynamics)
            st.plotly_chart(fig_dynamics, use_container_width=True)
        else:
            st.warning("⚠️ Нет данных для построения графика 'Динамика выдачи РД'.")
    except Exception as e:
        st.error(f"Ошибка при построении графика 'Динамика выдачи РД': {str(e)}")

    # Add separator
    st.divider()

    # Add "Просрочка выдачи РД" chart
    dashboard_rd_delay(df)


# ==================== DASHBOARD 8: Budget by Type (Plan/Fact/Reserve) ====================
def dashboard_budget_by_type(df):
    st.header("💰 Бюджет план/факт")

    col1, col2, col3 = st.columns(3)

    with col1:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_type_project"
            )
        else:
            selected_project = "Все"
            st.info("Колонка 'project name' не найдена")

    with col2:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_type_section"
            )
        else:
            selected_section = "Все"

    with col3:
        pass

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]
    # Check for budget columns (нормализуем русские названия)
    ensure_budget_columns(filtered_df)
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Отклонение = факт - план (положительное — перерасход, красный; отрицательное — экономия, зелёный)
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget fact"] - filtered_df["budget plan"]
    )

    # ========== Histogram: Budget by Project and Type ==========
    st.subheader("📊 Гистограмма: Бюджет план/факт/корректировка/отклонение по проектам")

    # Check for adjusted budget column in original dataframe
    adjusted_budget_col = None
    if "budget adjusted" in df.columns:
        adjusted_budget_col = "budget adjusted"
    elif "adjusted budget" in df.columns:
        adjusted_budget_col = "adjusted budget"

    # Filters for histogram
    col_hist1 = st.columns(1)[0]

    with col_hist1:
        # Checkbox for showing deviation
        show_reserve = st.checkbox(
            "Показать отклонение", value=False, key="budget_show_reserve"
        )

        # Budget types to show (always show Plan and Fact, optionally Deviation)
        selected_budget_types = ["Бюджет План", "Бюджет Факт"]
        if adjusted_budget_col:
            selected_budget_types.append("Бюджет Корректировка")
        if show_reserve:
            selected_budget_types.append("Отклонение (перерасход)")
            selected_budget_types.append("Отклонение (экономия)")

    # Apply filters for histogram - use filtered_df to respect project filter
    hist_df = filtered_df.copy()

    if selected_section != "Все" and "section" in hist_df.columns:
        hist_df = hist_df[
            hist_df["section"].astype(str).str.strip() == str(selected_section).strip()
        ]

    if hist_df.empty:
        st.info("Нет данных для отображения гистограммы с выбранными фильтрами.")
    else:
        # Convert budget columns to numeric
        hist_df["budget plan"] = pd.to_numeric(
            hist_df["budget plan"], errors="coerce"
        ).fillna(0)
        hist_df["budget fact"] = pd.to_numeric(
            hist_df["budget fact"], errors="coerce"
        ).fillna(0)
        hist_df["reserve budget"] = hist_df["budget fact"] - hist_df["budget plan"]

        # Group by project and aggregate
        if "project name" in hist_df.columns:
            budget_by_project = (
                hist_df.groupby("project name")
                .agg(
                    {
                        "budget plan": "sum",
                        "budget fact": "sum",
                        "reserve budget": "sum",
                    }
                )
                .reset_index()
            )

            # Add adjusted budget if available
            if adjusted_budget_col and adjusted_budget_col in hist_df.columns:
                # Convert to numeric first
                hist_df[adjusted_budget_col] = pd.to_numeric(
                    hist_df[adjusted_budget_col], errors="coerce"
                ).fillna(0)
                budget_by_project["budget adjusted"] = (
                    hist_df.groupby("project name")[adjusted_budget_col].sum().values
                )
            else:
                budget_by_project["budget adjusted"] = 0

            # Transform to long format
            hist_melted = []
            for idx, row in budget_by_project.iterrows():
                project = row["project name"]

                if "Бюджет План" in selected_budget_types:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Бюджет План",
                            "Сумма": row["budget plan"],
                        }
                    )

                if "Бюджет Факт" in selected_budget_types:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Бюджет Факт",
                            "Сумма": row["budget fact"],
                        }
                    )

                if (
                    "Бюджет Корректировка" in selected_budget_types
                    and adjusted_budget_col
                ):
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Бюджет Корректировка",
                            "Сумма": row["budget adjusted"],
                        }
                    )

                if "Отклонение (перерасход)" in selected_budget_types and row["reserve budget"] >= 0:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Отклонение (перерасход)",
                            "Сумма": row["reserve budget"],
                        }
                    )
                if "Отклонение (экономия)" in selected_budget_types and row["reserve budget"] < 0:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Отклонение (экономия)",
                            "Сумма": row["reserve budget"],
                        }
                    )

            hist_by_type_df = pd.DataFrame(hist_melted)

            if hist_by_type_df.empty:
                st.info("Нет данных для отображения с выбранными типами бюджета.")
            else:
                # Преобразуем значения в миллионы рублей для отображения на столбцах
                hist_by_type_df["Сумма_млн"] = hist_by_type_df["Сумма"] / 1000000

                # Create histogram
                fig_hist = px.bar(
                    hist_by_type_df,
                    x="project name",
                    y="Сумма",
                    color="Тип бюджета",
                    title="Бюджет план/факт/корректировка/отклонение по проектам",
                    labels={"project name": "Проект", "Сумма": "Сумма бюджета (руб.)"},
                    barmode="group",
                    text="Сумма_млн",
                    color_discrete_map={
                        "Бюджет План": "#2E86AB",
                        "Бюджет Факт": "#A23B72",
                        "Бюджет Корректировка": "#F18F01",
                        "Отклонение (перерасход)": "#e74c3c",
                        "Отклонение (экономия)": "#27ae60",
                    },
                )

                # Update layout
                fig_hist.update_layout(
                    xaxis_title="Проект",
                    yaxis_title="Сумма бюджета (руб.)",
                    height=600,
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                    ),
                    xaxis=dict(tickangle=-45, tickfont=dict(size=12)),
                )

                # Add text labels on the edge of bars (в миллионах рублей)
                fig_hist.update_traces(
                    textposition="outside",
                    texttemplate="%{text:.1f} млн руб.",
                    textfont=dict(size=12, color="white"),
                )

                fig_hist = apply_chart_background(fig_hist)
                st.plotly_chart(fig_hist, use_container_width=True)

                # Summary table (суммы в млн руб., два знака, подпись в названии колонки)
                with st.expander("📋 Сводная таблица по проектам", expanded=False):
                    summary_hist = hist_by_type_df.pivot_table(
                        index="project name",
                        columns="Тип бюджета",
                        values="Сумма",
                        aggfunc="sum",
                        fill_value=0,
                    ).reset_index()

                    # Переводим в млн руб., два знака после запятой; подпись "млн руб." в названии колонки
                    for col in summary_hist.columns:
                        if col != "project name":
                            summary_hist[col] = (
                                (summary_hist[col].astype(float) / 1e6)
                                .round(2)
                                .apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00")
                            )
                    summary_hist = summary_hist.rename(
                        columns={
                            c: f"{c}, млн руб."
                            for c in summary_hist.columns
                            if c != "project name"
                        }
                    )

                    st.table(style_dataframe_for_dark_theme(summary_hist))
        else:
            st.warning(
                "Колонка 'project name' не найдена в данных для построения гистограммы."
            )


# ==================== DASHBOARD 8.1: Budget Old Charts ====================
def dashboard_budget_old_charts(df):
    st.header("💰 БДДС (старые графики)")

    col1, col2, col3 = st.columns(3)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_old_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_old_project"
            )
        else:
            selected_project = "Все"

    with col3:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_old_section"
            )
        else:
            selected_section = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]
    # Check for budget columns (нормализуем русские названия)
    ensure_budget_columns(filtered_df)
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Отклонение = факт - план (положительное — перерасход, красный; отрицательное — экономия, зелёный)
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget fact"] - filtered_df["budget plan"]
    )

    # Group by period first to get totals
    budget_by_period = (
        filtered_df.groupby(period_col)
        .agg({"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"})
        .reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    budget_by_period[period_col] = budget_by_period[period_col].apply(
        format_period_display
    )

    # Checkbox to hide/show deviation (default: hidden)
    hide_reserve = st.checkbox(
        "Скрыть отклонение", value=True, key="budget_old_hide_reserve"
    )

    # Transform data to long format - group by budget type
    budget_melted = []
    for idx, row in budget_by_period.iterrows():
        period = row[period_col]
        budget_melted.append(
            {
                period_col: period,
                "Тип бюджета": "Бюджет План",
                "Сумма": row["budget plan"],
            }
        )
        budget_melted.append(
            {
                period_col: period,
                "Тип бюджета": "Бюджет Факт",
                "Сумма": row["budget fact"],
            }
        )
        # Add deviation only if not hidden (split by sign for red/green)
        if not hide_reserve:
            if row["reserve budget"] >= 0:
                budget_melted.append(
                    {
                        period_col: period,
                        "Тип бюджета": "Отклонение (перерасход)",
                        "Сумма": row["reserve budget"],
                    }
                )
            else:
                budget_melted.append(
                    {
                        period_col: period,
                        "Тип бюджета": "Отклонение (экономия)",
                        "Сумма": row["reserve budget"],
                    }
                )

    budget_by_type_df = pd.DataFrame(budget_melted)
    # Суммы в млн руб. (исходные в рублях)
    budget_by_type_df["Сумма"] = (budget_by_type_df["Сумма"] / 1e6).round(2)

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Stacked area chart showing all budget types
        fig = px.area(
            budget_by_type_df,
            x=period_col,
            y="Сумма",
            color="Тип бюджета",
            title="Бюджет по типам по периоду (накопительно)",
            labels={period_col: period_label, "Сумма": "Сумма, млн руб."},
            text="Сумма",
            color_discrete_map={
                "Бюджет План": "#2E86AB",
                "Бюджет Факт": "#A23B72",
                "Отклонение (перерасход)": "#e74c3c",
                "Отклонение (экономия)": "#27ae60",
            },
        )
        fig.update_xaxes(tickangle=-45)
        fig.update_traces(textposition="top center")
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Grouped bar chart
        fig = px.bar(
            budget_by_type_df,
            x=period_col,
            y="Сумма",
            color="Тип бюджета",
            title="Бюджет по типам по периоду",
            labels={period_col: period_label, "Сумма": "Сумма, млн руб."},
            barmode="group",
            text="Сумма",
            color_discrete_map={
                "Бюджет План": "#2E86AB",
                "Бюджет Факт": "#A23B72",
                "Отклонение (перерасход)": "#e74c3c",
                "Отклонение (экономия)": "#27ae60",
            },
        )
        fig.update_xaxes(tickangle=-45)
        fig.update_traces(textposition="outside", textfont=dict(size=14, color="white"))
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

    # Line chart comparing all types
    fig = px.line(
        budget_by_type_df,
        x=period_col,
        y="Сумма",
        color="Тип бюджета",
        title="Сравнение типов бюджета по периоду",
        labels={period_col: period_label, "Сумма": "Сумма, млн руб."},
        markers=True,
        text="Сумма",
        color_discrete_map={
            "Бюджет План": "#2E86AB",
            "Бюджет Факт": "#A23B72",
            "Отклонение (перерасход)": "#e74c3c",
            "Отклонение (экономия)": "#27ae60",
        },
    )
    fig.update_xaxes(tickangle=-45)
    fig.update_traces(textposition="top center")
    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics (суммы уже в млн руб.)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_plan = budget_by_type_df[
            budget_by_type_df["Тип бюджета"] == "Бюджет План"
        ]["Сумма"].sum()
        st.metric("Всего План", f"{total_plan:.2f} млн руб." if pd.notna(total_plan) else "Н/Д")
    with col2:
        total_fact = budget_by_type_df[
            budget_by_type_df["Тип бюджета"] == "Бюджет Факт"
        ]["Сумма"].sum()
        st.metric("Всего Факт", f"{total_fact:.2f} млн руб." if pd.notna(total_fact) else "Н/Д")
    with col3:
        total_dev = (
            budget_by_type_df[
                budget_by_type_df["Тип бюджета"].isin(
                    ["Отклонение (перерасход)", "Отклонение (экономия)"]
                )
            ]["Сумма"].sum()
            if budget_by_type_df["Тип бюджета"].isin(
                ["Отклонение (перерасход)", "Отклонение (экономия)"]
            ).any()
            else 0
        )
        st.metric(
            "Всего Отклонение",
            f"{total_dev:.2f} млн руб." if pd.notna(total_dev) else "Н/Д",
        )
    with col4:
        variance = (
            total_plan - total_fact
            if pd.notna(total_plan) and pd.notna(total_fact)
            else None
        )
        st.metric(
            "Отклонение",
            (
                f"{variance:.2f} млн руб."
                if variance is not None and pd.notna(variance)
                else "Н/Д"
            ),
        )

    # Pivot table for better readability (Сумма уже в млн — budget_by_type_df["Сумма"] = /1e6)
    pivot_table = budget_by_type_df.pivot(
        index=period_col, columns="Тип бюджета", values="Сумма"
    ).fillna(0)

    # Detailed table — суммы в млн руб., два знака, подпись "млн руб." в названии колонки
    st.subheader("Детальная таблица")
    detailed_table = pivot_table.copy()

    # Названия колонок с подписью "млн руб."
    detailed_table = detailed_table.rename(
        columns={c: f"{c}, млн руб." for c in detailed_table.columns}
    )
    # Формат: два знака после запятой
    for col in detailed_table.columns:
        detailed_table[col] = detailed_table[col].apply(
            lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
        )

    st.table(style_dataframe_for_dark_theme(detailed_table))


# ==================== DASHBOARD: Approved Budget ====================
def calculate_approved_budget(df, rule_name="default"):
    """
    Рассчитывает утвержденный бюджет на основе правил распределения.

    Логика расчета:
    1. Группируем задачи по проекту/разделу/задаче
    2. Для каждой группы находим все месяцы этапа (от минимальной даты начала до максимальной даты окончания)
    3. Для каждого месяца находим все задачи, активные в этом месяце
    4. Суммируем плановый бюджет активных задач - это 100% для месяца
    5. Распределяем эту сумму по правилу между месяцами этапа

    Правила распределения:
    - default: 50% - первый месяц, 45% - равномерно по промежуточным месяцам, 5% - последний месяц

    Args:
        df: DataFrame с данными проектов
        rule_name: название правила из справочника

    Returns:
        DataFrame с распределением утвержденного бюджета по месяцам
    """
    # Справочник правил распределения бюджета
    budget_rules = {
        "default": {
            "first_month_percent": 0.50,  # 50% на первый месяц
            "middle_months_percent": 0.45,  # 45% на промежуточные месяцы
            "last_month_percent": 0.05,  # 5% на последний месяц
            "description": "50% - первый месяц, 45% - равномерно по промежуточным месяцам, 5% - последний месяц",
        }
    }

    # Получаем правило
    if rule_name not in budget_rules:
        rule_name = "default"
    rule = budget_rules[rule_name]

    # Проверяем наличие необходимых колонок
    required_cols = ["budget plan", "plan start", "plan end"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return (
            pd.DataFrame(),
            f"Отсутствуют необходимые колонки: {', '.join(missing_cols)}",
        )

    # Копируем данные для работы
    work_df = df.copy()

    # Конвертируем даты
    work_df["plan start"] = pd.to_datetime(
        work_df["plan start"], errors="coerce", dayfirst=True
    )
    work_df["plan end"] = pd.to_datetime(
        work_df["plan end"], errors="coerce", dayfirst=True
    )
    work_df["budget plan"] = pd.to_numeric(work_df["budget plan"], errors="coerce")

    # Фильтруем строки с валидными данными
    valid_mask = (
        work_df["plan start"].notna()
        & work_df["plan end"].notna()
        & work_df["budget plan"].notna()
        & (work_df["budget plan"] > 0)
        & (work_df["plan start"] <= work_df["plan end"])
    )
    work_df = work_df[valid_mask].copy()

    if work_df.empty:
        return pd.DataFrame(), "Нет данных с валидными датами и бюджетом"

    # Определяем группировку: группируем по комбинации project + section + task
    # Это позволяет правильно обрабатывать случаи, когда выбраны разные уровни фильтрации
    grouping_cols = []
    if "project name" in work_df.columns:
        grouping_cols.append("project name")
    if "section" in work_df.columns:
        grouping_cols.append("section")
    if "task name" in work_df.columns:
        grouping_cols.append("task name")

    # Если нет колонок для группировки, обрабатываем все задачи вместе
    if not grouping_cols:
        # Создаем фиктивную группу для всех задач
        work_df["_group"] = "all"
        grouping_cols = ["_group"]

    # Список для хранения результатов
    approved_budget_rows = []

    # Группируем задачи
    if grouping_cols:
        grouped = work_df.groupby(grouping_cols)
    else:
        # Если нет колонок для группировки, создаем одну группу
        grouped = [("all", work_df)]

    for group_key, group_df in grouped:
        # Находим минимальную дату начала и максимальную дату окончания для группы
        min_start = group_df["plan start"].min()
        max_end = group_df["plan end"].max()

        if pd.isna(min_start) or pd.isna(max_end):
            continue

        # Генерируем все месяцы этапа
        current_date = min_start.replace(day=1)
        end_month = max_end.replace(day=1)

        months = []
        while current_date <= end_month:
            months.append(current_date.to_period("M"))
            # Переходим к следующему месяцу
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        if len(months) == 0:
            continue

        # Для каждого месяца находим активные задачи и суммируем их плановый бюджет
        monthly_budgets = {}
        for month in months:
            month_start = month.start_time
            month_end = month.end_time

            # Находим задачи, активные в этом месяце
            active_tasks = group_df[
                (group_df["plan start"] <= month_end)
                & (group_df["plan end"] >= month_start)
            ]

            # Суммируем плановый бюджет активных задач - это 100% для месяца
            total_budget = active_tasks["budget plan"].sum()
            monthly_budgets[month] = total_budget

        # Рассчитываем распределение бюджета по правилу
        num_months = len(months)

        if num_months == 1:
            # Если только один месяц, весь бюджет идет туда
            first_month_percent = 1.0
            middle_months_percent = 0.0
            last_month_percent = 0.0
        elif num_months == 2:
            # Если два месяца: 50% на первый, 50% на последний
            first_month_percent = rule["first_month_percent"]
            middle_months_percent = 0.0
            last_month_percent = (
                rule["middle_months_percent"] + rule["last_month_percent"]
            )
        else:
            # Если больше двух месяцев: 50% на первый, 45% равномерно на промежуточные, 5% на последний
            first_month_percent = rule["first_month_percent"]
            last_month_percent = rule["last_month_percent"]
            middle_months_percent = rule["middle_months_percent"] / (num_months - 2)

        # Распределяем бюджет по месяцам
        for i, month in enumerate(months):
            # Берем бюджет для этого месяца (100%)
            month_total_budget = monthly_budgets.get(month, 0)

            if month_total_budget == 0:
                continue

            # Определяем процент для этого месяца
            if i == 0:
                # Первый месяц
                month_percent = first_month_percent
            elif i == len(months) - 1:
                # Последний месяц
                month_percent = last_month_percent
            else:
                # Промежуточные месяцы
                month_percent = middle_months_percent

            # Рассчитываем утвержденный бюджет для месяца
            approved_budget = month_total_budget * month_percent

            # Получаем значения группировки
            group_dict = {}
            if grouping_cols:
                if isinstance(group_key, tuple):
                    group_dict = dict(zip(grouping_cols, group_key))
                elif len(grouping_cols) == 1:
                    group_dict = {grouping_cols[0]: group_key}
                else:
                    # Если group_key не кортеж и колонок несколько, возможно это одна группа
                    for col in grouping_cols:
                        if col in group_df.columns:
                            # Берем первое значение из группы
                            group_dict[col] = (
                                group_df[col].iloc[0] if len(group_df) > 0 else ""
                            )

            # Создаем строку с данными
            approved_row = {
                "month": month,
                "approved budget": approved_budget,
                "budget plan": month_total_budget,  # Плановый бюджет для месяца (100%)
                "rule_name": rule_name,
            }

            # Добавляем значения группировки (исключаем фиктивную колонку _group)
            for col in grouping_cols:
                if col != "_group":
                    approved_row[col] = group_dict.get(col, "")

            approved_budget_rows.append(approved_row)

    # Создаем DataFrame из результатов
    if not approved_budget_rows:
        return pd.DataFrame(), "Нет данных для расчета утвержденного бюджета"

    approved_budget_df = pd.DataFrame(approved_budget_rows)

    return approved_budget_df, None


def dashboard_approved_budget(df):
    """Панель для отображения утвержденного бюджета"""
    st.header("💰 Утвержденный бюджет")

    # Информация о правилах
    with st.expander("ℹ️ Правила распределения бюджета", expanded=False):
        st.markdown(
            """
        **Текущее правило (default):**
        - 50% планового бюджета - на первый месяц этапа
        - 45% планового бюджета - равномерно распределяется между промежуточными месяцами
        - 5% планового бюджета - на последний месяц этапа
        
        При изменении дат начала и окончания этапа бюджет автоматически пересчитывается.
        """
        )

    # Фильтры (три колонки: проект, этап, лот)
    col1, col2, col3 = st.columns(3)

    with col1:
        # Check for project column - try English name first (alias from load_data), then Russian
        project_col = None
        if "project name" in df.columns:
            project_col = "project name"
        elif "Проект" in df.columns:
            project_col = "Проект"
        
        if project_col:
            projects = ["Все"] + sorted(df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="approved_budget_project"
            )
        else:
            st.warning("⚠️ Колонка 'project name' не найдена.")
            selected_project = "Все"

    with col2:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="approved_budget_section"
            )
        else:
            selected_section = "Все"

    with col3:
        if "task name" in df.columns:
            tasks = ["Все"] + sorted(df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox(
                "Фильтр по лоту", tasks, key="approved_budget_task"
            )
        else:
            selected_task = "Все"

    # Применяем фильтры
    filtered_df = df.copy()
    if selected_project != "Все" and project_col and project_col in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df[project_col].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]
    if selected_task != "Все" and "task name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]

    # Рассчитываем утвержденный бюджет
    approved_budget_df, error = calculate_approved_budget(
        filtered_df, rule_name="default"
    )

    if error:
        st.error(error)
        return

    if approved_budget_df.empty:
        st.info("Нет данных для построения графика утвержденного бюджета.")
        return

    # Группируем по месяцам для графика
    monthly_approved = (
        approved_budget_df.groupby("month")
        .agg({"approved budget": "sum", "budget plan": "sum"})  # Для сравнения
        .reset_index()
    )

    # Сортируем по месяцам
    monthly_approved = monthly_approved.sort_values("month")

    # Форматируем месяц для отображения
    def format_month_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        try:
            if isinstance(period_val, pd.Period):
                month_num = period_val.month
                year = period_val.year
                RUSSIAN_MONTHS = {
                    1: "Январь",
                    2: "Февраль",
                    3: "Март",
                    4: "Апрель",
                    5: "Май",
                    6: "Июнь",
                    7: "Июль",
                    8: "Август",
                    9: "Сентябрь",
                    10: "Октябрь",
                    11: "Ноябрь",
                    12: "Декабрь",
                }
                return f"{RUSSIAN_MONTHS.get(month_num, 'Н/Д')} {year}"
            return str(period_val)
        except:
            return str(period_val)

    monthly_approved["Месяц"] = monthly_approved["month"].apply(format_month_display)
    # Значения в млн руб. для отображения
    monthly_approved["approved budget млн"] = (monthly_approved["approved budget"] / 1e6).round(2)
    monthly_approved["budget plan млн"] = (monthly_approved["budget plan"] / 1e6).round(2)

    # Создаем график (ось Y — млн руб.)
    fig = go.Figure()

    # Добавляем утвержденный бюджет
    fig.add_trace(
        go.Bar(
            x=monthly_approved["Месяц"],
            y=monthly_approved["approved budget млн"],
            name="Утвержденный бюджет",
            marker_color="#2E86AB",
            text=monthly_approved["approved budget млн"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Добавляем плановый бюджет для сравнения (линия)
    fig.add_trace(
        go.Scatter(
            x=monthly_approved["Месяц"],
            y=monthly_approved["budget plan млн"],
            name="Плановый бюджет (сумма)",
            mode="lines+markers",
            line=dict(color="#F18F01", width=2),
            marker=dict(size=8, color="#F18F01"),
        )
    )

    fig.update_layout(
        title="Утвержденный бюджет по месяцам",
        xaxis_title="Месяц",
        yaxis_title="млн руб.",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600,
    )

    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Сводная таблица (млн руб.)
    st.subheader("Сводная таблица утвержденного бюджета по месяцам")
    summary_table = monthly_approved[["Месяц", "approved budget млн", "budget plan млн"]].copy()
    summary_table.columns = ["Месяц", "Утвержденный бюджет, млн руб.", "Плановый бюджет (сумма), млн руб."]
    summary_table["Утвержденный бюджет, млн руб."] = summary_table["Утвержденный бюджет, млн руб."].apply(
        lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
    )
    summary_table["Плановый бюджет (сумма), млн руб."] = summary_table[
        "Плановый бюджет (сумма), млн руб."
    ].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00")
    st.table(style_dataframe_for_dark_theme(summary_table))

    # Детальная таблица (млн руб.)
    with st.expander("📋 Детальная таблица распределения бюджета", expanded=False):
        detail_table = approved_budget_df[
            [
                "project name",
                "section",
                "task name",
                "month",
                "budget plan",
                "approved budget",
            ]
        ].copy()
        detail_table["month"] = detail_table["month"].apply(format_month_display)
        detail_table["Плановый бюджет"] = (detail_table["budget plan"] / 1e6).round(2).apply(
            lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
        )
        detail_table["Утвержденный бюджет"] = (detail_table["approved budget"] / 1e6).round(2).apply(
            lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
        )
        detail_table = detail_table.drop(columns=["budget plan", "approved budget"], errors="ignore")
        detail_table.columns = [
            "Проект",
            "Раздел",
            "Задача",
            "Месяц",
            "Плановый бюджет, млн руб.",
            "Утвержденный бюджет, млн руб.",
        ]
        st.table(style_dataframe_for_dark_theme(detail_table))


# ==================== DASHBOARD: Forecast Budget ====================
def calculate_forecast_budget(df, edited_data=None, rule_name="default"):
    """
    Рассчитывает прогнозный бюджет на основе утвержденного бюджета с учетом возможных изменений.

    Args:
        df: DataFrame с исходными данными проектов
        edited_data: DataFrame с отредактированными данными (даты, утвержденный бюджет)
        rule_name: название правила распределения

    Returns:
        DataFrame с распределением прогнозного бюджета по месяцам
    """
    # Используем отредактированные данные, если они есть, иначе исходные
    work_df = edited_data.copy() if edited_data is not None else df.copy()

    # Рассчитываем утвержденный бюджет на основе текущих данных
    approved_budget_df, error = calculate_approved_budget(work_df, rule_name=rule_name)

    if error:
        return pd.DataFrame(), error

    # Прогнозный бюджет = утвержденный бюджет (но может быть изменен пользователем)
    # Если пользователь изменил утвержденный бюджет вручную, используем эти значения
    forecast_budget_df = approved_budget_df.copy()

    # Переименовываем колонку для ясности
    if "approved budget" in forecast_budget_df.columns:
        forecast_budget_df["forecast budget"] = forecast_budget_df["approved budget"]

    return forecast_budget_df, None


def dashboard_forecast_budget(df):
    """Панель для отображения и редактирования прогнозного бюджета"""
    st.header("📈 Прогнозный бюджет")

    # Информация о прогнозном бюджете
    with st.expander("ℹ️ О прогнозном бюджете", expanded=False):
        st.markdown(
            """
        **Прогнозный бюджет** рассчитывается на основе утвержденного бюджета и может быть скорректирован:
        - При изменении плановых дат начала и окончания этапов
        - При изменении утвержденного бюджета по задачам
        
        Прогнозный бюджет автоматически пересчитывается при любых изменениях.
        """
        )

    # Фильтр по проекту (обязательный для прогнозного бюджета)
    # Check English name first (alias created in load_data), then Russian
    project_col = None
    if "project name" in df.columns:
        project_col = "project name"
    elif "Проект" in df.columns:
        project_col = "Проект"
    
    if not project_col:
        st.warning(
            "Колонка 'project name' не найдена. Необходима для работы с прогнозным бюджетом."
        )
        return

    projects = sorted(df[project_col].dropna().unique().tolist())
    if not projects:
        st.warning("Проекты не найдены в данных.")
        return

    selected_project = st.selectbox(
        "Выберите проект", projects, key="forecast_budget_project"
    )

    # Фильтруем данные по выбранному проекту
    project_df = df[
        df[project_col].astype(str).str.strip() == str(selected_project).strip()
    ].copy()

    if project_df.empty:
        st.info("Нет данных для выбранного проекта.")
        return

    # Проверяем наличие необходимых колонок
    required_cols = ["budget plan", "plan start", "plan end", "task name"]
    missing_cols = [col for col in required_cols if col not in project_df.columns]
    if missing_cols:
        st.warning(f"Отсутствуют необходимые колонки: {', '.join(missing_cols)}")
        return

    # Инициализируем session_state для хранения отредактированных данных
    if f"forecast_edited_data_{selected_project}" not in st.session_state:
        st.session_state[f"forecast_edited_data_{selected_project}"] = project_df.copy()

    # Инициализируем session_state для хранения отредактированной таблицы (для отображения)
    if f"forecast_edit_table_{selected_project}" not in st.session_state:
        # Подготавливаем данные для редактирования в первый раз
        current_data = project_df.copy()
        if "section" not in current_data.columns:
            current_data["section"] = "—"
        edit_df = current_data[
            ["task name", "section", "plan start", "plan end", "budget plan"]
        ].copy()

        # Конвертируем даты в datetime для корректного отображения
        edit_df["plan start"] = pd.to_datetime(
            edit_df["plan start"], errors="coerce", dayfirst=True
        )
        edit_df["plan end"] = pd.to_datetime(
            edit_df["plan end"], errors="coerce", dayfirst=True
        )

        # Форматируем для отображения
        edit_df["plan start"] = edit_df["plan start"].dt.date
        edit_df["plan end"] = edit_df["plan end"].dt.date

        # Переименовываем колонки; бюджет в млн руб. для отображения с точкой
        edit_df["budget plan"] = (edit_df["budget plan"].astype(float) / 1e6).round(2)
        edit_df.columns = [
            "Задача",
            "Раздел",
            "План. начало",
            "План. окончание",
            "Плановый бюджет, млн руб.",
        ]

        st.session_state[f"forecast_edit_table_{selected_project}"] = edit_df.copy()

    # Получаем текущую таблицу для редактирования (страховка: пересобрать, если ключа не было)
    if f"forecast_edit_table_{selected_project}" not in st.session_state:
        current_data = project_df.copy()
        if "section" not in current_data.columns:
            current_data["section"] = "—"
        edit_df = current_data[
            ["task name", "section", "plan start", "plan end", "budget plan"]
        ].copy()
        edit_df["plan start"] = pd.to_datetime(
            edit_df["plan start"], errors="coerce", dayfirst=True
        )
        edit_df["plan end"] = pd.to_datetime(
            edit_df["plan end"], errors="coerce", dayfirst=True
        )
        edit_df["plan start"] = edit_df["plan start"].dt.date
        edit_df["plan end"] = edit_df["plan end"].dt.date
        edit_df["budget plan"] = (edit_df["budget plan"].astype(float) / 1e6).round(2)
        edit_df.columns = [
            "Задача",
            "Раздел",
            "План. начало",
            "План. окончание",
            "Плановый бюджет, млн руб.",
        ]
        st.session_state[f"forecast_edit_table_{selected_project}"] = edit_df.copy()
    edit_df = st.session_state[f"forecast_edit_table_{selected_project}"].copy()

    # Нормализация колонок: если в session_state старые имена (budget plan и т.д.), приводим к русским
    _budget_col = "Плановый бюджет, млн руб."
    if _budget_col not in edit_df.columns and "budget plan" in edit_df.columns:
        edit_df = edit_df.rename(columns={"budget plan": _budget_col})
    if "Задача" not in edit_df.columns and "task name" in edit_df.columns:
        edit_df = edit_df.rename(columns={"task name": "Задача"})
    if "Раздел" not in edit_df.columns and "section" in edit_df.columns:
        edit_df = edit_df.rename(columns={"section": "Раздел"})
    if "План. начало" not in edit_df.columns and "plan start" in edit_df.columns:
        edit_df = edit_df.rename(columns={"plan start": "План. начало"})
    if "План. окончание" not in edit_df.columns and "plan end" in edit_df.columns:
        edit_df = edit_df.rename(columns={"plan end": "План. окончание"})

    st.subheader("📝 Редактирование данных задач")
    st.info(
        "Измените даты начала/окончания или плановый бюджет (в млн руб.). Изменения применяются при нажатии 'Применить изменения'."
    )

    if edit_df.empty:
        st.info("Нет задач для отображения в таблице редактирования для выбранного проекта.")
        edited_df = edit_df.copy()
    else:
        # Форма с отдельными полями ввода вместо data_editor — текст и значения видны в тёмной теме
        # Заголовки в тех же колонках, что и данные — подписи не кучкуются
        h1, h2, h3, h4, h5 = st.columns(5)
        with h1:
            st.caption("**Задача**")
        with h2:
            st.caption("**Раздел**")
        with h3:
            st.caption("**План. начало**")
        with h4:
            st.caption("**План. окончание**")
        with h5:
            st.caption("**Плановый бюджет, млн руб.**")
        edited_rows = []
        budget_col_name = "Плановый бюджет, млн руб." if "Плановый бюджет, млн руб." in edit_df.columns else "budget plan"
        for i in range(len(edit_df)):
            row = edit_df.iloc[i]
            plan_start_val = row["План. начало"] if "План. начало" in row.index else row.get("plan start")
            plan_end_val = row["План. окончание"] if "План. окончание" in row.index else row.get("plan end")
            raw_budget = row.get(budget_col_name)
            if pd.notna(raw_budget):
                v = float(raw_budget)
                # Всегда показывать в млн руб.: если значение в рублях (по имени колонки или по величине), делим на 1e6
                if budget_col_name == "budget plan" or v > 1e5:
                    budget_val = round(v / 1e6, 2)
                else:
                    budget_val = v
            else:
                budget_val = 0.0
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.text(str(row["Задача"])[:50] + ("…" if len(str(row["Задача"])) > 50 else ""))
            with c2:
                st.text(str(row["Раздел"])[:30] + ("…" if len(str(row["Раздел"])) > 30 else ""))
            with c3:
                plan_start = st.date_input(
                    "План. начало",
                    value=plan_start_val,
                    key=f"forecast_plan_start_{selected_project}_{i}",
                    label_visibility="collapsed",
                )
            with c4:
                plan_end = st.date_input(
                    "План. окончание",
                    value=plan_end_val,
                    key=f"forecast_plan_end_{selected_project}_{i}",
                    label_visibility="collapsed",
                )
            with c5:
                budget = st.number_input(
                    "Бюджет, млн руб.",
                    value=budget_val,
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    key=f"forecast_budget_{selected_project}_{i}",
                    label_visibility="collapsed",
                )
            edited_rows.append({
                "Задача": row.get("Задача", row.get("task name", "")),
                "Раздел": row.get("Раздел", row.get("section", "")),
                "План. начало": plan_start,
                "План. окончание": plan_end,
                "Плановый бюджет, млн руб.": budget,
            })
        edited_df = pd.DataFrame(edited_rows)

    # Кнопка для применения изменений
    col_apply, col_reset = st.columns(2)
    with col_apply:
        apply_changes = st.button(
            "✅ Применить изменения",
            key=f"apply_forecast_{selected_project}",
            type="primary",
        )
    with col_reset:
        reset_changes = st.button(
            "🔄 Сбросить изменения", key=f"reset_forecast_{selected_project}"
        )

    # Обрабатываем сброс изменений
    if reset_changes:
        # Сбрасываем данные
        st.session_state[f"forecast_edited_data_{selected_project}"] = project_df.copy()
        project_for_reset = project_df.copy()
        if "section" not in project_for_reset.columns:
            project_for_reset["section"] = "—"
        edit_df_reset = project_for_reset[
            ["task name", "section", "plan start", "plan end", "budget plan"]
        ].copy()
        edit_df_reset["plan start"] = pd.to_datetime(
            edit_df_reset["plan start"], errors="coerce", dayfirst=True
        )
        edit_df_reset["plan end"] = pd.to_datetime(
            edit_df_reset["plan end"], errors="coerce", dayfirst=True
        )
        edit_df_reset["plan start"] = edit_df_reset["plan start"].dt.date
        edit_df_reset["plan end"] = edit_df_reset["plan end"].dt.date
        edit_df_reset["budget plan"] = (edit_df_reset["budget plan"].astype(float) / 1e6).round(2)
        edit_df_reset.columns = [
            "Задача",
            "Раздел",
            "План. начало",
            "План. окончание",
            "Плановый бюджет, млн руб.",
        ]
        st.session_state[f"forecast_edit_table_{selected_project}"] = (
            edit_df_reset.copy()
        )
        st.success("🔄 Изменения сброшены!")
        st.rerun()

    # Сохраняем отредактированную таблицу в session_state
    st.session_state[f"forecast_edit_table_{selected_project}"] = edited_df.copy()

    # Получаем исходные данные проекта
    current_data = st.session_state[f"forecast_edited_data_{selected_project}"].copy()

    # Обновляем исходные данные с учетом изменений из отредактированной таблицы
    updated_data = current_data.copy().reset_index(drop=True)
    edited_df_reset = edited_df.reset_index(drop=True)

    # Обновляем даты и бюджет по индексам (бюджет из млн руб. переводим в рубли)
    if len(updated_data) == len(edited_df_reset):
        # Обновляем даты - конвертируем из date обратно в datetime
        if "План. начало" in edited_df_reset.columns:
            updated_data["plan start"] = pd.to_datetime(
                edited_df_reset["План. начало"], errors="coerce"
            )
        if "План. окончание" in edited_df_reset.columns:
            updated_data["plan end"] = pd.to_datetime(
                edited_df_reset["План. окончание"], errors="coerce"
            )
        budget_col = "Плановый бюджет, млн руб." if "Плановый бюджет, млн руб." in edited_df_reset.columns else "Плановый бюджет"
        if budget_col in edited_df_reset.columns:
            millions = pd.to_numeric(edited_df_reset[budget_col], errors="coerce")
            updated_data["budget plan"] = (millions * 1e6).round(0)

    # Применяем изменения при нажатии кнопки
    if apply_changes:
        # Сохраняем обновленные данные в session_state
        st.session_state[f"forecast_edited_data_{selected_project}"] = updated_data
        st.success("✅ Изменения применены! График обновлен.")

    # ВСЕГДА используем актуальные данные из отредактированной таблицы для расчета
    # Это позволяет видеть изменения сразу после применения
    current_data = updated_data

    # Рассчитываем прогнозный бюджет с актуальными данными
    forecast_budget_df, error = calculate_forecast_budget(
        df, edited_data=current_data, rule_name="default"
    )

    # Перезапускаем только после применения изменений
    if apply_changes:
        st.rerun()

    if error:
        st.error(error)
        return

    if forecast_budget_df.empty:
        st.info("Нет данных для построения графика прогнозного бюджета.")
        return

    # Группируем по месяцам для графика
    monthly_forecast = (
        forecast_budget_df.groupby("month")
        .agg({"forecast budget": "sum", "budget plan": "sum"})  # Для сравнения
        .reset_index()
    )

    # Сортируем по месяцам
    monthly_forecast = monthly_forecast.sort_values("month")

    # Форматируем месяц для отображения
    def format_month_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        try:
            if isinstance(period_val, pd.Period):
                month_num = period_val.month
                year = period_val.year
                RUSSIAN_MONTHS = {
                    1: "Январь",
                    2: "Февраль",
                    3: "Март",
                    4: "Апрель",
                    5: "Май",
                    6: "Июнь",
                    7: "Июль",
                    8: "Август",
                    9: "Сентябрь",
                    10: "Октябрь",
                    11: "Ноябрь",
                    12: "Декабрь",
                }
                return f"{RUSSIAN_MONTHS.get(month_num, 'Н/Д')} {year}"
            return str(period_val)
        except:
            return str(period_val)

    monthly_forecast["Месяц"] = monthly_forecast["month"].apply(format_month_display)
    # Значения в млн руб. с точкой как десятичным разделителем
    monthly_forecast["forecast budget млн"] = (monthly_forecast["forecast budget"] / 1e6).round(2)
    monthly_forecast["budget plan млн"] = (monthly_forecast["budget plan"] / 1e6).round(2)

    def _fmt_million_dot(x):
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return ""
        return f"{float(x):.2f}".replace(",", ".")

    # Создаем график (ось Y — млн руб.)
    fig = go.Figure()

    # Добавляем прогнозный бюджет
    fig.add_trace(
        go.Bar(
            x=monthly_forecast["Месяц"],
            y=monthly_forecast["forecast budget млн"],
            name="Прогнозный бюджет",
            marker_color="#06A77D",
            text=monthly_forecast["forecast budget млн"].apply(
                lambda x: _fmt_million_dot(x) + " млн руб." if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Добавляем плановый бюджет для сравнения (линия)
    fig.add_trace(
        go.Scatter(
            x=monthly_forecast["Месяц"],
            y=monthly_forecast["budget plan млн"],
            name="Плановый бюджет (сумма)",
            mode="lines+markers",
            line=dict(color="#F18F01", width=2),
            marker=dict(size=8, color="#F18F01"),
        )
    )

    fig.update_layout(
        title=f"Прогнозный бюджет по месяцам (Проект: {selected_project})",
        xaxis_title="Месяц",
        yaxis_title="млн руб.",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600,
    )

    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Сводная таблица — значения в млн руб. (пересчёт из рублей: / 1e6)
    st.subheader("Сводная таблица прогнозного бюджета по месяцам")
    summary_table = monthly_forecast[["Месяц", "forecast budget", "budget plan"]].copy()
    summary_table.columns = ["Месяц", "Прогнозный бюджет, млн руб.", "Плановый бюджет (сумма), млн руб."]
    summary_table["Прогнозный бюджет, млн руб."] = (
        pd.to_numeric(summary_table["Прогнозный бюджет, млн руб."], errors="coerce").fillna(0) / 1e6
    ).round(2)
    summary_table["Плановый бюджет (сумма), млн руб."] = (
        pd.to_numeric(summary_table["Плановый бюджет (сумма), млн руб."], errors="coerce").fillna(0) / 1e6
    ).round(2)
    summary_table["Прогнозный бюджет, млн руб."] = summary_table["Прогнозный бюджет, млн руб."].apply(
        lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
    )
    summary_table["Плановый бюджет (сумма), млн руб."] = summary_table[
        "Плановый бюджет (сумма), млн руб."
    ].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00")
    st.table(style_dataframe_for_dark_theme(summary_table))

    # Детальная таблица — значения в млн руб. (пересчёт из рублей: / 1e6)
    with st.expander(
        "📋 Детальная таблица распределения прогнозного бюджета", expanded=False
    ):
        detail_table = forecast_budget_df[
            [
                "project name",
                "section",
                "task name",
                "month",
                "budget plan",
                "forecast budget",
            ]
        ].copy()
        detail_table["month"] = detail_table["month"].apply(format_month_display)
        # Пересчёт в млн руб.: исходные колонки в рублях
        detail_table["Плановый бюджет, млн руб."] = (
            pd.to_numeric(detail_table["budget plan"], errors="coerce").fillna(0) / 1e6
        ).round(2)
        detail_table["Прогнозный бюджет, млн руб."] = (
            pd.to_numeric(detail_table["forecast budget"], errors="coerce").fillna(0) / 1e6
        ).round(2)
        detail_table = detail_table.drop(columns=["budget plan", "forecast budget"], errors="ignore")
        detail_table = detail_table.rename(columns={
            "project name": "Проект",
            "section": "Раздел",
            "task name": "Задача",
            "month": "Месяц",
        })
        # Формат отображения с точкой
        detail_table["Плановый бюджет, млн руб."] = detail_table["Плановый бюджет, млн руб."].apply(
            lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
        )
        detail_table["Прогнозный бюджет, млн руб."] = detail_table["Прогнозный бюджет, млн руб."].apply(
            lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
        )
        st.table(style_dataframe_for_dark_theme(detail_table))
