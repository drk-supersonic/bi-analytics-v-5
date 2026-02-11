import sys
from pathlib import Path

# Ensure app directory is first on path (for deployment when CWD may not be bi-analytics)
_app_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_app_dir))

import streamlit as st
from auth import (
    check_authentication,
    get_current_user,
    has_admin_access,
    has_report_access,
    get_user_role_display,
    logout,
    init_db,
    render_sidebar_menu,
    authenticate,
    generate_reset_token,
    reset_password,
    verify_reset_token,
    get_user_by_username,
)
from data_loader import (
    load_data,
    ensure_data_session_state,
    update_session_with_loaded_file,
    clear_all_data_for_removed_files,
)

# ┌──────────────────────────────────────────────────────────────────────────┐ #
# │ ⊗ CSS CONNECT ¤ Start                                                    │ #
# └──────────────────────────────────────────────────────────────────────────┘ #

def load_custom_css():
    css_path = Path(__file__).parent / "static" / "css" / "style.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS файл не найден: " + str(css_path))

# ┌──────────────────────────────────────────────────────────────────────────┐ #
# │ ⊗ CSS CONNECT ¤ End                                                      │ #
# └──────────────────────────────────────────────────────────────────────────┘ #

# Инициализация базы данных (все таблицы создаются в db.init_all_tables)
init_db()

# Page configuration (должно быть первым)
st.set_page_config(
    page_title="Панель аналитики проектов",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# Файлы с префиксом _ уже скрыты из меню автоматически Streamlit
# Дополнительная попытка скрыть через st.navigation (может быть недоступно в версии 1.52.1)
# Удаляем этот вызов, так как он может вызывать ошибки

# ┌──────────────────────────────────────────────────────────────────────────┐ #
# │ ⊗ CSS CONNECT ¤ Start                                                    │ #
# └──────────────────────────────────────────────────────────────────────────┘ #

load_custom_css()

# ┌──────────────────────────────────────────────────────────────────────────┐ #
# │ ⊗ CSS CONNECT ¤ End                                                      │ #
# └──────────────────────────────────────────────────────────────────────────┘ #

# Custom CSS for better styling (dark theme)
# st.markdown(
#     """
#     <style>
#     .main-header {
#         font-size: 2.5rem;
#         font-weight: bold;
#         color: #1f77b4;
#         margin-bottom: 1rem;
#     }
#     .metric-card {
#         background-color: #262730;
#         padding: 1rem;
#         border-radius: 0.5rem;
#         margin: 0.5rem 0;
#     }
#     /* Фон основной области — как у меню (sidebar) */
#     .stApp {
#         background-color: #12385C !important;
#     }
#     /* Контейнер контента — тот же тон */
#     .main .block-container,
#     .main .element-container,
#     .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
#     .main p, .main span, .main label {
#         color: #ffffff !important;
#     }
#     .main .block-container {
#         background-color: rgba(18, 56, 92, 0.8) !important;
#     }
#     /* Хедер — такой же цвет, как фон */
#     header[data-testid="stHeader"],
#     [data-testid="stHeader"],
#     .stHeader,
#     div[data-testid="stHeader"],
#     .stHeader > div,
#     header > div,
#     div[data-testid="stHeader"] > div {
#         background-color: #12385C !important;
#         border-bottom: none !important;
#     }
#     header[data-testid="stHeader"] *,
#     [data-testid="stHeader"] *,
#     .stHeader * {
#         color: #ffffff !important;
#     }
#
#     /* Стилизация полей ввода - подсветка для видимости на темном фоне */
#     .stTextInput > div > div > input,
#     .stTextInput > div > div > input:focus,
#     input[type="text"],
#     input[type="password"],
#     input[type="email"],
#     input[type="number"],
#     textarea {
#         background-color: #2a2a3a !important;
#         color: #ffffff !important;
#         border: 1px solid #4a5568 !important;
#         border-radius: 4px !important;
#         padding: 0.5rem !important;
#     }
#     .stTextInput > div > div > input:focus,
#     input[type="text"]:focus,
#     input[type="password"]:focus,
#     input[type="email"]:focus,
#     input[type="number"]:focus,
#     textarea:focus {
#         border-color: #1f77b4 !important;
#         box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
#         outline: none !important;
#     }
#
#     /* Стилизация кнопок - темные с окантовкой, белый текст */
#     .stButton > button {
#         background-color: #2a2a3a !important;
#         color: #ffffff !important;
#         border: 1px solid #4a5568 !important;
#         border-radius: 4px !important;
#         padding: 0.5rem 1rem !important;
#         font-weight: 500 !important;
#         transition: all 0.2s ease !important;
#     }
#     .stButton > button:hover {
#         background-color: #3a3a4a !important;
#         border-color: #5a5a6a !important;
#         color: #ffffff !important;
#     }
#     .stButton > button:focus {
#         border-color: #1f77b4 !important;
#         box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
#         outline: none !important;
#     }
#     /* Кнопки primary - темные с более яркой окантовкой */
#     .stButton > button[kind="primary"] {
#         background-color: #1a1a2a !important;
#         color: #ffffff !important;
#         border: 1px solid #1f77b4 !important;
#     }
#     .stButton > button[kind="primary"]:hover {
#         background-color: #2a2a3a !important;
#         border-color: #2a8bc4 !important;
#         color: #ffffff !important;
#     }
#     /* Отключенные кнопки */
#     .stButton > button:disabled {
#         background-color: #1a1a2a !important;
#         color: #666666 !important;
#         border-color: #333333 !important;
#         opacity: 0.6 !important;
#     }
#     /* Стилизация selectbox */
#     .stSelectbox > div > div > select {
#         background-color: #2a2a3a !important;
#         color: #ffffff !important;
#         border: 1px solid #4a5568 !important;
#         border-radius: 4px !important;
#     }
#     .stSelectbox > div > div > select:focus {
#         border-color: #1f77b4 !important;
#         box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
#         outline: none !important;
#     }
#     /* Стилизация checkbox */
#     .stCheckbox > label {
#         color: #ffffff !important;
#     }
#     /* Стилизация date input */
#     .stDateInput > div > div > input {
#         background-color: #2a2a3a !important;
#         color: #ffffff !important;
#         border: 1px solid #4a5568 !important;
#     }
#     /* Стилизация number input */
#     .stNumberInput > div > div > input {
#         background-color: #2a2a3a !important;
#         color: #ffffff !important;
#         border: 1px solid #4a5568 !important;
#         border-radius: 4px !important;
#     }
#     .stNumberInput > div > div > input:focus {
#         border-color: #1f77b4 !important;
#         box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
#         outline: none !important;
#     }
#     /* Стилизация multiselect */
#     .stMultiSelect > div > div {
#         background-color: #2a2a3a !important;
#         color: #ffffff !important;
#         border: 1px solid #4a5568 !important;
#     }
#     /* Стилизация file uploader */
#     .stFileUploader > div {
#         background-color: #2a2a3a !important;
#         border: 1px solid #4a5568 !important;
#         border-radius: 4px !important;
#     }
#     /* Таблицы — фон синий #12385C, шрифт белый (переопределяем стандартный чёрный Streamlit) */
#     .main table,
#     .main table th,
#     .main table td,
#     .main table thead th,
#     .main table tbody th,
#     .main table tbody td,
#     table,
#     table th,
#     table td,
#     table thead th,
#     table tbody th,
#     table tbody td {
#         background-color: #12385C !important;
#         color: #ffffff !important;
#         border-color: rgba(255, 255, 255, 0.25) !important;
#         font-size: 14px !important;
#     }
#     .main table *,
#     table th *,
#     table td * {
#         color: #ffffff !important;
#     }
#     /* st.dataframe и st.table — контейнер и все ячейки */
#     [data-testid="stDataFrame"],
#     [data-testid="stDataFrame"] *,
#     .stDataFrame,
#     .stDataFrame *,
#     div[data-testid="stDataFrame"] [role="cell"],
#     div[data-testid="stDataFrame"] [role="columnheader"],
#     [data-testid="stDataFrame"] td,
#     [data-testid="stDataFrame"] th,
#     [data-testid="stDataFrame"] .cell,
#     [data-testid="stDataFrame"] [class*="cell"] {
#         background-color: #12385C !important;
#         color: #ffffff !important;
#         font-size: 14px !important;
#     }
#     [data-testid="stDataFrame"] span,
#     [data-testid="stDataFrame"] div,
#     .stDataFrame span,
#     .stDataFrame div {
#         color: #ffffff !important;
#     }
#     /* Таблица редактирования (st.data_editor) — видимый текст */
#     [data-testid="stDataFrame"] input,
#     [data-testid="stDataFrame"] [contenteditable="true"],
#     .stDataFrame input,
#     .stDataFrame [contenteditable="true"] {
#         color: #ffffff !important;
#         background-color: #1e3a5f !important;
#         border: 1px solid rgba(255,255,255,0.3) !important;
#     }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )




# ==================== MAIN APP ====================
def main():
    # Проверка авторизации - если не авторизован, показываем форму входа
    if not check_authentication():
        # Скрываем боковую панель на странице входа и настраиваем ширину формы
        st.markdown(
            """
            <style>
            .stSidebar {
                display: none !important;
            }
            [data-testid="stSidebar"] {
                display: none !important;
            }

            /* Контейнер для формы авторизации - 75% ширины экрана */
            /* Используем более специфичные селекторы для переопределения Streamlit */
            section[data-testid="stAppViewContainer"] .main .block-container,
            section[data-testid="stAppViewContainer"] .main > div,
            .main .block-container,
            .main > div,
            div[data-testid="stAppViewContainer"] .main .block-container,
            div[data-testid="stAppViewContainer"] .main > div,
            [data-testid="stAppViewContainer"] .main .block-container,
            [data-testid="stAppViewContainer"] .main > div {
                max-width: 75% !important;
                width: 75% !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 3rem !important;
                padding-bottom: 3rem !important;
            }

            /* Убеждаемся, что основной контейнер занимает всю ширину для центрирования */
            .main,
            section[data-testid="stAppViewContainer"] .main,
            div[data-testid="stAppViewContainer"] .main,
            [data-testid="stAppViewContainer"] .main {
                width: 100% !important;
                max-width: 100% !important;
            }

            /* Переопределяем стандартные ограничения Streamlit */
            section[data-testid="stAppViewContainer"] > div,
            div[data-testid="stAppViewContainer"] > div,
            [data-testid="stAppViewContainer"] > div {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Переопределяем для layout="wide" */
            .stApp[data-layout="wide"] .main .block-container,
            .stApp[data-layout="wide"] .main > div,
            [data-layout="wide"] .main .block-container,
            [data-layout="wide"] .main > div {
                max-width: 75% !important;
                width: 75% !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            /* Дополнительно переопределяем все возможные inline стили */
            .element-container {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Центрируем форму входа */
            .stForm {
                max-width: 100% !important;
                width: 100% !important;
                margin: 0 auto !important;
            }
            form[data-testid="stForm"] {
                max-width: 100% !important;
                width: 100% !important;
                margin: 0 auto !important;
            }

            /* Убеждаемся, что все элементы формы используют доступную ширину */
            .stForm > div {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Переопределяем внутренние контейнеры Streamlit */
            [data-testid="stForm"] {
                max-width: 100% !important;
                width: 100% !important;
            }

            [data-testid="stForm"] > div {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Expander также 50% ширины */
            .stExpander {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Центрируем колонки формы */
            [data-testid="column"] {
                max-width: 100% !important;
            }

            /* Центрируем заголовок и другой контент */
            h1, h2, h3, p {
                text-align: center !important;
            }

            /* Центрируем markdown блоки */
            .element-container {
                max-width: 100% !important;
            }

            /* Стилизация кнопок - одинаковая ширина и высота */
            .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки */
            .stButton > button > div,
            .stButton > button > span,
            .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Убеждаемся, что кнопки в колонках имеют одинаковую ширину и высоту */
            [data-testid="column"] .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки в колонках */
            [data-testid="column"] .stButton > button > div,
            [data-testid="column"] .stButton > button > span,
            [data-testid="column"] .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Кнопки в формах также должны иметь одинаковую высоту и ширину */
            form .stButton > button {
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                width: 100% !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки в формах */
            form .stButton > button > div,
            form .stButton > button > span,
            form .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Дополнительно для кнопок в колонках формы входа */
            form [data-testid="column"] .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки в колонках формы входа */
            form [data-testid="column"] .stButton > button > div,
            form [data-testid="column"] .stButton > button > span,
            form [data-testid="column"] .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            </style>
            <script>
            // Принудительно применяем ширину контейнера после загрузки
            function setContainerWidth() {
                const containers = document.querySelectorAll('.main .block-container, .main > div');
                containers.forEach(container => {
                    container.style.setProperty('max-width', '75%', 'important');
                    container.style.setProperty('width', '75%', 'important');
                    container.style.setProperty('margin-left', 'auto', 'important');
                    container.style.setProperty('margin-right', 'auto', 'important');
                });
            }
            // Применяем сразу и после загрузки DOM
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', setContainerWidth);
            } else {
                setContainerWidth();
            }
            // Также применяем после небольшой задержки для Streamlit
            setTimeout(setContainerWidth, 100);
            setTimeout(setContainerWidth, 500);
            setTimeout(setContainerWidth, 1000);
            // Наблюдаем за изменениями DOM (Streamlit динамически обновляет страницу)
            const observer = new MutationObserver(setContainerWidth);
            observer.observe(document.body, { childList: true, subtree: true });
            </script>
        """,
            unsafe_allow_html=True,
        )

        # Заголовок страницы входа
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="color: #ffffff; font-size: 3rem; margin-bottom: 0.5rem;">🔐</h1>
                <h1 style="color: #ffffff; font-size: 2rem; margin-bottom: 0.5rem;">BI Analytics</h1>
                <p style="color: #a0a0a0; font-size: 1.1rem;">Войдите в систему для доступа к панели аналитики</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # Инициализация переменных для восстановления пароля
        if "reset_mode" not in st.session_state:
            st.session_state.reset_mode = False
        if "reset_token" not in st.session_state:
            st.session_state.reset_token = None

        # Режим восстановления пароля по токену
        if st.session_state.reset_mode and st.session_state.reset_token:
            st.subheader("Восстановление пароля")

            token = st.session_state.reset_token
            username = verify_reset_token(token)

            if not username:
                st.error("⚠️ Токен восстановления недействителен или истек")
                st.session_state.reset_mode = False
                st.session_state.reset_token = None
                if st.button("Вернуться к входу"):
                    st.rerun()
                st.stop()

            st.info(f"Восстановление пароля для пользователя: **{username}**")

            new_password = st.text_input(
                "Новый пароль", type="password", key="new_password"
            )
            confirm_password = st.text_input(
                "Подтвердите пароль", type="password", key="confirm_password"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Сбросить пароль", type="primary"):
                    if not new_password or len(new_password) < 6:
                        st.error("Пароль должен содержать минимум 6 символов")
                    elif new_password != confirm_password:
                        st.error("Пароли не совпадают")
                    else:
                        if reset_password(token, new_password):
                            st.success("✅ Пароль успешно изменен!")
                            st.info("Теперь вы можете войти с новым паролем")
                            st.session_state.reset_mode = False
                            st.session_state.reset_token = None
                            if st.button("Перейти к входу"):
                                st.rerun()
                        else:
                            st.error("Ошибка при сбросе пароля")

            with col2:
                if st.button("Отмена"):
                    st.session_state.reset_mode = False
                    st.session_state.reset_token = None
                    st.rerun()
            st.stop()

        # Режим запроса восстановления пароля
        elif st.session_state.reset_mode:
            st.subheader("Восстановление пароля")

            tab1, tab2 = st.tabs(["По имени пользователя", "По токену"])

            with tab1:
                username = st.text_input(
                    "Введите имя пользователя", key="reset_username"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Создать токен восстановления", type="primary"):
                        if username:
                            user = get_user_by_username(username)
                            if user:
                                token = generate_reset_token(username)
                                if token:
                                    st.success("✅ Токен восстановления создан!")
                                    st.info(f"**Токен восстановления:** `{token}`")
                                    st.warning(
                                        "⚠️ В реальном приложении токен будет отправлен на email пользователя"
                                    )
                                    st.info(
                                        "Для демонстрации скопируйте токен и используйте вкладку 'По токену'"
                                    )

                                    st.session_state.reset_token = token
                                    st.rerun()
                                else:
                                    st.error("Ошибка при создании токена")
                            else:
                                st.error("Пользователь не найден")
                        else:
                            st.warning("Введите имя пользователя")

                with col2:
                    if st.button("Отмена"):
                        st.session_state.reset_mode = False
                        st.rerun()

            with tab2:
                token_input = st.text_input(
                    "Введите токен восстановления", key="token_input"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Использовать токен", type="primary"):
                        if token_input:
                            username = verify_reset_token(token_input)
                            if username:
                                st.session_state.reset_token = token_input
                                st.rerun()
                            else:
                                st.error("⚠️ Токен недействителен или истек")
                        else:
                            st.warning("Введите токен")

                with col2:
                    if st.button("Отмена", key="cancel_token"):
                        st.session_state.reset_mode = False
                        st.rerun()

            st.markdown("---")
            if st.button("← Вернуться к входу"):
                st.session_state.reset_mode = False
                st.rerun()
            st.stop()

        # Режим входа
        else:
            # Форма входа в центрированном контейнере (50% ширины экрана)
            # Используем пустые колонки для центрирования
            col_left, col_center, col_right = st.columns([1, 1, 1])
            with col_center:
                with st.form("login_form", clear_on_submit=False):
                    st.markdown("### Вход в систему")
                    st.markdown("---")

                    username = st.text_input(
                        "👤 Имя пользователя",
                        key="login_username",
                        placeholder="Введите имя пользователя",
                        autocomplete="username",
                    )

                    password = st.text_input(
                        "🔒 Пароль",
                        type="password",
                        key="login_password",
                        placeholder="Введите пароль",
                        autocomplete="current-password",
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        submit_button = st.form_submit_button(
                            "🚀 Войти", type="primary", use_container_width=True
                        )

                    with col2:
                        if st.form_submit_button(
                            "❓ Забыли пароль?", use_container_width=True
                        ):
                            st.session_state.reset_mode = True
                            st.rerun()

                    if submit_button:
                        if username and password:
                            success, user = authenticate(username, password)
                            if success and user:
                                st.session_state.authenticated = True
                                st.session_state.user = user
                                st.success(f"✅ Добро пожаловать, {user['username']}!")
                                st.balloons()
                                import time

                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Неверное имя пользователя или пароль")
                        else:
                            st.warning("⚠️ Заполните все поля")

                st.markdown("---")

                # Информация о доступе (учётные данные задаются при развёртывании)
                # with st.expander("ℹ️ Учётные данные", expanded=False):
                #     st.markdown(
                #         """
                #     Логин и пароль задаются при развёртывании (переменные окружения `DEFAULT_ADMIN_USERNAME` и `DEFAULT_ADMIN_PASSWORD`).
                #     См. файл `.env.example` и документацию в README.
                #     """
                #     )

                # # Информация о демо-доступе
                # with st.expander("ℹ️ Демо-доступ", expanded=False):
                #     st.markdown(
                #         """
                #     **Тестовые учетные данные:**
                #     - **Имя пользователя:** `admin`
                #     - **Пароль:** `admin123`
                #     - **Роль:** Суперадминистратор
                #     """
                #     )
                with st.container(border=True):
                    st.markdown("""
                    **Тестовые учетные данные:**
                    - **Имя пользователя:** `admin`
                    - **Пароль:** `admin123`
                    - **Роль:** Суперадминистратор
                    """)

        st.stop()

    user = get_current_user()

    # Проверка, что пользователь получен
    if not user:
        st.error("⚠️ Ошибка получения данных пользователя")
        st.info("Пожалуйста, войдите в систему заново.")
        if st.button("Перейти к авторизации", type="primary"):
            logout()
            st.rerun()
        st.stop()

    # Проверка прав доступа к отчетам
    if not has_report_access(user["role"]):
        st.error("⚠️ У вас нет доступа к отчетам")
        st.info("Доступ к отчетам имеют менеджеры, аналитики и администраторы.")
        if st.button("Выйти"):
            logout()
            st.rerun()
        st.stop()

    st.markdown(
        '<h1 class="main-header">📊 Панель аналитики проектов</h1>',
        unsafe_allow_html=True,
    )

    # Боковая панель с меню навигации
    render_sidebar_menu(current_page="reports")

    # Загрузка данных - перенесена в основную область
    uploaded_files = st.file_uploader(
        "📁 Загрузите файлы с данными (можно несколько)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Загрузите CSV или Excel файлы с данными проекта, ресурсов или техники",
    )

    ensure_data_session_state()

    df = None
    current_file_names = [f.name for f in uploaded_files] if uploaded_files else []

    if uploaded_files is not None and len(uploaded_files) > 0:
        current_file_names = [f.name for f in uploaded_files]
        files_to_remove = [
            f
            for f in st.session_state.loaded_files_info.keys()
            if f not in current_file_names
        ]
        clear_all_data_for_removed_files(files_to_remove)

        for uploaded_file in uploaded_files:
            file_id = uploaded_file.name
            if file_id in st.session_state.loaded_files_info:
                continue
            df_loaded = load_data(uploaded_file, file_id)
            if df_loaded is not None:
                update_session_with_loaded_file(df_loaded, file_id)

    # Use project data as main df for backward compatibility
    df = st.session_state.project_data

    # Dashboard selection - allow access if any data is loaded (project, resources, or technique)
    has_project_data = df is not None and not df.empty
    resources_data = st.session_state.get("resources_data")
    technique_data = st.session_state.get("technique_data")
    has_resources_data = resources_data is not None and not resources_data.empty
    has_technique_data = technique_data is not None and not technique_data.empty
    has_any_data = has_project_data or has_resources_data or has_technique_data

    if has_any_data:
        # Check if dashboard was selected from sidebar menu
        dashboard_selected_from_menu = st.session_state.get(
            "dashboard_selected_from_menu", False
        )
        current_dashboard = st.session_state.get("current_dashboard", "")

        # Initialize session state for dashboard selection
        if "current_dashboard" not in st.session_state:
            # Set default dashboard based on available data
            if has_technique_data and not has_project_data:
                st.session_state.current_dashboard = "Аналитика по технике"
            elif (has_resources_data or has_technique_data) and not has_project_data:
                st.session_state.current_dashboard = "График движения рабочей силы"
            else:
                st.session_state.current_dashboard = "Динамика отклонений"

        # If dashboard was selected from sidebar menu, show only the selected dashboard
        # without the selection panels
        if dashboard_selected_from_menu and current_dashboard:
            # Display only the selected dashboard
            selected_dashboard = current_dashboard
            # Reset the flag after processing (will be reset after rerun if button clicked)
            st.session_state.dashboard_selected_from_menu = False

            # Выбор df по типу дашборда: project_fixed -> project_data; Прочее (техника/ресурсы) -> свои данные
            dashboards_using_technique = ("Аналитика по технике",)
            dashboards_using_resources = ("График движения рабочей силы", "СКУД стройка")
            if selected_dashboard in dashboards_using_technique:
                df_for_render = technique_data if has_technique_data else df
            elif selected_dashboard in dashboards_using_resources:
                df_for_render = resources_data if has_resources_data else (technique_data if has_technique_data else df)
            else:
                df_for_render = df

            # Route to selected dashboard (локальный словарь, без импорта из dashboards)
            try:
                from dashboards import get_dashboards
                dashboards = get_dashboards()
                render_fn = dashboards.get(selected_dashboard)
                if render_fn:
                    render_fn(df_for_render)
                else:
                    st.warning(
                        f"График '{selected_dashboard}' не найден. Пожалуйста, выберите другой график."
                    )
            except Exception as e:
                st.error(
                    f"Ошибка при отображении графика '{selected_dashboard}': {str(e)}"
                )
                st.exception(e)

            # Stop here - don't show selection panels
            st.stop()

        # Выбор панели - перенесен в основную область
        st.markdown("### 📊 Выбор панели")

        # Единый источник списка отчётов — dashboards.REPORT_CATEGORIES (3 категории)
        from dashboards import REPORT_CATEGORIES
        reason_options = REPORT_CATEGORIES[0][1]
        budget_options = REPORT_CATEGORIES[1][1]
        other_options = REPORT_CATEGORIES[2][1]

        # Determine current selection indices based on current_dashboard
        # Also sync radio button values in session_state when dashboard is selected from menu
        dashboard_selected_from_menu = st.session_state.get(
            "dashboard_selected_from_menu", False
        )

        # Determine indices and sync session_state for radio buttons
        # When dashboard is selected from menu, we need to ensure radio buttons reflect the selection
        current_dashboard = st.session_state.get("current_dashboard", "")

        # If dashboard was selected from menu, sync all radio buttons
        # We need to set the actual option value, not the index, for Streamlit radio buttons
        if dashboard_selected_from_menu and current_dashboard:
            # Set the selected radio button to the correct value (not index)
            if current_dashboard in reason_options:
                st.session_state.reason_radio = current_dashboard
                if budget_options:
                    st.session_state.budget_radio = budget_options[0]
                if other_options:
                    st.session_state.other_radio = other_options[0]
            elif current_dashboard in budget_options:
                st.session_state.budget_radio = current_dashboard
                if reason_options:
                    st.session_state.reason_radio = reason_options[0]
                if other_options:
                    st.session_state.other_radio = other_options[0]
            elif current_dashboard in other_options:
                st.session_state.other_radio = current_dashboard
                if reason_options:
                    st.session_state.reason_radio = reason_options[0]
                if budget_options:
                    st.session_state.budget_radio = budget_options[0]

        # Синхронизируем радиокнопки с current_dashboard при каждой загрузке,
        # чтобы после выбора отчёта из бокового меню (например БДДС) отображался правильный пункт
        if current_dashboard:
            if current_dashboard in reason_options:
                st.session_state.reason_radio = current_dashboard
            if current_dashboard in budget_options:
                st.session_state.budget_radio = current_dashboard
            if current_dashboard in other_options:
                st.session_state.other_radio = current_dashboard

        # Determine indices from session_state or current_dashboard
        # Streamlit radio stores the actual option value, not the index
        reason_index = 0
        if current_dashboard in reason_options:
            reason_index = reason_options.index(current_dashboard)
        elif "reason_radio" in st.session_state:
            try:
                # session_state contains the actual option value, not index
                if st.session_state.reason_radio in reason_options:
                    reason_index = reason_options.index(st.session_state.reason_radio)
                else:
                    # If value is not in options, use default
                    reason_index = 0
            except (ValueError, TypeError, IndexError):
                reason_index = 0

        budget_index = 0
        if current_dashboard in budget_options:
            budget_index = budget_options.index(current_dashboard)
        elif "budget_radio" in st.session_state:
            try:
                if st.session_state.budget_radio in budget_options:
                    budget_index = budget_options.index(st.session_state.budget_radio)
                else:
                    budget_index = 0
            except (ValueError, TypeError, IndexError):
                budget_index = 0

        other_index = 0
        if current_dashboard in other_options:
            other_index = other_options.index(current_dashboard)
        elif "other_radio" in st.session_state:
            try:
                if st.session_state.other_radio in other_options:
                    other_index = other_options.index(st.session_state.other_radio)
                else:
                    other_index = 0
            except (ValueError, TypeError, IndexError):
                other_index = 0

        # Определяем, какой expander должен быть развернут при выборе из меню
        current_dashboard = st.session_state.get("current_dashboard", "")

        # Определяем, какой expander разворачивать
        expand_reason = True  # По умолчанию разворачиваем первый
        expand_budget = False
        expand_other = False

        if dashboard_selected_from_menu and current_dashboard:
            if current_dashboard in reason_options:
                expand_reason = True
                expand_budget = False
                expand_other = False
            elif current_dashboard in budget_options:
                expand_reason = False
                expand_budget = True
                expand_other = False
            elif current_dashboard in other_options:
                expand_reason = False
                expand_budget = False
                expand_other = True

        # Section 1: Причины отклонений
        with st.expander("🔍 Причины отклонений", expanded=expand_reason):
            reason_dashboard = st.radio(
                "",
                reason_options,
                key="reason_radio",
                label_visibility="collapsed",
                index=reason_index,
            )

        # Section 2: Аналитика по финансам
        with st.expander("💰 Аналитика по финансам", expanded=expand_budget):
            budget_dashboard = st.radio(
                "",
                budget_options,
                key="budget_radio",
                label_visibility="collapsed",
                index=budget_index,
            )

        # Section 3: Прочее
        with st.expander("🔧 Прочее", expanded=expand_other):
            other_dashboard = st.radio(
                "",
                other_options,
                key="other_radio",
                label_visibility="collapsed",
                index=other_index,
            )

            # Determine selected dashboard based on radio button values
            # Note: Selection from sidebar menu is handled earlier and stops execution with st.stop()
            # So this code only runs when user selects dashboard via radio buttons in main area
            # Always use current radio button values to determine selected dashboard
            # This ensures that clicking on a radio button (even if already selected) works correctly
            if reason_dashboard != st.session_state.get(
                "prev_reason", reason_options[0]
            ):
                selected_dashboard = reason_dashboard
                st.session_state.current_dashboard = reason_dashboard
                st.session_state.prev_reason = reason_dashboard
                st.session_state.prev_budget = budget_options[0]
                st.session_state.prev_other = other_options[0]
            elif budget_dashboard != st.session_state.get(
                "prev_budget", budget_options[0]
            ):
                selected_dashboard = budget_dashboard
                st.session_state.current_dashboard = budget_dashboard
                st.session_state.prev_budget = budget_dashboard
                st.session_state.prev_reason = reason_options[0]
                st.session_state.prev_other = other_options[0]
            elif other_dashboard != st.session_state.get(
                "prev_other", other_options[0]
            ):
                selected_dashboard = other_dashboard
                st.session_state.current_dashboard = other_dashboard
                st.session_state.prev_other = other_dashboard
                st.session_state.prev_reason = reason_options[0]
                st.session_state.prev_budget = budget_options[0]
            else:
                # Сохраняем текущий выбор из меню/радио: приоритет у current_dashboard,
                # чтобы после выбора из бокового меню (например БДДС) не переключалось на первый пункт «Причины отклонений»
                current = st.session_state.current_dashboard
                if current and (
                    current in reason_options
                    or current in budget_options
                    or current in other_options
                ):
                    selected_dashboard = current
                elif reason_dashboard in reason_options:
                    selected_dashboard = reason_dashboard
                elif budget_dashboard in budget_options:
                    selected_dashboard = budget_dashboard
                elif other_dashboard in other_options:
                    selected_dashboard = other_dashboard
                else:
                    selected_dashboard = current or reason_dashboard
                st.session_state.current_dashboard = selected_dashboard

        # Выбор df по типу дашборда (project / техника / ресурсы)
        dashboards_using_technique = ("Аналитика по технике",)
        dashboards_using_resources = ("График движения рабочей силы", "СКУД стройка")
        if selected_dashboard in dashboards_using_technique:
            df_for_render = technique_data if has_technique_data else df
        elif selected_dashboard in dashboards_using_resources:
            df_for_render = resources_data if has_resources_data else (technique_data if has_technique_data else df)
        else:
            df_for_render = df

        # Route to selected dashboard via registry
        try:
            from dashboards import get_dashboards
            dashboards = get_dashboards()
            render_fn = dashboards.get(selected_dashboard)
            if render_fn:
                render_fn(df_for_render)
            else:
                st.warning(
                    f"График '{selected_dashboard}' не найден. Пожалуйста, выберите другой график."
                )
                st.info(f"Текущий выбор: {selected_dashboard}")
        except Exception as e:
            st.error(f"Ошибка при отображении графика '{selected_dashboard}': {str(e)}")
            st.exception(e)
    else:
        # Welcome message
        st.info(
            """
        👋 **Добро пожаловать в Панель аналитики проектов!**

        Эта панель предоставляет комплексную аналитику для управления проектами:

        **Доступные панели:**

        **🔍 Причины отклонений:**
        - **Динамика отклонений** (табы: по месяцам, динамика, причины)
        - **Отклонение текущего срока от базового плана**, **Значения отклонений от базового плана**

        **💰 Аналитика по финансам:**
        - **БДДС** (табы: по периодам, по лотам); **БДР**, **Бюджет план/факт**, **Утвержденный бюджет**, **Прогнозный бюджет**

        **🔧 Прочее:**
        - **Выдача рабочей/проектной документации** (включая просрочку выдачи РД), **Аналитика по технике**, **График движения рабочей силы** (включая СКУД стройка)

        **Для начала работы:**
        1. Загрузите файл с данными (CSV или Excel) через боковую панель
        2. Выберите панель из меню боковой панели
        3. Используйте фильтры для фокусировки на конкретных данных
        """
        )


if __name__ == "__main__":
    main()
