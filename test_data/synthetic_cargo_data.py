# -*- coding: utf-8 -*-
"""
Синтетические данные грузов для автотестирования
Реалистичные грузы с разными параметрами для проверки логики ИИ-диспетчера
"""

from datetime import datetime, timedelta
from typing import List, Dict

# Синтетические грузы для тестирования
SYNTHETIC_CARGOS: List[Dict] = [
    {
        "Id": "test-cargo-001",
        "ExternalId": "AI_TEST_001", 
        "Number": "T001",
        "CargoName": "Стройматериалы (кирпич)",
        "FromCityName": "Москва",
        "ToCityName": "Санкт-Петербург",
        "Weight": 15000,  # 15 тонн
        "Volume": 25.0,   # 25 м³
        "DateAdded": (datetime.now() - timedelta(hours=2)).isoformat() + "Z",
        "LastDate": (datetime.now() + timedelta(days=3)).isoformat() + "Z",
        "IsArchived": False,
        "Payment": {
            "FixedRate": False,
            "Torg": True,
            "RateSum": 0
        },
        "Loading": {
            "CityId": 1,
            "TimeStart": None,
            "TimeEnd": None,
            "IsRoundTheClock": True
        },
        "Unloading": {
            "CityId": 2,
            "TimeStart": None, 
            "TimeEnd": None,
            "IsRoundTheClock": False
        },
        "Transport": {
            "CarType": 1,  # Тент
            "TrucksQuantity": 1
        }
    },
    {
        "Id": "test-cargo-002",
        "ExternalId": "AI_TEST_002",
        "Number": "T002", 
        "CargoName": "Продукты питания (замороженные)",
        "FromCityName": "Екатеринбург",
        "ToCityName": "Новосибирск",
        "Weight": 8500,   # 8.5 тонн
        "Volume": 35.0,   # 35 м³
        "DateAdded": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",
        "LastDate": (datetime.now() + timedelta(days=2)).isoformat() + "Z",
        "IsArchived": False,
        "Payment": {
            "FixedRate": False,
            "Torg": True,
            "RateSum": 0
        },
        "Loading": {
            "CityId": 56,
            "TimeStart": "09:00:00",
            "TimeEnd": "17:00:00",
            "IsRoundTheClock": False
        },
        "Unloading": {
            "CityId": 67,
            "TimeStart": "08:00:00",
            "TimeEnd": "18:00:00", 
            "IsRoundTheClock": False
        },
        "Transport": {
            "CarType": 4,  # Рефрижератор
            "TrucksQuantity": 1,
            "TemperatureFrom": -18,
            "TemperatureTo": -15
        }
    },
    {
        "Id": "test-cargo-003",
        "ExternalId": "AI_TEST_003",
        "Number": "T003",
        "CargoName": "Мебель и товары для дома",
        "FromCityName": "Казань", 
        "ToCityName": "Ростов-на-Дону",
        "Weight": 12000,  # 12 тонн
        "Volume": 45.0,   # 45 м³
        "DateAdded": (datetime.now() - timedelta(minutes=30)).isoformat() + "Z",
        "LastDate": (datetime.now() + timedelta(days=5)).isoformat() + "Z",
        "IsArchived": False,
        "Payment": {
            "FixedRate": False,
            "Torg": True,
            "RateSum": 0
        },
        "Loading": {
            "CityId": 43,
            "TimeStart": "10:00:00",
            "TimeEnd": "16:00:00",
            "IsRoundTheClock": False
        },
        "Unloading": {
            "CityId": 39,
            "TimeStart": "09:00:00",
            "TimeEnd": "17:00:00",
            "IsRoundTheClock": False
        },
        "Transport": {
            "CarType": 1,  # Тент
            "TrucksQuantity": 1
        }
    },
    {
        "Id": "test-cargo-004",
        "ExternalId": "AI_TEST_004", 
        "Number": "T004",
        "CargoName": "Металлоизделия",
        "FromCityName": "Челябинск",
        "ToCityName": "Воронеж",
        "Weight": 20000,  # 20 тонн (максимум)
        "Volume": 15.0,   # 15 м³ (тяжелый груз)
        "DateAdded": (datetime.now() - timedelta(hours=3)).isoformat() + "Z",
        "LastDate": (datetime.now() + timedelta(days=1)).isoformat() + "Z",
        "IsArchived": False,
        "Payment": {
            "FixedRate": False,
            "Torg": True,
            "RateSum": 0
        },
        "Loading": {
            "CityId": 77,
            "TimeStart": "08:00:00",
            "TimeEnd": "20:00:00",
            "IsRoundTheClock": False
        },
        "Unloading": {
            "CityId": 33,
            "TimeStart": "08:00:00",
            "TimeEnd": "18:00:00",
            "IsRoundTheClock": False
        },
        "Transport": {
            "CarType": 2,  # Открытая платформа
            "TrucksQuantity": 1,
            "LoadingType": 1,  # Кран
            "UnloadingType": 1
        }
    },
    {
        "Id": "test-cargo-005",
        "ExternalId": "AI_TEST_005",
        "Number": "T005",
        "CargoName": "Текстиль и одежда",
        "FromCityName": "Нижний Новгород",
        "ToCityName": "Краснодар", 
        "Weight": 3500,   # 3.5 тонны (легкий груз)
        "Volume": 60.0,   # 60 м³ (объемный)
        "DateAdded": (datetime.now() - timedelta(minutes=45)).isoformat() + "Z",
        "LastDate": (datetime.now() + timedelta(days=4)).isoformat() + "Z",
        "IsArchived": False,
        "Payment": {
            "FixedRate": False,
            "Torg": True,
            "RateSum": 0
        },
        "Loading": {
            "CityId": 47,
            "TimeStart": "09:00:00",
            "TimeEnd": "18:00:00",
            "IsRoundTheClock": False
        },
        "Unloading": {
            "CityId": 35,
            "TimeStart": "10:00:00",
            "TimeEnd": "17:00:00",
            "IsRoundTheClock": False
        },
        "Transport": {
            "CarType": 1,  # Тент
            "TrucksQuantity": 1
        }
    }
]

# Дополнительные тестовые грузы для разных сценариев
EXPIRED_CARGO = {
    "Id": "test-cargo-expired",
    "ExternalId": "AI_TEST_EXPIRED",
    "Number": "TEXP",
    "CargoName": "Просроченный груз",
    "FromCityName": "Москва",
    "ToCityName": "Казань",
    "Weight": 5000,
    "Volume": 20.0,
    "DateAdded": (datetime.now() - timedelta(days=2)).isoformat() + "Z",
    "LastDate": (datetime.now() - timedelta(hours=1)).isoformat() + "Z",  # Просрочен
    "IsArchived": False
}

ARCHIVED_CARGO = {
    "Id": "test-cargo-archived",
    "ExternalId": "AI_TEST_ARCHIVED", 
    "Number": "TARCH",
    "CargoName": "Архивный груз",
    "FromCityName": "Москва",
    "ToCityName": "Казань",
    "Weight": 5000,
    "Volume": 20.0,
    "DateAdded": (datetime.now() - timedelta(days=1)).isoformat() + "Z",
    "LastDate": (datetime.now() + timedelta(days=2)).isoformat() + "Z",
    "IsArchived": True  # В архиве
}

def get_synthetic_cargo_by_id(cargo_id: str) -> Dict:
    """Получить синтетический груз по ID"""
    for cargo in SYNTHETIC_CARGOS:
        if cargo["Id"] == cargo_id:
            return cargo
    
    # Проверяем специальные грузы
    if cargo_id == "test-cargo-expired":
        return EXPIRED_CARGO
    elif cargo_id == "test-cargo-archived":
        return ARCHIVED_CARGO
        
    return None

def get_random_cargo() -> Dict:
    """Получить случайный груз для тестирования"""
    import random
    return random.choice(SYNTHETIC_CARGOS) 