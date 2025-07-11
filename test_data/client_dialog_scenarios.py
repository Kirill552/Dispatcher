# -*- coding: utf-8 -*-
"""
Сценарии диалогов с клиентами для тестирования ИИ-продажника
Различные типы возражений и реакций клиентов
"""

from typing import List, Dict, Tuple
from enum import Enum

class ClientType(Enum):
    """Типы клиентов для тестирования"""
    EASY_CLIENT = "easy"           # Легкий клиент (быстро соглашается)
    PRICE_SENSITIVE = "price"      # Чувствительный к цене
    DEMANDING = "demanding"        # Требовательный клиент
    INDECISIVE = "indecisive"     # Нерешительный
    AGGRESSIVE = "aggressive"      # Агрессивный
    PROFESSIONAL = "professional"  # Профессиональный логист
    HESITANT = "hesitant"          # Нерешительный клиент

# Базовые сценарии диалогов
CLIENT_DIALOG_SCENARIOS = {
    
    ClientType.EASY_CLIENT: {
        "name": "Легкий клиент",
        "description": "Быстро принимает решения, минимум возражений",
        "conversations": [
            {
                "scenario_id": "easy_001",
                "client_messages": [
                    "Отлично! Подходящая цена."
                ],
                "expected_outcome": "offer_sent_and_completed",
                "objection_count": 0,
                "context": "Клиент уже дал все данные о грузе. Перевозчики уже знают маршрут, дату, тип кузова. Бот предложил цену."
            },
            {
                "scenario_id": "easy_002", 
                "client_messages": [
                    "Цена нормальная, меня устраивает."
                ],
                "expected_outcome": "offer_sent_and_completed",
                "objection_count": 1,
                "context": "Клиент согласен на цену, уточняет только время подачи"
            }
        ]
    },
    
    ClientType.PRICE_SENSITIVE: {
        "name": "Чувствительный к цене",
        "description": "Торгуется, сравнивает цены, просит скидки",
        "conversations": [
            {
                "scenario_id": "price_001",
                "client_messages": [
                    "Дорого получается. На прошлой неделе возил за 35 тысяч.",
                    "Но все равно дороговато. Можете скидку сделать?",
                    "А если постоянное сотрудничество - какие условия?",
                    "Ладно, согласен на ваши условия."
                ],
                "expected_outcome": "offer_sent_and_completed",
                "objection_count": 3,
                "context": "Клиент торгуется за цену, ссылается на прошлый опыт. Груз и маршрут уже известны."
            },
            {
                "scenario_id": "price_002",
                "client_messages": [
                    "У конкурентов дешевле на 5 тысяч!",
                    "Не могу согласиться на такую цену.",
                    "Это окончательная цена?"
                ],
                "expected_outcome": "escalation",
                "objection_count": 3,
                "context": "Клиент сравнивает цены с конкурентами, нужна эскалация для финальных переговоров"
            },
            {
                "scenario_id": "price_003",
                "client_messages": [
                    "Цена кусается. В прошлый раз было 30 тысяч за этот же маршрут.",
                    "Понятно про рынок, но все равно дорого.",
                    "А какие у вас гарантии по срокам и сохранности?"
                ],
                "expected_outcome": "continuing_dialog",
                "objection_count": 3,
                "context": "Клиент ищет дополнительную ценность - гарантии, надежность"
            }
        ]
    },
    
    ClientType.DEMANDING: {
        "name": "Требовательный клиент",
        "description": "Много вопросов, хочет гарантии, детали",
        "conversations": [
            {
                "scenario_id": "demanding_001",
                "client_messages": [
                    "Цена устраивает, но хочу подробности о перевозчике.",
                    "Какие гарантии что доставят в срок?",
                    "А если будет задержка или повреждения?",
                    "Можно ли отследить груз в пути?",
                    "Хорошо, если все гарантии есть - согласен."
                ],
                "expected_outcome": "agreement", 
                "objection_count": 4,
                "context": "Клиент согласен на цену, но требует гарантии надежности сервиса"
            },
            {
                "scenario_id": "demanding_002",
                "client_messages": [
                    "Нужны документы на перевозчика - лицензии, страховка.",
                    "Груз дорогой, нужны дополнительные гарантии.",
                    "Можете предоставить договор на ознакомление?"
                ],
                "expected_outcome": "escalation",
                "objection_count": 3,
                "context": "Клиент требует документооборот и юридические гарантии"
            }
        ]
    },
    
    ClientType.INDECISIVE: {
        "name": "Нерешительный клиент", 
        "description": "Долго думает, просит время, советуется",
        "conversations": [
            {
                "scenario_id": "indecisive_001",
                "client_messages": [
                    "Хм, нужно подумать...",
                    "Цена вроде нормальная, но не знаю...",
                    "А можно до завтра время?",
                    "Нужно с руководством посоветоваться.",
                    "Хорошо, завтра дам окончательный ответ."
                ],
                "expected_outcome": "postponed",
                "objection_count": 4,
                "context": "Клиент не уверен в решении, просит время на обдумывание"
            },
            {
                "scenario_id": "indecisive_002",
                "client_messages": [
                    "Не знаю... а что если найдется дешевле?",
                    "Может еще поискать варианты?",
                    "Сложно решить сразу.",
                    "Ладно, беру ваше предложение."
                ],
                "expected_outcome": "agreement",
                "objection_count": 3,
                "context": "Клиент сомневается но в итоге принимает решение"
            }
        ]
    },
    
    ClientType.AGGRESSIVE: {
        "name": "Агрессивный клиент",
        "description": "Критично настроен, много претензий",
        "conversations": [
            {
                "scenario_id": "aggressive_001",
                "client_messages": [
                    "Что за грабительские цены? У всех дешевле!",
                    "Вы вообще на рынке ориентируетесь?",
                    "Последний раз работал с вами - сплошные проблемы были.",
                    "Если не снизите цену - иду к конкурентам!"
                ],
                "expected_outcome": "escalation",
                "objection_count": 4,
                "context": "Агрессивно настроенный клиент с претензиями к цене и прошлому опыту"
            }
        ]
    },
    
    ClientType.PROFESSIONAL: {
        "name": "Профессиональный логист",
        "description": "Знает рынок, профессиональные вопросы",
        "conversations": [
            {
                "scenario_id": "professional_001", 
                "client_messages": [
                    "Цена рыночная, но как с документооборотом?",
                    "Нужна полная отчетность - ТТН, счета-фактуры.",
                    "Работаете через ЭДО? У нас Диадок.",
                    "Отлично, тогда можем начинать сотрудничество."
                ],
                "expected_outcome": "agreement",
                "objection_count": 0,
                "context": "Профессиональный логист уточняет рабочие процессы"
            },
            {
                "scenario_id": "professional_002",
                "client_messages": [
                    "По цене устраивает, но нужно в тендер включить.",
                    "Пришлите коммерческое предложение на фирменном бланке.",
                    "Решение будет через неделю после тендера."
                ],
                "expected_outcome": "formal_process",
                "objection_count": 0,
                "context": "Крупная компания с формальными процедурами"
            }
        ]
    },
    
    ClientType.HESITANT: {
        "name": "Нерешительный клиент",  
        "description": "Долго думает, откладывает решение",
        "conversations": [
            {
                "scenario_id": "hesitant_001",
                "client_messages": [
                    "Нужно подумать, это серьезное решение.",
                    "А может в следующем месяце лучше отправить?",
                    "Сколько времени у меня есть на раздумья?",
                    "Ладно, решились - давайте оформляйте."
                ],
                "expected_outcome": "agreement",
                "objection_count": 3,
                "context": "Клиент колеблется в принятии решения, но цена его устраивает"
            },
            {
                "scenario_id": "hesitant_002",
                "client_messages": [
                    "Хм, а может еще поискать варианты?",
                    "Не уверен что сейчас подходящее время.",
                    "Перезвоню через пару дней, хорошо?"
                ],
                "expected_outcome": "postponement",
                "objection_count": 3,
                "context": "Клиент откладывает решение на потом"
            }
        ]
    },
}

# Отдельные возражения для тестирования классификатора
INDIVIDUAL_OBJECTIONS = [
    # Ценовые возражения
    {"message": "Дорого", "intent": "price_objection", "subtype": "too_expensive"},
    {"message": "Цена не устраивает", "intent": "price_objection", "subtype": "too_expensive"},
    {"message": "Раньше дешевле было", "intent": "price_objection", "subtype": "past_cheaper"},
    {"message": "У конкурентов дешевле", "intent": "price_objection", "subtype": "competitor_cheaper"},
    {"message": "Бюджет не позволяет", "intent": "price_objection", "subtype": "budget_limit"},
    {"message": "Можете скидку?", "intent": "price_objection", "subtype": "discount_request"},
    
    # Согласие
    {"message": "Да, согласен", "intent": "agreement", "subtype": None},
    {"message": "Подходит", "intent": "agreement", "subtype": None},
    {"message": "Беру", "intent": "agreement", "subtype": None}, 
    {"message": "Оформляем", "intent": "agreement", "subtype": None},
    {"message": "Договорились", "intent": "agreement", "subtype": None},
    
    # Отказ
    {"message": "Нет, не подходит", "intent": "rejection", "subtype": "direct_no"},
    {"message": "Не интересно", "intent": "rejection", "subtype": "not_interested"},
    {"message": "Отказываемся", "intent": "rejection", "subtype": "direct_no"},
    {"message": "Нам не нужно", "intent": "rejection", "subtype": "not_needed"},
    
    # Запрос информации
    {"message": "Расскажите подробнее", "intent": "information_request", "subtype": "details"},
    {"message": "Какие гарантии?", "intent": "information_request", "subtype": "guarantees"},
    {"message": "Сроки доставки?", "intent": "information_request", "subtype": "timing"},
    {"message": "Документы есть?", "intent": "information_request", "subtype": "documents"},
    
    # Запрос руководителя
    {"message": "Дайте руководителя", "intent": "manager_request", "subtype": None},
    {"message": "Хочу с начальником", "intent": "manager_request", "subtype": None},
    {"message": "Вызовите менеджера", "intent": "manager_request", "subtype": None},
    
    # Неясные намерения
    {"message": "Хм...", "intent": "unclear", "subtype": None},
    {"message": "Не знаю", "intent": "unclear", "subtype": None},
    {"message": "Посмотрим", "intent": "unclear", "subtype": None}
]

def get_scenario_by_id(scenario_id: str) -> Dict:
    """Получить сценарий по ID"""
    for client_type, data in CLIENT_DIALOG_SCENARIOS.items():
        for conversation in data["conversations"]:
            if conversation["scenario_id"] == scenario_id:
                return {
                    "client_type": client_type,
                    "client_name": data["name"],
                    "scenario": conversation
                }
    return None

def get_scenarios_by_client_type(client_type: ClientType) -> List[Dict]:
    """Получить все сценарии для типа клиента"""
    return CLIENT_DIALOG_SCENARIOS.get(client_type, {}).get("conversations", [])

def get_random_scenario():
    """Возвращает случайный сценарий диалога с клиентом"""
    import random
    
    # Выбираем случайный тип клиента  
    client_type = random.choice(list(ClientType))
    
    # Пропускаем типы клиентов без сценариев
    if client_type not in CLIENT_DIALOG_SCENARIOS:
        client_type = ClientType.EASY_CLIENT
    
    # Выбираем случайный диалог для этого типа клиента
    conversations = CLIENT_DIALOG_SCENARIOS[client_type]["conversations"]
    conversation = random.choice(conversations)
    
    return client_type, {
        "client_messages": conversation["client_messages"],
        "expected_outcome": conversation["expected_outcome"],
        "objection_count": conversation["objection_count"],
        "context": conversation.get("context", "Стандартный диалог с клиентом"),
        "client_type_name": CLIENT_DIALOG_SCENARIOS[client_type]["name"],
        "client_description": CLIENT_DIALOG_SCENARIOS[client_type]["description"],
        "scenario_id": conversation["scenario_id"]
    }

def get_objections_by_intent(intent: str) -> List[Dict]:
    """Получить возражения по типу намерения"""
    return [obj for obj in INDIVIDUAL_OBJECTIONS if obj["intent"] == intent] 