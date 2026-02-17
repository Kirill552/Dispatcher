#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Новый клиент для работы с ATI.SU API v2
Основан на успешном тесте test_cargo_final.py
"""

import requests
import json
import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("ATI_CLIENT_V2")


class ATIClientV2:
    """Клиент для работы с ATI.SU API v2"""
    
    def __init__(self):
        self.api_base = "https://api.ati.su"
        self.token = settings.ati_api_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ati_integrator_ai_dispatcher"
        }
        self._contact_id = None
        self._body_types_cache = None
        
    async def get_city_id(self, city_name: str) -> Tuple[Optional[int], Optional[Dict]]:
        """Получить ID города через автокомплит"""
        url = f"{self.api_base}/gw/gis-dict/v1/autocomplete/suggestions"
        
        data = {
            "prefix": city_name,
            "suggestion_types": 1,  # Населённый пункт
            "limit": 5,
            "country_id": 1  # Россия
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=data)
            logger.info(f"🔍 Поиск города {city_name}: статус {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("suggestions"):
                    suggestion = result["suggestions"][0]
                    city_data = suggestion.get("city", {})
                    if city_data:
                        logger.info(f"✅ Найден: {city_data['name']}, {suggestion.get('region', {}).get('name', 'N/A')}")
                        return city_data["id"], city_data
            
            logger.warning(f"❌ Город {city_name} не найден")
            return None, None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска города {city_name}: {e}")
            return None, None

    async def get_contact_id(self) -> Optional[int]:
        """Получить ID контакта для создания грузов"""
        if self._contact_id is not None:
            return self._contact_id
            
        # 1. Пробуем получить все контакты фирмы
        url_contacts = f"{self.api_base}/v1.0/firms/contacts"
        try:
            response = requests.get(url_contacts, headers=self.headers)
            logger.info(f"📥 Статус ответа /v1.0/firms/contacts: {response.status_code}")
            
            if response.status_code == 200:
                contacts = response.json()
                if contacts and len(contacts) > 0:
                    # Ищем видимый контакт
                    for contact in contacts:
                        if contact.get("is_visible", False) and not contact.get("is_deleted", False):
                            contact_id = contact.get("id")
                            if contact_id is not None:  # ID может быть 0!
                                logger.info(f"✅ Найден видимый контакт ID: {contact_id} (имя: {contact.get('name', 'N/A')})")
                                self._contact_id = contact_id
                                return contact_id
                    
                    # Если нет видимых, берем первый
                    contact_id = contacts[0].get("id")
                    if contact_id is not None:  # ID может быть 0!
                        logger.info(f"✅ Найден первый контакт ID: {contact_id}")
                        self._contact_id = contact_id
                        return contact_id
        except Exception as e:
            logger.error(f"❌ Ошибка получения контактов: {e}")
        
        # 2. Пробуем получить текущий контакт
        url_contact = f"{self.api_base}/v1.0/firms/contact"
        try:
            response = requests.get(url_contact, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                contact_id = data.get("id")
                if contact_id is not None:  # ID может быть 0!
                    logger.info(f"✅ Найден текущий контакт ID: {contact_id}")
                    self._contact_id = contact_id
                    return contact_id
        except Exception as e:
            logger.error(f"❌ Ошибка получения текущего контакта: {e}")
        
        logger.error("❌ Не удалось получить ID контакта")
        return None

    async def get_body_types(self) -> Dict[str, int]:
        """Получить словарь типов кузовов"""
        if self._body_types_cache:
            return self._body_types_cache
            
        url = f"{self.api_base}/v1.0/dictionaries/carTypes"
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                car_types = response.json()
                
                # Создаем словарь название -> TypeId
                body_types = {}
                for car_type in car_types:
                    name = car_type.get('Name', '').lower()
                    type_id = car_type.get('TypeId')
                    if name and type_id:
                        body_types[name] = type_id
                
                self._body_types_cache = body_types
                logger.info(f"✅ Загружено {len(body_types)} типов кузовов")
                return body_types
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения типов кузовов: {e}")
        
        # Возвращаем базовые типы если API недоступен
        return {
            "тентованный": 200,
            "бортовой": 1100,
            "рефрижератор": 300,
            "фургон": 500,
            "контейнер": 100
        }

    def select_body_type(self, cargo_type: str, cargo_description: str = "") -> int:
        """Выбрать подходящий тип кузова на основе типа груза"""
        cargo_lower = f"{cargo_type} {cargo_description}".lower()
        
        # Правила выбора кузова
        if any(word in cargo_lower for word in ['мебель', 'бытовая техника', 'электроника', 'одежда']):
            return 500  # фургон
        elif any(word in cargo_lower for word in ['продукты', 'мясо', 'рыба', 'молоко', 'заморозка']):
            return 300  # рефрижератор
        elif any(word in cargo_lower for word in ['металл', 'трубы', 'профиль', 'арматура', 'пиломатериал']):
            return 1100  # бортовой
        elif any(word in cargo_lower for word in ['контейнер', 'паллет']):
            return 100  # контейнер
        else:
            return 200  # тентованный (универсальный)

    async def create_cargo_request(self, order_data: Dict) -> Tuple[bool, Dict]:
        """
        Создать груз с запросом ставки на ATI.SU
        
        Args:
            order_data: Данные заказа от клиента
            
        Returns:
            Tuple[success, result_data]
        """
        try:
            logger.info(f"🚀 Создаем груз на ATI.SU: {order_data.get('cargo_description', 'N/A')}")
            
            # Данные уже должны быть подготовлены в правильном формате
            # Проверяем обязательные поля
            required_fields = ['contact_id', 'loading_city_id', 'unloading_city_id', 'cargo_description', 'weight', 'volume', 'loading_date']
            for field in required_fields:
                if field not in order_data:
                    return False, {"error": f"Отсутствует обязательное поле: {field}"}
            
            # Формируем данные груза согласно документации ATI API v1.0
            cargo_data = {
                # ОБЯЗАТЕЛЬНЫЕ ПОЛЯ
                "contact_id": order_data["contact_id"],
                "loading_city_id": order_data["loading_city_id"],
                "unloading_city_id": order_data["unloading_city_id"],
                "cargo_description": order_data["cargo_description"],
                "weight": order_data["weight"],
                "volume": order_data["volume"],
                "loading_date": order_data["loading_date"],
                
                # ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ
                "body_type_id": order_data.get("body_type_id", 1100),  # Бортовой по умолчанию
                "loading_type_id": order_data.get("loading_type_id", 1),  # 1 - ручная загрузка
                "unloading_type_id": order_data.get("unloading_type_id", 1),  # 1 - ручная разгрузка
                
                # КОНТАКТНАЯ ИНФОРМАЦИЯ
                "contact_person": order_data.get("contact_person", ""),
                "contact_phone": order_data.get("contact_phone", ""),
                
                # АДРЕСА
                "loading_address": order_data.get("loading_address", ""),
                "unloading_address": order_data.get("unloading_address", ""),
                
                # ВРЕМЕННЫЕ РАМКИ
                "loading_time_from": order_data.get("loading_time_from", "09:00"),
                "loading_time_to": order_data.get("loading_time_to", "18:00"),
                "loading_readiness_type": order_data.get("loading_readiness_type", "ready"),
                "loading_date_from": order_data.get("loading_date_from"),
                "loading_date_to": order_data.get("loading_date_to"),
                
                # ТИП ЗАГРУЗКИ
                "load_type": order_data.get("load_type", "ftl"),
                
                # ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ
                "notes": order_data.get("notes", ""),
                
                # РАЗМЕРЫ (если указаны)
                "length": order_data.get("length"),
                "width": order_data.get("width"),
                "height": order_data.get("height"),
                
                # НАСТРОЙКИ ОПЛАТЫ
                "payment_type": order_data.get("payment_type", "rate-request"),
                "currency_id": 1,  # RUB
                "hide_counter_offers": False,
                "direct_offer": False,
                
                # СТАВКИ (если указаны)
                "rate_with_vat": order_data.get("rate_amount") if order_data.get("payment_type") == "rate_with_vat" else None,
                "rate_without_vat": order_data.get("rate_amount") if order_data.get("payment_type") == "rate_without_vat" else None,
                "cash": order_data.get("rate_amount") if order_data.get("payment_type") == "cash" else None,
                
                # ПУБЛИКАЦИЯ
                "publication_mode": "now",
                "boards": ["ati"]  # Публикуем на ATI.SU
            }
            
            # Убираем None значения
            cargo_data = {k: v for k, v in cargo_data.items() if v is not None}
            
            logger.info(f"📦 Отправляем данные в ATI API:")
            for key, value in cargo_data.items():
                logger.info(f"   📌 {key}: {value}")
            
            # Создаем правильную структуру для API v2/cargos согласно документации
            api_payload = {
                "cargo_application": {
                    # external_id нужен для: 1) связи груза с нашей системой, 2) статистики, 3) поиска в логах
                    "external_id": f"AI_{int(time.time())}",
                    "route": {
                        "loading": {
                            "location": {
                                "type": "manual",
                                "city_id": cargo_data["loading_city_id"],
                                "address": cargo_data.get("loading_address", "")
                            },
                            "dates": self._build_loading_dates(cargo_data),
                            "cargos": [{
                                "id": 1,
                                "name": cargo_data["cargo_description"],
                                "weight": {
                                    "type": "kilos",
                                    "quantity": cargo_data["weight"]
                                },
                                "volume": {
                                    "quantity": cargo_data["volume"]
                                },
                                "sizes": {
                                    "length": {"value": cargo_data.get("length", 4.0)},
                                    "width": {"value": cargo_data.get("width", 2.0)},
                                    "height": {"value": cargo_data.get("height", 1.0)}
                                }
                            }]
                        },
                        "unloading": {
                            "location": {
                                "type": "manual",
                                "city_id": cargo_data["unloading_city_id"],
                                "address": cargo_data.get("unloading_address", "")
                            }
                        }
                    },
                    "truck": {
                        "trucks_count": 1,
                        "load_type": cargo_data.get("load_type", "ftl"),
                        "body_types": [cargo_data["body_type_id"]],
                        **({
                            "body_loading": cargo_data["body_loading"]
                        } if cargo_data.get("body_loading") else {
                            "body_loading": {
                                "types": [cargo_data.get("loading_type_id", 1)],
                                "is_all_required": False
                            }
                        }),
                        **({
                            "body_unloading": cargo_data["body_unloading"]
                        } if cargo_data.get("body_unloading") else {
                            "body_unloading": {
                                "types": [cargo_data.get("unloading_type_id", 1)],
                                "is_all_required": False
                            }
                        })
                    },
                    "payment": {
                        "type": cargo_data.get("payment_type", "rate-request"),
                        "currency_type": cargo_data.get("currency_id", 1),
                        "hide_counter_offers": cargo_data.get("hide_counter_offers", False),
                        "direct_offer": cargo_data.get("direct_offer", False),
                        # Устанавливаем доступность ставок на основе payment_type
                        "cash_available": cargo_data.get("payment_type") == "cash",
                        "rate_with_nds_available": cargo_data.get("payment_type") == "rate_with_vat",
                        "rate_without_nds_available": cargo_data.get("payment_type") == "rate_without_vat",
                        # Если ни один тип не выбран, разрешаем все типы ставок
                        **({
                            "cash_available": True,
                            "rate_with_nds_available": True,
                            "rate_without_nds_available": True
                        } if cargo_data.get("payment_type") == "rate-request" else {}),
                        # Добавляем конкретные суммы если есть
                        "rate_with_vat": cargo_data.get("rate_with_vat"),
                        "rate_without_vat": cargo_data.get("rate_without_vat"),
                        "cash": cargo_data.get("cash")
                    },
                    "boards": [{
                        "id": "a0a0a0a0a0a0a0a0a0a0a0a0",  # ID общей площадки ATI.SU
                        "publication_mode": cargo_data.get("publication_mode", "now"),
                        "publication_time": "1970-01-01T00:00:00.000Z",
                        "cancel_publish_on_auction_bet": False,
                        "reservation_enabled": False
                    }],
                    "note": cargo_data.get("notes", ""),
                    "contacts": [cargo_data["contact_id"]]
                }
            }

            logger.info(f"🔧 Структура API payload для v2/cargos:")
            logger.info(f"   📌 external_id: {api_payload['cargo_application']['external_id']}")
            logger.info(f"   📌 loading_city_id: {api_payload['cargo_application']['route']['loading']['location']['city_id']}")
            logger.info(f"   📌 unloading_city_id: {api_payload['cargo_application']['route']['unloading']['location']['city_id']}")
            logger.info(f"   📌 cargo_name: {api_payload['cargo_application']['route']['loading']['cargos'][0]['name']}")
            logger.info(f"   📌 weight: {api_payload['cargo_application']['route']['loading']['cargos'][0]['weight']['quantity']} кг")
            logger.info(f"   📌 body_types: {api_payload['cargo_application']['truck']['body_types']}")
            logger.info(f"   📌 boards: {[b['id'] for b in api_payload['cargo_application']['boards']]}")
            logger.info(f"   📅 dates: {api_payload['cargo_application']['route']['loading']['dates']}")
            logger.info(f"   💰 payment: {api_payload['cargo_application']['payment']}")

            # Отправляем запрос на создание груза
            url = f"{self.api_base}/v2/cargos"
            response = requests.post(url, headers=self.headers, json=api_payload)
            
            logger.info(f"📥 Статус создания груза: {response.status_code}")
            logger.info(f"📄 Ответ сервера: {response.text[:500]}...")
            
            if response.status_code in [200, 201, 202]:
                try:
                    result = response.json()
                    
                    # Извлекаем ID груза из ответа v2/cargos
                    cargo_app = result.get("cargo_application", {})
                    cargo_id = cargo_app.get("cargo_application_id") or cargo_app.get("cargo_id")
                    cargo_number = cargo_app.get("cargo_application_number") or cargo_app.get("cargo_number")
                    
                    success_data = {
                        "cargo_id": cargo_id,
                        "cargo_number": cargo_number,
                        "loading_city": order_data.get("loading_city_name", ""),
                        "unloading_city": order_data.get("unloading_city_name", ""),
                        "body_type_id": cargo_data["body_type_id"],
                        "created_at": datetime.now().isoformat(),
                        "ati_response": result
                    }
                    
                    logger.info(f"✅ Груз создан успешно!")
                    logger.info(f"🆔 ID груза: {cargo_id}")
                    logger.info(f"📋 Номер груза: {cargo_number}")
                    return True, success_data
                    
                except Exception as json_error:
                    logger.error(f"❌ Ошибка парсинга JSON ответа: {json_error}")
                    return False, {"error": f"Ошибка парсинга ответа: {json_error}", "response": response.text}
            else:
                try:
                    error_data = response.json()
                    logger.error(f"❌ Ошибка создания груза: {error_data}")
                    return False, error_data
                except:
                    error_text = response.text
                    logger.error(f"❌ Ошибка создания груза: {error_text}")
                    return False, {"error": error_text, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"❌ Исключение при создании груза: {e}")
            return False, {"error": str(e)}

    async def get_cargo_responses(self, cargo_id: str) -> List[Dict]:
        """Получить встречные предложения на груз"""
        url = f"{self.api_base}/v1.0/loads/new/responses"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                all_responses = response.json()
                
                # Фильтруем отклики только на наш груз
                cargo_responses = [
                    resp for resp in all_responses 
                    if resp.get("LoadId") == cargo_id
                ]
                
                logger.info(f"📨 Получено {len(cargo_responses)} откликов на груз {cargo_id}")
                return cargo_responses
            else:
                logger.error(f"❌ Ошибка получения откликов: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса откликов: {e}")
            return []

    async def get_best_offer(self, cargo_id: str, wait_time: int = 3600) -> Optional[Dict]:
        """
        Ждать и выбрать лучшее предложение
        
        Args:
            cargo_id: ID груза на ATI.SU
            wait_time: Время ожидания в секундах (по умолчанию 1 час)
            
        Returns:
            Лучшее предложение или None
        """
        logger.info(f"⏳ Ожидаем предложения на груз {cargo_id} в течение {wait_time} секунд")
        
        best_offer = None
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < wait_time:
            responses = await self.get_cargo_responses(cargo_id)
            
            if responses:
                # Сортируем по цене (самая низкая первая)
                sorted_responses = sorted(
                    responses, 
                    key=lambda x: x.get("Price", float('inf'))
                )
                
                current_best = sorted_responses[0]
                
                if not best_offer or current_best.get("Price", 0) < best_offer.get("Price", float('inf')):
                    best_offer = current_best
                    logger.info(f"💰 Новое лучшее предложение: {best_offer.get('Price')} руб от {best_offer.get('FirmName')}")
            
            # Ждем 5 минут перед следующей проверкой
            await asyncio.sleep(300)
        
        if best_offer:
            logger.info(f"🏆 Лучшее предложение: {best_offer.get('Price')} руб")
        else:
            logger.warning(f"😞 Предложений на груз {cargo_id} не поступило")
            
        return best_offer

    async def calculate_client_price(self, carrier_price: float, markup_percent: float = 40.0) -> Dict:
        """
        Рассчитать цену для клиента с наценкой
        
        Args:
            carrier_price: Цена от перевозчика
            markup_percent: Процент наценки (по умолчанию 40%)
            
        Returns:
            Данные о ценообразовании
        """
        markup_amount = carrier_price * (markup_percent / 100)
        client_price = carrier_price + markup_amount
        
        return {
            "carrier_price": carrier_price,
            "markup_percent": markup_percent,
            "markup_amount": markup_amount,
            "client_price": client_price,
            "profit": markup_amount
        }

    async def get_cargo_by_id(self, cargo_id: str) -> Optional[Dict]:
        """
        Получить груз по ID согласно документации ATI
        Использует /v1.0/loads для получения полной информации
        
        Args:
            cargo_id: ID груза
            
        Returns:
            Данные груза или None
        """
        try:
            # Сначала пробуем получить через v1.0/loads (полная информация)
            url = f"{self.api_base}/v1.0/loads"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                all_loads = response.json()
                
                # Ищем наш груз среди всех грузов
                for load in all_loads:
                    if load.get("Id") == cargo_id:
                        logger.info(f"✅ Получен груз {cargo_id} через /v1.0/loads")
                        return load
                
                # Если не найден, пробуем v2/cargos
                url_v2 = f"{self.api_base}/v2/cargos/{cargo_id}"
                response_v2 = requests.get(url_v2, headers=self.headers)
                
                if response_v2.status_code == 200:
                    cargo_data = response_v2.json()
                    logger.info(f"✅ Получен груз {cargo_id} через /v2/cargos")
                    return cargo_data
                else:
                    logger.warning(f"⚠️ Груз {cargo_id} не найден ни в v1.0/loads, ни в v2/cargos")
                    return None
            else:
                logger.error(f"❌ Ошибка получения списка грузов: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса груза {cargo_id}: {e}")
            return None

    async def renew_cargo(self, cargo_id: str) -> bool:
        """
        Обновить груз для поднятия в списке согласно документации ATI
        
        Args:
            cargo_id: ID груза для обновления
            
        Returns:
            True если успешно обновлен
        """
        try:
            # Сначала получаем груз чтобы убедиться что он существует
            cargo_data = await self.get_cargo_by_id(cargo_id)
            if not cargo_data:
                logger.warning(f"⚠️ Груз {cargo_id} не найден для обновления")
                return False
            
            # Обновляем груз
            url = f"{self.api_base}/v1.0/loads/{cargo_id}/renew"
            response = requests.put(url, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                
                # Проверяем статус операции
                for key, status_info in result.items():
                    status_code = status_info.get("Status", -1)
                    message = status_info.get("Message", "")
                    
                    if status_code == 0:  # Успех
                        logger.info(f"✅ Груз {cargo_id} успешно обновлен")
                        return True
                    elif status_code == 2:
                        logger.warning(f"⚠️ Груз {cargo_id} был обновлен менее часа назад")
                        return False
                    else:
                        logger.error(f"❌ Ошибка обновления груза {cargo_id}: {message} (код: {status_code})")
                        return False
            else:
                logger.error(f"❌ Ошибка обновления груза {cargo_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления груза {cargo_id}: {e}")
            return False

    def _translate_pack_type(self, pack_type: str) -> str:
        """Перевод типа упаковки на русский"""
        translations = {
            'bags': 'в мешках',
            'boxes': 'в коробках',
            'pallets': 'на поддонах',
            'containers': 'в контейнерах',
            'stack': 'штабелем',
            'bulk': 'навалом',
            'roll': 'в рулонах'
        }
        return translations.get(pack_type, pack_type)

    def _translate_loading_method(self, loading_method: str) -> str:
        """Перевод способа загрузки на русский"""
        translations = {
            'mechanized': 'механизированная',
            'manual': 'ручная',
            'crane': 'краном',
            'forklift': 'погрузчиком',
            'conveyor': 'конвейером'
        }
        return translations.get(loading_method, loading_method)

    def _build_loading_dates(self, cargo_data: Dict) -> Dict:
        """Построение структуры дат загрузки согласно документации ATI API v2"""
        
        readiness_type = cargo_data.get("loading_readiness_type", "ready")
        logger.info(f"📅 Строим dates структуру для типа: {readiness_type} (используем from-date для одного дня)")
        
        if readiness_type == "ready":
            # Один день - используем from-date вместо ready
            # Согласно предложению пользователя: type: "from-date" работает лучше чем "ready"
            loading_date = cargo_data.get("loading_date")
            
            if loading_date:
                # Конвертируем дату в ISO формат для ATI API
                first_date = f"{loading_date}T00:00:00.000Z"
                last_date = f"{loading_date}T23:59:59.000Z"
                
                result = {
                    "type": "from-date",  # Изменено с ready на from-date
                    "first_date": first_date,
                    "last_date": last_date,
                    "time": {
                        "type": "bounded"
                    }
                }
                logger.info(f"✅ Создана dates структура 'from-date' (был ready) с датой {loading_date}: {result}")
                return result
            else:
                # Если даты нет, используем сегодня
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                first_date = f"{today}T00:00:00.000Z"
                last_date = f"{today}T23:59:59.000Z"
                
                result = {
                    "type": "from-date",  # Изменено с ready на from-date
                    "first_date": first_date,
                    "last_date": last_date,
                    "time": {
                        "type": "bounded"
                    }
                }
                logger.info(f"✅ Создана dates структура 'from-date' (был ready, по умолчанию сегодня): {result}")
                return result
        elif readiness_type == "interval":
            # Интервал дат - ИСПРАВЛЕНО согласно документации
            # Согласно ати2_груз.txt: type: "from-date" с first_date и last_date
            from_date = cargo_data.get("loading_date_from", cargo_data.get("loading_date"))
            to_date = cargo_data.get("loading_date_to")
            
            # Конвертируем строки в ISO формат для ATI API
            if isinstance(from_date, str) and from_date:
                from_date = f"{from_date}T00:00:00.000Z"
            if isinstance(to_date, str) and to_date:
                to_date = f"{to_date}T23:59:59.000Z"
                
            result = {
                "type": "from-date",
                "first_date": from_date,
                "last_date": to_date,
                "time": {
                    "type": "bounded"
                }
            }
            logger.info(f"✅ Создана dates структура 'from-date' bounded БЕЗ ВРЕМЕНИ: {result}")
            return result
        elif readiness_type == "permanent":
            # Постоянно - регулярные перевозки
            # Согласно ати2_груз.txt: type: "permanent"
            return {
                "type": "permanent",
                "time": {
                    "type": "bounded"
                }
            }
        elif readiness_type == "rate_request":
            # Груза нет, запрос ставки
            # Согласно ати2_груз.txt: type: "rate-request"
            result = {
                "type": "rate-request"
            }
            logger.info(f"✅ Создана dates структура 'rate-request': {result}")
            return result
        else:
            # По умолчанию - from-date (было ready)
            return {
                "type": "from-date",
                "time": {
                    "type": "bounded"
                },
                "is_available_tomorrow": False
            }

    async def get_cargo_types(self) -> Dict[str, int]:
        """
        Получение типов грузов из ATI API
        GET /v1.0/dictionaries/cargoTypes
        """
        try:
            url = f"{self.api_base}/v1.0/dictionaries/cargoTypes"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                cargo_types = response.json()
                logger.info(f"✅ Получено {len(cargo_types)} типов грузов")
                
                # Преобразуем в удобный формат {название: id}
                cargo_dict = {}
                for cargo in cargo_types:
                    cargo_dict[cargo.get('name', '')] = cargo.get('id')
                
                return cargo_dict
            else:
                logger.error(f"❌ Ошибка получения типов грузов: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса типов грузов: {e}")
            return {}

    async def get_cargo_responses_new(self, cargo_id: str = None) -> List[Dict]:
        """
        Получение встречных предложений на грузы фирмы
        GET /v1.0/loads/new/responses
        
        Args:
            cargo_id: ID конкретного груза (опционально)
        """
        try:
            url = f"{self.api_base}/v1.0/loads/new/responses"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                all_responses = response.json()
                
                if cargo_id:
                    # Фильтруем отклики только на указанный груз
                    filtered_responses = [
                        resp for resp in all_responses 
                        if resp.get("LoadId") == cargo_id
                    ]
                    logger.info(f"📨 Получено {len(filtered_responses)} откликов на груз {cargo_id}")
                    return filtered_responses
                else:
                    logger.info(f"📨 Получено {len(all_responses)} откликов на все грузы")
                    return all_responses
            else:
                logger.error(f"❌ Ошибка получения откликов: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса откликов: {e}")
            return []



    async def get_all_company_loads(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Получение всех грузов фирмы с информацией о RenewRestriction
        GET /v1.0/loads
        
        Args:
            limit: Максимальное количество грузов
            offset: Смещение для пагинации
            
        Returns:
            Список грузов с полной информацией
        """
        try:
            url = f"{self.api_base}/v1.0/loads"
            params = {
                "limit": limit,
                "offset": offset
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                loads_data = response.json()
                
                # Извлекаем грузы из ответа и логируем информацию о возможности обновления
                for load in loads_data:
                    load_id = load.get("Id", "N/A")
                    can_be_renewed = load.get("CanBeRenewed", False)
                    renew_restriction = load.get("RenewRestriction", "")
                    
                    if can_be_renewed:
                        logger.info(f"✅ Груз {load_id} можно обновить")
                    else:
                        logger.info(f"⏳ Груз {load_id} ограничение: {renew_restriction}")
                
                logger.info(f"📦 Получено {len(loads_data)} грузов (offset: {offset}, limit: {limit})")
                return loads_data
            else:
                logger.error(f"❌ Ошибка получения грузов: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса грузов: {e}")
            return []

    async def renew_multiple_cargos(self, cargo_ids: List[str]) -> Dict[str, Dict]:
        """
        Обновление нескольких грузов
        PUT /v1.0/loads/renew
        
        Args:
            cargo_ids: Список ID грузов для обновления
            
        Returns:
            Словарь с результатами обновления {cargo_id: {Status, Message}}
        """
        try:
            if not cargo_ids:
                logger.warning("⚠️ Пустой список грузов для обновления")
                return {}
            
            # Проверяем и фильтруем валидные ID
            valid_cargo_ids = []
            for cargo_id in cargo_ids:
                if cargo_id and isinstance(cargo_id, str) and len(cargo_id.strip()) > 0:
                    cleaned_id = cargo_id.strip()
                    # Проверяем формат GUID
                    if self._is_valid_guid(cleaned_id):
                        valid_cargo_ids.append(cleaned_id)
                    else:
                        logger.warning(f"⚠️ Неверный формат GUID: {cleaned_id}")
                else:
                    logger.warning(f"⚠️ Неверный ID груза: {cargo_id}")
            
            if not valid_cargo_ids:
                logger.warning("⚠️ Нет валидных ID грузов для обновления")
                return {}
            
            url = f"{self.api_base}/v1.0/loads/renew"
            
            # Формируем тело запроса согласно документации ATI.SU
            # Отправляем объект с полем ids содержащим массив ID
            import json
            request_data = {"ids": valid_cargo_ids}
            request_body_json = json.dumps(request_data)
            
            logger.info(f"🔄 Обновляем {len(valid_cargo_ids)} грузов: {valid_cargo_ids}")
            logger.debug(f"📤 Тело запроса JSON: {request_body_json}")
            
            # Обновляем заголовки для JSON
            headers_with_json = self.headers.copy()
            headers_with_json['Content-Type'] = 'application/json'
            
            response = requests.put(url, headers=headers_with_json, data=request_body_json)
            
            logger.debug(f"📥 Ответ API: {response.status_code} - {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                
                # Обрабатываем результаты обновления
                success_count = 0
                delay_count = 0
                error_count = 0
                
                for cargo_id, status_info in result.items():
                    status_code = status_info.get("Status", -1)
                    message = status_info.get("Message", "")
                    error = status_info.get("Error", "")
                    
                    if status_code == 0:  # Успех
                        logger.info(f"✅ Груз {cargo_id} успешно обновлен")
                        success_count += 1
                    elif status_code == 2:  # Обновлен менее часа назад - это НОРМАЛЬНО
                        logger.info(f"⏳ Груз {cargo_id}: {message} (это нормально)")
                        delay_count += 1
                    else:
                        logger.warning(f"❌ Груз {cargo_id}: {message} (код: {status_code}, ошибка: {error})")
                        error_count += 1
                
                # Улучшенная статистика
                if delay_count > 0 and success_count == 0 and error_count == 0:
                    logger.info(f"📊 Все грузы обновлены недавно: ⏳{delay_count} (это нормально)")
                else:
                    logger.info(f"📊 Обновление завершено: ✅{success_count} ⏳{delay_count} ❌{error_count}")
                return result
                
            else:
                logger.error(f"❌ Ошибка запроса обновления: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка массового обновления грузов: {e}")
            return {}

    def parse_renew_restriction(self, renew_restriction: str) -> Optional[int]:
        """
        Парсинг строки RenewRestriction для извлечения времени ожидания в минутах
        
        Args:
            renew_restriction: Строка типа "Груз можно обновить не ранее чем через 39 минут"
            
        Returns:
            Количество минут до возможности обновления или None если сейчас можно
        """
        import re
        
        if not renew_restriction or renew_restriction.strip() == "":
            return None  # Можно обновлять сейчас
        
        # Ищем число минут в строке
        minutes_match = re.search(r'(\d+)\s*минут', renew_restriction)
        if minutes_match:
            return int(minutes_match.group(1))
        
        # Ищем часы
        hours_match = re.search(r'(\d+)\s*час', renew_restriction)
        if hours_match:
            return int(hours_match.group(1)) * 60
        
        logger.warning(f"⚠️ Не удалось распарсить ограничение: {renew_restriction}")
        return None

    async def get_renewable_loads(self) -> List[Dict]:
        """
        Получить грузы которые можно обновить прямо сейчас
        
        Returns:
            Список грузов готовых к обновлению
        """
        renewable_loads = []
        
        try:
            # Получаем все грузы
            all_loads = await self.get_all_company_loads()
            
            for load in all_loads:
                can_be_renewed = load.get("CanBeRenewed", False)
                renew_restriction = load.get("RenewRestriction", "")
                
                if can_be_renewed and (not renew_restriction or renew_restriction.strip() == ""):
                    renewable_loads.append(load)
                    logger.info(f"🟢 Груз {load.get('Id')} готов к обновлению")
                else:
                    wait_minutes = self.parse_renew_restriction(renew_restriction)
                    if wait_minutes:
                        logger.info(f"⏳ Груз {load.get('Id')} можно обновить через {wait_minutes} мин")
            
            logger.info(f"📈 Найдено {len(renewable_loads)} грузов готовых к обновлению")
            return renewable_loads
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения обновляемых грузов: {e}")
            return []

    async def get_firm_contacts_summary(self, ati_id: str) -> Optional[List[Dict]]:
        """
        Получение краткой информации о всех контактах фирмы для анализа надежности
        
        Args:
            ati_id: ID фирмы в ATI.SU
            
        Returns:
            Список контактов с информацией о репутации
        """
        url = f"{self.api_base}/v1.0/firms/{ati_id}/contacts/summary"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                contacts = response.json()
                
                logger.info(f"✅ Получены данные о фирме {ati_id}: {len(contacts)} контактов")
                
                # Логируем ключевые показатели
                for contact in contacts:
                    firm_name = contact.get("firm_name", "N/A")
                    score = contact.get("score", 0)
                    claims = contact.get("claims_count", 0)
                    recommendations = contact.get("recommendations_count", 0)
                    bad_mentions = contact.get("bad_partner_mentions_count", 0)
                    
                    logger.info(f"📊 {firm_name}: ⭐{score} 👍{recommendations} 👎{claims} ⚠️{bad_mentions}")
                
                return contacts
            else:
                logger.warning(f"⚠️ Не удалось получить данные о фирме {ati_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка запроса данных о фирме {ati_id}: {e}")
            return None

    def _is_valid_guid(self, guid: str) -> bool:
        """
        Проверка валидности GUID
        
        Args:
            guid: Строка для проверки
            
        Returns:
            True если GUID валидный
        """
        import re
        
        if not guid or not isinstance(guid, str):
            return False
        
        # Паттерн для GUID: 8-4-4-4-12 символов
        guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        return bool(re.match(guid_pattern, guid.strip()))

    def get_loading_type_id(self, loading_type: str) -> int:
        """
        Получение ID типа загрузки по названию
        
        Args:
            loading_type: Название типа загрузки
            
        Returns:
            ID типа загрузки
        """
        # Маппинг популярных типов загрузки согласно ATI.SU API
        loading_map = {
            'верхняя': 1,
            'боковая': 2, 
            'задняя': 4,
            'с полной растентовкой': 8,
            'боковая с 2-х сторон': 4096,
            'налив': 8192
        }
        
        return loading_map.get(loading_type.lower(), 2)  # По умолчанию боковая

    def get_unloading_type_id(self, unloading_type: str) -> int:
        """
        Получение ID типа разгрузки по названию
        
        Args:
            unloading_type: Название типа разгрузки
            
        Returns:
            ID типа разгрузки
        """
        # Маппинг популярных типов разгрузки согласно ATI.SU API
        unloading_map = {
            'верхняя': 1,
            'боковая': 2,
            'задняя': 4, 
            'с полной растентовкой': 8,
            'боковая с 2-х сторон': 4096,
            'гидроборт': 256  # Для разгрузки используется гидроборт вместо налива
        }
        
        return unloading_map.get(unloading_type.lower(), 2)  # По умолчанию боковая 

    async def get_city_by_id(self, city_id: int) -> Optional[Dict]:
        """
        Получение информации о городе по ID через ATI GIS API
        
        Args:
            city_id: ID города из словаря ATI
            
        Returns:
            Словарь с информацией о городе или None
        """
        try:
            # Используем новый GIS API для получения информации о городе
            url = f"{self.api_base}/gw/gis-dict/v1/cities/by-ids"
            
            payload = {
                "ids": [city_id]
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                cities = data.get("cities", [])
                
                if cities:
                    city_data = cities[0]  # Берем первый (и единственный) город
                    city_name = city_data.get("clarified_name", city_data.get("name", "N/A"))
                    logger.info(f"✅ Получен город {city_id}: {city_name}")
                    
                    # Возвращаем в совместимом формате
                    return {
                        "CityId": city_data.get("city_id", city_id),
                        "Name": city_name,
                        "RegionId": city_data.get("region_id"),
                        "CountryId": city_data.get("country_id"),
                        "IsRegionalCenter": city_data.get("is_regional_center", False),
                        "Size": city_data.get("size", 0),
                        "Coordinates": city_data.get("geo_point"),
                        "Timezone": city_data.get("timezone")
                    }
                else:
                    logger.warning(f"⚠️ Город с ID {city_id} не найден в ответе API")
                    return {"CityId": city_id, "Name": f"Город ID:{city_id}"}
            else:
                logger.warning(f"⚠️ Ошибка запроса города {city_id}: {response.status_code} - {response.text}")
                return {"CityId": city_id, "Name": f"Город ID:{city_id}"}
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения города {city_id}: {e}")
            # Fallback - возвращаем базовую информацию
            return {"CityId": city_id, "Name": f"Город ID:{city_id}"}