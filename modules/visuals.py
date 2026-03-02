"""
Модуль общих утилит для отображения: CSS-стили и вспомогательные функции.
Диаграммы дашборда вынесены в layouts/dashboard/visuals.py.
"""


def style_css(font_size=16) -> str:
    """
    Генерирует строку с CSS-стилями для кастомизации интерфейса Streamlit.

    Args:
        font_size (int): Базовый размер шрифта для элементов.

    Returns:
        str: Строка, содержащая тег <style> с CSS-правилами.
    """
    return f"""
    <style>
    h1, h2, h3 {{ line-height: 1.2; }}
    h2 {{ font-size: 1.6rem !important; }}
    h3 {{ font-size: 1.3rem !important; }}

    [data-testid="stMetricValue"] {{ font-size: 2rem; }}
    [data-testid="stMetricLabel"] {{ font-size: 1.1rem; }}
    [data-testid="stMetricDelta"] {{ font-size: 1rem; }}

    .block-container p, .stAlert {{ font-size: 1rem; }}
    
    /* Стилизация кнопки "Добавить корм" */
    div[data-testid="stExpander"] > details > summary {{
        font-size: 1.1rem;
        font-weight: bold;
        background-color: #f0f2f6;
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
    }}
    div[data-testid="stExpander"] > details > summary:hover {{
        background-color: #e6e9ef;
    }}
    
    /* Уменьшение отступов у number_input в сайдбаре */
    [data-testid="stSidebar"] [data-testid="stNumberInput"] {{
        padding-top: 0;
        margin-bottom: -15px; 
    }}
    
    /* Стилизация виджета number_input для кормов */
    [data-testid="stSidebar"] [data-testid="stNumberInput"] > label {{
        font-size: 0.9rem; /* Уменьшаем шрифт лейбла */
        white-space: normal; /* Разрешаем перенос строк */
        word-break: break-word; /* Ломаем длинные слова/ID */
        height: 3.5em; /* Выделяем 3 строки под лейбл */
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }}
    
    </style>
    """


def clean_nutrient_name(name: str) -> str:
    """
    Убирает '%' и лишние пробелы из названий нутриентов для отображения.

    Args:
        name (str): Исходное имя нутриента (напр. '% сырой протеин (СП)')

    Returns:
        str: Очищенное имя (напр. 'Сырой протеин (СП)')
    """
    if not isinstance(name, str):
        return str(name)

    # Удаляем %, заменяем несколько пробелов одним, убираем пробелы в начале/конце
    cleaned_name = name.replace('%', '').replace('  ', ' ').strip()

    # Делаем первую букву заглавной
    if cleaned_name:
        return cleaned_name[0].upper() + cleaned_name[1:]
    return cleaned_name


def shorten_feed_id(long_id: str) -> str:
    """Сокращает длинный ID корма для отображения в UI."""
    try:
        parts = long_id.split(' | ')
        if len(parts) == 8:
            return f"{parts[5]} ({parts[6]})"
        return long_id
    except Exception:
        return long_id
