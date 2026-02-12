# """
# Модуль для логирования действий пользователей
# """
# import sqlite3
# from datetime import datetime
# from typing import Optional, List, Dict
#
# from config import DB_PATH
#
#
# def log_action(username: str, action: str, details: Optional[str] = None, ip_address: Optional[str] = None):
#     """
#     Логирование действия пользователя
#
#     Args:
#         username: Имя пользователя
#         action: Тип действия (например, 'login', 'logout', 'change_role')
#         details: Дополнительные детали действия
#         ip_address: IP-адрес пользователя
#     """
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
#         cursor.execute("""
#             INSERT INTO user_activity_logs (username, action, details, ip_address, created_at)
#             VALUES (?, ?, ?, ?, ?)
#         """, (username, action, details, ip_address, datetime.now().isoformat()))
#         conn.commit()
#         conn.close()
#     except Exception as e:
#         import logging
#         logging.getLogger(__name__).warning("Ошибка при логировании действия: %s", e)
#
#
# def get_logs(limit: int = 100, username: Optional[str] = None, action: Optional[str] = None) -> List[Dict]:
#     """
#     Получение логов действий пользователей
#
#     Args:
#         limit: Максимальное количество записей
#         username: Фильтр по имени пользователя
#         action: Фильтр по типу действия
#
#     Returns:
#         Список словарей с логами
#     """
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
#
#         query = "SELECT id, username, action, details, ip_address, created_at FROM user_activity_logs WHERE 1=1"
#         params = []
#
#         if username:
#             query += " AND username = ?"
#             params.append(username)
#
#         if action:
#             query += " AND action = ?"
#             params.append(action)
#
#         query += " ORDER BY created_at DESC LIMIT ?"
#         params.append(limit)
#
#         cursor.execute(query, params)
#         rows = cursor.fetchall()
#         conn.close()
#
#         # Преобразуем в список словарей
#         logs = []
#         for row in rows:
#             logs.append({
#                 'id': row[0],
#                 'username': row[1],
#                 'action': row[2],
#                 'details': row[3],
#                 'ip_address': row[4],
#                 'created_at': row[5]
#             })
#
#         return logs
#     except Exception as e:
#         import logging
#         logging.getLogger(__name__).warning("Ошибка при получении логов: %s", e)
#         return []
#
#
# def get_logs_count(username: Optional[str] = None, action: Optional[str] = None) -> int:
#     """
#     Получение количества логов
#
#     Args:
#         username: Фильтр по имени пользователя
#         action: Фильтр по типу действия
#
#     Returns:
#         Количество записей
#     """
#     try:
#         conn = sqlite3.connect(DB_PATH)
#         cursor = conn.cursor()
#
#         query = "SELECT COUNT(*) FROM user_activity_logs WHERE 1=1"
#         params = []
#
#         if username:
#             query += " AND username = ?"
#             params.append(username)
#
#         if action:
#             query += " AND action = ?"
#             params.append(action)
#
#         cursor.execute(query, params)
#         count = cursor.fetchone()[0]
#         conn.close()
#
#         return count
#     except Exception as e:
#         import logging
#         logging.getLogger(__name__).warning("Ошибка при подсчете логов: %s", e)
#         return 0
#
#

"""
Модуль для логирования действий пользователей
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from config import DB_PATH


def get_client_ip() -> Optional[str]:
    """
    Пытается получить IP-адрес клиента из контекста Streamlit.
    Возвращает None, если не удалось определить.
    """
    try:
        import streamlit as st

        # Streamlit передаёт заголовки через st.context.headers (в новых версиях)
        headers = st.context.headers

        # 1. X-Forwarded-For — самый распространённый (учитывает прокси)
        forwarded = headers.get("X-Forwarded-For")
        if forwarded:
            # Может быть цепочка: "client_ip, proxy1, proxy2"
            # Берём самый первый (реальный клиент)
            return forwarded.split(",")[0].strip()

        # 2. X-Real-IP — часто используется в nginx
        real_ip = headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # 3. Remote-Addr — если прямое подключение
        remote_addr = headers.get("Remote-Addr")
        if remote_addr:
            return remote_addr.strip()

        return None

    except Exception:
        # Если st.context недоступен или другая ошибка — просто возвращаем None
        return None


def log_action(
    username: str,
    action: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Логирование действия пользователя

    Args:
        username: Имя пользователя
        action: Тип действия (например, 'login', 'logout', 'change_role')
        details: Дополнительные детали действия
        ip_address: IP-адрес пользователя (если передан вручную)
    """
    # Если IP не передан явно — пытаемся определить автоматически
    if ip_address is None:
        ip_address = get_client_ip()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_activity_logs
            (username, action, details, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, action, details, ip_address, datetime.now().isoformat()),
        )
        conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Ошибка при логировании действия: %s", e)
    finally:
        if 'conn' in locals():
            conn.close()


def get_logs(
    limit: int = 100,
    username: Optional[str] = None,
    action: Optional[str] = None,
) -> List[Dict]:
    """
    Получение логов действий пользователей

    Args:
        limit: Максимальное количество записей
        username: Фильтр по имени пользователя
        action: Фильтр по типу действия

    Returns:
        Список словарей с логами
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = """
            SELECT id, username, action, details, ip_address, created_at
            FROM user_activity_logs
            WHERE 1=1
        """
        params = []

        if username:
            query += " AND username = ?"
            params.append(username)

        if action:
            query += " AND action = ?"
            params.append(action)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Преобразуем в список словарей
        logs = []
        for row in rows:
            logs.append(
                {
                    "id": row[0],
                    "username": row[1],
                    "action": row[2],
                    "details": row[3],
                    "ip_address": row[4],
                    "created_at": row[5],
                }
            )

        return logs

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Ошибка при получении логов: %s", e)
        return []
    finally:
        if 'conn' in locals():
            conn.close()


def get_logs_count(
    username: Optional[str] = None,
    action: Optional[str] = None,
) -> int:
    """
    Получение количества логов

    Args:
        username: Фильтр по имени пользователя
        action: Фильтр по типу действия

    Returns:
        Количество записей
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM user_activity_logs WHERE 1=1"
        params = []

        if username:
            query += " AND username = ?"
            params.append(username)

        if action:
            query += " AND action = ?"
            params.append(action)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]

        return count

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Ошибка при подсчете логов: %s", e)
        return 0
    finally:
        if 'conn' in locals():
            conn.close()
