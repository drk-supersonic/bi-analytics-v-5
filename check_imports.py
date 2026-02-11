"""
Скрипт для проверки всех импортов перед запуском приложения
"""
import sys
import os
import io

# Устанавливаем UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Добавляем текущую директорию в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("=" * 60)
print("Проверка импортов для BI Analytics")
print("=" * 60)
print()

errors = []

# Проверка базовых модулей
modules_to_check = [
    ("streamlit", "st"),
    ("pandas", "pd"),
    ("plotly.express", "px"),
    ("plotly.graph_objects", "go"),
    ("numpy", "np"),
]

for module_name, alias in modules_to_check:
    try:
        print(f"✓ Импорт {module_name}...", end=" ")
        __import__(module_name)
        print("OK")
    except ImportError as e:
        print(f"ОШИБКА: {e}")
        errors.append(f"{module_name}: {e}")

print()

# Проверка собственных модулей
own_modules = [
    "auth",
    "logger",
    "settings",
    "permissions",
    "filters",
    "report_params",
]

for module_name in own_modules:
    try:
        print(f"✓ Импорт {module_name}...", end=" ")
        __import__(module_name)
        print("OK")
    except ImportError as e:
        print(f"ОШИБКА: {e}")
        errors.append(f"{module_name}: {e}")
    except Exception as e:
        print(f"ОШИБКА: {type(e).__name__}: {e}")
        errors.append(f"{module_name}: {type(e).__name__}: {e}")

print()

# Проверка загрузки дашбордов (dashboards._renderers)
try:
    print("✓ Загрузка дашбордов (get_dashboards)...", end=" ")
    from dashboards import get_dashboards
    dashboards = get_dashboards()
    print(f"OK ({len(dashboards)} дашбордов)")
except Exception as e:
    print(f"ОШИБКА: {e}")
    errors.append(f"dashboards/get_dashboards: {e}")
    import traceback
    traceback.print_exc()

print()

# Проверка инициализации базы данных
try:
    print("✓ Инициализация базы данных...", end=" ")
    from auth import init_db
    init_db()
    print("OK")
except Exception as e:
    print(f"ОШИБКА: {e}")
    errors.append(f"init_db: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)

if errors:
    print("НАЙДЕНЫ ОШИБКИ:")
    print()
    for error in errors:
        print(f"  - {error}")
    print()
    print("Исправьте ошибки перед запуском приложения!")
    sys.exit(1)
else:
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print()
    print("Приложение готово к запуску.")
    print("Используйте: streamlit run project_visualization_app.py --server.port 8501")











