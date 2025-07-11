#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ИИ-обработчик сообщений пользователей
Заменяет кнопки на естественное общение с ИИ
"""

import asyncio
from typing import Dict, Optional, List, Tuple
from openai import AsyncOpenAI
from database.crud import get_orders_by_telegram_id
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("MESSAGE_PROCESSOR")


class MessageProcessor:
    """ИИ-обработчик сообщений пользователей"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.enabled = True  # Флаг для быстрого отключения
        
    async def process_message(self, message: str, user_id: int) -> Optional[Dict]:
        """
        Обрабатывает сообщение пользователя через ИИ
        
        Returns:
            Dict с типом действия и данными, или None если не обработано
        """
        if not self.enabled:
            return None
            
        try:
            # Определяем намерение пользователя
            intent = await self._detect_intent(message)
            
            if intent['type'] == 'order_status':
                return await self._handle_order_status_request(user_id, message)
            elif intent['type'] == 'help':
                return await self._handle_help_request(message)
            elif intent['type'] == 'new_order':
                return {'action': 'new_order', 'trigger_callback': True}
            elif intent['type'] == 'contact':
                return await self._handle_contact_request()
            elif intent['type'] == 'main_menu':
                return {'action': 'main_menu', 'trigger_callback': True}
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            return None
    
    async def _detect_intent(self, message: str) -> Dict:
        """Определяет намерение пользователя через ИИ"""
        
        prompt = f"""
Определи намерение пользователя по сообщению: "{message}"

Возможные намерения:
1. order_status - спрашивает о статусе заказов 
   Примеры: "мои заказы", "где груз", "статус", "как дела с заказом", "что с перевозкой"

2. help - просит помощь или справку
   Примеры: "помощь", "справка", "как работает", "что умеешь", "инструкция", "хелп", "помощь..."

3. new_order - хочет создать заказ или перевезти груз
   Примеры: "заказать перевозку", "перевезти", "доставить", "нужно перевезти", "увезти", "уыезти", "груз", "машину", "транспорт"

4. contact - спрашивает контакты
   Примеры: "контакты", "как связаться", "телефон", "связь", "номер"

5. main_menu - хочет в главное меню
   Примеры: "главное меню", "меню", "начало", "старт", "заново", "в начало"

6. other - всё остальное

ВАЖНО: 
- Учитывай опечатки: "уыезти" = "увезти" = new_order
- "заказать перевозку" = new_order
- "главное меню..." = main_menu  
- "помощь..." = help
- Будь внимателен к разговорной речи и сленгу

Ответь ТОЛЬКО одним словом: order_status, help, new_order, contact, main_menu или other
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            intent_type = response.choices[0].message.content.strip().lower()
            
            # Валидация ответа
            valid_intents = ['order_status', 'help', 'new_order', 'contact', 'main_menu', 'other']
            if intent_type not in valid_intents:
                intent_type = 'other'
                
            logger.info(f"🎯 Намерение пользователя: {intent_type} для сообщения: '{message[:50]}...'")
            return {'type': intent_type}
            
        except Exception as e:
            logger.error(f"❌ Ошибка определения намерения: {e}")
            return {'type': 'other'}
    
    async def _handle_order_status_request(self, user_id: int, message: str) -> Dict:
        """Обработка вопросов о статусе заказов"""
        
        try:
            # Получаем заказы пользователя
            orders = await get_orders_by_telegram_id(user_id)
            
            if not orders:
                response = """📋 У вас пока нет активных заказов

🚀 Хотите создать новый заказ? Просто опишите что нужно перевезти:
• Откуда и куда
• Что за груз, вес
• Когда нужна подача

Пример: "Мебель из Москвы в СПб, 500 кг, завтра утром" """
                
                return {
                    'action': 'respond',
                    'text': response
                }
            
            # Формируем ответ через ИИ
            orders_summary = self._format_orders_for_ai(orders)
            
            prompt = f"""
Ты - опытный диспетчер логистики. Пользователь спрашивает: "{message}"

Информация о его заказах:
{orders_summary}

Ответь профессионально и дружелюбно о статусе заказов. 
Статусы: pending (ожидает обработки), searching (ищем перевозчиков), offers_found (найдены предложения), placed_on_ati (размещен на платформе).

Если статус searching или pending - сообщи что активно ищем лучшие варианты.
Используй эмодзи. Будь лаконичным но информативным.
"""
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            return {
                'action': 'respond',
                'text': ai_response
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса статуса: {e}")
            return {
                'action': 'respond',
                'text': "❌ Не удалось получить информацию о заказах. Попробуйте позже."
            }
    
    async def _handle_help_request(self, message: str) -> Dict:
        """Обработка запросов помощи"""
        
        help_text = f"""📚 Справка по ИИ-Диспетчеру 2025

🚀 Как заказать перевозку:
Просто опишите что нужно перевезти! Например:
• "Нужно перевезти мебель"
• "Доставить холодильник"
• "Груз из Сарапула в Ижевск"

🔍 Что я умею:
• Нахожу лучших перевозчиков
• Рассчитываю стоимость доставки  
• Контролирую выполнение заказа
• Работаю 24/7 без выходных

⚖️ Ограничения: только грузы от 200 кг
🌍 География: вся Россия
⏱️ Время поиска: 15-30 минут

📞 Контакты:
• Telegram: {settings.dispatcher_telegram}
• Email: {settings.dispatcher_email}

💬 Частые вопросы:
• "Мои заказы" - покажу статус ваших грузов
• "Контакты" - как с нами связаться"""

        return {
            'action': 'respond', 
            'text': help_text
        }
    
    async def _handle_contact_request(self) -> Dict:
        """Обработка запросов контактов"""
        
        contact_text = f"""📞 Контакты для связи

💬 Telegram: {settings.dispatcher_telegram}  
📧 Email: {settings.dispatcher_email}

🕐 Часы работы: 24/7

💬 Все вопросы: пишите в этот чат

🚛 Готов помочь с организацией перевозки!"""

        return {
            'action': 'respond',
            'text': contact_text
        }
    
    def _format_orders_for_ai(self, orders: List[Dict]) -> str:
        """Форматирует заказы для передачи ИИ"""
        
        if not orders:
            return "Заказов нет"
            
        formatted_orders = []
        for order in orders:
            order_info = f"""
Заказ #{order.get('id')}:
- Груз: {order.get('cargo_type', 'N/A')}
- Маршрут: {order.get('from_city', 'N/A')} → {order.get('to_city', 'N/A')}
- Вес: {order.get('weight', 'N/A')} кг
- Дата загрузки: {order.get('loading_date', 'N/A')}
- Статус: {order.get('status', 'N/A')}
- Создан: {order.get('created_at', 'N/A')}"""
            formatted_orders.append(order_info)
            
        return '\n'.join(formatted_orders)
    
    def enable(self):
        """Включить ИИ-обработку"""
        self.enabled = True
        logger.info("✅ ИИ-обработка сообщений включена")
    
    def disable(self):
        """Отключить ИИ-обработку"""
        self.enabled = False
        logger.info("❌ ИИ-обработка сообщений отключена")


# Глобальный экземпляр процессора
message_processor = MessageProcessor() 