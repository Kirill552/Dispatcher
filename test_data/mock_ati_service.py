# -*- coding: utf-8 -*-
"""
Мок-сервис для замены реальных АТИ API вызовов
Использует синтетические данные для тестирования без реальных запросов к АТИ
"""

import asyncio
import random
from typing import List, Dict, Optional
from datetime import datetime

from synthetic_cargo_data import (
    SYNTHETIC_CARGOS, EXPIRED_CARGO, ARCHIVED_CARGO,
    get_synthetic_cargo_by_id, get_random_cargo
)
from synthetic_offers_data import (
    get_offers_for_cargo, get_best_offer, SYNTHETIC_CARRIERS
)

class MockATIService:
    """Мок-сервис для эмуляции АТИ API"""
    
    def __init__(self):
        self.is_mock_mode = True
        self.delay_simulation = True  # Симулируем задержки API
        self.api_call_count = 0
        
        # Внутреннее состояние для симуляции
        self._monitoring_sessions = {}
        self._created_cargos = []
        
    async def get_all_company_loads(self) -> List[Dict]:
        """Мок: получение всех грузов компании"""
        await self._simulate_api_delay(0.5, 1.5)
        self.api_call_count += 1
        
        # Возвращаем все синтетические грузы + случайные неопределенные
        loads = SYNTHETIC_CARGOS.copy()
        
        # Добавляем несколько случайных "не наших" грузов для проверки фильтрации
        other_loads = [
            {
                "Id": "other-cargo-001",
                "ExternalId": "OTHER_001",  # Не начинается с AI_
                "Number": "O001",
                "CargoName": "Чужой груз 1",
                "FromCityName": "Москва",
                "ToCityName": "Казань",
                "IsArchived": False
            },
            {
                "Id": "other-cargo-002", 
                "ExternalId": "",  # Пустой external_id
                "Number": "O002",
                "CargoName": "Чужой груз 2",
                "FromCityName": "СПб",
                "ToCityName": "Москва",
                "IsArchived": False
            }
        ]
        
        loads.extend(other_loads)
        
        # Иногда добавляем просроченный/архивный груз для проверки фильтрации
        if random.random() < 0.3:
            loads.append(EXPIRED_CARGO)
        if random.random() < 0.2:
            loads.append(ARCHIVED_CARGO)
            
        return loads
    
    async def get_cargo_responses_new(self, cargo_id: str) -> List[Dict]:
        """Мок: получение встречных предложений для груза"""
        await self._simulate_api_delay(0.3, 1.0)
        self.api_call_count += 1
        
        # Находим данные груза
        cargo_data = get_synthetic_cargo_by_id(cargo_id)
        if not cargo_data:
            return []
            
        # Получаем предложения для груза
        offers = get_offers_for_cargo(cargo_id, cargo_data)
        
        # Симулируем постепенное поступление предложений
        # В первый раз может быть меньше предложений
        session_key = f"offers_count_{cargo_id}"
        current_count = self._monitoring_sessions.get(session_key, 0)
        
        if current_count == 0:
            # Первый раз - только 1-2 предложения
            visible_offers = offers[:random.randint(1, 2)]
            self._monitoring_sessions[session_key] = len(visible_offers)
        elif current_count < len(offers):
            # Постепенно добавляем больше предложений
            new_count = min(len(offers), current_count + random.randint(1, 2))
            visible_offers = offers[:new_count]
            self._monitoring_sessions[session_key] = new_count
        else:
            # Все предложения уже доступны
            visible_offers = offers
            
        return visible_offers
    
    async def get_cargo_responses(self, cargo_id: str) -> List[Dict]:
        """Мок: альтернативный метод получения предложений (совместимость)"""
        return await self.get_cargo_responses_new(cargo_id)
    
    async def create_cargo_request(self, cargo_data: Dict) -> tuple[bool, Dict]:
        """Мок: создание заявки на груз"""
        await self._simulate_api_delay(1.0, 2.0)
        self.api_call_count += 1
        
        # Генерируем ID нового груза
        new_cargo_id = f"test-cargo-{len(self._created_cargos) + 100:03d}"
        
        # Создаем объект груза
        created_cargo = {
            "Id": new_cargo_id,
            "ExternalId": f"AI_TEST_{len(self._created_cargos) + 100:03d}",
            "Number": f"T{len(self._created_cargos) + 100:03d}",
            "CargoName": cargo_data.get('cargo_description', 'Тестовый груз'),
            "FromCityName": cargo_data.get('loading_city_name', 'Москва'),
            "ToCityName": cargo_data.get('unloading_city_name', 'СПб'),
            "Weight": cargo_data.get('weight', 10000),
            "Volume": cargo_data.get('volume', 30),
            "DateAdded": datetime.now().isoformat() + "Z",
            "LastDate": (datetime.now()).isoformat() + "Z",
            "IsArchived": False,
            "Payment": {
                "FixedRate": False,
                "Torg": True,
                "RateSum": 0
            }
        }
        
        self._created_cargos.append(created_cargo)
        
        # Успешный результат
        return True, {
            "cargo_id": new_cargo_id,
            "status": "created", 
            "message": "Груз успешно создан"
        }
    
    async def get_city_by_id(self, city_id: int) -> Optional[Dict]:
        """Мок: получение данных города по ID"""
        await self._simulate_api_delay(0.1, 0.3)
        self.api_call_count += 1
        
        # Простой маппинг основных городов
        cities = {
            1: {"Name": "Москва", "Region": "Московская область"},
            2: {"Name": "Санкт-Петербург", "Region": "Ленинградская область"},
            43: {"Name": "Казань", "Region": "Республика Татарстан"},
            56: {"Name": "Екатеринбург", "Region": "Свердловская область"},
            67: {"Name": "Новосибирск", "Region": "Новосибирская область"},
            39: {"Name": "Ростов-на-Дону", "Region": "Ростовская область"},
            77: {"Name": "Челябинск", "Region": "Челябинская область"},
            33: {"Name": "Воронеж", "Region": "Воронежская область"},
            47: {"Name": "Нижний Новгород", "Region": "Нижегородская область"},
            35: {"Name": "Краснодар", "Region": "Краснодарский край"}
        }
        
        return cities.get(city_id)
    
    async def _simulate_api_delay(self, min_delay: float = 0.1, max_delay: float = 0.5):
        """Симуляция задержки API для реалистичности"""
        if self.delay_simulation:
            delay = random.uniform(min_delay, max_delay)
            await asyncio.sleep(delay)
    
    def reset_state(self):
        """Сброс состояния мок-сервиса для нового теста"""
        self._monitoring_sessions.clear()
        self._created_cargos.clear()
        self.api_call_count = 0
    
    def get_stats(self) -> Dict:
        """Получить статистику работы мок-сервиса"""
        return {
            "api_calls_made": self.api_call_count,
            "created_cargos": len(self._created_cargos),
            "monitoring_sessions": len(self._monitoring_sessions),
            "is_mock_mode": self.is_mock_mode
        }
    
    def simulate_new_offers(self, cargo_id: str, additional_offers: int = 1):
        """Симуляция поступления новых предложений"""
        session_key = f"offers_count_{cargo_id}"
        current_count = self._monitoring_sessions.get(session_key, 0)
        self._monitoring_sessions[session_key] = current_count + additional_offers
    
    def get_monitoring_session_status(self, cargo_id: str) -> Dict:
        """Получить статус сессии мониторинга"""
        session_key = f"offers_count_{cargo_id}"
        offers_count = self._monitoring_sessions.get(session_key, 0)
        
        return {
            "cargo_id": cargo_id,
            "offers_count": offers_count,
            "status": "monitoring" if offers_count < 3 else "ready_for_sale"
        }

# Глобальный экземпляр мок-сервиса
mock_ati_service = MockATIService()

def patch_ati_client_for_testing():
    """Функция для подмены реального ATI клиента мок-сервисом"""
    import sys
    from unittest.mock import AsyncMock, patch
    
    # Создаем мок-класс
    class MockATIClient:
        def __init__(self):
            self.mock_service = mock_ati_service
            
        async def get_all_company_loads(self):
            return await self.mock_service.get_all_company_loads()
            
        async def get_cargo_responses_new(self, cargo_id: str):
            return await self.mock_service.get_cargo_responses_new(cargo_id)
            
        async def get_cargo_responses(self, cargo_id: str):
            return await self.mock_service.get_cargo_responses(cargo_id)
            
        async def create_cargo_request(self, cargo_data: Dict):
            return await self.mock_service.create_cargo_request(cargo_data)
            
        async def get_city_by_id(self, city_id: int):
            return await self.mock_service.get_city_by_id(city_id)
    
    return MockATIClient()

def enable_mock_mode():
    """Включить тестовый режим с мок-данными"""
    mock_ati_service.is_mock_mode = True
    mock_ati_service.reset_state()
    
def disable_mock_mode():
    """Выключить тестовый режим"""
    mock_ati_service.is_mock_mode = False 