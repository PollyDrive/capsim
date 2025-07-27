"""
Утилиты для работы с симуляционным временем.

Модуль содержит функции для конвертации симуляционного времени
в человеческое время суток с фиксированным началом в 08:00.
"""


def convert_sim_time_to_human(simulation_minutes: float) -> str:
    """
    Преобразует симуляционное время в человеческое время суток.
    
    Симуляция всегда начинается с 08:00 утра.
    Формула: human_time_minutes = (simulation_minutes + 480) % 1440
    где 480 = 8 часов * 60 минут (начало в 08:00)
    
    Args:
        simulation_minutes: Время в симуляции в минутах (float или int)
        
    Returns:
        Строка времени в формате "ЧЧ:ММ" (например, "08:15", "14:30")
        
    Examples:
        >>> convert_sim_time_to_human(0)      # Начало симуляции
        '08:00'
        >>> convert_sim_time_to_human(120)    # Через 2 часа
        '10:00'
        >>> convert_sim_time_to_human(960)    # Полночь (переход к дню 1)
        '00:00'
        >>> convert_sim_time_to_human(1440)   # Утро дня 1 (24 часа симуляции)
        '08:00'
    """
    # Конвертируем в целые минуты
    sim_minutes = int(simulation_minutes)
    
    # Добавляем 480 минут (8 часов) для начала в 08:00
    # и берем остаток от деления на 1440 (24 часа) для обработки переходов через полночь
    human_time_minutes = (sim_minutes + 480) % 1440
    
    # Вычисляем часы и минуты
    hours = human_time_minutes // 60
    minutes = human_time_minutes % 60
    
    # Форматируем в строку "ЧЧ:ММ"
    return f"{hours:02d}:{minutes:02d}"


def get_simulation_day(simulation_minutes: float) -> int:
    """
    Возвращает номер дня симуляции (начиная с 0).
    
    День симуляции меняется в полночь (00:00), а не в момент начала симуляции (08:00).
    Учитываем смещение начала симуляции на 8 часов (480 минут).
    
    Args:
        simulation_minutes: Время в симуляции в минутах
        
    Returns:
        Номер дня симуляции (0, 1, 2, ...)
        
    Examples:
        >>> get_simulation_day(0)     # 08:00 дня 0
        0
        >>> get_simulation_day(960)   # 00:00 дня 1
        1
        >>> get_simulation_day(1440)  # 08:00 дня 1
        1
        >>> get_simulation_day(2400)  # 00:00 дня 2
        2
    """
    # Добавляем смещение 480 минут (8 часов) и делим на 1440 (24 часа)
    return int((simulation_minutes + 480) // 1440)


def format_simulation_time_detailed(simulation_minutes: float) -> str:
    """
    Форматирует симуляционное время с указанием дня и времени суток.
    
    Args:
        simulation_minutes: Время в симуляции в минутах
        
    Returns:
        Строка в формате "День X, ЧЧ:ММ"
        
    Examples:
        >>> format_simulation_time_detailed(0)     # Начало симуляции
        'День 0, 08:00'
        >>> format_simulation_time_detailed(960)   # Полночь
        'День 1, 00:00'
        >>> format_simulation_time_detailed(1440)  # Утро следующего дня
        'День 1, 08:00'
    """
    day = get_simulation_day(simulation_minutes)
    time_str = convert_sim_time_to_human(simulation_minutes)
    return f"День {day}, {time_str}"


def get_time_of_day_category(simulation_minutes: float) -> str:
    """
    Определяет категорию времени суток для симуляционного времени.
    
    Args:
        simulation_minutes: Время в симуляции в минутах
        
    Returns:
        Категория времени: "утро", "день", "вечер", "ночь"
        
    Examples:
        >>> get_time_of_day_category(0)  # 08:00
        'утро'
        >>> get_time_of_day_category(360)  # 14:00
        'день'
    """
    human_time = convert_sim_time_to_human(simulation_minutes)
    hour = int(human_time.split(':')[0])
    
    if 6 <= hour < 12:
        return "утро"
    elif 12 <= hour < 18:
        return "день"
    elif 18 <= hour < 22:
        return "вечер"
    else:
        return "ночь"