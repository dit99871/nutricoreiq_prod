import os


def print_directory_structure(path, indent=0):
    """
    Рекурсивно выводит схематичную структуру видимых директорий и файлов проекта,
    игнорируя скрытые директории, файлы, __pycache__ и файлы типа __init__.

    Args:
        path (str): Путь к директории
        indent (int): Уровень отступа для форматирования вывода
    """
    try:
        # Получаем список всех элементов (директорий и файлов)
        items = [
            item
            for item in os.listdir(path)
            if not item.startswith(".")
            and item != "__pycache__"
            and not item.startswith("__init__")
        ]
        # Сортируем для предсказуемого порядка
        items.sort()

        for item in items:
            item_path = os.path.join(path, item)
            # Формируем отступ для текущего уровня
            prefix = "  " * indent
            if os.path.isdir(item_path):
                # Выводим имя директории
                print(f"{prefix}└── {item}/")
                # Рекурсивно обходим содержимое директории
                print_directory_structure(item_path, indent + 1)
            else:
                # Выводим имя файла
                print(f"{prefix}└── {item}")

    except PermissionError:
        print(f"{prefix}└── [Нет доступа к {path}]")
    except Exception as e:
        print(f"{prefix}└── [Ошибка: {str(e)}]")


def main():
    # Получаем текущую директорию
    current_dir = os.getcwd()
    print(f"Структура директорий и файлов в {current_dir}:")
    print_directory_structure(current_dir)


if __name__ == "__main__":
    main()
