"""
Централизованный модуль для маппинга топиков трендов к категориям интересов.

Обеспечивает единый источник истины для всех модулей, тестов и сидов.
Использует кэширование для производительности и fallback к константам.
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

# Константы-fallback для случаев, когда DB недоступна
CANONICAL_TOPIC_MAPPINGS = {
    "ECONOMIC": {
        "display": "Economic",
        "interest_category": "Economics",
        "description": "Economic trends and financial topics"
    },
    "HEALTH": {
        "display": "Health", 
        "interest_category": "Wellbeing",
        "description": "Health, wellness and medical topics"
    },
    "SPIRITUAL": {
        "display": "Spiritual",
        "interest_category": "Spirituality",
        "description": "Spiritual, religious and philosophical topics"
    },
    "CONSPIRACY": {
        "display": "Conspiracy",
        "interest_category": "Society",
        "description": "Conspiracy theories and social distrust topics"
    },
    "SCIENCE": {
        "display": "Science",
        "interest_category": "Knowledge", 
        "description": "Scientific discoveries and educational content"
    },
    "CULTURE": {
        "display": "Culture",
        "interest_category": "Creativity",
        "description": "Cultural events, arts and creative expression"
    },
    "SPORT": {
        "display": "Sport",
        "interest_category": "Society",
        "description": "Sports events and physical activities"
    }
}

# Кэш для производительности
_mapping_cache: Optional[Dict[str, Dict[str, str]]] = None


def get_all_topic_codes() -> List[str]:
    """Возвращает все доступные коды топиков."""
    return list(CANONICAL_TOPIC_MAPPINGS.keys())


def get_all_interest_categories() -> List[str]:
    """Возвращает все уникальные категории интересов."""
    categories = set()
    for mapping in CANONICAL_TOPIC_MAPPINGS.values():
        categories.add(mapping["interest_category"])
    return list(categories)


def topic_to_interest_category(topic_code: str) -> str:
    """
    Преобразует код топика в категорию интереса.
    
    Args:
        topic_code: Код топика (ECONOMIC, HEALTH, etc.)
        
    Returns:
        Категория интереса (Economics, Wellbeing, etc.)
        
    Raises:
        KeyError: Если топик не найден
    """
    topic_code = topic_code.upper()
    if topic_code not in CANONICAL_TOPIC_MAPPINGS:
        raise KeyError(f"Unknown topic code: {topic_code}")
    
    return CANONICAL_TOPIC_MAPPINGS[topic_code]["interest_category"]


def topic_to_display_name(topic_code: str) -> str:
    """
    Преобразует код топика в отображаемое имя.
    
    Args:
        topic_code: Код топика (ECONOMIC, HEALTH, etc.)
        
    Returns:
        Отображаемое имя (Economic, Health, etc.)
    """
    topic_code = topic_code.upper()
    if topic_code not in CANONICAL_TOPIC_MAPPINGS:
        return topic_code.capitalize()  # Fallback
    
    return CANONICAL_TOPIC_MAPPINGS[topic_code]["display"]


def interest_category_to_topics(interest_category: str) -> List[str]:
    """
    Возвращает все топики для данной категории интереса.
    
    Args:
        interest_category: Категория интереса (Economics, Wellbeing, etc.)
        
    Returns:
        Список кодов топиков
    """
    topics = []
    for topic_code, mapping in CANONICAL_TOPIC_MAPPINGS.items():
        if mapping["interest_category"] == interest_category:
            topics.append(topic_code)
    return topics


def validate_topic_code(topic_code: str) -> bool:
    """
    Проверяет валидность кода топика.
    
    Args:
        topic_code: Код топика для проверки
        
    Returns:
        True если топик валиден
    """
    return topic_code.upper() in CANONICAL_TOPIC_MAPPINGS


def validate_interest_category(interest_category: str) -> bool:
    """
    Проверяет валидность категории интереса.
    
    Args:
        interest_category: Категория интереса для проверки
        
    Returns:
        True если категория валидна
    """
    return interest_category in get_all_interest_categories()


def load_mappings_from_db(db_session: Session) -> Dict[str, Dict[str, str]]:
    """
    Загружает маппинги из базы данных с fallback к константам.
    
    Args:
        db_session: Сессия SQLAlchemy
        
    Returns:
        Словарь маппингов {topic_code: {display, interest_category, description}}
    """
    global _mapping_cache
    
    if _mapping_cache is not None:
        return _mapping_cache
    
    try:
        from capsim.db.models import TopicInterestMapping
        
        mappings = {}
        rows = db_session.query(TopicInterestMapping).all()
        
        for row in rows:
            mappings[row.topic_code] = {
                "display": row.topic_display,
                "interest_category": row.interest_category,
                "description": row.description or ""
            }
        
        # Если DB пустая, используем константы
        if not mappings:
            mappings = CANONICAL_TOPIC_MAPPINGS.copy()
        
        _mapping_cache = mappings
        return mappings
        
    except (SQLAlchemyError, ImportError) as e:
        # Fallback к константам при ошибке DB
        print(f"Warning: Failed to load topic mappings from DB: {e}")
        _mapping_cache = CANONICAL_TOPIC_MAPPINGS.copy()
        return _mapping_cache


def clear_cache():
    """Очищает кэш маппингов (для тестов)."""
    global _mapping_cache
    _mapping_cache = None


# Удобные функции для обратной совместимости
def get_topic_mapping() -> Dict[str, str]:
    """
    Возвращает простой маппинг topic_code -> interest_category.
    
    Returns:
        Словарь {ECONOMIC: Economics, HEALTH: Wellbeing, ...}
    """
    return {
        topic_code: mapping["interest_category"]
        for topic_code, mapping in CANONICAL_TOPIC_MAPPINGS.items()
    }


def get_display_mapping() -> Dict[str, str]:
    """
    Возвращает маппинг topic_code -> display_name.
    
    Returns:
        Словарь {ECONOMIC: Economic, HEALTH: Health, ...}
    """
    return {
        topic_code: mapping["display"]
        for topic_code, mapping in CANONICAL_TOPIC_MAPPINGS.items()
    } 