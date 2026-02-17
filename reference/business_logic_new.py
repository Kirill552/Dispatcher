#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Новая бизнес-логика для работы с ATI.SU API v2
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from ati_integration.ati_client_v2 import ATIClientV2
from ai_services.sales_agent import SalesAgent
from database.models import Order, CarrierContact, SystemStats
from database.crud import create_order, update_order_status, create_commission
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("ATI_BUSINESS")


class ATIBusinessLogic:
    """Новая бизнес-логика для ATI.SU"""
    
    def __init__(self):
        self.ati_client = ATIClientV2()
        self.sales_agent = SalesAgent()
        
    async def process_external_order(self, order_data: Dict) -> Dict:
        """
        Обработка заказа полученного извне
        1. ИИ общается с заказчиком
        2. Размещаем груз на ATI.SU
        3. Ищем исполнителей
        4. Делаем наценку и предлагаем заказчику
        """
        try:
            logger.info(f"🔄 Обрабатываем внешний заказ: {order_data}")
            
            # Шаг 1: ИИ уточняет детали заказа
            detailed_order = await self._clarify_order_details(order_data)
            
            # Шаг 2: Размещаем груз на ATI.SU
            ati_cargo = await self._publish_cargo_to_ati(detailed_order)
            
            # Шаг 3: Ждем откликов и выбираем лучших исполнителей
            carriers = await self._select_best_carriers(ati_cargo['cargo_id'])
            
            # Шаг 4: Рассчитываем стоимость с наценкой
            final_offer = await self._calculate_final_price(detailed_order, carriers)
            
            # Шаг 5: Предлагаем заказчику
            customer_response = await self._present_offer_to_customer(detailed_order, final_offer)
            
            return {
                "status": "processed",
                "order_id": detailed_order['id'],
                "ati_cargo_id": ati_cargo['cargo_id'],
                "selected_carriers": len(carriers),
                "final_price": final_offer['total_price'],
                "customer_response": customer_response
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки заказа: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def _clarify_order_details(self, order_data: Dict) -> Dict:
        """ИИ общается с заказчиком для уточнения деталей"""
        
        # Генерируем вопросы для уточнения
        clarification_questions = await self.sales_agent.generate_clarification_questions(order_data)
        
        logger.info(f"🤖 ИИ задает вопросы заказчику: {len(clarification_questions)} вопросов")
        
        # В реальной системе здесь будет диалог с заказчиком
        # Пока симулируем получение полных данных
        detailed_order = {
            **order_data,
            "id": f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "from_address": order_data.get("from_address", "Уточнено с заказчиком"),
            "to_address": order_data.get("to_address", "Уточнено с заказчиком"),
            "cargo_weight": order_data.get("cargo_weight", 1000),
            "cargo_type": order_data.get("cargo_type", "Обычный груз"),
            "loading_date": order_data.get("loading_date", (datetime.now() + timedelta(days=2)).isoformat()),
            "special_requirements": order_data.get("special_requirements", []),
            "customer_budget": order_data.get("customer_budget", 0),
            "customer_contact": order_data.get("customer_contact", {}),
            "clarified_at": datetime.now().isoformat()
        }
        
        # Сохраняем в базу данных
        await create_order({
            "external_id": detailed_order['id'],
            "from_address": detailed_order['from_address'],
            "to_address": detailed_order['to_address'],
            "cargo_weight": detailed_order['cargo_weight'],
            "cargo_type": detailed_order['cargo_type'],
            "loading_date": detailed_order['loading_date'],
            "customer_budget": detailed_order['customer_budget'],
            "status": "clarified",
            "created_at": datetime.now()
        })
        
        return detailed_order
    
    async def _publish_cargo_to_ati(self, order: Dict) -> Dict:
        """Размещение груза на ATI.SU"""
        
        # Формируем данные груза для ATI.SU
        cargo_data = {
            "from_city": self._extract_city(order['from_address']),
            "to_city": self._extract_city(order['to_address']),
            "cargo_type": order['cargo_type'],
            "weight": order['cargo_weight'],
            "volume": order.get('cargo_volume', 0),
            "loading_date": order['loading_date'],
            "description": f"Перевозка {order['cargo_type']} {order['cargo_weight']}кг",
            "price": 0,  # Ждем предложений от перевозчиков
            "contacts": {
                "phone": settings.dispatcher_phone,
                "name": settings.dispatcher_name,
                "company": settings.company_name
            }
        }
        
        logger.info(f"📦 Размещаем груз на ATI.SU: {cargo_data}")
        
        # Размещаем через API
        ati_response = await self.ati_client.create_cargo(cargo_data)
        
        # Обновляем статус в базе
        try:
            # Преобразуем order_id в int если это строка
            order_id = int(order['id']) if isinstance(order['id'], str) and order['id'].isdigit() else None
            if order_id:
                await update_order_status(
                    order_id,
                    "published_on_ati",
                    ati_cargo_id=ati_response.get('cargo_id'),
                    published_at=datetime.now().isoformat()
                )
            else:
                logger.warning(f"⚠️ Не удалось обновить статус - некорректный order_id: {order['id']}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса в БД: {e}")
        
        return {
            "cargo_id": ati_response.get('cargo_id'),
            "ati_url": f"https://ati.su/loads/{ati_response.get('cargo_id')}",
            "published_at": datetime.now().isoformat()
        }
    
    async def _select_best_carriers(self, cargo_id: str) -> List[Dict]:
        """Поиск и выбор лучших исполнителей"""
        
        # Ждем откликов 24 часа (в реальности можно настроить)
        await asyncio.sleep(5)  # Для демо
        
        # Получаем список откликнувшихся перевозчиков
        # В реальной API это будет запрос к /cargo/{cargo_id}/responses
        
        # Симулируем получение откликов
        mock_carriers = [
            {
                "id": "carrier_001",
                "company_name": "ООО Транспорт Плюс",
                "price": 45000,
                "rating": 4.8,
                "reviews_count": 234,
                "vehicle_type": "Фура 20 тонн",
                "driver_experience": 5,
                "contact_phone": "+7(123)456-78-90"
            },
            {
                "id": "carrier_002", 
                "company_name": "ИП Иванов И.И.",
                "price": 42000,
                "rating": 4.6,
                "reviews_count": 89,
                "vehicle_type": "Газель 3 тонны",
                "driver_experience": 3,
                "contact_phone": "+7(123)456-78-91"
            },
            {
                "id": "carrier_003",
                "company_name": "Логистик Транс",
                "price": 48000,
                "rating": 4.9,
                "reviews_count": 456,
                "vehicle_type": "Фура 20 тонн",
                "driver_experience": 8,
                "contact_phone": "+7(123)456-78-92"
            }
        ]
        
        # ИИ анализирует и выбирает лучших
        selected_carriers = await self.sales_agent.select_best_carriers(mock_carriers)
        
        logger.info(f"✅ Выбрано {len(selected_carriers)} лучших перевозчиков")
        
        # Общаемся с выбранными перевозчиками через ATI мессенджер
        for carrier in selected_carriers:
            await self._negotiate_with_carrier(carrier)
        
        return selected_carriers
    
    async def _negotiate_with_carrier(self, carrier: Dict):
        """Переговоры с перевозчиком через ATI мессенджер"""
        
        # Генерируем сообщение через ИИ
        message = await self.sales_agent.generate_carrier_message(carrier)
        
        # Отправляем через ATI мессенджер
        try:
            await self.ati_client.send_message(
                recipient_id=carrier['id'],
                message=message
            )
            logger.info(f"💬 Отправлено сообщение перевозчику {carrier['company_name']}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения: {str(e)}")
    
    async def _calculate_final_price(self, order: Dict, carriers: List[Dict]) -> Dict:
        """Расчет финальной стоимости с наценкой"""
        
        # Находим лучшую цену от перевозчиков
        best_carrier_price = min(carrier['price'] for carrier in carriers)
        
        # Добавляем нашу наценку
        commission_percent = settings.default_commission_percent
        commission_amount = best_carrier_price * (commission_percent / 100)
        final_price = best_carrier_price + commission_amount
        
        # Проверяем бюджет заказчика
        customer_budget = order.get('customer_budget', 0)
        is_within_budget = final_price <= customer_budget if customer_budget > 0 else True
        
        offer = {
            "carrier_price": best_carrier_price,
            "commission_percent": commission_percent,
            "commission_amount": commission_amount,
            "total_price": final_price,
            "customer_budget": customer_budget,
            "within_budget": is_within_budget,
            "savings": customer_budget - final_price if customer_budget > final_price else 0
        }
        
        logger.info(f"💰 Рассчитана стоимость: {best_carrier_price}₽ + {commission_percent}% = {final_price}₽")
        
        return offer
    
    async def _present_offer_to_customer(self, order: Dict, offer: Dict) -> Dict:
        """Предложение заказчику с наценкой"""
        
        # Генерируем коммерческое предложение через ИИ
        proposal = await self.sales_agent.generate_customer_proposal(order, offer)
        
        logger.info(f"📋 Сформировано предложение для заказчика: {offer['total_price']}₽")
        
        # В реальной системе отправляем предложение заказчику
        # Пока симулируем ответ
        customer_response = {
            "status": "interested",
            "response_time": datetime.now().isoformat(),
            "message": "Устраивает, когда можете забрать груз?",
            "accepted_price": offer['total_price']
        }
        
        # Сохраняем комиссию в базу
        await create_commission({
            "order_id": order['id'],
            "carrier_price": offer['carrier_price'],
            "commission_percent": offer['commission_percent'],
            "commission_amount": offer['commission_amount'],
            "total_price": offer['total_price'],
            "status": "pending",
            "created_at": datetime.now()
        })
        
        return customer_response
    
    def _extract_city(self, address: str) -> str:
        """Извлечь город из адреса"""
        # Простая логика извлечения города
        # В реальной системе можно использовать геокодирование
        words = address.split()
        for word in words:
            if len(word) > 3 and word[0].isupper():
                return word
        return address.split(',')[0].strip()
    
    async def get_business_stats(self) -> Dict:
        """Статистика новой бизнес-модели"""
        return {
            "total_orders_processed": 0,
            "total_commission_earned": 0,
            "average_commission_percent": settings.default_commission_percent,
            "successful_conversions": 0,
            "ati_expenses": {
                "cargo_publications": 0,
                "messenger_messages": 0,
                "api_searches": 0
            }
        }


# Создаем глобальный экземпляр
ati_business = ATIBusinessLogic() 