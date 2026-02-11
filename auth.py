"""
Модуль авторизации для BI Analytics приложения
"""
import sys
from pathlib import Path

# Ensure app directory is first on path (for deployment: pages may add repo root, we need app root first)
_app_dir = Path(__file__).resolve().parent
_app_dir_str = str(_app_dir)
sys.path.insert(0, _app_dir_str)

import sqlite3
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
import streamlit as st

from config import DB_PATH

# Роли пользователей
ROLES = {
    "superadmin": "Суперадминистратор",
    "admin": "Администратор",
    "manager": "Менеджер",
    "analyst": "Аналитик",
}

# Роли с доступом к настройкам
ADMIN_ROLES = ["superadmin", "admin"]

# Роли с доступом к отчетам
REPORT_ROLES = ["manager", "analyst", "admin", "superadmin"]


def init_db():
    """Инициализация базы данных: создание всех таблиц (делегируется в db)."""
    from db import init_all_tables
    def _show(msg):
        try:
            st.info(msg)
        except Exception:
            pass
    init_all_tables(_show)


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Проверка пароля"""
    return hash_password(password) == password_hash


def create_user(
    username: str,
    password: str,
    role: str,
    email: Optional[str] = None,
    created_by: Optional[str] = None,
) -> bool:
    """Создание нового пользователя"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        password_hash = hash_password(password)
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, role, email)
            VALUES (?, ?, ?, ?)
        """,
            (username, password_hash, role, email),
        )

        conn.commit()
        conn.close()

        # Логируем создание пользователя
        try:
            from logger import log_action

            creator = created_by or "system"
            log_action(
                creator,
                "create_user",
                f"Создан пользователь: {username} с ролью {role}",
            )
        except:
            pass  # Не прерываем выполнение при ошибке логирования

        return True
    except sqlite3.IntegrityError:
        return False
    except Exception:
        return False


def authenticate(username: str, password: str) -> Tuple[bool, Optional[dict]]:
    """Аутентификация пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, username, password_hash, role, email, is_active
        FROM users
        WHERE username = ?
    """,
        (username,),
    )

    user = cursor.fetchone()

    if user and user[5] == 1:  # is_active
        user_id, username_db, password_hash, role, email, is_active = user

        if verify_password(password, password_hash):
            # Обновляем время последнего входа
            cursor.execute(
                """
                UPDATE users
                SET last_login = ?
                WHERE id = ?
            """,
                (datetime.now(), user_id),
            )
            conn.commit()

            conn.close()

            # Логируем вход
            try:
                from logger import log_action

                log_action(username_db, "login", f"Успешный вход в систему")
            except:
                pass  # Не прерываем выполнение при ошибке логирования

            return True, {
                "id": user_id,
                "username": username_db,
                "role": role,
                "email": email,
            }

    conn.close()
    return False, None


def get_user_by_username(username: str) -> Optional[dict]:
    """Получение пользователя по имени"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, username, role, email, is_active
        FROM users
        WHERE username = ?
    """,
        (username,),
    )

    user = cursor.fetchone()
    conn.close()

    if user:
        return {
            "id": user[0],
            "username": user[1],
            "role": user[2],
            "email": user[3],
            "is_active": user[4],
        }
    return None


def generate_reset_token(username: str) -> Optional[str]:
    """Генерация токена для восстановления пароля"""
    user = get_user_by_username(username)
    if not user:
        return None

    # Генерируем случайный токен
    token = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
    )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Удаляем старые неиспользованные токены для этого пользователя
    cursor.execute(
        """
        DELETE FROM password_reset_tokens
        WHERE username = ? AND used = 0
    """,
        (username,),
    )

    # Создаем новый токен (действителен 1 час)
    expires_at = datetime.now() + timedelta(hours=1)
    cursor.execute(
        """
        INSERT INTO password_reset_tokens (username, token, expires_at)
        VALUES (?, ?, ?)
    """,
        (username, token, expires_at),
    )

    conn.commit()
    conn.close()

    return token


def verify_reset_token(token: str) -> Optional[str]:
    """Проверка токена восстановления пароля"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT username, expires_at, used
        FROM password_reset_tokens
        WHERE token = ?
    """,
        (token,),
    )

    result = cursor.fetchone()
    conn.close()

    if result:
        username, expires_at, used = result
        expires_at = datetime.fromisoformat(expires_at)

        if not used and datetime.now() < expires_at:
            return username

    return None


def reset_password(token: str, new_password: str) -> bool:
    """Сброс пароля по токену"""
    username = verify_reset_token(token)
    if not username:
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Обновляем пароль
    password_hash = hash_password(new_password)
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE username = ?
    """,
        (password_hash, username),
    )

    # Помечаем токен как использованный
    cursor.execute(
        """
        UPDATE password_reset_tokens
        SET used = 1
        WHERE token = ?
    """,
        (token,),
    )

    conn.commit()
    conn.close()

    return True


def has_admin_access(user_role: str) -> bool:
    """Проверка доступа к административной панели"""
    return user_role in ADMIN_ROLES


def has_report_access(user_role: str) -> bool:
    """Проверка доступа к отчетам"""
    return user_role in REPORT_ROLES


def get_user_role_display(role: str) -> str:
    """Получение отображаемого названия роли"""
    return ROLES.get(role, role)


def check_authentication() -> bool:
    """Проверка авторизации пользователя в сессии"""
    if "authenticated" not in st.session_state:
        return False
    return st.session_state.get("authenticated", False)


def get_current_user() -> Optional[dict]:
    """Получение текущего пользователя из сессии"""
    if check_authentication():
        return st.session_state.get("user", None)
    return None


def logout():
    """Выход из системы"""
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]
    if "user" in st.session_state:
        del st.session_state["user"]


def change_password(
    username: str, old_password: str, new_password: str
) -> Tuple[bool, str]:
    """
    Изменение пароля пользователя

    Args:
        username: Имя пользователя
        old_password: Текущий пароль
        new_password: Новый пароль

    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем текущий пароль
    cursor.execute(
        """
        SELECT password_hash FROM users
        WHERE username = ? AND is_active = 1
    """,
        (username,),
    )

    result = cursor.fetchone()
    if not result:
        conn.close()
        return False, "Пользователь не найден"

    password_hash = result[0]
    if not verify_password(old_password, password_hash):
        conn.close()
        return False, "Неверный текущий пароль"

    # Обновляем пароль
    new_password_hash = hash_password(new_password)
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE username = ?
    """,
        (new_password_hash, username),
    )

    conn.commit()
    conn.close()

    return True, "Пароль успешно изменен"


def update_user_email(username: str, new_email: Optional[str]) -> Tuple[bool, str]:
    """
    Обновление email пользователя

    Args:
        username: Имя пользователя
        new_email: Новый email (может быть None)

    Returns:
        Tuple[bool, str]: (успех, сообщение)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем существование пользователя
    cursor.execute(
        """
        SELECT id FROM users
        WHERE username = ? AND is_active = 1
    """,
        (username,),
    )

    result = cursor.fetchone()
    if not result:
        conn.close()
        return False, "Пользователь не найден"

    # Обновляем email
    cursor.execute(
        """
        UPDATE users
        SET email = ?
        WHERE username = ?
    """,
        (new_email, username),
    )

    conn.commit()
    conn.close()

    return True, "Email успешно обновлен"


def is_streamlit_context():
    """Проверка, что код выполняется в контексте Streamlit"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except:
        return False


def require_auth():
    """Декоратор для проверки авторизации (для использования в Streamlit)"""
    # Проверяем, что мы в контексте Streamlit
    if not is_streamlit_context():
        return

    if not check_authentication():
        st.error("⚠️ Требуется авторизация")
        st.info("Пожалуйста, войдите в систему для доступа к этой странице.")
        if st.button("Перейти к авторизации"):
            st.switch_page("project_visualization_app.py")
        st.stop()


def render_sidebar_menu(current_page: str = "reports"):
    """
    Отображение боковой панели с меню навигации

    Args:
        current_page: Текущая страница ("reports", "admin", "profile", "analyst_params")
    """
    if not is_streamlit_context():
        return

    # Проверка авторизации - меню показывается только авторизованным пользователям
    if not check_authentication():
        return

    user = get_current_user()
    if not user:
        return

    # CSS для скрытия стандартной навигации Streamlit и стилизации элементов
    # Этот CSS применяется глобально для всех страниц
    st.markdown(
        """
        <style>
        /* Скрываем стандартную навигацию Streamlit в боковой панели */
        [data-testid="stSidebarNav"],
        div[data-testid="stSidebarNav"],
        ul[data-testid="stSidebarNav"],
        nav[data-testid="stSidebarNav"],
        .stSidebar [data-testid="stSidebarNav"],
        section[data-testid="stSidebarNav"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            overflow: hidden !important;
        }
        /* Скрываем стандартные ссылки на страницы в боковой панели */
        .stSidebar a[href*="pages/"],
        .stSidebar a[href*="project_visualization_app"] {
            display: none !important;
        }
        
        /* Хедер — такой же цвет, как фон приложения */
        header[data-testid="stHeader"],
        [data-testid="stHeader"],
        .stHeader,
        header,
        div[data-testid="stHeader"],
        .stHeader > div,
        header > div,
        div[data-testid="stHeader"] > div {
            background-color: #12385C !important;
            border-bottom: none !important;
        }
        header[data-testid="stHeader"] *,
        [data-testid="stHeader"] *,
        .stHeader *,
        header * {
            color: #ffffff !important;
        }
        
        /* Стилизация полей ввода - подсветка для видимости на темном фоне */
        .stTextInput > div > div > input,
        .stTextInput > div > div > input:focus,
        input[type="text"],
        input[type="password"],
        input[type="email"],
        input[type="number"],
        textarea {
            background-color: #2a2a3a !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
            border-radius: 4px !important;
            padding: 0.5rem !important;
        }
        .stTextInput > div > div > input:focus,
        input[type="text"]:focus,
        input[type="password"]:focus,
        input[type="email"]:focus,
        input[type="number"]:focus,
        textarea:focus {
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
            outline: none !important;
        }
        
        /* Стилизация кнопок - фон цвета основного фона, белый текст */
        .stButton > button {
            background-color: #12385C !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 4px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button:hover {
            background-color: rgba(18, 56, 92, 0.9) !important;
            border-color: rgba(255, 255, 255, 0.5) !important;
            color: #ffffff !important;
        }
        .stButton > button:focus {
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
            outline: none !important;
        }
        /* Кнопки primary - фон цвета основного фона с более яркой окантовкой */
        .stButton > button[kind="primary"] {
            background-color: #12385C !important;
            color: #ffffff !important;
            border: 1px solid #1f77b4 !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: rgba(18, 56, 92, 0.9) !important;
            border-color: #2a8bc4 !important;
            color: #ffffff !important;
        }
        /* Отключенные кнопки */
        .stButton > button:disabled {
            background-color: rgba(18, 56, 92, 0.6) !important;
            color: #666666 !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
            opacity: 0.6 !important;
        }
        /* Стилизация selectbox */
        .stSelectbox > div > div > select {
            background-color: #2a2a3a !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
            border-radius: 4px !important;
        }
        .stSelectbox > div > div > select:focus {
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
            outline: none !important;
        }
        /* Стилизация checkbox */
        .stCheckbox > label {
            color: #ffffff !important;
        }
        /* Стилизация date input */
        .stDateInput > div > div > input {
            background-color: #2a2a3a !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
        }
        /* Стилизация number input */
        .stNumberInput > div > div > input {
            background-color: #2a2a3a !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
            border-radius: 4px !important;
        }
        .stNumberInput > div > div > input:focus {
            border-color: #1f77b4 !important;
            box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
            outline: none !important;
        }
        /* Стилизация multiselect */
        .stMultiSelect > div > div {
            background-color: #2a2a3a !important;
            color: #ffffff !important;
            border: 1px solid #4a5568 !important;
        }
        /* Стилизация file uploader */
        .stFileUploader > div {
            background-color: #2a2a3a !important;
            border: 1px solid #4a5568 !important;
            border-radius: 4px !important;
        }
        
        /* Таблицы — фон синий #12385C, шрифт белый */
        .main table, .main table th, .main table td,
        table, table th, table td, table thead th, table tbody th, table tbody td {
            background-color: #12385C !important;
            color: #ffffff !important;
            border-color: rgba(255, 255, 255, 0.25) !important;
        }
        .main table *, table th *, table td * {
            color: #ffffff !important;
        }
        [data-testid="stDataFrame"], [data-testid="stDataFrame"] *,
        .stDataFrame, .stDataFrame * {
            background-color: #12385C !important;
            color: #ffffff !important;
        }
        
        /* Стилизация sidebar (бокового меню) - фон цвета основного фона */
        .stSidebar,
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"],
        div[data-testid="stSidebar"],
        .stSidebar > div,
        [data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] > div,
        div[data-testid="stSidebar"] > div {
            background-color: #12385C !important;
        }
        
        /* Разделитель между sidebar и основной областью - отступ 30px от границы кнопок */
        .stSidebar,
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"],
        div[data-testid="stSidebar"] {
            border-right: 1px solid rgba(255, 255, 255, 0.3) !important;
            padding-right: 30px !important;
        }
        
        /* Текст в sidebar - белый */
        .stSidebar *,
        [data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] *,
        div[data-testid="stSidebar"] * {
            color: #ffffff !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        # Меню навигации
        st.markdown("### 📋 Меню")

        # 1. Отчеты (если есть доступ)
        if has_report_access(user["role"]):
            if current_page == "reports":
                st.button(
                    "📊 Отчеты",
                    use_container_width=True,
                    type="primary",
                    disabled=True,
                    help="Текущая страница",
                )
            else:
                if st.button("📊 Отчеты", use_container_width=True):
                    st.switch_page("project_visualization_app.py")

            # Список отчетов под кнопкой "Отчеты" (единый источник: dashboards.REPORT_CATEGORIES)
            if current_page == "reports":
                from dashboards import REPORT_CATEGORIES
                st.markdown("---")
                st.markdown("#### 📋 Список отчетов")
                current_dashboard = st.session_state.get("current_dashboard", "")
                # Иконки: Причины отклонений, Аналитика по финансам, Прочее (3 категории)
                icons = ["🔍", "💰", "🔧"]
                for i, (cat_name, reports) in enumerate(REPORT_CATEGORIES):
                    icon = icons[i] if i < len(icons) else "📋"
                    with st.expander(f"{icon} {cat_name}", expanded=False):
                        for report in reports:
                            button_type = (
                                "primary" if current_dashboard == report else "secondary"
                            )
                            if st.button(
                                f"• {report}",
                                use_container_width=True,
                                key=f"menu_report_{report}",
                                type=button_type,
                            ):
                                st.session_state.current_dashboard = report
                                st.session_state.dashboard_selected_from_menu = True
                                st.rerun()

        # 2. Настройки
        if has_admin_access(user["role"]):
            # Для администраторов: общие настройки и профиль
            if current_page == "admin":
                st.button(
                    "⚙️ Общие настройки",
                    use_container_width=True,
                    type="primary",
                    disabled=True,
                    help="Текущая страница",
                )
            else:
                if st.button("⚙️ Общие настройки", use_container_width=True):
                    st.switch_page("pages/admin.py")

        # Настройки профиля (для всех ролей)
        if current_page == "profile":
            st.button(
                "👤 Настройки профиля",
                use_container_width=True,
                type="primary",
                disabled=True,
                help="Текущая страница",
            )
        else:
            if st.button("👤 Настройки профиля", use_container_width=True):
                st.switch_page("pages/profile.py")

        # Параметры отчетов (фильтры) - доступны аналитикам и администраторам (не менеджерам)
        if user["role"] in ["analyst", "admin", "superadmin"]:
            if current_page == "analyst_params":
                st.button(
                    "📝 Параметры отчетов",
                    use_container_width=True,
                    type="primary",
                    disabled=True,
                    help="Текущая страница",
                )
            else:
                if st.button("📝 Параметры отчетов", use_container_width=True):
                    st.switch_page("pages/analyst_params.py")

        # 3. Выход (для всех ролей)
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            logout()
            st.success("Вы вышли из системы")
            st.rerun()

        st.markdown("---")

        # Информация о загруженных файлах
        if has_report_access(user["role"]):
            loaded_files_info = st.session_state.get("loaded_files_info", {})
            if loaded_files_info:
                st.markdown("### 📊 Загруженные файлы")

                project_data = st.session_state.get("project_data")
                if project_data is not None:
                    total_rows = len(project_data)
                    st.success(f"✅ Проекты: {total_rows} строк")
                    project_files = [
                        f
                        for f, info in loaded_files_info.items()
                        if info["type"] == "project"
                    ]
                    for file_name in project_files:
                        st.caption(
                            f"  • {file_name} ({loaded_files_info[file_name]['rows']} строк)"
                        )

                resources_data = st.session_state.get("resources_data")
                if resources_data is not None:
                    total_rows = len(resources_data)
                    st.success(f"✅ Ресурсы: {total_rows} строк")
                    resources_files = [
                        f
                        for f, info in loaded_files_info.items()
                        if info["type"] == "resources"
                    ]
                    for file_name in resources_files:
                        st.caption(
                            f"  • {file_name} ({loaded_files_info[file_name]['rows']} строк)"
                        )

                technique_data = st.session_state.get("technique_data")
                if technique_data is not None:
                    total_rows = len(technique_data)
                    st.success(f"✅ Техника: {total_rows} строк")
                    technique_files = [
                        f
                        for f, info in loaded_files_info.items()
                        if info["type"] == "technique"
                    ]
                    for file_name in technique_files:
                        st.caption(
                            f"  • {file_name} ({loaded_files_info[file_name]['rows']} строк)"
                        )

                st.markdown("---")

        # Информация о пользователе
        st.markdown("### 👤 Пользователь")
        st.write(f"**{user['username']}**")
        st.caption(f"Роль: {get_user_role_display(user['role'])}")
