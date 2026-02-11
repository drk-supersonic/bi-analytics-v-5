"""
Страница для настройки фильтров отчетов
"""
import sys
from pathlib import Path

# App root: walk up until we find auth.py + config.py (works when __file__ or CWD is wrong)
_here = Path(__file__).resolve().parent

_app_root = _here.parent

_p = _here.parent

while _p != _p.parent:

    if (_p / "auth.py").exists() and (_p / "config.py").exists():

        _app_root = _p

        break
    _p = _p.parent
    
sys.path.insert(0, str(_app_root))

# ┌──────────────────────────────────────────────────────────────────────────┐ #
# │ ⊗ CSS CONNECT ¤ Start                                                    │ #
# └──────────────────────────────────────────────────────────────────────────┘ #

def load_custom_css():

    css_path = _app_root / "static" / "css" / "style.css"

    if css_path.exists():

        with open(css_path, encoding="utf-8") as f:

            css_content = f.read()

        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

    else:

        st.warning(f"CSS файл не найден: {css_path}")

# ┌──────────────────────────────────────────────────────────────────────────┐ #
# │ ⊗ CSS CONNECT ¤ End                                                      │ #
# └──────────────────────────────────────────────────────────────────────────┘ #

import streamlit as st
import pandas as pd
from auth import (
    check_authentication,
    get_current_user,
    require_auth,
    get_user_role_display,
    ROLES,
    init_db,
    render_sidebar_menu
)
try:
    from filters import (
        get_default_filters,
        set_default_filter,
        delete_default_filter,
        get_all_default_filters,
        copy_filters_to_role,
        AVAILABLE_REPORTS,
        FILTER_TYPES
    )

except ImportError as e:

    AVAILABLE_REPORTS = []

    FILTER_TYPES = {}

    def get_default_filters(*args, **kwargs):

        return {}

    def set_default_filter(*args, **kwargs):

        return False

    def delete_default_filter(*args, **kwargs):

        return False

    def get_all_default_filters(*args, **kwargs):

        return []

    def copy_filters_to_role(*args, **kwargs):

        return False

    import warnings

    warnings.warn(f"Ошибка импорта модуля filters: {e}")

try:

    from logger import log_action

except ImportError:

    def log_action(*args, **kwargs):

        pass

# Инициализация базы данных
init_db()

# Проверка, что мы в контексте Streamlit
def is_streamlit_context():

    """Проверка, что код выполняется в контексте Streamlit"""

    try:

        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None

    except:

        return False

# Выполняем код только в контексте Streamlit
if is_streamlit_context():
    # Настройка страницы
    st.set_page_config(
        page_title="Параметры отчетов - BI Analytics",
        page_icon="⚙️",
        layout="wide",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ CSS CONNECT ¤ Start                                                │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    load_custom_css()

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ CSS CONNECT ¤ End                                                  │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    # # Custom CSS для фона страницы
    # st.markdown(
    #     """
    #     <style>
    #     /* Фон приложения - основной цвет */
    #     .stApp {
    #         background-color: #12385C !important;
    #     }
    #
    #     /* Стилизация хедера Streamlit - фон цвета основного фона */
    #     header[data-testid="stHeader"],
    #     .stHeader,
    #     header,
    #     div[data-testid="stHeader"],
    #     .stHeader > div,
    #     header > div,
    #     div[data-testid="stHeader"] > div {
    #         background-color: #12385C !important;
    #         border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    #     }
    #
    #     /* Текст в хедере */
    #     header[data-testid="stHeader"] *,
    #     .stHeader *,
    #     header *,
    #     div[data-testid="stHeader"] * {
    #         color: #ffffff !important;
    #     }
    #
    #     /* Основной контент - белый текст на темном фоне */
    #     .main .block-container,
    #     .main .element-container,
    #     .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    #     .main p, .main span, .main div,
    #     .main label {
    #         color: #ffffff !important;
    #     }
    #
    #     /* Контейнеры с контентом - темный фон */
    #     .main .block-container {
    #         background-color: rgba(18, 56, 92, 0.8) !important;
    #     }
    #
    #     /* Стилизация таблиц (dataframes) - фон цвета основного фона с белым текстом и границами */
    #     /* Базовые контейнеры */
    #     .stDataFrame,
    #     div[data-testid="stDataFrame"],
    #     .dataframe {
    #         background-color: #12385C !important;
    #     }
    #
    #     /* Вложенные div элементы */
    #     .stDataFrame > div,
    #     div[data-testid="stDataFrame"] > div,
    #     .dataframe > div,
    #     .stDataFrame div,
    #     div[data-testid="stDataFrame"] div,
    #     .dataframe div {
    #         background-color: #12385C !important;
    #     }
    #
    #     /* Таблицы - белый текст и белые границы */
    #     .stDataFrame table,
    #     div[data-testid="stDataFrame"] table,
    #     .dataframe table {
    #         background-color: #12385C !important;
    #         border-collapse: collapse !important;
    #         border: 1px solid #ffffff !important;
    #         color: #ffffff !important;
    #     }
    #
    #     /* Заголовки таблиц */
    #     .stDataFrame thead,
    #     div[data-testid="stDataFrame"] thead,
    #     .dataframe thead {
    #         background-color: rgba(18, 56, 92, 0.95) !important;
    #     }
    #
    #     /* Тела таблиц */
    #     .stDataFrame tbody,
    #     div[data-testid="stDataFrame"] tbody,
    #     .dataframe tbody {
    #         background-color: #12385C !important;
    #     }
    #
    #     /* Строки таблиц */
    #     .stDataFrame tr,
    #     div[data-testid="stDataFrame"] tr,
    #     .dataframe tr {
    #         background-color: #12385C !important;
    #         border-bottom: 1px solid #ffffff !important;
    #     }
    #
    #     /* Заголовки ячеек - белый текст, белые границы */
    #     .stDataFrame th,
    #     div[data-testid="stDataFrame"] th,
    #     .dataframe th {
    #         background-color: rgba(18, 56, 92, 0.95) !important;
    #         color: #ffffff !important;
    #         border: 1px solid #ffffff !important;
    #         border-right: 1px solid #ffffff !important;
    #         border-bottom: 1px solid #ffffff !important;
    #         border-left: 1px solid #ffffff !important;
    #         border-top: 1px solid #ffffff !important;
    #         padding: 8px !important;
    #         font-weight: bold !important;
    #     }
    #
    #     /* Ячейки таблиц - белый текст, белые границы */
    #     .stDataFrame td,
    #     div[data-testid="stDataFrame"] td,
    #     .dataframe td {
    #         background-color: rgba(18, 56, 92, 0.85) !important;
    #         color: #ffffff !important;
    #         border: 1px solid #ffffff !important;
    #         border-right: 1px solid #ffffff !important;
    #         border-bottom: 1px solid #ffffff !important;
    #         border-left: 1px solid #ffffff !important;
    #         border-top: 1px solid #ffffff !important;
    #         padding: 8px !important;
    #     }
    #
    #     /* Четные строки */
    #     .stDataFrame tbody tr:nth-child(even),
    #     div[data-testid="stDataFrame"] tbody tr:nth-child(even),
    #     .dataframe tbody tr:nth-child(even) {
    #         background-color: rgba(18, 56, 92, 0.7) !important;
    #     }
    #
    #     .stDataFrame tbody tr:nth-child(even) td,
    #     div[data-testid="stDataFrame"] tbody tr:nth-child(even) td,
    #     .dataframe tbody tr:nth-child(even) td {
    #         background-color: rgba(18, 56, 92, 0.7) !important;
    #         color: #ffffff !important;
    #         border: 1px solid #ffffff !important;
    #         border-right: 1px solid #ffffff !important;
    #         border-bottom: 1px solid #ffffff !important;
    #         border-left: 1px solid #ffffff !important;
    #         border-top: 1px solid #ffffff !important;
    #     }
    #
    #     /* При наведении */
    #     .stDataFrame tbody tr:hover,
    #     div[data-testid="stDataFrame"] tbody tr:hover,
    #     .dataframe tbody tr:hover {
    #         background-color: rgba(18, 56, 92, 1) !important;
    #     }
    #
    #     .stDataFrame tbody tr:hover td,
    #     div[data-testid="stDataFrame"] tbody tr:hover td,
    #     .dataframe tbody tr:hover td {
    #         background-color: rgba(18, 56, 92, 1) !important;
    #         color: #ffffff !important;
    #         border: 1px solid #ffffff !important;
    #         border-right: 1px solid #ffffff !important;
    #         border-bottom: 1px solid #ffffff !important;
    #         border-left: 1px solid #ffffff !important;
    #         border-top: 1px solid #ffffff !important;
    #     }
    #
    #     /* Текст в таблицах - принудительно белый для всех элементов */
    #     .stDataFrame,
    #     div[data-testid="stDataFrame"],
    #     .dataframe,
    #     .stDataFrame *,
    #     div[data-testid="stDataFrame"] *,
    #     .dataframe * {
    #         color: #ffffff !important;
    #     }
    #
    #     /* Специфичные селекторы для текста в ячейках - переопределяем все возможные стили Streamlit */
    #     .stDataFrame td,
    #     .stDataFrame th,
    #     div[data-testid="stDataFrame"] td,
    #     div[data-testid="stDataFrame"] th {
    #         color: #ffffff !important;
    #     }
    #
    #     /* Вложенные элементы в ячейках - белый текст */
    #     .stDataFrame td *,
    #     .stDataFrame th *,
    #     div[data-testid="stDataFrame"] td *,
    #     div[data-testid="stDataFrame"] th *,
    #     .stDataFrame td span,
    #     .stDataFrame th span,
    #     div[data-testid="stDataFrame"] td span,
    #     div[data-testid="stDataFrame"] th span,
    #     .stDataFrame td div,
    #     .stDataFrame th div,
    #     div[data-testid="stDataFrame"] td div,
    #     div[data-testid="stDataFrame"] th div,
    #     .stDataFrame td p,
    #     .stDataFrame th p,
    #     div[data-testid="stDataFrame"] td p,
    #     div[data-testid="stDataFrame"] th p,
    #     .stDataFrame td strong,
    #     .stDataFrame th strong,
    #     div[data-testid="stDataFrame"] td strong,
    #     div[data-testid="stDataFrame"] th strong {
    #         color: #ffffff !important;
    #     }
    #     </style>
    #     """,
    #     unsafe_allow_html=True,
    # )








    # # Проверка авторизации
    # require_auth()
    #
    # user = get_current_user()
    #
    # # Проверка, что пользователь получен
    # if not user:
    #     st.error("⚠️ Ошибка получения данных пользователя")
    #     st.stop()
    #
    # # Проверка прав доступа - менеджеры не имеют доступа к параметрам отчетов
    # if user['role'] == 'manager':
    #     st.error("⚠️ У вас нет доступа к этой странице")
    #     st.info("Доступ к параметрам отчетов имеют только аналитики и администраторы.")
    #     if st.button("Вернуться к отчетам"):
    #         st.switch_page("project_visualization_app.py")
    #     st.stop()
    #
    # # Боковая панель с меню навигации
    # render_sidebar_menu(current_page="analyst_params")
    #
    # # Заголовок
    # st.title("⚙️ Параметры отчетов")
    #
    # st.markdown("---")
    #
    # # Информация о текущем пользователе
    # col1, col2, col3 = st.columns(3)
    #
    # with col1:
    #
    #     st.metric("Пользователь", user['username'])
    #
    # with col2:
    #
    #     st.metric("Роль", get_user_role_display(user['role']))
    #
    # with col3:
    #
    #     if st.button("🚪 Выйти"):
    #
    #         from auth import logout
    #
    #         log_action(user['username'], 'logout', 'Выход из системы')
    #
    #         logout()
    #
    #         st.success("Вы вышли из системы")
    #
    #         st.rerun()
    #
    # st.markdown("---")
    #
    # st.info("""
    # Здесь вы можете настроить фильтры по умолчанию для всех ролей и отчетов.
    # Фильтры определяют значения по умолчанию для различных параметров отчетов.
    # """)
    #
    # st.markdown("---")
    #
    # # Выбор режима работы
    # mode = st.radio(
    #     "Режим работы",
    #     ["Настроить фильтры для роли и отчета", "Просмотр всех фильтров", "Копирование фильтров между ролями"],
    #     horizontal=True
    # )
    #
    # st.markdown("---")
    #
    # if mode == "Настроить фильтры для роли и отчета":
    #     st.markdown("### Настройка фильтров")
    #
    #     with st.form("filter_form"):
    #         col1, col2 = st.columns(2)
    #
    #         with col1:
    #             selected_role = st.selectbox(
    #                 "Роль *",
    #                 options=list(ROLES.keys()),
    #                 format_func=lambda x: ROLES[x]
    #             )
    #
    #             selected_report = st.selectbox(
    #                 "Отчет *",
    #                 options=AVAILABLE_REPORTS
    #             )
    #
    #         with col2:
    #             filter_key = st.text_input("Ключ фильтра *", help="Например: selected_project, date_range, etc.")
    #             filter_type = st.selectbox(
    #                 "Тип фильтра *",
    #                 options=list(FILTER_TYPES.keys()),
    #                 format_func=lambda x: FILTER_TYPES[x]
    #             )
    #
    #         filter_value = st.text_input(
    #             "Значение фильтра",
    #             help="Введите значение фильтра. Для select/multiselect используйте JSON формат: [\"значение1\", \"значение2\"]"
    #         )
    #
    #         submitted = st.form_submit_button("Сохранить фильтр", type="primary")
    #
    #         if submitted:
    #             if filter_key and selected_role and selected_report:
    #                 if set_default_filter(
    #                     selected_role, selected_report, filter_key, filter_value,
    #                     filter_type, user['username']
    #                 ):
    #                     log_action(
    #                         user['username'],
    #                         'set_default_filter',
    #                         f'Установлен фильтр {filter_key} для роли {get_user_role_display(selected_role)} в отчете {selected_report}'
    #                     )
    #                     st.success("✅ Фильтр успешно сохранен!")
    #                     st.rerun()
    #                 else:
    #                     st.error("❌ Ошибка при сохранении фильтра")
    #             else:
    #                 st.warning("Заполните обязательные поля (отмечены *)")
    #
    #     st.markdown("---")
    #
    #     # Текущие фильтры для выбранной роли и отчета
    #     st.markdown("### Текущие фильтры")
    #
    #     col1, col2 = st.columns(2)
    #     with col1:
    #         view_role = st.selectbox(
    #             "Роль для просмотра",
    #             options=['Все'] + list(ROLES.keys()),
    #             format_func=lambda x: ROLES.get(x, x) if x != 'Все' else x,
    #             key='view_filter_role'
    #         )
    #     with col2:
    #         view_report = st.selectbox(
    #             "Отчет для просмотра",
    #             options=['Все'] + AVAILABLE_REPORTS,
    #             key='view_filter_report'
    #         )
    #
    #     filters = get_all_default_filters(
    #         role=None if view_role == 'Все' else view_role,
    #         report_name=None if view_report == 'Все' else view_report
    #     )
    #
    #     if filters:
    #         filters_data = []
    #         for f in filters:
    #             filters_data.append({
    #                 'Роль': get_user_role_display(f['role']),
    #                 'Отчет': f['report_name'],
    #                 'Ключ': f['filter_key'],
    #                 'Значение': f['filter_value'] or '-',
    #                 'Тип': FILTER_TYPES.get(f['filter_type'], f['filter_type']),
    #                 'Обновлено': f['updated_at'] or '-',
    #                 'Обновил': f['updated_by'] or '-'
    #             })
    #
    #         df_filters = pd.DataFrame(filters_data)
    #         st.dataframe(df_filters, use_container_width=True, hide_index=True)
    #
    #         # Удаление фильтров
    #         st.markdown("#### Удаление фильтра")
    #         with st.form("delete_filter_form"):
    #             del_col1, del_col2, del_col3 = st.columns(3)
    #             with del_col1:
    #                 del_role = st.selectbox(
    #                     "Роль",
    #                     options=list(ROLES.keys()),
    #                     format_func=lambda x: ROLES[x],
    #                     key='del_filter_role'
    #                 )
    #             with del_col2:
    #                 del_report = st.selectbox(
    #                     "Отчет",
    #                     options=AVAILABLE_REPORTS,
    #                     key='del_filter_report'
    #                 )
    #             with del_col3:
    #                 # Получаем фильтры для выбранной роли и отчета
    #                 role_filters = get_default_filters(del_role, del_report)
    #                 del_filter_key = st.selectbox(
    #                     "Ключ фильтра",
    #                     options=list(role_filters.keys()) if role_filters else [],
    #                     key='del_filter_key'
    #                 )
    #
    #             if st.form_submit_button("Удалить фильтр", type="primary"):
    #                 if del_filter_key:
    #                     if delete_default_filter(del_role, del_report, del_filter_key):
    #                         log_action(
    #                             user['username'],
    #                             'delete_default_filter',
    #                             f'Удален фильтр {del_filter_key} для роли {get_user_role_display(del_role)} в отчете {del_report}'
    #                         )
    #                         st.success("✅ Фильтр успешно удален!")
    #                         st.rerun()
    #                     else:
    #                         st.error("❌ Ошибка при удалении фильтра")
    #     else:
    #         st.info("Фильтры не найдены")
    #
    # elif mode == "Просмотр всех фильтров":
    #     st.markdown("### Все фильтры по умолчанию")
    #
    #     all_filters = get_all_default_filters()
    #
    #     if all_filters:
    #         # Группировка по ролям и отчетам
    #         filters_by_role_report = {}
    #         for f in all_filters:
    #             key = (f['role'], f['report_name'])
    #             if key not in filters_by_role_report:
    #                 filters_by_role_report[key] = []
    #             filters_by_role_report[key].append(f)
    #
    #         for (role, report), filters_list in sorted(filters_by_role_report.items()):
    #             with st.expander(f"📋 {get_user_role_display(role)} - {report} ({len(filters_list)} фильтров)"):
    #                 filters_data = []
    #                 for f in filters_list:
    #                     filters_data.append({
    #                         'Ключ': f['filter_key'],
    #                         'Значение': f['filter_value'] or '-',
    #                         'Тип': FILTER_TYPES.get(f['filter_type'], f['filter_type']),
    #                         'Обновлено': f['updated_at'] or '-',
    #                         'Обновил': f['updated_by'] or '-'
    #                     })
    #                 df = pd.DataFrame(filters_data)
    #                 st.dataframe(df, use_container_width=True, hide_index=True)
    #     else:
    #         st.info("Фильтры не настроены")
    #
    # elif mode == "Копирование фильтров между ролями":
    #     st.markdown("### Копирование фильтров")
    #
    #     st.info("Скопируйте все фильтры из одной роли в другую. Можно скопировать для конкретного отчета или для всех отчетов.")
    #
    #     with st.form("copy_filters_form"):
    #         col1, col2 = st.columns(2)
    #
    #         with col1:
    #             source_role = st.selectbox(
    #                 "Исходная роль",
    #                 options=list(ROLES.keys()),
    #                 format_func=lambda x: ROLES[x],
    #                 key='copy_source_role'
    #             )
    #
    #         with col2:
    #             target_role = st.selectbox(
    #                 "Целевая роль",
    #                 options=list(ROLES.keys()),
    #                 format_func=lambda x: ROLES[x],
    #                 key='copy_target_role'
    #             )
    #
    #         copy_report = st.selectbox(
    #             "Отчет (оставьте 'Все' для копирования всех отчетов)",
    #             options=['Все'] + AVAILABLE_REPORTS,
    #             key='copy_report'
    #         )
    #
    #         if st.form_submit_button("Копировать фильтры", type="primary"):
    #             if source_role == target_role:
    #                 st.warning("⚠️ Исходная и целевая роли не могут быть одинаковыми")
    #             else:
    #                 report_name = None if copy_report == 'Все' else copy_report
    #                 if copy_filters_to_role(source_role, target_role, report_name):
    #                     log_action(
    #                         user['username'],
    #                         'copy_filters',
    #                         f'Скопированы фильтры из роли {get_user_role_display(source_role)} в роль {get_user_role_display(target_role)}' +
    #                         (f' для отчета {copy_report}' if report_name else ' для всех отчетов')
    #                     )
    #                     st.success(f"✅ Фильтры успешно скопированы!")
    #                     st.rerun()
    #                 else:
    #                     st.error("❌ Ошибка при копировании фильтров")
    #
    # st.markdown("---")
    #
    # # Кнопка возврата
    # if st.button("← Вернуться к отчетам"):
    #     st.switch_page("project_visualization_app.py")

    # Проверка авторизации
    require_auth()

    user = get_current_user()

    # Проверка, что пользователь получен
    if not user:

        st.error("⚠️ Ошибка получения данных пользователя")

        st.stop()

    # Проверка прав доступа - менеджеры не имеют доступа к параметрам отчетов
    if user['role'] == 'manager':

        st.error("⚠️ У вас нет доступа к этой странице")

        st.info("Доступ к параметрам отчетов имеют только аналитики и администраторы.")

        if st.button("Вернуться к отчетам"):

            st.switch_page("project_visualization_app.py")

        st.stop()

    # Боковая панель с меню навигации
    render_sidebar_menu(current_page="analyst_params")

    # Заголовок
    st.title("⚙️ Параметры отчетов")

    st.markdown("---")

    # Информация о текущем пользователе
    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric("Пользователь", user['username'])

    with col2:

        st.metric("Роль", get_user_role_display(user['role']))

    with col3:

        # if st.button("🚪 Выйти"):
        if st.button("Выйти"):

            from auth import logout

            log_action(user['username'], 'logout', 'Выход из системы')

            logout()

            st.success("Вы вышли из системы")

            st.rerun()

    st.markdown("---")

    st.info("""
    Здесь вы можете настроить фильтры по умолчанию для всех ролей и отчетов.
    Фильтры определяют значения по умолчанию для различных параметров отчетов.
    """)

    st.markdown("---")

    # Вкладки вместо radio
    tab_setup, tab_view_all, tab_copy = st.tabs([
        "Настроить фильтры",
        "Просмотр всех фильтров",
        "Копирование фильтров"
    ])

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ TAB 1: Настроить фильтры ¤ Start                                   │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    with tab_setup:

        st.subheader("Настройка фильтров")

        with st.form("filter_form"):

            col1, col2 = st.columns(2)

            with col1:

                selected_role = st.selectbox(
                    "Роль *",
                    options=list(ROLES.keys()),
                    format_func=lambda x: ROLES[x],
                    key="setup_role"
                )
                selected_report = st.selectbox(
                    "Отчет *",
                    options=AVAILABLE_REPORTS,
                    key="setup_report"
                )

            with col2:

                filter_key = st.text_input(
                    "Ключ фильтра *",
                    help="Например: selected_project, date_range, etc.",
                    key="setup_key"
                )
                filter_type = st.selectbox(
                    "Тип фильтра *",
                    options=list(FILTER_TYPES.keys()),
                    format_func=lambda x: FILTER_TYPES[x],
                    key="setup_type"
                )

            filter_value = st.text_input(
                "Значение фильтра",
                help="Для select/multiselect — JSON: [\"значение1\", \"значение2\"]",
                key="setup_value"
            )

            submitted = st.form_submit_button("Сохранить фильтр", type="primary")

            if submitted:

                if filter_key and selected_role and selected_report:

                    if set_default_filter(
                        selected_role, selected_report, filter_key, filter_value,
                        filter_type, user['username']
                    ):
                        log_action(
                            user['username'],
                            'set_default_filter',
                            f'Установлен фильтр {filter_key} для роли {get_user_role_display(selected_role)} в отчете {selected_report}'
                        )

                        st.success("✅ Фильтр успешно сохранен!")

                        st.rerun()

                    else:

                        st.error("❌ Ошибка при сохранении фильтра")
                else:

                    st.warning("Заполните обязательные поля (отмечены *)")

        st.markdown("---")

        # Текущие фильтры
        st.subheader("Текущие фильтры")

        col1, col2 = st.columns(2)

        with col1:

            view_role = st.selectbox(
                "Роль для просмотра",
                options = ['Все'] + list(ROLES.keys()),
                format_func = lambda x: ROLES.get(x, x) if x != 'Все' else x,
                key = 'view_role_setup'
            )

        with col2:

            view_report = st.selectbox(
                "Отчет для просмотра",
                options = ['Все'] + AVAILABLE_REPORTS,
                key = 'view_report_setup'
            )

        filters = get_all_default_filters(
            role = None if view_role == 'Все' else view_role,
            report_name = None if view_report == 'Все' else view_report
        )

        if filters:

            filters_data = []

            for f in filters:

                filters_data.append({
                    'Роль': get_user_role_display(f['role']),
                    'Отчет': f['report_name'],
                    'Ключ': f['filter_key'],
                    'Значение': f['filter_value'] or '-',
                    'Тип': FILTER_TYPES.get(f['filter_type'], f['filter_type']),
                    'Обновлено': f['updated_at'] or '-',
                    'Обновил': f['updated_by'] or '-'
                })

            df_filters = pd.DataFrame(filters_data)

            st.dataframe(df_filters, use_container_width=True, hide_index=True)

            # Удаление фильтров
            st.markdown("#### Удаление фильтра")

            with st.form("delete_filter_form"):

                del_col1, del_col2, del_col3 = st.columns(3)

                with del_col1:

                    del_role = st.selectbox(
                        "Роль",
                        options=list(ROLES.keys()),
                        format_func=lambda x: ROLES[x],
                        key='del_role_setup'
                    )

                with del_col2:

                    del_report = st.selectbox(
                        "Отчет",
                        options=AVAILABLE_REPORTS,
                        key='del_report_setup'
                    )

                with del_col3:

                    role_filters = get_default_filters(del_role, del_report)

                    del_filter_key = st.selectbox(
                        "Ключ фильтра",
                        options=list(role_filters.keys()) if role_filters else [],
                        key='del_key_setup'
                    )

                if st.form_submit_button("Удалить фильтр", type="primary"):

                    if del_filter_key:

                        if delete_default_filter(del_role, del_report, del_filter_key):

                            log_action(
                                user['username'],
                                'delete_default_filter',
                                f'Удален фильтр {del_filter_key} для роли {get_user_role_display(del_role)} в отчете {del_report}'
                            )

                            st.success("✅ Фильтр успешно удален!")

                            st.rerun()

                        else:

                            st.error("❌ Ошибка при удалении фильтра")
        else:

            st.info("Фильтры не найдены")

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ TAB 1: Настроить фильтры ¤ End                                     │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ TAB 2: Просмотр всех фильтров ¤ Start                              │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    with tab_view_all:

        st.subheader("Все фильтры по умолчанию")

        all_filters = get_all_default_filters()

        if all_filters:

            filters_by_role_report = {}

            for f in all_filters:

                key = (f['role'], f['report_name'])

                filters_by_role_report.setdefault(key, []).append(f)

            for (role, report), filters_list in sorted(filters_by_role_report.items()):

                with st.expander(f"📋 {get_user_role_display(role)} - {report} ({len(filters_list)} фильтров)"):

                    filters_data = []

                    for f in filters_list:

                        filters_data.append({
                            'Ключ': f['filter_key'],
                            'Значение': f['filter_value'] or '-',
                            'Тип': FILTER_TYPES.get(f['filter_type'], f['filter_type']),
                            'Обновлено': f['updated_at'] or '-',
                            'Обновил': f['updated_by'] or '-'
                        })

                    df = pd.DataFrame(filters_data)

                    st.dataframe(df, use_container_width=True, hide_index=True)
        else:

            st.info("Фильтры не настроены")

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ TAB 2: Просмотр всех фильтров ¤ End                                │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ TAB 3: Копирование фильтров ¤ Start                                │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    with tab_copy:

        st.subheader("Копирование фильтров")

        st.info("Скопируйте все фильтры из одной роли в другую. Можно для конкретного отчета или всех.")

        with st.form("copy_filters_form"):

            col1, col2 = st.columns(2)

            with col1:

                source_role = st.selectbox(
                    "Исходная роль",
                    options=list(ROLES.keys()),
                    format_func=lambda x: ROLES[x],
                    key="copy_source_role"
                )

            with col2:

                target_role = st.selectbox(
                    "Целевая роль",
                    options=list(ROLES.keys()),
                    format_func=lambda x: ROLES[x],
                    key="copy_target_role"
                )

            copy_report = st.selectbox(
                "Отчет (оставьте 'Все' для копирования всех)",
                options=['Все'] + AVAILABLE_REPORTS,
                key="copy_report"
            )

            if st.form_submit_button("Копировать фильтры", type="primary"):

                if source_role == target_role:

                    st.warning("⚠️ Исходная и целевая роли не могут быть одинаковыми")

                else:

                    report_name = None if copy_report == 'Все' else copy_report

                    if copy_filters_to_role(source_role, target_role, report_name):

                        log_action(
                            user['username'],
                            'copy_filters',
                            f'Скопированы фильтры из роли {get_user_role_display(source_role)} в роль {get_user_role_display(target_role)}' +
                            (f' для отчета {copy_report}' if report_name else ' для всех отчетов')
                        )

                        st.success("✅ Фильтры успешно скопированы!")

                        st.rerun()

                    else:

                        st.error("❌ Ошибка при копировании фильтров")

    # ┌──────────────────────────────────────────────────────────────────────┐ #
    # │ ⊗ TAB 3: Копирование фильтров ¤ End                                  │ #
    # └──────────────────────────────────────────────────────────────────────┘ #

    st.markdown("---")

    if st.button("← Вернуться к отчетам"):

        st.switch_page("project_visualization_app.py")
