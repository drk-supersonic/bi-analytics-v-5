"""
Регистр дашбордов: имя отчёта -> функция отрисовки.
Функции отрисовки импортируются из dashboards._renderers.
"""
from typing import Callable, Dict, List, Tuple

# Список отчётов по категориям (3 категории: причины+отклонения от плана, финансы, прочее)
REPORT_CATEGORIES: List[Tuple[str, List[str]]] = [
    (
        "Причины отклонений",
        [
            "Динамика отклонений",
            "Отклонение текущего срока от базового плана",
            "Значения отклонений от базового плана",
        ],
    ),
    (
        "Аналитика по финансам",
        [
            "БДДС",
            "БДР",
            "Бюджет план/факт",
            "Утвержденный бюджет",
            "Прогнозный бюджет",
        ],
    ),
    (
        "Прочее",
        [
            "Выдача рабочей/проектной документации",
            "Аналитика по технике",
            "График движения рабочей силы",
        ],
    ),
]


def _get_dashboards() -> Dict[str, Callable]:
    """Строит словарь имя_отчёта -> render(df). Импорт из dashboards._renderers."""
    import os
    import sys
    import streamlit as st
    # Родительская папка (bi-analytics) должна быть в sys.path для config, utils и т.д.
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_this_dir)
    if _parent and _parent not in sys.path:
        sys.path.insert(0, _parent)
    try:
        from dashboards import _renderers
    except Exception as e:
        import traceback
        raise RuntimeError(
            f"Ошибка при загрузке дашбордов (dashboards._renderers): {e!r}\n\n"
            f"Полный traceback:\n{traceback.format_exc()}"
        ) from e

    dashboard_deviations_combined = _renderers.dashboard_deviations_combined
    dashboard_reasons_of_deviation = _renderers.dashboard_reasons_of_deviation
    dashboard_dynamics_of_deviations = _renderers.dashboard_dynamics_of_deviations
    dashboard_plan_fact_dates = _renderers.dashboard_plan_fact_dates
    dashboard_deviation_by_tasks_current_month = _renderers.dashboard_deviation_by_tasks_current_month
    dashboard_dynamics_of_reasons = _renderers.dashboard_dynamics_of_reasons
    dashboard_budget_by_period = _renderers.dashboard_budget_by_period
    dashboard_budget_by_section = _renderers.dashboard_budget_by_section
    dashboard_bdr = getattr(_renderers, "dashboard_bdr", None)
    if dashboard_bdr is None:

        def _stub_bdr(df):
            st.error(
                "Дашборд БДР не найден в dashboards/_renderers.py. "
                "Убедитесь, что функция dashboard_bdr определена в файле."
            )

        dashboard_bdr = _stub_bdr
    dashboard_budget_by_type = _renderers.dashboard_budget_by_type
    dashboard_approved_budget = _renderers.dashboard_approved_budget
    dashboard_forecast_budget = _renderers.dashboard_forecast_budget
    dashboard_rd_delay = _renderers.dashboard_rd_delay
    dashboard_documentation = _renderers.dashboard_documentation
    dashboard_technique = _renderers.dashboard_technique
    dashboard_workforce_movement = _renderers.dashboard_workforce_movement
    dashboard_workforce_and_skud = getattr(_renderers, "dashboard_workforce_and_skud", None)
    if dashboard_workforce_and_skud is None:
        dashboard_workforce_and_skud = _renderers.dashboard_workforce_movement
    dashboard_skud_stroyka = _renderers.dashboard_skud_stroyka

    return {
        "Динамика отклонений": dashboard_deviations_combined,
        "Динамика отклонений по месяцам": dashboard_deviations_combined,
        "Динамика причин отклонений": dashboard_deviations_combined,
        "БДДС": dashboard_budget_by_period,
        "БДДС по месяцам": dashboard_budget_by_period,
        "БДР": dashboard_bdr,
        "Бюджет по лотам": dashboard_budget_by_period,
        "Бюджет план/факт": dashboard_budget_by_type,
        "Бюджет План/Прогноз/Факт": dashboard_budget_by_type,
        "Утвержденный бюджет": dashboard_approved_budget,
        "Бюджет по проекту": dashboard_approved_budget,
        "Прогнозный бюджет": dashboard_forecast_budget,
        "Отклонение текущего срока от базового плана": dashboard_plan_fact_dates,
        "Значения отклонений от базового плана": dashboard_deviation_by_tasks_current_month,
        "Выдача рабочей/проектной документации": dashboard_documentation,
        "Аналитика по технике": dashboard_technique,
        "График движения рабочей силы": dashboard_workforce_and_skud,
        "Просрочка выдачи РД": dashboard_rd_delay,
        "СКУД стройка": dashboard_skud_stroyka,
    }


# Ленивая загрузка, чтобы при импорте dashboards не тянуть project_visualization_app
_dashboards_cache: Dict[str, Callable] = {}


def get_dashboards() -> Dict[str, Callable]:
    """Возвращает словарь DASHBOARDS (кэшируется)."""
    global _dashboards_cache
    if not _dashboards_cache:
        _dashboards_cache = _get_dashboards()
    return _dashboards_cache


def get_dashboard_renderer(name: str) -> Callable:
    """Возвращает функцию отрисовки по имени отчёта или None."""
    return get_dashboards().get(name)


def get_all_report_names() -> List[str]:
    """Возвращает плоский список всех имён отчётов (для report_params, filters и т.д.)."""
    return [r for _, reports in REPORT_CATEGORIES for r in reports]
