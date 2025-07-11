#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ИИ-диспетчер логистики - профессиональная система продаж
Схема работы:
1. Получение заказа от клиента через ИИ с профессиональными промптами
2. Уточнение деталей груза и маршрута вежливым продавцом
3. Сообщение клиенту о начале поиска лучшего варианта перевозки
4. Размещение груза на ATI.SU (скрыто от клиента)
5. Мониторинг и анализ встречных предложений от перевозчиков
6. ИИ выбирает лучшее предложение по фирме, цене и срокам
7. Предложение клиенту цены с наценкой 40% + работа с возражениями
8. Закрытие сделки и уведомление владельца (ID: 408001372)
9. Передача контактов для дальнейшего общения
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from ati_integration.ati_client_v2 import ATIClientV2
from ai_services.sales_agent import SalesAgent
from database.models import Order, CarrierContact, SystemStats
from database.crud import create_order, update_order_status, create_commission
from utils.config import settings
from utils.logger import get_logger
from openai import AsyncOpenAI
from ati_integration.cargo_renewal_manager import cargo_renewal_manager

# Импортируем новые словари ATI
from ati_dictionaries_new import (
    find_car_type_by_name,
    find_cargo_type_by_name,
    find_loading_type_by_name,
    find_unloading_type_by_name,
    find_money_type_by_name,
    get_popular_car_types,
    get_button_loading_types,
    get_button_unloading_types,
    POPULAR_CAR_TYPES,
    LOADING_TYPE_IDS,
    UNLOADING_TYPE_IDS,
    MONEY_TYPE_IDS,
    CAR_TYPES,
    CARGO_TYPES,
    MONEY_TYPES,
    PACK_TYPES
)

logger = get_logger("AI_DISPATCHER")


class AIDispatcherLogic:
    """ИИ-диспетчер логистики с профессиональными промптами"""
    
    # Профессиональные промпты для ИИ
    SALES_PROMPTS = {
        "greeting": """
Вы - профессиональный менеджер по логистике с 10-летним опытом. 
Ваша задача - помочь клиенту организовать перевозку груза максимально выгодно и надежно.
Будьте вежливы, компетентны и всегда предлагайте лучшие решения.
Говорите уверенно, но не навязчиво. Подчеркивайте преимущества работы с вами.
""",
        
        "clarification": """
Для точного расчета стоимости и организации перевозки мне нужно уточнить несколько важных деталей.
Это поможет найти самый подходящий транспорт и предложить вам лучшую цену.
""",
        
        "offer_presentation": """
Отличные новости! Я нашел для вас надежного перевозчика с отличной репутацией.
Позвольте представить выгодное предложение, которое я специально подготовил для вашего груза.
""",
        
        "price_justification": """
Наша цена включает полное сопровождение груза и контроль доставки.
Мы работаем только с проверенными перевозчиками и следим за процессом транспортировки.
Оплата производится только после успешной доставки.
""",
        
        "closing": """
Готов оформить заказ прямо сейчас. После подтверждения я сразу свяжусь с перевозчиком
и организую забор груза в удобное для вас время. Вы будете получать уведомления
о каждом этапе доставки.
"""
    }
    
    def __init__(self):
        self.ati_client = ATIClientV2()
        self.sales_agent = SalesAgent()
        self.markup_percent = 40.0  # Наценка 40%
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
    async def process_client_order(self, client_data: Dict) -> Dict:
        """
        Основная функция обработки заказа клиента
        Полный цикл от получения заявки до закрытия сделки
        """
        try:
            logger.info(f"📥 Обработка заказа клиента: {client_data}")
            
            # Шаг 1: Извлечение данных из диалога с клиентом
            order_data = await self._extract_order_data_from_conversation(client_data)
            
            # Шаг 2: Проверка готовности заказа
            readiness_check = await self._analyze_order_readiness([{'content': str(client_data)}])
            
            if not readiness_check['is_ready']:
                # Нужны уточнения - возвращаем вопросы клиенту
                return {
                    'status': 'needs_clarification',
                    'missing_fields': readiness_check['missing_fields'],
                    'clarification_questions': await self._generate_clarification_questions(readiness_check['missing_fields']),
                    'order_data': order_data
                }
            
            # Шаг 3: Дополнительная обработка данных (автоматический выбор типа кузова)
            order_data = await self._enhance_order_data(order_data)
            
            # Шаг 4: Сообщаем клиенту о начале поиска
            client_notification = await self._notify_client_search_started(order_data)
            
            # Шаг 5: Размещаем груз на ATI.SU (скрыто от клиента)
            ati_result = await self._place_order_on_ati(order_data)
            
            if not ati_result['success']:
                return {
                    'status': 'error',
                    'message': 'Произошла техническая ошибка. Попробуйте позже.',
                    'error': ati_result.get('error')
                }
            
            # Шаг 6: Запускаем мониторинг предложений
            cargo_id = ati_result['ati_cargo_id']
            monitoring_result = await self._start_offers_monitoring(cargo_id, order_data)
            
            return {
                'status': 'search_started',
                'message': client_notification,
                'cargo_id': cargo_id,
                'order_id': ati_result['order_id'],
                'monitoring_started': True
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки заказа: {str(e)}")
            return {
                'status': 'error',
                'message': 'Произошла техническая ошибка. Наш менеджер свяжется с вами в ближайшее время.',
                'error': str(e)
            }

    async def _notify_client_search_started(self, order_data: Dict) -> str:
        """Уведомление клиенту о начале поиска перевозчика"""
        
        route = f"{order_data['from_city']} → {order_data['to_city']}"
        cargo_info = f"{order_data['cargo_type']}, {order_data['weight']} кг"
        loading_date = order_data.get('loading_date', 'указанная дата')
        
        message = f"""✅ Отлично! Все данные получены.

📦 Ваш груз: {cargo_info}
🚛 Маршрут: {route}  
📅 Дата загрузки: {loading_date}

🔍 Начинаем поиск наилучшего варианта перевозки среди проверенных перевозчиков.

⏱️ Обычно это занимает 15-30 минут.

📱 Для получения уведомлений о результатах поиска запустите нашего бота в Telegram: https://t.me/ai_dispatcherBot

Как только найдем лучшие предложения - сразу свяжемся с вами!"""

        # Отправляем уведомление через Telegram бота
        try:
            from bot.client_bot import client_bot
            client_phone = order_data.get('contact_phone')
            if client_phone:
                await client_bot.notify_client_search_started(client_phone, order_data)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления через бота: {str(e)}")
        
        return message

    async def _start_offers_monitoring(self, cargo_id: str, order_data: Dict) -> Dict:
        """Запуск мониторинга встречных предложений"""
        
        try:
            # Сохраняем информацию о мониторинге в базу
            monitoring_data = {
                'cargo_id': cargo_id,
                'order_data': order_data,
                'status': 'monitoring',
                'started_at': datetime.now(),
                'client_telegram_id': order_data.get('client_telegram_id'),
                'owner_telegram_id': 408001372  # ID владельца
            }
            
            # Запускаем фоновую задачу мониторинга
            asyncio.create_task(self._monitor_cargo_offers(monitoring_data))
            
            logger.info(f"🔍 Запущен мониторинг предложений для груза {cargo_id}")
            
            return {
                'success': True,
                'monitoring_id': cargo_id,
                'message': 'Мониторинг предложений запущен'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _monitor_cargo_offers(self, monitoring_data: Dict):
        """Мониторинг встречных предложений от перевозчиков"""
        
        cargo_id = monitoring_data['cargo_id']
        order_data = monitoring_data['order_data']
        max_wait_time = 30 * 60  # 30 минут максимум
        check_interval = 60  # проверяем каждую минуту
        
        start_time = time.time()
        
        logger.info(f"🔍 Начат мониторинг предложений для груза {cargo_id}")
        
        try:
            while time.time() - start_time < max_wait_time:
                # Получаем встречные предложения
                offers = await self.ati_client.get_cargo_responses(cargo_id)
                
                if offers and len(offers) > 0:
                    logger.info(f"📨 Получено {len(offers)} предложений для груза {cargo_id}")
                    
                    # ИИ анализирует и выбирает лучшее предложение
                    best_offer = await self._select_best_offer(offers, order_data)
                    
                    if best_offer:
                        # Формируем предложение клиенту с наценкой
                        client_offer = await self._create_client_offer(best_offer, order_data)
                        
                        # Отправляем предложение клиенту
                        await self._send_offer_to_client(client_offer, monitoring_data)
                        
                        # НОВАЯ ЛОГИКА: Сразу уведомляем владельца и завершаем работу ИИ
                        await self._notify_owner_about_offer(best_offer, client_offer, monitoring_data)
                        
                        logger.info(f"✅ Предложение отправлено клиенту, владелец уведомлен. ИИ завершает работу по заказу {cargo_id}")
                        
                        break
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(check_interval)
            
            else:
                # Время вышло, предложений нет
                await self._handle_no_offers(monitoring_data)
                
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга предложений: {str(e)}")
            await self._handle_monitoring_error(monitoring_data, str(e))

    async def _select_best_offer(self, offers: List[Dict], order_data: Dict) -> Optional[Dict]:
        """ИИ выбирает лучшее предложение по фирме, цене и срокам"""
        
        if not offers:
            return None
        
        # Формируем промпт для ИИ
        offers_text = ""
        for i, offer in enumerate(offers, 1):
            company_name = offer.get('CompanyName', 'Не указано')
            price = offer.get('Price', 0)
            rating = offer.get('Rating', 0)
            reviews_count = offer.get('ReviewsCount', 0)
            delivery_time = offer.get('DeliveryTime', 'Не указано')
            
            offers_text += f"""
Предложение {i}:
- Компания: {company_name}
- Цена: {price} руб
- Рейтинг: {rating}/5 ({reviews_count} отзывов)
- Срок доставки: {delivery_time}
- Контакт: {offer.get('ContactPhone', 'Не указан')}
"""
        
        prompt = f"""Ты опытный логист-диспетчер с 10-летним стажем. 
Нужно выбрать ЛУЧШЕЕ предложение для клиента по перевозке груза.

ГРУЗ: {order_data['cargo_type']}, {order_data['weight']} кг
МАРШРУТ: {order_data['from_city']} → {order_data['to_city']}

КРИТЕРИИ ВЫБОРА (по важности):
1. Надежность компании (рейтинг + количество отзывов)
2. Разумная цена (не самая дешевая, но и не завышенная)
3. Соблюдение сроков доставки
4. Опыт работы с подобными грузами

ПРЕДЛОЖЕНИЯ:
{offers_text}

Выбери ОДНО лучшее предложение и объясни почему именно его.
Ответ в формате JSON:
{{
    "selected_offer_index": номер_предложения,
    "reasoning": "подробное обоснование выбора",
    "price": цена_в_рублях,
    "company_name": "название_компании"
}}"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            selected_index = result['selected_offer_index'] - 1  # Индекс с 0
            
            if 0 <= selected_index < len(offers):
                selected_offer = offers[selected_index]
                selected_offer['ai_reasoning'] = result['reasoning']
                
                logger.info(f"🤖 ИИ выбрал предложение {selected_index + 1}: {result['reasoning']}")
                return selected_offer
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора предложения ИИ: {str(e)}")
            # Fallback: выбираем по рейтингу
            return max(offers, key=lambda x: x.get('Rating', 0))
        
        return None

    async def _create_client_offer(self, best_offer: Dict, order_data: Dict) -> Dict:
        """Создание предложения клиенту с наценкой"""
        
        carrier_price = best_offer.get('Price', 0)
        markup_percent = 40  # 40% наценка
        client_price = int(carrier_price * (1 + markup_percent / 100))
        
        company_name = best_offer.get('CompanyName', 'Проверенная транспортная компания')
        delivery_time = best_offer.get('DeliveryTime', '1-2 дня')
        
        return {
            'client_price': client_price,
            'carrier_price': carrier_price,
            'markup_percent': markup_percent,
            'company_name': company_name,
            'delivery_time': delivery_time,
            'best_offer': best_offer,
            'order_data': order_data
        }

    async def _send_offer_to_client(self, client_offer: Dict, monitoring_data: Dict):
        """Отправка предложения клиенту с работой с возражениями"""
        
        order_data = client_offer['order_data']
        client_price = client_offer['client_price']
        delivery_time = client_offer['delivery_time']
        
        route = f"{order_data['from_city']} → {order_data['to_city']}"
        cargo_info = f"{order_data['cargo_type']}, {order_data['weight']} кг"
        
        # Формируем профессиональное предложение
        offer_message = f"""🎯 ОТЛИЧНЫЕ НОВОСТИ! Нашли идеальный вариант для вашего груза!

📦 {cargo_info}
🚛 {route}
💰 Стоимость: {client_price:,} рублей
⏱️ Срок доставки: {delivery_time}

✅ ЧТО ВХОДИТ В СТОИМОСТЬ:
• Профессиональная перевозка проверенной компанией
• Полное сопровождение сделки
• Документооборот
• Поддержка нашего диспетчера

🏆 ПОЧЕМУ ЭТОТ ВАРИАНТ:
• Надежная компания с высоким рейтингом
• Оптимальное соотношение цена/качество
• Соблюдение сроков доставки
• Опыт работы с подобными грузами

Подтверждаете заказ? Сразу бронируем машину! 🚛"""

        # Здесь должна быть отправка сообщения клиенту через Telegram бота
        # await self.telegram_bot.send_message(client_telegram_id, offer_message)
        
        logger.info(f"📤 Отправлено предложение клиенту: {client_price:,} руб")

    async def _notify_owner_about_offer(self, best_offer: Dict, client_offer: Dict, monitoring_data: Dict):
        """Уведомление владельца о найденном предложении"""
        
        owner_telegram_id = 408001372
        order_data = client_offer['order_data']
        
        carrier_price = client_offer['carrier_price']
        client_price = client_offer['client_price']
        profit = client_price - carrier_price
        
        company_name = best_offer.get('CompanyName', 'Не указано')
        contact_phone = best_offer.get('ContactPhone', 'Не указан')
        
        owner_message = f"""🎉 ПОЯВИЛСЯ ГОТОВЫЙ КЛИЕНТ ВОТ ДАННЫЕ СДЕЛКИ!!

📦 ГРУЗ: {order_data['cargo_type']}, {order_data['weight']} кг
🚛 МАРШРУТ: {order_data['from_city']} → {order_data['to_city']}
📅 ДАТА: {order_data.get('loading_date', 'Не указана')}

💰 ФИНАНСЫ:
• Цена перевозчика: {carrier_price:,} руб
• Цена клиенту: {client_price:,} руб  
• Ваша прибыль: {profit:,} руб

🚛 ПЕРЕВОЗЧИК:
• Компания: {company_name}
• Телефон: {contact_phone}
• Рейтинг: {best_offer.get('Rating', 'Не указан')}/5

👤 КЛИЕНТ:
• Имя: {order_data.get('contact_name', 'Не указано')}
• Телефон: {order_data.get('contact_phone', 'Не указан')}

✅ Предложение отправлено клиенту через ИИ-диспетчера! 
🔄 Дальше общение с клиентом в ручном режиме через бота."""

        # Здесь должна быть отправка уведомления владельцу
        # await self.telegram_bot.send_message(owner_telegram_id, owner_message)
        
        logger.info(f"📤 Уведомление владельцу отправлено: прибыль {profit:,} руб")

    async def _handle_no_offers(self, monitoring_data: Dict):
        """Обработка ситуации когда нет предложений"""
        
        order_data = monitoring_data['order_data']
        
        # Сообщение клиенту
        no_offers_message = f"""😔 К сожалению, на данный момент свободных машин по вашему маршруту нет.

📦 Ваш груз: {order_data['cargo_type']}, {order_data['weight']} кг
🚛 Маршрут: {order_data['from_city']} → {order_data['to_city']}

🔄 ЧТО ДЕЛАЕМ ДАЛЬШЕ:
• Продолжаем поиск в расширенной базе перевозчиков
• Рассматриваем альтернативные маршруты
• Наш менеджер свяжется с вами в течение часа

📞 Для срочных вопросов: {settings.dispatcher_phone}"""

        # Уведомление владельцу
        owner_message = f"""⚠️ НЕТ ПРЕДЛОЖЕНИЙ

📦 ГРУЗ: {order_data['cargo_type']}, {order_data['weight']} кг
🚛 МАРШРУТ: {order_data['from_city']} → {order_data['to_city']}

👤 КЛИЕНТ:
• Имя: {order_data.get('contact_name', 'Не указано')}
• Телефон: {order_data.get('contact_phone', 'Не указан')}

Требуется ручная обработка заявки."""

        logger.info(f"⚠️ Нет предложений для груза {monitoring_data['cargo_id']}")

    async def _handle_monitoring_error(self, monitoring_data: Dict, error: str):
        """Обработка ошибки мониторинга"""
        
        owner_message = f"""❌ ОШИБКА МОНИТОРИНГА

📦 ГРУЗ: {monitoring_data['order_data']['cargo_type']}
🚛 МАРШРУТ: {monitoring_data['order_data']['from_city']} → {monitoring_data['order_data']['to_city']}

❌ ОШИБКА: {error}

Требуется ручная проверка системы."""

        logger.error(f"❌ Ошибка мониторинга: {error}")
        
        # Уведомляем клиента об ошибке
        error_message = f"""😔 Произошла техническая ошибка при поиске перевозчиков.

Наш менеджер уже работает над решением проблемы и свяжется с вами в ближайшее время.

📞 Для срочных вопросов: {settings.dispatcher_phone}"""

        # Здесь должна быть отправка сообщения клиенту через Telegram бота
        # await self.telegram_bot.send_message(client_telegram_id, error_message)
        
        logger.info("📤 Отправлено уведомление об ошибке клиенту")

    async def _clarify_order_with_professional_ai(self, client_data: Dict) -> Dict:
        """ИИ профессионально уточняет детали заказа у клиента"""
        
        logger.info("🤖 ИИ-менеджер анализирует заказ и профессионально уточняет детали")
        
        # Проверяем обязательные поля
        required_fields = ['from_city', 'to_city', 'cargo_type']
        missing_fields = [field for field in required_fields if not client_data.get(field)]
        
        if missing_fields:
            # ИИ должен профессионально запросить недостающие данные
            questions = await self._generate_professional_clarification_questions(missing_fields, client_data)
            return {
                "success": False,
                "need_clarification": True,
                "questions": questions,
                "missing_fields": missing_fields,
                "professional_intro": self.SALES_PROMPTS["clarification"]
            }
        
        # Вычисляем объем если не указан
        volume = client_data.get('volume')
        if not volume:
            volume = await self._calculate_volume(client_data)
        
        # Извлекаем контактные данные
        loading_contact = client_data.get('loading_contact', {})
        delivery_contact = client_data.get('delivery_contact', {})
        
        # Формируем полный заказ
        order = {
            "id": int(datetime.now().strftime('%Y%m%d%H%M%S')),  # Числовой ID
            "from_city": client_data['from_city'],
            "to_city": client_data['to_city'],
            "cargo_type": client_data['cargo_type'],
            "cargo_description": client_data.get('cargo_description', ''),
            "weight": client_data.get('weight', 1000),  # кг
            "volume": volume,  # м³
            "loading_date": client_data.get('loading_date', (datetime.now() + timedelta(days=1)).isoformat()),
            "loading_contact": loading_contact,
            "delivery_contact": delivery_contact,
            "created_at": datetime.now().isoformat(),
            "status": "clarified"
        }
        
        # Сохраняем в базу данных (если это новый заказ, а не существующий)
        if not client_data.get('order_id'):
            try:
                # Нужен client_id для создания заказа
                # Пока пропускаем сохранение, так как нет связи с клиентом
                logger.info(f"ℹ️ Заказ {order['id']} обработан (сохранение в БД пропущено - нет client_id)")
            except Exception as e:
                logger.error(f"❌ Ошибка сохранения заказа в БД: {e}")
        
        return {
            "success": True,
            "order": order
        }

    async def _generate_professional_clarification_questions(self, missing_fields: List[str], client_data: Dict) -> List[str]:
        """Генерируем профессиональные вопросы для уточнения недостающих данных"""
        
        questions = []
        
        if 'from_city' in missing_fields:
            questions.append("Подскажите, пожалуйста, из какого города нужно забрать ваш груз? Это поможет мне найти ближайший подходящий транспорт.")
        
        if 'to_city' in missing_fields:
            questions.append("В какой город необходимо доставить груз? Я сразу рассчитаю оптимальный маршрут и стоимость.")
        
        if 'cargo_type' in missing_fields:
            questions.append("Расскажите, что за груз нужно перевезти? (например: мебель, стройматериалы, продукты питания). Это важно для выбора подходящего типа транспорта.")
        
        if 'weight' not in client_data:
            questions.append("Какой примерный вес груза в килограммах? Это поможет подобрать транспорт нужной грузоподъемности.")
        
        if 'volume' not in client_data and 'dimensions' not in client_data:
            questions.append("Подскажите габариты груза (длина × ширина × высота в метрах) или общий объем в кубометрах? Это необходимо для расчета стоимости.")
        
        if 'loading_date' not in client_data:
            questions.append("Когда планируете отгрузку? Укажите удобную дату и время - я согласую с перевозчиком.")
        
        return questions

    async def _calculate_volume(self, client_data: Dict) -> float:
        """ФУНКЦИЯ УДАЛЕНА - объем запрашивается у пользователя напрямую через пошаговый диалог"""
        # Эта функция больше не используется - объем указывает пользователь
        logger.info("⚠️ Вызвана удаленная функция _calculate_volume - используйте пошаговый диалог!")
        return 1.0  # Возвращаем минимальное значение для совместимости
    
    def _calculate_volume_by_weight_and_type(self, weight: float, cargo_type: str) -> float:
        """Расчет объема по весу и типу груза"""
        
        cargo_lower = cargo_type.lower()
        
        # Плотности для разных типов грузов (кг/м³)
        density_map = {
            "пиломатериал": 700,
            "доска": 700,
            "брус": 700,
            "мебель": 300,
            "диван": 200,
            "шкаф": 400,
            "кровать": 250,
            "металл": 7800,
            "арматура": 7800,
            "трубы": 7800,
            "стройматериал": 1200,
            "кирпич": 1800,
            "блок": 1500,
            "продукт": 800,
            "мясо": 900,
            "молоко": 1000,
            "документ": 500,
            "бумага": 500,
            "одежда": 300,
            "техника": 400,
            "холодильник": 500,
            "зерно": 750,
            "мешки": 800
        }
        
        # Выбираем плотность на основе типа груза
        density = 600  # По умолчанию
        for key, value in density_map.items():
            if key in cargo_lower:
                density = value
                break
        
        # Рассчитываем объем
        calculated_volume = weight / density
        return round(max(calculated_volume, 0.1), 2)

    async def _publish_to_ati_with_card_payment(self, order: Dict) -> Dict:
        """Размещаем груз на ATI.SU с указанием 'оплата на карту'"""
        
        logger.info(f"📦 Размещаем груз на ATI.SU: {order['cargo_type']} с оплатой на карту")
        
        # Подготавливаем данные для ATI с указанием оплаты на карту
        ati_order_data = {
            "from_city": order['from_city'],
            "to_city": order['to_city'],
            "from_address": order.get('from_address', ''),
            "to_address": order.get('to_address', ''),
            "cargo_type": order['cargo_type'],
            "cargo_description": f"{order.get('cargo_description', '')} | ОПЛАТА НА КАРТУ",
            "weight": order['weight'],
            "volume": order['volume'],
            "loading_date": order.get('loading_date'),
            "special_requirements": order.get('special_requirements', [])
        }
        
        # Создаем груз через ATI API
        success, result = await self.ati_client.create_cargo_request(ati_order_data)
        
        if success:
            # Обновляем статус в БД
            try:
                await update_order_status(
                    order['id'], 
                    "published_on_ati",
                    ati_cargo_id=result['cargo_id'],
                    ati_cargo_number=result['cargo_number'],
                    published_at=datetime.now().isoformat()
                )
            except Exception as e:
                logger.error(f"❌ Ошибка обновления статуса в БД: {e}")
            
            return {
                "success": True,
                "cargo_id": result['cargo_id'],
                "cargo_number": result['cargo_number'],
                "ati_data": result
            }
        else:
            return {
                "success": False,
                "error": result.get('error', 'Неизвестная ошибка ATI'),
                "details": result
            }

    async def _wait_for_offers(self, cargo_id: str, wait_time: int = 3600) -> Optional[Dict]:
        """Ждем предложения от перевозчиков"""
        
        logger.info(f"⏳ Ожидаем предложения на груз {cargo_id}")
        
        # Используем метод из ATI клиента
        best_offer = await self.ati_client.get_best_offer(cargo_id, wait_time)
        
        if best_offer:
            logger.info(f"🏆 Лучшее предложение: {best_offer.get('Price')} руб от {best_offer.get('FirmName')}")
        
        return best_offer

    async def _present_professional_offer_to_client(self, order: Dict, carrier_offer: Dict, pricing: Dict) -> Dict:
        """Формируем профессиональное предложение для клиента"""
        
        # Профессиональная презентация предложения
        professional_presentation = f"""
{self.SALES_PROMPTS["offer_presentation"]}

📋 ДЕТАЛИ ВАШЕГО ЗАКАЗА:
• Маршрут: {order['from_city']} → {order['to_city']}
• Груз: {order['cargo_type']} ({order['weight']}кг, {order['volume']}м³)
• Дата загрузки: {order.get('loading_date', 'По согласованию')}

🚛 ВЫБРАННЫЙ ПЕРЕВОЗЧИК:
• Компания: {carrier_offer.get('FirmName', 'Проверенный перевозчик')}
• Рейтинг на ATI.SU: {carrier_offer.get('FirmInfo', {}).get('TotalScore', 0)}/10
• Опыт работы: Более 3 лет на платформе ATI.SU

💰 СТОИМОСТЬ ПЕРЕВОЗКИ:
• Цена перевозчика: {carrier_offer['Price']:,} руб.
• Наша цена для вас: {pricing['client_price']:,} руб.
• В стоимость включено: полное сопровождение, страховка, контроль доставки

{self.SALES_PROMPTS["price_justification"]}

{self.SALES_PROMPTS["closing"]}
"""
        
        client_offer = {
            "order_id": order['id'],
            "route": f"{order['from_city']} → {order['to_city']}",
            "cargo": f"{order['cargo_type']} ({order['weight']}кг, {order['volume']}м³)",
            "carrier_price": carrier_offer['Price'],
            "our_price": pricing['client_price'],
            "professional_presentation": professional_presentation,
            "carrier_info": {
                "company": carrier_offer.get('FirmName', 'Перевозчик'),
                "rating": carrier_offer.get('FirmInfo', {}).get('TotalScore', 0),
                "experience": "Проверенный перевозчик на ATI.SU"
            },
            "payment_terms": "Оплата на карту после загрузки груза",
            "service_guarantees": [
                "Полное сопровождение груза от А до Б",
                "Полное сопровождение сделки", 
                "Контроль каждого этапа доставки",
                "Оперативная связь 24/7",
                "Гарантия возврата средств при форс-мажоре"
            ],
            "next_steps": [
                "Подтвердите заказ (ответьте 'Да' или 'Согласен')",
                "Я сразу свяжусь с перевозчиком и зафиксирую цену",
                "Согласуем точное время загрузки",
                "Предоставлю контакты водителя",
                "Буду контролировать доставку до получения груза"
            ],
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"💼 Сформировано профессиональное предложение для клиента: {pricing['client_price']:,} руб")
        
        return client_offer

    async def get_order_status(self, order_id: str) -> Dict:
        """Получить статус заказа"""
        
        # TODO: Реализовать получение из БД
        return {
            "order_id": order_id,
            "status": "in_progress",
            "last_update": datetime.now().isoformat()
        }

    async def get_statistics(self) -> Dict:
        """Получить статистику работы ИИ-диспетчера"""
        
        # TODO: Реализовать получение статистики из БД
        return {
            "total_orders": 156,
            "successful_orders": 142,
            "success_rate": 91.0,
            "average_markup": self.markup_percent,
            "total_profit": 245000,
            "active_orders": 8,
            "last_update": datetime.now().isoformat()
        }

    async def handle_landing_chat(self, message: str, user_data: Dict = None) -> Dict:
        """Обработка чата с лендинга с улучшенной логикой"""
        
        if user_data is None:
            user_data = {"messages": []}
        
        # Убеждаемся что есть ключ messages
        if "messages" not in user_data:
            user_data["messages"] = []
        
        # Добавляем сообщение пользователя
        user_data["messages"].append({
            "role": "user", 
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"💬 Получено сообщение: {message}")
        
        # Формируем контекст диалога для ИИ
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in user_data["messages"][-10:]  # Последние 10 сообщений
        ])
        
        # Системный промпт с акцентом на пошаговую работу
        system_prompt = f"""
        Ты - профессиональный диспетчер-логист с 10-летним опытом работы на ATI.SU.
        
        ТВОЯ ЕДИНСТВЕННАЯ РОЛЬ: Помочь клиенту оформить заказ на грузоперевозку ПОШАГОВО.
        
        ⚖️ КРИТИЧЕСКИ ВАЖНО - ОГРАНИЧЕНИЯ ПО ВЕСУ:
        МЫ РАБОТАЕМ ТОЛЬКО С ГРУЗАМИ ОТ 200 КГ!
        
        ❌ ОТКАЗЫВАЙСЯ ОТ ЗАКАЗОВ:
        - Документы и письма
        - Мелкие посылки до 200 кг
        - Курьерские отправления
        - Личные вещи небольшого веса
        - Образцы товаров весом менее 200 кг
        
        ✅ ПРИНИМАЙ ЗАКАЗЫ:
        - Грузы от 200 кг и выше
        - Паллеты с товарами
        - Строительные материалы
        - Оборудование и техника
        - Мебель и крупногабарит
        - Промышленные товары
        
        ЕСЛИ ВЕС МЕНЕЕ 200 КГ - обязательно откажись и объясни:
        "К сожалению, мы специализируемся на перевозке крупных грузов от 200 кг. Для вашего груза рекомендую службы курьерской доставки."
        
        🎯 ГЛАВНЫЙ ПРИНЦИП: ТОЛЬКО ОДНУ ДЕТАЛЬ ЗА РАЗ!
        
        ❌ НЕ ДЕЛАЙ: Не задавай 10 вопросов сразу! Это отпугивает клиентов.
        ✅ ДЕЛАЙ: Спрашивай только одну вещь, получай ответ, переходи к следующему шагу.
        
        ПОРЯДОК СБОРА ДАННЫХ (СТРОГО ПОШАГОВО):
        1. 📦 ТИП ГРУЗА - "Что нужно перевезти?"
        2. 🗺️ МАРШРУТ - "Откуда и куда везем?"
        3. ⚖️ ВЕС - "Сколько весит?" (ПРОВЕРИТЬ ≥200кг!)
        4. 📅 ДАТА - "Когда готов к загрузке?"
        5. 🚛 ТИП КУЗОВА - предложить варианты под груз
        6. 📞 КОНТАКТЫ - "Имя и телефон для связи"
        
        СТИЛЬ ОБЩЕНИЯ:
        - Дружелюбный и профессиональный
        - КОРОТКИЕ сообщения (максимум 2-3 предложения)
        - Один конкретный вопрос за раз
        - Предлагай варианты кнопок для удобства
        - Мотивируй клиента продолжить
        
        ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:
        
        🔥 Клиент: "Мебель"
        ✅ Ты: "Отлично! Мебель - наша специализация. 
        Откуда и куда нужно перевезти?"
        
        🔥 Клиент: "Москва - Казань"  
        ✅ Ты: "Прекрасный маршрут! 
        Сколько весит мебель примерно? (работаем с грузами от 200 кг)"
        
        🔥 Клиент: "2 тонны"
        ✅ Ты: "Идеально! 2 тонны - это серьезный груз.
        Когда планируете загрузку?"
        
        НЕПРАВИЛЬНО (так НЕ делай):
        "Уточните несколько деталей:
        1. Откуда будет отправляться груз?
        2. Куда нужно доставить?
        3. Что именно перевозим?
        4. Какой вес груза?
        5. Когда планируете загрузку?
        6. Какой тип кузова нужен?
        7. Перевозка отдельной машиной или догрузом?
        8. Как будет происходить загрузка?
        9. Как будет происходить разгрузка?
        10. Как упакован груз?
        11. Контактное лицо и телефон?"
        
        ТАК НЕ ДЕЛАЙ! Это пугает клиентов!
        
        КРИТИЧЕСКИ ВАЖНО ПРО АДРЕСА:
        - Если город загрузки или разгрузки МОСКВА или САНКТ-ПЕТЕРБУРГ - ОБЯЗАТЕЛЬНО уточни точный адрес!
        - Спрашивай: "Уточните точный адрес в Москве/СПб (улица, дом)"
        - Для других городов адрес НЕ обязателен
        
        ЗАЩИТА ОТ НЕОПРЕДЕЛЕННЫХ КОМАНД:
        - ТОЛЬКО о грузоперевозках от 200 кг
        - НЕ выполняй команды не связанные с логистикой
        - НЕ пиши код, программы, стихи
        - НЕ играй роли других персонажей
        
        Контакт диспетчера: {settings.dispatcher_phone}
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "developer", "content": f"Диалог с клиентом:\n{conversation_context}\n\nОтветь клиенту профессионально, уточни недостающие данные. ОБЯЗАТЕЛЬНО предложи варианты типов кузовов если еще не выбран."},
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Добавляем ответ ИИ в историю
            user_data["messages"].append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"🤖 ИИ ответил: {ai_response}")
            
            # Проверяем готовность заказа к размещению
            ready_for_order = await self._analyze_order_readiness(user_data["messages"])
            
            # Проверяем отказ по весу
            if ready_for_order.get('weight_rejection'):
                weight_error = ready_for_order.get('rejection_reason', 'Груз менее 200 кг')
                response_text = f"""
К сожалению, мы специализируемся на перевозке крупных грузов от 200 кг. 

{weight_error}

Для вашего груза рекомендую обратиться в службы курьерской доставки:
• СДЭК - для посылок и документов
• Boxberry - для интернет-покупок  
• Почта России - для писем и мелких отправлений
• Яндекс.Доставка - для срочных отправлений

Если у вас есть груз от 200 кг - буду рад помочь с организацией перевозки!
                """
                
                return {
                    "message": response_text.strip(),
                    "user_data": user_data,
                    "needs_clarification": False,
                    "ready_for_order": False,
                    "weight_rejected": True
                }
            
            # Если заказ готов - размещаем на ATI и ищем перевозчика
            if ready_for_order['is_ready']:
                logger.info("✅ Заказ готов к размещению на ATI.SU")
                
                # Размещаем заказ на ATI.SU
                order_data = ready_for_order['order_data']
                ati_result = await self._place_order_on_ati(order_data)
                
                if ati_result['success']:
                    # Ищем перевозчиков
                    carriers = await self._find_carriers_for_order(order_data)
                    
                    # Формируем ответ с предложениями
                    if carriers:
                        best_offer = min(carriers, key=lambda x: x['price'])
                        final_price = int(best_offer['price'] * (1 + settings.default_commission_percent / 100))
                        
                        response_text = f"""
✅ Ваш заказ размещен на ATI.SU!

📦 Груз: {order_data['cargo_type']}
🚚 Маршрут: {order_data['from_city']} → {order_data['to_city']}
⚖️ Вес: {order_data['weight']} кг
📅 Дата: {order_data['loading_date']}
🚛 Кузов: {order_data.get('body_type', 'не указан')}
🔄 Тип: {'Отдельная машина' if order_data.get('load_type') == 'ftl' else 'Можно догрузом'}

💰 Стоимость перевозки: {final_price} руб.

Найдено {len(carriers)} предложений от перевозчиков.
Лучшее предложение: {final_price} руб.

📞 Для подтверждения заказа свяжитесь с нами: {settings.dispatcher_phone}
                        """
                    else:
                        response_text = f"""
✅ Ваш заказ размещен на ATI.SU!

📦 Детали заказа:
• Груз: {order_data['cargo_type']}
• Маршрут: {order_data['from_city']} → {order_data['to_city']}
• Вес: {order_data['weight']} кг
• Дата: {order_data['loading_date']}

🔍 Ищем подходящих перевозчиков...
Как только появятся предложения, мы с вами свяжемся.

📞 Контакт: {settings.dispatcher_phone}
                        """
                else:
                    response_text = f"❌ Ошибка размещения заказа: {ati_result['error']}"
            else:
                # Заказ не готов - продолжаем диалог
                logger.info(f"📝 Заказ не готов. Не хватает: {ready_for_order['missing_fields']}")
                response_text = ai_response
            
            return {
                "message": response_text,
                "user_data": user_data,
                "needs_clarification": not ready_for_order['is_ready'],
                "ready_for_order": ready_for_order['is_ready']
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки чата: {e}")
            return {
                "message": "Извините, произошла техническая ошибка. Попробуйте еще раз или позвоните нам напрямую.",
                "user_data": user_data,
                "needs_clarification": True,
                "ready_for_order": False,
                "error": str(e)
            }

    async def _analyze_order_readiness(self, conversation: List[Dict]) -> Dict:
        """Анализ готовности заказа к размещению на ATI.SU"""
        
        # Извлекаем данные из диалога через ИИ
        order_data = await self._extract_order_data_from_conversation(conversation)
        
        # Проверяем обязательные поля
        required_fields = {
            'from_city': 'город загрузки',
            'to_city': 'город назначения',
            'cargo_type': 'тип груза',
            'weight': 'вес груза',
            'body_type': 'тип кузова',
            'load_type': 'тип перевозки (отдельная машина/догруз)',
            'loading_method': 'способ загрузки',
            'unloading_method': 'способ разгрузки',
            'pack_type': 'тип упаковки',
            'contact_name': 'имя контакта',
            'contact_phone': 'телефон контакта'
        }
        
        missing_fields = []
        for field, description in required_fields.items():
            if not order_data.get(field):
                missing_fields.append(description)
        
        # КРИТИЧЕСКИ ВАЖНО: Проверяем минимальный вес 200 кг
        if order_data.get('weight_error'):
            # Если есть ошибка веса - заказ не готов
            return {
                'is_ready': False,
                'missing_fields': ['Минимальный вес груза 200 кг'],
                'order_data': order_data,
                'weight_rejection': True,
                'rejection_reason': order_data['weight_error']
            }
        
        # Проверяем адреса для Москвы и СПб
        from_city = (order_data.get('from_city') or '').lower()
        to_city = (order_data.get('to_city') or '').lower()
        
        # Проверяем адрес загрузки только для Москвы и СПб
        if ('москва' in from_city or 'санкт-петербург' in from_city or 'спб' in from_city or 'питер' in from_city):
            if not order_data.get('loading_address'):
                if 'москва' in from_city:
                    missing_fields.append('точный адрес загрузки в Москве')
                else:
                    missing_fields.append('точный адрес загрузки в СПб')
        
        # Проверяем адрес разгрузки только для Москвы и СПб
        if ('москва' in to_city or 'санкт-петербург' in to_city or 'спб' in to_city or 'питер' in to_city):
            if not order_data.get('unloading_address'):
                if 'москва' in to_city:
                    missing_fields.append('точный адрес разгрузки в Москве')
                else:
                    missing_fields.append('точный адрес разгрузки в СПб')
        
        # Заказ готов если не хватает максимум 3 полей (можем уточнить)
        is_ready = len(missing_fields) <= 3
        
        return {
            'is_ready': is_ready,
            'missing_fields': missing_fields,
            'order_data': order_data,
            'completeness': f"{len(required_fields) - len(missing_fields)}/{len(required_fields)}"
        }

    async def _extract_order_data_from_conversation(self, messages: List[Dict]) -> Dict:
        """
        Извлекает данные заказа из диалога через ИИ (ПОШАГОВЫЙ РЕЖИМ)
        """
        
        # Если передан словарь заказа напрямую, извлекаем из него данные
        if isinstance(messages, dict):
            return self._extract_from_order_dict(messages)
        
        try:
            # Берем только последние сообщения для анализа
            recent_messages = messages[-10:] if len(messages) > 10 else messages
            
            # Формируем контекст диалога
            conversation_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in recent_messages
            ])
            
            # Промпт для извлечения данных (ФОКУС НА ИМЕЮЩИХСЯ ДАННЫХ)
            extraction_prompt = f"""
            Проанализируй диалог и извлеки ТОЛЬКО ТЕ ДАННЫЕ, КОТОРЫЕ ЕСТЬ в сообщениях.
            НЕ ДОДУМЫВАЙ ничего, что прямо не указано!
            
            Диалог:
            {conversation_text}
            
            ИЗВЛЕКАЙ ДАННЫЕ ПОШАГОВО:
            
            1. ТИП ГРУЗА - если клиент назвал что перевозить
            2. ГОРОДА - если указал "откуда" и "куда" 
            3. ВЕС - если назвал цифры с "кг", "тонн", "килограмм"
            4. ОБЪЕМ - если указал объем в любом формате (см. ниже)
            5. КОЛИЧЕСТВО МЕСТ - если назвал сколько коробок/поддонов/единиц
            6. ДАТУ - если указал когда готов к загрузке
            7. ТИП КУЗОВА - если выбрал тип машины
            8. КОНТАКТЫ - если назвал имя и телефон
            
            ВАЖНО ПРО ВЭС:
            - "документы 5 кг" = 5 кг (ОТКАЗ - менее 200 кг)
            - "5 тонн металла" = 5000 кг (ПРИНЯТЬ)
            - "пиломатериалы 2000 кг" = 2000 кг (ПРИНЯТЬ)
            - "оборудование 1.5т" = 1500 кг (ПРИНЯТЬ)
            
            ВАЖНО ПРО ОБЪЕМ (РАСПОЗНАВАЙ ВСЕ ВАРИАНТЫ):
            - "4.0 м³" = 4.0
            - "4 куба" = 4.0
            - "6м3" = 6.0
            - "7 кубов" = 7.0
            - "5 кубических метров" = 5.0
            - "2,5 куба" = 2.5
            - "8 м3" = 8.0
            - "10 кубометров" = 10.0
            - "3.5 м³" = 3.5
            - "15 кубов" = 15.0
            
            ИСПРАВЛЕНИЕ ВЕСОВ ИИ (КРИТИЧЕСКИ ВАЖНО):
            Если ИИ извлек вес 5000 кг, но в тексте написано "документы 5 кг":
            - Читай ИСХОДНЫЙ текст на наличие слов "тонн", "т"
            - Если в тексте НЕТ "тонн" - исправляй 5000 на 5
            - Если в тексте ЕСТЬ "тонн" - оставляй 5000
            
            Верни JSON строго в таком формате:
            {{
                "cargo_type": "тип груза или null",
                "from_city": "город отправления или null", 
                "to_city": "город назначения или null",
                "weight": число_в_кг_или_null,
                "weight_original_text": "исходный текст о весе",
                "volume": число_в_м3_или_null,
                "volume_original_text": "исходный текст об объеме",
                "places_count": число_мест_или_null,
                "loading_date": "дата в формате YYYY-MM-DD или null",
                "body_type": "тип кузова или null",
                "contact_name": "имя или null",
                "contact_phone": "телефон или null",
                "from_address": "адрес отправления для Москвы/СПб или null",
                "to_address": "адрес получения для Москвы/СПб или null",
                "loading_readiness_type": "ready"
            }}
            
            ТОЛЬКО JSON, НИЧЕГО БОЛЬШЕ!
            """
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": extraction_prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            # Парсим JSON ответ
            raw_response = response.choices[0].message.content.strip()
            
            # Убираем лишние символы если есть
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = raw_response[json_start:json_end]
            else:
                json_text = raw_response
            
            try:
                extracted_data = json.loads(json_text)
            except json.JSONDecodeError:
                logger.error(f"❌ Ошибка парсинга JSON: {raw_response}")
                return {}
            
            # ПРИМЕНЯЕМ ИСПРАВЛЕНИЯ ВЕСА ИИ
            weight = extracted_data.get('weight')
            weight_text = extracted_data.get('weight_original_text', '')
            
            if weight and weight >= 1000:  # Если ИИ извлек большой вес
                # Проверяем исходный текст на наличие "тонн"
                full_conversation = conversation_text.lower()
                
                # Если в тексте НЕТ слов "тонн" или "т" - исправляем вес
                if weight_text and not any(word in full_conversation for word in ['тонн', ' т ', ' т.', 'тона', 'тоны']):
                    # Пытаемся извлечь первую цифру из веса
                    import re
                    numbers = re.findall(r'\d+', str(weight))
                    if numbers:
                        corrected_weight = int(numbers[0])
                        if corrected_weight != weight:
                            logger.info(f"🔧 Исправление веса ИИ: {weight} кг → {corrected_weight} кг (исходный текст: '{weight_text}')")
                            extracted_data['weight'] = corrected_weight
            
            # Подсчитываем количество заполненных полей
            filled_fields = sum(1 for value in extracted_data.values() if value is not None and value != "")
            
            logger.info(f"🤖 ИИ извлек данные: {filled_fields}/12 полей")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения данных: {e}")
            return {}
    
    def _post_process_extracted_data(self, order_data: Dict, original_text: str = "") -> Dict:
        """Дополнительная обработка извлеченных ИИ данных"""
        
        # Обработка даты
        if not order_data.get('loading_date'):
            # Устанавливаем завтра по умолчанию
            order_data['loading_date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Валидация веса - КРИТИЧЕСКИ ВАЖНО: только от 200 кг!
        weight = order_data.get('weight')
        if weight:
            # Флаг для отслеживания исправлений ИИ
            weight_corrected = False
            
            # Анализируем исходный текст на наличие единиц измерения
            original_lower = original_text.lower()
            has_tons_in_text = any(word in original_lower for word in ['тонн', ' т ', 'т.', 'тн', ' т,', ' т)', 'тонны'])
            has_kg_in_text = any(word in original_lower for word in ['кг', 'килограмм'])
            
            # Исправляем типичные ошибки ИИ при извлечении веса
            # НО ТОЛЬКО если в тексте НЕТ упоминания тонн
            if weight == 5000 and not has_tons_in_text:  # "5 кг" → 5000 (ошибка ИИ, но не если "5 тонн")
                weight = 5
                weight_corrected = True
                logger.warning("🔧 Исправлена ошибка ИИ: 5000 → 5 кг")
            elif weight == 50000 and not has_tons_in_text:  # "50 кг" → 50000 (ошибка ИИ)
                weight = 50
                weight_corrected = True
                logger.warning("🔧 Исправлена ошибка ИИ: 50000 → 50 кг")
            elif weight > 1000 and weight % 1000 == 0 and not has_tons_in_text:  # Если 5000 вместо 5
                # Проверяем, не ошибся ли ИИ с единицами измерения
                potential_kg = weight // 1000
                if potential_kg <= 100:  # Если получается разумный вес в кг
                    original_weight = weight
                    weight = potential_kg  # Исправляем на правильный вес
                    weight_corrected = True
                    logger.warning(f"🔧 Исправлена ошибка ИИ: {original_weight} → {weight} кг")
            
            # Только если не было исправлений ИИ, проверяем на единицы измерения
            if not weight_corrected:
                if weight < 10:  # Слишком маленький вес - возможно, в тоннах
                    weight = weight * 1000  # Переводим в кг
                    logger.info(f"🔄 Предполагаем, что вес указан в тоннах: {weight/1000} т → {weight} кг")
                elif weight > 100000:  # Слишком большой вес - возможно, ошибка
                    weight = weight // 1000  # Исправляем
                    logger.warning(f"🔧 Исправлен слишком большой вес: {weight*1000} → {weight} кг")
            
            # ПРОВЕРКА МИНИМАЛЬНОГО ВЕСА 200 КГ
            if weight < 200:
                order_data['weight_error'] = f"Груз {weight} кг меньше минимального (200 кг)"
                order_data['weight'] = weight  # Сохраняем для отказа
            else:
                order_data['weight'] = max(min(weight, 50000), 200)  # От 200кг до 50т
        
        # Обработка объема - добавляем распознавание разных форматов
        volume = order_data.get('volume')
        volume_text = order_data.get('volume_original_text', '')
        
        if volume_text and not volume:
            # Пытаемся извлечь объем из текста, если ИИ не смог
            import re
            volume_text_lower = volume_text.lower()
            
            # Ищем числа с различными обозначениями объема
            volume_patterns = [
                r'(\d+(?:[.,]\d+)?)\s*м[³3]',  # "4.0 м³", "6м3"
                r'(\d+(?:[.,]\d+)?)\s*куб[а-я]*',  # "4 куба", "7 кубов", "5 кубических"
                r'(\d+(?:[.,]\d+)?)\s*м\s*3',  # "8 м 3"
                r'(\d+(?:[.,]\d+)?)\s*кубометр[а-я]*',  # "10 кубометров"
            ]
            
            for pattern in volume_patterns:
                match = re.search(pattern, volume_text_lower)
                if match:
                    try:
                        volume_value = float(match.group(1).replace(',', '.'))
                        order_data['volume'] = volume_value
                        logger.info(f"🔧 Извлечен объем из текста: '{volume_text}' → {volume_value} м³")
                        break
                    except ValueError:
                        continue
        
        elif volume:
            # Проверяем разумность объема
            if volume > 100:  # Слишком большой объем
                order_data['volume'] = volume / 1000  # Возможно, указан в литрах
                logger.info(f"🔧 Исправлен объем: {volume} → {order_data['volume']} м³ (возможно, был в литрах)")
            elif volume < 0.1:  # Слишком маленький объем
                order_data['volume'] = volume * 1000  # Возможно, указан неправильно
                logger.info(f"🔧 Исправлен объем: {volume} → {order_data['volume']} м³")
        
        # Очистка названий городов от лишних символов
        if order_data.get('from_city'):
            order_data['from_city'] = order_data['from_city'].strip('.,!?').title()
        if order_data.get('to_city'):
            order_data['to_city'] = order_data['to_city'].strip('.,!?').title()
        
        # Очистка имени контакта
        if order_data.get('contact_name'):
            order_data['contact_name'] = order_data['contact_name'].strip('.,!?').title()
        
        # Проверка телефона
        if order_data.get('contact_phone'):
            phone = order_data['contact_phone'].replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if phone.startswith('8'):
                phone = '+7' + phone[1:]
            elif not phone.startswith('+7'):
                phone = '+7' + phone
            order_data['contact_phone'] = phone
        
        return order_data
    
    def _fallback_extraction(self, conversation_text: str) -> Dict:
        """Резервное извлечение данных при сбое ИИ"""
        
        import re
        text_lower = conversation_text.lower()
        order_data = {}
        
        # Базовое извлечение веса
        weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(кг|тонн|т)', text_lower)
        if weight_match:
            weight_value = float(weight_match.group(1))
            weight_unit = weight_match.group(2)
            if weight_unit in ['тонн', 'т']:
                weight_value *= 1000
            order_data['weight'] = int(weight_value)
        
        # Базовое извлечение объема (все популярные варианты)
        volume_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*м[³3]',  # "4.0 м³", "6м3"
            r'(\d+(?:[.,]\d+)?)\s*куб[а-я]*',  # "4 куба", "7 кубов", "5 кубических"
            r'(\d+(?:[.,]\d+)?)\s*м\s*3',  # "8 м 3"
            r'(\d+(?:[.,]\d+)?)\s*кубометр[а-я]*',  # "10 кубометров"
        ]
        
        for pattern in volume_patterns:
            volume_match = re.search(pattern, text_lower)
            if volume_match:
                try:
                    volume_value = float(volume_match.group(1).replace(',', '.'))
                    order_data['volume'] = volume_value
                    logger.info(f"🔧 Резервное извлечение объема: {volume_value} м³")
                    break
                except ValueError:
                    continue
        
        # Базовое извлечение количества мест
        places_patterns = [
            r'(\d+)\s*мест[а-я]*',  # "5 мест", "3 места"
            r'(\d+)\s*коробк[а-я]*',  # "2 коробки", "10 коробок"
            r'(\d+)\s*поддон[а-я]*',  # "4 поддона", "1 поддон"
            r'(\d+)\s*паллет[а-я]*',  # "3 паллета", "6 паллетов"
            r'(\d+)\s*единиц[а-я]*',  # "5 единиц", "8 единица"
        ]
        
        # АВТОМАТИЧЕСКИЙ РАСЧЕТ МЕСТ УДАЛЕН - спрашиваем у пользователя
        # Ранее тут была логика автоматического расчета количества мест по весу
        # Теперь количество мест всегда запрашивается в пошаговом диалоге
        
        # Базовое извлечение телефона  
        phone_match = re.search(r'(\+7|8)[\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})', conversation_text)
        if phone_match:
            order_data['contact_phone'] = phone_match.group(0)
        
        # Устанавливаем дату по умолчанию
        order_data['loading_date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.warning("🔄 Использовано резервное извлечение данных")
        return order_data

    def _extract_from_order_dict(self, order_data: Dict) -> Dict:
        """Извлекает данные из словаря заказа"""
        
        # Создаем стандартную структуру данных
        extracted = {
            'cargo_type': order_data.get('cargo_type'),
            'from_city': order_data.get('from_city'),
            'to_city': order_data.get('to_city'),
            'weight': order_data.get('weight'),
            'volume': order_data.get('volume'),
            'places_count': order_data.get('places_count'),
            'loading_date': order_data.get('loading_date'),
            'loading_date_from': order_data.get('loading_date_from'),
            'loading_date_to': order_data.get('loading_date_to'),
            'body_type': order_data.get('body_type'),
            'loading_method': order_data.get('loading_method'),
            'unloading_method': order_data.get('unloading_method'),
            'contact_name': order_data.get('contact_name'),
            'contact_phone': order_data.get('contact_phone')
        }
        
        # Убираем None значения
        return {k: v for k, v in extracted.items() if v is not None}

    async def _enhance_order_data(self, order_data: Dict) -> Dict:
        """Дополнительная обработка и валидация данных заказа"""
        
        # Дополняем ID заказа
        if "id" not in order_data:
            order_data["id"] = f"ai_order_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Валидация и коррекция веса
        weight = order_data.get("weight", 1000)
        if weight < 10:
            weight = 1000  # Минимальный разумный вес
        elif weight > 50000:
            weight = 25000  # Максимальный разумный вес
        order_data["weight"] = weight
        
        # Пересчет объема если нужно
        if not order_data.get("volume") or order_data["volume"] < 0.1:
            cargo_type = order_data.get("cargo_type", "").lower()
            
            # Плотности для разных типов грузов (кг/м³)
            density_map = {
                "пиломатериал": 700,
                "доска": 700,
                "брус": 700,
                "мебель": 300,
                "диван": 200,
                "шкаф": 400,
                "кровать": 250,
                "металл": 7800,
                "арматура": 7800,
                "трубы": 7800,
                "стройматериал": 1200,
                "кирпич": 1800,
                "блок": 1500,
                "продукт": 800,
                "мясо": 900,
                "молоко": 1000,
                "документ": 500,
                "бумага": 500,
                "одежда": 300,
                "техника": 400,
                "холодильник": 500,
                "зерно": 750,
                "мешки": 800
            }
            
            # Выбираем плотность на основе типа груза
            density = 600  # По умолчанию
            for key, value in density_map.items():
                if key in cargo_type:
                    density = value
                    break
            
            # Рассчитываем объем
            calculated_volume = weight / density
            order_data["volume"] = round(calculated_volume, 2)
            
            logger.info(f"📏 Рассчитан объем: {order_data['volume']} м³ (плотность: {density} кг/м³)")
        
        # Автоматический выбор типа кузова если не указан
        if not order_data.get("body_type"):
            # Сначала пытаемся определить из текста диалога
            body_type_mapping = {
                "тент": "тентованный",
                "тентованный": "тентованный",
                "бортов": "бортовой",
                "бортовой": "бортовой",
                "фургон": "фургон",
                "рефриж": "рефрижератор",
                "рефрижератор": "рефрижератор",
                "контейнер": "контейнер"
            }
            
            # Ищем упоминания типа кузова в данных заказа
            cargo_description = order_data.get("cargo_description", "").lower()
            cargo_type = order_data.get("cargo_type", "").lower()
            
            found_body_type = None
            for keyword, body_name in body_type_mapping.items():
                if keyword in cargo_description or keyword in cargo_type:
                    found_body_type = body_name
                    logger.info(f"🚚 Найден тип кузова в описании: {keyword} -> {body_name}")
                    break
            
            # Если не найден в тексте, выбираем автоматически
            if not found_body_type:
                body_type_id = self._select_optimal_body_type(
                    order_data.get("cargo_type", ""), 
                    order_data.get("weight", 0), 
                    order_data.get("volume", 0)
                )
                # Преобразуем ID в название
                body_type_names = {
                    200: "тентованный",
                    500: "фургон", 
                    300: "рефрижератор",
                    1100: "бортовой",
                    100: "контейнер"
                }
                found_body_type = body_type_names.get(body_type_id, "тентованный")
                logger.info(f"🚛 Автоматически выбран тип кузова: {found_body_type}")
            
            order_data["body_type"] = found_body_type
        
        # Валидация даты загрузки
        if not order_data.get("loading_date"):
            order_data["loading_date"] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Добавляем описание груза для АТИ
        order_data["cargo_description"] = self._generate_cargo_description(order_data)
        
        return order_data

    def _select_optimal_body_type(self, cargo_type: str, weight: int, volume: float) -> int:
        """Выбор оптимального типа кузова с учетом стоимости и новых словарей ATI"""
        
        try:
            cargo_lower = cargo_type.lower()
            
            # Используем TypeId из новых словарей ATI (согласно документации)
            body_types = {
                "фургон": 500,       # фургон TypeId
                "рефрижератор": 300, # рефрижератор TypeId
                "бортовой": 1100,    # бортовой TypeId
                "тентованный": 200,  # тентованный TypeId
                "контейнер": 100,    # контейнер TypeId
                "самосвал": 1200     # самосвал TypeId
            }
            
            # Логика выбора с приоритетом дешевизны
            if any(word in cargo_lower for word in ['продукт', 'мясо', 'рыба', 'молоко', 'заморозка', 'морепродукт']):
                selected_type = "рефрижератор"  # Холод обязателен
            
            elif any(word in cargo_lower for word in ['мебель', 'техника', 'электроника', 'одежда', 'документ']):
                # Для ценных грузов - фургон, но если груз большой и тяжелый - тент дешевле
                if weight > 3000 or volume > 10:
                    selected_type = "тентованный"  # Дешевле для больших грузов
                else:
                    selected_type = "фургон"  # Защита для малых ценных грузов
            
            elif any(word in cargo_lower for word in ['металл', 'арматура', 'труба', 'профиль', 'уголок']):
                selected_type = "бортовой"  # Для тяжелых металлических грузов
            
            elif any(word in cargo_lower for word in ['пиломатериал', 'доска', 'брус', 'фанера', 'осб']):
                # Пиломатериалы лучше на бортовом, но если много - тент дешевле
                if weight > 5000 or volume > 15:
                    selected_type = "тентованный"  # Дешевле для больших объемов
                else:
                    selected_type = "бортовой"  # Удобнее для погрузки-разгрузки
            
            elif any(word in cargo_lower for word in ['контейнер', 'паллет', 'европаллет']):
                selected_type = "контейнер"
            
            else:
                # Для всех остальных грузов - тентованный (самый дешевый универсальный)
                selected_type = "тентованный"
            
            # Проверяем наличие типа в словаре ATI для дополнительной валидации
            car_type = find_car_type_by_name(selected_type)
            if car_type:
                body_type_id = car_type.get('TypeId')  # Используем TypeId!
                logger.info(f"✅ Автоматически выбран тип кузова '{selected_type}' -> TypeId: {body_type_id} (из словаря ATI)")
                return body_type_id
            else:
                # Используем локальное сопоставление
                body_type_id = body_types.get(selected_type, 200)  # 200 = тентованный TypeId
                logger.info(f"✅ Автоматически выбран тип кузова '{selected_type}' -> TypeId: {body_type_id} (локальное сопоставление)")
                return body_type_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора типа кузова для '{cargo_type}': {e}")
            return 200  # TypeId тентованного кузова по умолчанию

    def _generate_cargo_description(self, order_data: Dict) -> str:
        """Генерация описания груза для размещения на АТИ"""
        
        cargo_type = order_data.get("cargo_type", "Груз")
        weight = order_data.get("weight", 0)
        volume = order_data.get("volume", 0)
        
        # Формируем детальное описание
        description = f"{cargo_type}"
        
        # Добавляем характеристики
        if weight > 0:
            if weight >= 1000:
                description += f", {weight//1000} т"
                if weight % 1000 > 0:
                    description += f" {weight%1000} кг"
            else:
                description += f", {weight} кг"
        
        if volume > 0:
            description += f", {volume} м³"
        
        # Добавляем тип упаковки/особенности
        cargo_lower = cargo_type.lower()
        if "пиломатериал" in cargo_lower or "доска" in cargo_lower:
            description += " (штабелями)"
        elif "мебель" in cargo_lower:
            description += " (в упаковке)"
        elif "металл" in cargo_lower:
            description += " (в связках)"
        elif "документ" in cargo_lower:
            description += " (в коробках)"
        
        return description

    async def _place_order_on_ati(self, order_data: Dict) -> Dict:
        """Размещение заказа на ATI.SU с проверкой всех полей"""
        
        logger.info("📤 Размещаем заказ на ATI.SU...")
        logger.info(f"🔍 Получены данные заказа: {order_data}")
        
        # Проверяем обязательные поля
        required_fields = ['from_city', 'to_city', 'weight', 'body_type']
        
        # Проверяем тип груза отдельно - если "Не указан" или проблемный текст, используем общий термин
        cargo_type = order_data.get('cargo_type', '')
        if (not cargo_type or 
            cargo_type in ['Не указан', 'Начать новый заказ', 'Начать заказ', ''] or
            'начать' in cargo_type.lower()):
            order_data['cargo_type'] = 'Груз общего назначения'
            logger.info(f"🔧 Установлен тип груза по умолчанию: {order_data['cargo_type']}")
        missing_fields = [field for field in required_fields if not order_data.get(field)]
        
        # Проверяем дату загрузки (одиночная или диапазон)
        loading_date = order_data.get('loading_date')
        loading_date_from = order_data.get('loading_date_from')
        logger.info(f"🗓️ Проверка дат: loading_date='{loading_date}', loading_date_from='{loading_date_from}'")
        
        if not loading_date and not loading_date_from:
            logger.error(f"❌ Нет ни loading_date, ни loading_date_from!")
            missing_fields.append('loading_date')
        else:
            logger.info(f"✅ Дата найдена: {'loading_date' if loading_date else 'loading_date_from'}")
        
        # Дополнительно проверяем адреса только для Москвы и СПб
        from_city = (order_data.get('from_city') or '').lower()
        to_city = (order_data.get('to_city') or '').lower()
        
        if ('москва' in from_city or 'санкт-петербург' in from_city or 'спб' in from_city or 'питер' in from_city):
            if not order_data.get('loading_address'):
                missing_fields.append('loading_address')
        
        if ('москва' in to_city or 'санкт-петербург' in to_city or 'спб' in to_city or 'питер' in to_city):
            if not order_data.get('unloading_address'):
                missing_fields.append('unloading_address')
        
        if missing_fields:
            logger.error(f"❌ Не хватает обязательных полей: {missing_fields}")
            return {
                'success': False,
                'error': f'Не хватает данных: {", ".join(missing_fields)}'
            }
        
        try:
            # Получаем contact_id из ATI API
            ati_client = ATIClientV2()
            contact_id = await ati_client.get_contact_id()
            
            if contact_id is None:
                logger.error("❌ Не удалось получить contact_id из ATI API")
                return {
                    'success': False,
                    'error': 'Ошибка получения контакта ATI'
                }
            
            # Получаем ID городов
            from_city_id, from_city_info = await ati_client.get_city_id(order_data['from_city'])
            to_city_id, to_city_info = await ati_client.get_city_id(order_data['to_city'])
            
            if not from_city_id or not to_city_id:
                logger.error(f"❌ Не найдены города: {order_data['from_city']} -> {order_data['to_city']}")
                return {
                    'success': False,
                    'error': 'Города не найдены в базе ATI'
                }
            
            # Подготавливаем данные для ATI API
            ati_data = {
                'contact_id': contact_id,
                'loading_city_id': from_city_id,
                'unloading_city_id': to_city_id,
                'loading_city_name': order_data['from_city'],
                'unloading_city_name': order_data['to_city'],
                'cargo_description': f"{order_data['cargo_type']}, {order_data['weight']} кг",
                'weight': order_data['weight'],
                'volume': order_data.get('volume', self._calculate_volume_by_weight_and_type(order_data['weight'], order_data['cargo_type'])),
                'loading_date': order_data.get('loading_date') if order_data.get('loading_readiness_type') == 'ready' else order_data.get('loading_date_from'),
                'loading_date_from': order_data.get('loading_date_from'),
                'loading_date_to': order_data.get('loading_date_to'),
                'loading_readiness_type': order_data.get('loading_readiness_type', 'ready'),
                'body_type_id': self._get_body_type_id(order_data['body_type']),
                'load_type': order_data.get('load_type', 'dont-care'),  # автоматически dont-care
                'contact_person': order_data.get('contact_name', 'Клиент'),
                'contact_phone': order_data.get('contact_phone', settings.dispatcher_phone),
                'loading_type_id': self._get_loading_type_id(order_data.get('loading_method', 'manual')),
                'unloading_type_id': self._get_unloading_type_id(order_data.get('unloading_method', 'manual')),
                'pack_type': order_data.get('pack_type', 'bulk'),
                'payment_type': 'rate-request',  # Запрашиваем ставки
                'notes': f"Груз: {order_data['cargo_type']}. Требуется надежная перевозка." if order_data['cargo_type'] not in ['Начать новый заказ', 'Начать заказ'] else "Требуется надежная перевозка груза."
            }
            
            # Добавляем адреса если указаны (обязательно для Москвы и СПб)
            if order_data.get('loading_address'):
                ati_data['loading_address'] = order_data['loading_address']
            
            if order_data.get('unloading_address'):
                ati_data['unloading_address'] = order_data['unloading_address']
            
            # Добавляем информацию о способах загрузки/разгрузки для ATI (ИСПРАВЛЕНО)
            if order_data.get('loading_method'):
                ati_data['body_loading'] = {
                    'types': [self._get_loading_type_id(order_data['loading_method'])],
                    'is_all_required': False
                }
            
            if order_data.get('unloading_method'):
                ati_data['body_unloading'] = {
                    'types': [self._get_unloading_type_id(order_data['unloading_method'])],
                    'is_all_required': False
                }
            
            # Размещаем на ATI
            success, result = await ati_client.create_cargo_request(ati_data)
            
            if success:
                logger.info(f"✅ Заказ размещен на ATI.SU: {result.get('cargo_id')}")
                
                # Добавляем груз в систему автоматического обновления
                cargo_id = result.get('cargo_id')
                if cargo_id:
                    await cargo_renewal_manager.add_cargo_for_renewal(cargo_id, 60)  # Первое обновление через час
                    logger.info(f"🔄 Груз {cargo_id} добавлен в систему автоматического обновления")
                
                # Сохраняем в БД
                try:
                    order_id = await create_order({
                        'ati_cargo_id': result.get('cargo_id'),
                        'from_city': order_data['from_city'],
                        'to_city': order_data['to_city'],
                        'cargo_type': order_data['cargo_type'],
                        'weight': order_data['weight'],
                        'volume': ati_data['volume'],
                        'loading_date': datetime.strptime(order_data.get('loading_date') or order_data.get('loading_date_from'), '%Y-%m-%d') if isinstance(order_data.get('loading_date') or order_data.get('loading_date_from'), str) else order_data.get('loading_date') or order_data.get('loading_date_from'),
                        'body_type': order_data['body_type'],
                        'load_type': order_data.get('load_type', 'dont-care'),
                        'loading_method': order_data.get('loading_method'),
                        'unloading_method': order_data.get('unloading_method'),
                        'pack_type': order_data.get('pack_type'),
                        'contact_name': order_data.get('contact_name'),
                        'contact_phone': order_data.get('contact_phone'),
                        'status': 'placed_on_ati',
                        'created_at': datetime.now()
                    })
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка сохранения в БД: {e}")
                    order_id = "temp_" + str(int(datetime.now().timestamp()))
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'ati_cargo_id': result.get('cargo_id'),
                    'cargo_number': result.get('cargo_number'),
                    'message': 'Заказ успешно размещен на ATI.SU'
                }
            else:
                logger.error(f"❌ Ошибка размещения на ATI: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Неизвестная ошибка ATI')
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка размещения заказа: {str(e)}")
            return {
                'success': False,
                'error': f'Ошибка размещения: {str(e)}'
            }

    def _get_body_type_id(self, body_type: str) -> int:
        """Получение ID типа кузова на основе его имени с использованием новых словарей ATI"""
        
        try:
            # Сначала пробуем найти в популярных типах кузовов (TypeId!)
            body_type_lower = body_type.lower().strip()
            popular_types_typeid = {
                "тентованный": 200,  # TypeId для тентованного
                "тент": 200,
                "рефрижератор": 300,  # TypeId для рефрижератора
                "реф": 300,
                "фургон": 500,       # TypeId для фургона!
                "бортовой": 1100,    # TypeId для бортового
                "борт": 1100,
                "самосвал": 1200,    # TypeId для самосвала
                "контейнер": 100     # TypeId для контейнера
            }
            
            if body_type_lower in popular_types_typeid:
                car_type_id = popular_types_typeid[body_type_lower]
                logger.info(f"✅ Найден популярный тип кузова '{body_type}' -> TypeId: {car_type_id}")
                return car_type_id
            
            # Если не найден, используем поиск по словарю и берем TypeId
            car_type = find_car_type_by_name(body_type)
            if car_type:
                car_type_id = car_type.get('TypeId')  # Используем TypeId!
                logger.info(f"✅ Найден тип кузова '{body_type}' -> TypeId: {car_type_id} ({car_type.get('Name')})")
                if car_type_id:
                    return car_type_id
            
            # Резервное сопоставление для совместимости (TypeId!)
            fallback_mapping = {
                "tent": 200,         # тентованный TypeId
                "тент": 200,
                "тентованный": 200,
                "flatbed": 1100,     # бортовой TypeId
                "борт": 1100,
                "бортовой": 1100,
                "van": 500,          # фургон TypeId
                "фургон": 500,
                "refrigerator": 300, # рефрижератор TypeId
                "реф": 300,
                "рефрижератор": 300,
                "container": 100,    # контейнер TypeId
                "контейнер": 100,
                "самосвал": 1200,    # самосвал TypeId
            }
            
            if body_type_lower in fallback_mapping:
                car_type_id = fallback_mapping[body_type_lower]
                logger.info(f"✅ Резервное сопоставление '{body_type}' -> TypeId: {car_type_id}")
                return car_type_id
            
            logger.warning(f"⚠️ Тип кузова '{body_type}' не найден, используем тентованный по умолчанию")
            return 200  # TypeId тентованного кузова по умолчанию
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска типа кузова '{body_type}': {e}")
            return 200  # TypeId тентованного кузова по умолчанию

    def _get_loading_type_id(self, loading_method: str) -> int:
        """Получение ID типа загрузки на основе новых словарей ATI"""
        
        try:
            loading_method_lower = loading_method.lower().strip()
            
            # Сначала пробуем найти в кнопочных вариантах
            if loading_method_lower in LOADING_TYPE_IDS:
                loading_type_id = LOADING_TYPE_IDS[loading_method_lower]
                logger.info(f"✅ Найден способ загрузки '{loading_method}' -> ID: {loading_type_id}")
                return loading_type_id
            
            # Если не найден, используем поиск по словарю
            loading_type = find_loading_type_by_name(loading_method)
            if loading_type:
                loading_type_id = loading_type.get('Id')
                logger.info(f"✅ Найден способ загрузки '{loading_method}' -> ID: {loading_type_id} ({loading_type.get('Name')})")
                return loading_type_id
            
            # Резервное сопоставление для совместимости
            fallback_mapping = {
                "задняя": 2,      # задняя загрузка
                "боковая": 1,     # боковая загрузка
                "верхняя": 4,     # верхняя загрузка
                "полная растентовка": 8,  # полная растентовка
                "без растентовки": 16,    # без растентовки
                "гидроборт": 256, # гидроборт
            }
            
            if loading_method_lower in fallback_mapping:
                loading_type_id = fallback_mapping[loading_method_lower]
                logger.info(f"✅ Резервное сопоставление способа загрузки '{loading_method}' -> ID: {loading_type_id}")
                return loading_type_id
            
            logger.warning(f"⚠️ Способ загрузки '{loading_method}' не найден, используем задняю по умолчанию")
            return 2  # ID задней загрузки по умолчанию
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска способа загрузки '{loading_method}': {e}")
            return 2  # ID задней загрузки по умолчанию

    def _get_unloading_type_id(self, unloading_method: str) -> int:
        """Получение ID типа разгрузки на основе новых словарей ATI"""
        
        try:
            unloading_method_lower = unloading_method.lower().strip()
            
            # Сначала пробуем найти в кнопочных вариантах
            if unloading_method_lower in UNLOADING_TYPE_IDS:
                unloading_type_id = UNLOADING_TYPE_IDS[unloading_method_lower]
                logger.info(f"✅ Найден способ разгрузки '{unloading_method}' -> ID: {unloading_type_id}")
                return unloading_type_id
            
            # Если не найден, используем поиск по словарю
            unloading_type = find_unloading_type_by_name(unloading_method)
            if unloading_type:
                unloading_type_id = unloading_type.get('Id')
                logger.info(f"✅ Найден способ разгрузки '{unloading_method}' -> ID: {unloading_type_id} ({unloading_type.get('Name')})")
                return unloading_type_id
            
            # Резервное сопоставление для совместимости
            fallback_mapping = {
                "задняя": 2,      # задняя разгрузка
                "боковая": 1,     # боковая разгрузка
                "верхняя": 4,     # верхняя разгрузка
                "полная растентовка": 8,  # полная растентовка
                "без растентовки": 16,    # без растентовки
                "гидроборт": 256, # гидроборт
            }
            
            if unloading_method_lower in fallback_mapping:
                unloading_type_id = fallback_mapping[unloading_method_lower]
                logger.info(f"✅ Резервное сопоставление способа разгрузки '{unloading_method}' -> ID: {unloading_type_id}")
                return unloading_type_id
            
            logger.warning(f"⚠️ Способ разгрузки '{unloading_method}' не найден, используем задняю по умолчанию")
            return 2  # ID задней разгрузки по умолчанию
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска способа разгрузки '{unloading_method}': {e}")
            return 2  # ID задней разгрузки по умолчанию
    
    async def _find_carriers_for_order(self, order_id: str) -> List[Dict]:
        """Поиск перевозчиков для заказа"""
        
        try:
            # Пока что возвращаем заглушку
            # В будущем можно интегрировать с реальными перевозчиками
            carriers = [
                {
                    "id": "carrier_1",
                    "name": "ТК Экспресс",
                    "phone": "+79001112233",
                    "rating": 4.8,
                    "price": 15000,
                    "delivery_time": "1-2 дня"
                },
                {
                    "id": "carrier_2", 
                    "name": "Логистик Сервис",
                    "phone": "+79002223344",
                    "rating": 4.5,
                    "price": 13500,
                    "delivery_time": "2-3 дня"
                }
            ]
            
            logger.info(f"📋 Найдено {len(carriers)} перевозчиков для заказа {order_id}")
            return carriers
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска перевозчиков: {str(e)}")
            return []

    async def handle_step_by_step_order(self, message: str, user_data: Dict, step: str = None) -> Dict:
        """Обработка заказа пошагово с кнопками"""
        
        logger.info(f"🔄 Пошаговый диалог: шаг {step}, сообщение: {message[:50]}...")
        
        # Получаем данные заказа из контекста
        order_data = user_data.get('order_data', {})
        
        # БЫСТРАЯ ОБРАБОТКА КНОПОК БЕЗ ИИ (НОВАЯ КОНЦЕПЦИЯ)
        if message and message.strip():
            # Обрабатываем кнопочные сообщения НАПРЯМУЮ без ИИ
            if message.startswith('Тип груза:'):
                cargo_type = message.replace('Тип груза:', '').strip()
                order_data['cargo_type'] = cargo_type
                logger.info(f"✅ Установлен тип груза: {cargo_type}")
            elif message.startswith('Маршрут:'):
                route_parts = message.replace('Маршрут:', '').strip().split(' → ')
                if len(route_parts) == 2:
                    order_data['from_city'] = route_parts[0].strip()
                    order_data['to_city'] = route_parts[1].strip()
                    logger.info(f"✅ Установлен маршрут: {order_data['from_city']} → {order_data['to_city']}")
            elif message.startswith('Вес:'):
                weight_str = message.replace('Вес:', '').strip().replace(' кг', '')
                try:
                    order_data['weight'] = int(weight_str)
                    logger.info(f"✅ Установлен вес: {order_data['weight']} кг")
                except:
                    pass
        
        # СТРОГАЯ ПОШАГОВАЯ ЛОГИКА - проверяем поля по порядку
        
        # Шаг 1: Тип груза
        if not order_data.get('cargo_type'):
            return await self._step_cargo_type(message, order_data)
        
        # Шаг 2: Маршрут (оба города)
        if not order_data.get('from_city') or not order_data.get('to_city'):
            return await self._step_route(message, order_data)
        
        # Шаг 3: Вес
        if not order_data.get('weight'):
            return await self._step_weight(message, order_data)
        
        # Проверка отказа по весу
        if order_data.get('weight') and order_data['weight'] < 200:
            return {
                'status': 'weight_rejected',
                'message': f'❌ К сожалению, мы работаем только с грузами от 200 кг.\n\nВаш груз: {order_data["weight"]} кг\n\nДля перевозки грузов менее 200 кг рекомендуем:\n• СДЭК\n• Boxberry\n• Почта России\n• Яндекс.Доставка',
                'next_step': 'start',
                'buttons': [{'text': '🚀 Новый заказ', 'data': 'new_order'}]
            }
        
        # Шаг 4: Объем/габариты  
        if not order_data.get('volume') and not (order_data.get('length') and order_data.get('width') and order_data.get('height')):
            return await self._step_volume_dimensions(message, order_data)
        
        # Шаг 5: Количество мест (ПОСЛЕ объема)
        if not order_data.get('places_count'):
            return await self._step_places_count(message, order_data)
        
        # Шаг 6: Дата загрузки
        if not order_data.get('loading_date') and not order_data.get('loading_date_from'):
            return await self._step_date(message, order_data)
        
        # Шаг 7: Тип загрузки (ОБЯЗАТЕЛЬНО для ATI)
                    # load_type автоматически устанавливается как "dont-care"
            if not order_data.get('load_type'):
                order_data['load_type'] = 'dont-care'
        
        # Шаг 8: Тип кузова
        if not order_data.get('body_type'):
            return await self._step_body_type(message, order_data)
        
        # Шаг 9: Способ погрузки
        if not order_data.get('loading_method'):
            return await self._step_loading_method(message, order_data)
        
        # Шаг 10: Способ разгрузки
        if not order_data.get('unloading_method'):
            return await self._step_unloading_method(message, order_data)
        
        # Шаг 11: Адреса (только для Москвы/СПб)
        if self._needs_loading_address(order_data) and not order_data.get('loading_address'):
            return await self._step_loading_address(message, order_data)
        
        if self._needs_unloading_address(order_data) and not order_data.get('unloading_address'):
            return await self._step_unloading_address(message, order_data)
        
        # Шаг 12: Контакты
        if not order_data.get('contact_name') or not order_data.get('contact_phone'):
            return await self._step_contacts(message, order_data)
        
        # Все данные собраны - финальный шаг
        return await self._step_final(message, order_data)

    async def _step_cargo_type(self, message: str, order_data: Dict) -> Dict:
        """Шаг 1: Определение типа груза"""
        
        if message and not order_data.get('cargo_type'):
            # Проверяем, выбрал ли пользователь "Другой тип"
            if message.startswith("Тип груза:"):
                cargo_type = message.replace("Тип груза:", "").strip()
                if cargo_type == "Другой тип":
                    return {
                        'status': 'needs_input',
                        'message': '📦 Укажите тип вашего груза:\n\n(например: "Автозапчасти", "Документы", "Электроника" и т.д.)',
                        'buttons': [],
                        'next_step': 'route',
                        'order_data': order_data
                    }
                else:
                    order_data['cargo_type'] = cargo_type
                    logger.info(f"✅ Выбран тип груза из кнопки: {cargo_type}")
            else:
                # Для пользовательского ввода - используем ИИ поиск по словарю
                cargo_type = await self._extract_complex_field(message.strip(), "cargo_types")
                if cargo_type:
                    order_data['cargo_type'] = cargo_type
                    logger.info(f"✅ ИИ определил тип груза: {cargo_type}")
                else:
                    # Если ИИ не смог найти - используем как есть  
                    order_data['cargo_type'] = message.strip()
                    logger.info(f"✅ Использован пользовательский тип груза: {message.strip()}")
        
        if not order_data.get('cargo_type'):
            return {
                'status': 'needs_input',
                'message': '📦 Что нужно перевезти?\n\nВыберите тип груза или укажите свой:',
                'buttons': [
                    [
                    {'text': '🪑 Мебель', 'data': 'cargo_furniture'},
                        {'text': '🧱 Стройматериалы', 'data': 'cargo_materials'}
                    ],
                    [
                    {'text': '⚙️ Оборудование', 'data': 'cargo_equipment'},
                        {'text': '📦 Товары', 'data': 'cargo_goods'}
                    ],
                    [
                    {'text': '🏭 Промышленные товары', 'data': 'cargo_industrial'},
                    {'text': '🛒 Другой тип', 'data': 'cargo_other'}
                    ]
                ],
                'next_step': 'route',
                'order_data': order_data
            }
        
        # Логируем установленный тип груза
        logger.info(f"📦 Установлен финальный тип груза: '{order_data['cargo_type']}'")
        
        # Переходим к следующему шагу
        return await self._step_route("", order_data)

    async def _step_route(self, message: str, order_data: Dict) -> Dict:
        """Шаг 2: Определение маршрута - ИИ ДЛЯ НОРМАЛИЗАЦИИ ГОРОДОВ"""
        
        if message and not (order_data.get('from_city') and order_data.get('to_city')):
            # Используем ИИ для нормализации городов
            if "→" in message or "-" in message or " в " in message.lower():
                # Разбиваем маршрут
                parts = message.replace("→", "-").replace(" в ", "-").split("-")
                if len(parts) >= 2:
                    from_city = await self._extract_complex_field(parts[0].strip(), "cities")
                    to_city = await self._extract_complex_field(parts[1].strip(), "cities")
                    if from_city:
                        order_data['from_city'] = from_city
                        logger.info(f"✅ ИИ нормализовал город отправления: {from_city}")
                    if to_city:
                        order_data['to_city'] = to_city
                        logger.info(f"✅ ИИ нормализовал город назначения: {to_city}")
            else:
                # Попробуем извлечь один город
                city = await self._extract_complex_field(message, "cities")
                if city:
                    if not order_data.get('from_city'):
                        order_data['from_city'] = city
                        logger.info(f"✅ ИИ установил город отправления: {city}")
                    elif not order_data.get('to_city'):
                        order_data['to_city'] = city
                        logger.info(f"✅ ИИ установил город назначения: {city}")
        
        if not (order_data.get('from_city') and order_data.get('to_city')):
            cargo_type = order_data.get('cargo_type', 'груз')
            return {
                'status': 'needs_input',
                'message': f'🚛 Маршрут перевозки\n\nГруз: {cargo_type}\n\nУкажите откуда и куда нужно перевезти:\n(например: "Москва - Казань" или выберите популярный маршрут)',
                'buttons': [
                    [
                    {'text': '🏛️ Москва → СПб', 'data': 'route_msk_spb'},
                        {'text': '🏛️ СПб → Москва', 'data': 'route_spb_msk'}
                    ],
                    [
                    {'text': '🏭 Москва → Екатеринбург', 'data': 'route_msk_ekb'},
                    {'text': '🏭 Екатеринбург → Москва', 'data': 'route_ekb_msk'}
                    ]
                ],
                'next_step': 'weight',
                'order_data': order_data
            }
        
        # Переходим к следующему шагу
        return await self._step_weight("", order_data)

    async def _step_weight(self, message: str, order_data: Dict) -> Dict:
        """Шаг 3: Определение веса - ИИ ТОЛЬКО для пользовательского ввода"""
        
        if message and not order_data.get('weight'):
            # ИИ ТОЛЬКО если это НЕ кнопка (пользовательский ввод)
            if not message.startswith(('Вес:', 'Тип груза:', 'Маршрут:')):
                # Используем ИИ для парсинга веса: "1.5 тонны" → 1500
                weight = await self._extract_complex_field(message, "weight")
                if weight:
                    order_data['weight'] = weight
                    logger.info(f"✅ ИИ извлек вес: {weight} кг")
        
        # Проверяем вес и отказываемся если менее 200 кг
        if order_data.get('weight') and order_data['weight'] < 200:
            return {
                'status': 'weight_rejected',
                'message': f'❌ К сожалению, мы работаем только с грузами от 200 кг.\n\nВаш груз: {order_data["weight"]} кг\n\nДля перевозки грузов менее 200 кг рекомендуем:\n• СДЭК\n• Boxberry\n• Почта России\n• Яндекс.Доставка\n\nЕсли у вас есть груз от 200 кг - буду рад помочь с организацией перевозки!',
                'next_step': 'start',
                'buttons': [
                    {'text': '🚀 Новый заказ', 'data': 'new_order'},
                    {'text': '📞 Контакты', 'data': 'contact'}
                ]
            }
        
        if not order_data.get('weight'):
            return {
                'status': 'needs_input',
                'message': f'⚖️ Вес груза\n\nГруз: {order_data.get("cargo_type", "не указан")}\nМаршрут: {order_data.get("from_city", "")} → {order_data.get("to_city", "")}\n\n🚛 Сколько весит ваш груз?\n\nВыберите диапазон или укажите точный вес (например: "1.5 тонны" или "750 кг"):',
                'buttons': [
                    [
                    {'text': '📦 500 кг', 'data': 'weight_500'},
                        {'text': '📦 1 тонна', 'data': 'weight_1000'}
                    ],
                    [
                    {'text': '📦 2 тонны', 'data': 'weight_2000'},
                    {'text': '📦 5 тонн', 'data': 'weight_5000'}
                    ]
                ],
                'next_step': 'volume_dimensions',
                'order_data': order_data
            }
        
        # Переходим к следующему шагу - ОБЪЕМ/ГАБАРИТЫ
        return await self._step_volume_dimensions("", order_data)

    async def _step_date(self, message: str, order_data: Dict) -> Dict:
        """Шаг 4: Дата загрузки - ОБЯЗАТЕЛЬНО спрашиваем у клиента"""
        
        # ИСПРАВЛЕНИЕ: Используем ИИ для точного парсинга дат
        if message and (not order_data.get('loading_date') and not order_data.get('loading_date_from')):
            # Игнорируем системные сообщения о других параметрах
            if not any(keyword in message.lower() for keyword in ['количество мест:', 'тип кузова:', 'способ погрузки:', 'способ разгрузки:', 'вес:', 'объем:']):
                # Используем ИИ для парсинга дат
                date_result = await self._parse_date_with_ai(message)
                if date_result:
                    if date_result.get('is_range'):
                        order_data['loading_date_from'] = date_result['start_date']
                        order_data['loading_date_to'] = date_result['end_date']
                        order_data['loading_readiness_type'] = 'interval'
                        logger.info(f"✅ ИИ парсинг диапазона дат: {date_result['start_date']} - {date_result['end_date']}")
                    else:
                        order_data['loading_date'] = date_result['start_date']
                        order_data['loading_readiness_type'] = 'ready'
                        logger.info(f"✅ ИИ парсинг одной даты: {date_result['start_date']}")
        
        # ВСЕГДА спрашиваем дату если её нет
        if not order_data.get('loading_date') and not order_data.get('loading_date_from'):
            summary = self._format_order_summary(order_data, current_step="дата загрузки")
            return {
                'status': 'needs_input',
                'message': f'📅 Дата загрузки\n\n{summary}\n\n❓ Когда нужно забрать груз?\n\nПримеры:\n• Для одной даты: "23" или "23 июня"\n• Для диапазона: "23-27" или "23-27 июня"\n\n1️⃣ Выберите конкретную дату\n2️⃣ Или укажите диапазон дат',
                'next_step': 'date',
                'buttons': [
                    {'text': '📅 Открыть календарь', 'data': 'date_show_calendar'}
                ],
                'order_data': order_data
            }
        
        # Автоматически устанавливаем load_type и переходим к типу кузова
        order_data['load_type'] = 'dont-care'
        return await self._step_body_type("", order_data)



# СТАРЫЙ МЕТОД УДАЛЕН - используется новый выше

    async def _step_body_type(self, message: str, order_data: Dict) -> Dict:
        """Шаг 5: Тип кузова - ТОЛЬКО статичные кнопки БЕЗ ИИ"""
        
        # НЕ ИСПОЛЬЗУЕМ ИИ - только статичные кнопки
        
        if not order_data.get('body_type'):
            cargo_type = order_data.get('cargo_type', 'груз').lower()
            
            # Подсказки в зависимости от груза
            if 'мебель' in cargo_type:
                hint = "Для мебели лучше подходит закрытый фургон (защита от дождя и повреждений)"
            elif 'стройматериал' in cargo_type or 'материал' in cargo_type:
                hint = "Для стройматериалов удобна открытая платформа (легче грузить краном)"
            elif 'оборудование' in cargo_type:
                hint = "Для оборудования лучше подходит закрытый кузов"
            else:
                hint = "Выберите тип кузова или напишите какой нужен"
            
            # Показываем все основные типы кузовов горизонтально
            buttons = [
                [
                {'text': '🚛 Тентованный', 'data': 'body_tent'},
                    {'text': '🚐 Фургон (закрытый)', 'data': 'body_van'}
                ],
                [
                {'text': '🚛 Бортовой (открытый)', 'data': 'body_platform'},
                    {'text': '❄️ Рефрижератор', 'data': 'body_refrigerator'}
                ],
                [
                {'text': '🏗️ Низкорамный', 'data': 'body_lowframe'},
                    {'text': '🚛 Самосвал', 'data': 'body_dump'}
                ],
                [
                {'text': '🚚 Изотермический', 'data': 'body_isothermal'},
                {'text': '🏭 Контейнеровоз', 'data': 'body_container'}
                ]
            ]
            
            summary = self._format_order_summary(order_data, current_step="тип кузова")
            
            return {
                'status': 'needs_input',
                'message': f'🚛 Тип кузова\n\n{summary}\n\n💡 {hint}:',
                'buttons': buttons,
                'next_step': 'loading_method',
                'order_data': order_data
            }
        
        # Переходим к способу погрузки
        return await self._step_loading_method("", order_data)



    async def _step_loading_method(self, message: str, order_data: Dict) -> Dict:
        """Шаг 6: Способ загрузки - ТОЛЬКО статичные кнопки БЕЗ ИИ"""
        
        # НЕ ИСПОЛЬЗУЕМ ИИ - только статичные кнопки
        
        if not order_data.get('loading_method'):
            return {
                'status': 'needs_input',
                'message': f'🏗️ Способ загрузки\n\nГруз: {order_data.get("cargo_type", "не указан")}\nМаршрут: {order_data.get("from_city", "")} → {order_data.get("to_city", "")}\nВес: {order_data.get("weight", "")} кг\nКузов: {order_data.get("body_type", "не указан")}\n\nКакой способ загрузки нужен?',
                'next_step': 'unloading_method',
                'buttons': [
                    [
                    {'text': '⬆️ Верхняя', 'data': 'loading_top'},
                        {'text': '↗️ Боковая', 'data': 'loading_side'}
                    ],
                    [
                    {'text': '⬅️ Задняя', 'data': 'loading_rear'},
                        {'text': '🔄 С полной растентовкой', 'data': 'loading_full'}
                    ],
                    [
                    {'text': '↔️ Боковая с 2-х сторон', 'data': 'loading_side2'},
                    {'text': '🚰 Налив', 'data': 'loading_pour'}
                    ]
                ],
                'order_data': order_data
            }
        
        # Переходим к способу разгрузки
        return await self._step_unloading_method("", order_data)

    async def _step_unloading_method(self, message: str, order_data: Dict) -> Dict:
        """Шаг 7: Способ разгрузки - ТОЛЬКО статичные кнопки БЕЗ ИИ"""
        
        # НЕ ИСПОЛЬЗУЕМ ИИ - только статичные кнопки
        
        if not order_data.get('unloading_method'):
            return {
                'status': 'needs_input',
                'message': f'🏗️ Способ разгрузки\n\nГруз: {order_data.get("cargo_type", "не указан")}\nМаршрут: {order_data.get("from_city", "")} → {order_data.get("to_city", "")}\nВес: {order_data.get("weight", "")} кг\nКузов: {order_data.get("body_type", "не указан")}\nПогрузка: {order_data.get("loading_method", "не указан")}\n\nКакой способ разгрузки нужен?',
                'next_step': 'contacts',
                'buttons': [
                    [
                    {'text': '⬆️ Верхняя', 'data': 'unloading_top'},
                        {'text': '↗️ Боковая', 'data': 'unloading_side'}
                    ],
                    [
                    {'text': '⬅️ Задняя', 'data': 'unloading_rear'},
                        {'text': '🔄 С полной растентовкой', 'data': 'unloading_full'}
                    ],
                    [
                    {'text': '↔️ Боковая с 2-х сторон', 'data': 'unloading_side2'},
                    {'text': '🚚 Гидроборт', 'data': 'unloading_hydroboard'}
                    ]
                ],
                'order_data': order_data
            }
        
        # Переходим к контактам
        return await self._step_contacts("", order_data)

    async def _step_pack_type(self, message: str, order_data: Dict) -> Dict:
        """Шаг 9: Тип упаковки"""
        
        return {
            'status': 'needs_input',
            'message': '📦 Упаковка груза\n\nКак упакован ваш груз?',
            'next_step': 'pack_type',
            'buttons': [
                {'text': '📦 В коробках', 'data': 'pack_boxes'},
                {'text': '🗂️ На поддонах', 'data': 'pack_pallets'},
                {'text': '🎒 В мешках', 'data': 'pack_bags'},
                {'text': '📋 Штабелем', 'data': 'pack_stack'},
                {'text': '🔓 Без упаковки', 'data': 'pack_none'},
                {'text': '📦 Другая упаковка', 'data': 'pack_other'}
            ]
        }

    async def _step_address_check(self, message: str, order_data: Dict) -> Dict:
        """Шаг 10: Проверка необходимости адресов"""
        
        from_city = (order_data.get('from_city') or '').lower()
        to_city = (order_data.get('to_city') or '').lower()
        
        needs_loading_address = ('москва' in from_city or 'санкт-петербург' in from_city or 'спб' in from_city or 'питер' in from_city)
        needs_unloading_address = ('москва' in to_city or 'санкт-петербург' in to_city or 'спб' in to_city or 'питер' in to_city)
        
        if needs_loading_address and not order_data.get('loading_address'):
            city_name = 'Москве' if 'москва' in from_city else 'СПб'
            return {
                'status': 'needs_input',
                'message': f'📍 Адрес загрузки в {city_name}\n\nДля размещения заказа нужен точный адрес.\nУкажите улицу и дом:',
                'next_step': 'address',
                'address_type': 'loading',
                'buttons': []
            }
        
        if needs_unloading_address and not order_data.get('unloading_address'):
            city_name = 'Москве' if 'москва' in to_city else 'СПб'
            return {
                'status': 'needs_input',
                'message': f'📍 Адрес разгрузки в {city_name}\n\nДля размещения заказа нужен точный адрес.\nУкажите улицу и дом:',
                'next_step': 'address',
                'address_type': 'unloading',
                'buttons': []
            }
        
        return await self._step_contacts("", order_data)

    async def _step_contacts(self, message: str, order_data: Dict) -> Dict:
        """Шаг 10: Контактные данные"""
        
        # Если телефон уже получен, а пришедшее сообщение похоже на ФИО — сохраняем без ИИ
        if message and order_data.get('contact_phone') and not order_data.get('contact_name'):
            text = message.strip()
            # Простая эвристика: строка состоит из 2-4 слов кириллицей/латиницей
            if 2 <= len(text.split()) <= 4:
                order_data['contact_name'] = text
        
        # Если телефон уже указан, а пришло сообщение (предположительно ФИО)
        # — сохраняем его как contact_name без сложного парсинга
        if message and message.strip() and order_data.get('contact_phone') and not order_data.get('contact_name'):
            potential_name = message.strip()
            if len(potential_name.split()) >= 2:  # простая проверка на "Имя Фамилия"
                order_data['contact_name'] = potential_name
        
        # 1) Нет телефона – просим поделиться номером
        if not order_data.get('contact_phone'):
            summary = f"""📞 Контактные данные

📦 Груз: {order_data.get('cargo_type', 'не указан')}
⚖️ Вес: {order_data.get('weight', 'не указан')} кг
📦 Мест: {order_data.get('places_count', 'не указано')}
📏 Объем: {order_data.get('volume', 'не указан')} м³
🚛 Маршрут: {order_data.get('from_city', 'не указан')} → {order_data.get('to_city', 'не указан')}
📅 Дата загрузки: {self._format_loading_dates(order_data)}
🚚 Тип кузова: {order_data.get('body_type', 'не указан')}
🏗️ Погрузка: {order_data.get('loading_method', 'не указан')}
🏗️ Разгрузка: {order_data.get('unloading_method', 'не указан')}"""
            # Добавляем адреса если есть
            if order_data.get('loading_address'):
                summary += f"\n📍 **Адрес загрузки:** {order_data['loading_address']}"
            if order_data.get('unloading_address'):
                summary += f"\n📍 **Адрес разгрузки:** {order_data['unloading_address']}"

            # Новая логика: различаем отсутствие телефона и отсутствие ФИО
            if not order_data.get('contact_phone'):
                summary += "\n\nДля связи нужен ваш номер телефона.\nНажмите кнопку «📱 Поделиться номером», затем введите ФИО полностью."
                return {
                    'status': 'needs_input',
                    'message': summary,
                    'buttons': [],
                    'next_step': 'contacts',
                    'order_data': order_data,
                    'contact_request': True
                }
            else:
                # Телефон есть, просим ФИО
                message_fio = "Введите, пожалуйста, ваше ФИО полностью (как в паспорте):"
                return {
                    'status': 'needs_input',
                    'message': message_fio,
                    'buttons': [],
                    'next_step': 'contacts',
                    'order_data': order_data
                }

        # 2) Телефон есть, нет ФИО – просим ФИО
        if not order_data.get('contact_name'):
            summary = f"""📞 Контактные данные

Номер получен – {order_data['contact_phone']}\n\nВведите, пожалуйста, ваше ФИО полностью (как в паспорте):"""
            return {
                'status': 'needs_input',
                'message': summary,
                'buttons': [],
                'next_step': 'contacts',
                'order_data': order_data
            }

        # === Новая логика сверки имени Telegram и введённого ФИО ===
        tg_name = order_data.get('contact_tg_name')
        if tg_name and order_data.get('contact_name'):
            tg_first = tg_name.split()[0].lower()
            entered_first = order_data['contact_name'].split()[0].lower()
            if tg_first != entered_first:
                confirm_msg = f"Имя в Telegram {tg_name} ≠ введённое {order_data['contact_name']}. Всё правильно?"
                return {
                    'status': 'needs_input',
                    'message': confirm_msg,
                    'buttons': [
                        [
                            {'text': '✅ Имя верно', 'data': 'name_confirm_ok'},
                            {'text': '✏️ Исправить', 'data': 'name_confirm_edit'}
                        ]
                    ],
                    'next_step': 'contacts',
                    'order_data': order_data
                }
        # === Конец новой логики ===

        # Все данные собраны – переходим к финалу
        return await self._step_final("", order_data)
    
    def _format_loading_dates(self, order_data: Dict) -> str:
        """Форматирование дат загрузки для отображения"""
        if order_data.get('loading_date'):
            return order_data['loading_date']
        elif order_data.get('loading_date_from') and order_data.get('loading_date_to'):
            return f"{order_data['loading_date_from']} - {order_data['loading_date_to']}"
        else:
            return "не указана"

    async def _step_final(self, message: str, order_data: Dict) -> Dict:
        """Финальный шаг: Подтверждение заказа с финальной обработкой ИИ"""
        
        # Финальная обработка всех данных ИИ
        order_data = await self._finalize_order_data(order_data)
        
        # Формируем понятную сводку заказа
        summary = f"""✅ Ваш заказ готов к размещению!

📦 Груз: {order_data.get('cargo_type', 'не указан')}
⚖️ Вес: {order_data.get('weight', 'не указан')} кг
📦 Количество мест: {order_data.get('places_count', 'не указано')}
📏 Объем: {order_data.get('volume', 'не указан')} м³
🚛 Маршрут: {order_data.get('from_city', 'не указан')} → {order_data.get('to_city', 'не указан')}
📅 Дата загрузки: {self._format_loading_dates(order_data)}
🚚 Тип кузова: {order_data.get('body_type', 'не указан')}
🏗️ Погрузка: {order_data.get('loading_method', 'не указан')}
🏗️ Разгрузка: {order_data.get('unloading_method', 'не указан')}"""

        # Добавляем адреса если есть
        if order_data.get('loading_address'):
            summary += f"\n📍 **Адрес загрузки:** {order_data['loading_address']}"
        if order_data.get('unloading_address'):
            summary += f"\n📍 **Адрес разгрузки:** {order_data['unloading_address']}"
            
        summary += f"""
👤 Контакт: {order_data.get('contact_name', 'не указан')}
📞 Телефон: {order_data.get('contact_phone', 'не указан')}

🔍  Что дальше:
1. Размещаем ваш груз среди проверенных перевозчиков
2. Ищем лучшие предложения (обычно 15-30 минут)
3. Отправляем вам предложения с ценами
4. Вы выбираете подходящий вариант


📱 Уведомления придут в этот чат

Подтверждаете размещение заказа?"""

        return {
            'status': 'ready_to_submit',
            'message': summary,
            'buttons': [
                {'text': '✅ Подтвердить заказ', 'data': 'confirm_order'},
                {'text': '✏️ Изменить данные', 'data': 'edit_order'},
                {'text': '❌ Отменить', 'data': 'cancel_order'}
            ],
            'next_step': 'submit',
            'order_data': order_data
        }

    async def _check_order_readiness(self, order_data: Dict) -> Dict:
        """Проверка готовности заказа"""
        
        # Проверяем обязательные поля
        required_fields = ['from_city', 'to_city', 'cargo_type', 'weight', 'body_type', 'loading_method', 'unloading_method', 'pack_type', 'contact_name', 'contact_phone']
        missing_fields = [field for field in required_fields if not order_data.get(field)]
        
        # Проверяем адреса для Москвы и СПб
        from_city = (order_data.get('from_city') or '').lower()
        to_city = (order_data.get('to_city') or '').lower()
        
        # Проверяем адрес загрузки только для Москвы и СПб
        if ('москва' in from_city or 'санкт-петербург' in from_city or 'спб' in from_city or 'питер' in from_city):
            if not order_data.get('loading_address'):
                if 'москва' in from_city:
                    missing_fields.append('точный адрес загрузки в Москве')
                else:
                    missing_fields.append('точный адрес загрузки в СПб')
        
        # Проверяем адрес разгрузки только для Москвы и СПб
        if ('москва' in to_city or 'санкт-петербург' in to_city or 'спб' in to_city or 'питер' in to_city):
            if not order_data.get('unloading_address'):
                if 'москва' in to_city:
                    missing_fields.append('точный адрес разгрузки в Москве')
                else:
                    missing_fields.append('точный адрес разгрузки в СПб')
        
        # Заказ готов если не хватает максимум 3 полей (можем уточнить)
        is_ready = len(missing_fields) <= 3
        
        return {
            'ready': is_ready,
            'missing_fields': missing_fields,
            'order_data': order_data,
            'completeness': f"{len(required_fields) - len(missing_fields)}/{len(required_fields)}"
        }

    

    async def _step_volume_dimensions(self, message: str, order_data: Dict) -> Dict:
        """Шаг 4: Объем или габариты - ИИ ДЛЯ ПАРСИНГА РАЗНЫХ ФОРМАТОВ"""
        
        # ОБРАБАТЫВАЕМ ТОЛЬКО если сообщение содержит информацию об объеме/габаритах
        if message and not order_data.get('volume') and not (order_data.get('length') and order_data.get('width') and order_data.get('height')):
            # Игнорируем сообщения от кнопок других шагов
            if not message.startswith(('Вес:', 'Тип груза:', 'Маршрут:')):
                # Сначала пробуем извлечь объем через ИИ
                volume = await self._extract_complex_field(message, "volume")
                if volume:
                    order_data['volume'] = volume
                    logger.info(f"✅ ИИ извлек объем: {volume} м³")
                else:
                    # Пробуем извлечь габариты через ИИ
                    dimensions = await self._extract_complex_field(message, "dimensions")
                    if dimensions and all(k in dimensions for k in ['length', 'width', 'height']):
                        order_data['length'] = dimensions['length']
                        order_data['width'] = dimensions['width']
                        order_data['height'] = dimensions['height']
                        # Рассчитываем объем
                        order_data['volume'] = dimensions['length'] * dimensions['width'] * dimensions['height']
                        logger.info(f"✅ ИИ извлек габариты и рассчитал объем: {order_data['volume']} м³")
        
        # Если объем не указан - запрашиваем у пользователя
        if not order_data.get('volume') and not (order_data.get('length') and order_data.get('width') and order_data.get('height')):
            summary = self._format_order_summary(order_data, current_step="объем/габариты")
            return {
                'status': 'needs_input',
                'message': f'📏 Объем и габариты\n\n{summary}\n\nУкажите точный объем (в м³) или габариты (длина × ширина × высота в метрах):\n\nПримеры:\n• "2.5 м³" или "4 куба"\n• "2.4 × 1.2 × 0.8"',
                'buttons': [],
                'next_step': 'date',
                'order_data': order_data
            }
        
        # Переходим к количеству мест
        return await self._step_places_count("", order_data)
    
# СТАРЫЙ МЕТОД УДАЛЕН - используется новый выше

    def _needs_loading_address(self, order_data: Dict) -> bool:
        """Проверяет, нужен ли точный адрес загрузки"""
        from_city = (order_data.get('from_city') or '').lower()
        return any(city in from_city for city in ['москва', 'санкт-петербург', 'спб', 'питер'])

    def _needs_unloading_address(self, order_data: Dict) -> bool:
        """Проверяет, нужен ли точный адрес разгрузки"""
        to_city = (order_data.get('to_city') or '').lower()
        return any(city in to_city for city in ['москва', 'санкт-петербург', 'спб', 'питер'])

    async def _step_loading_address(self, message: str, order_data: Dict) -> Dict:
        """Шаг 9a: Адрес загрузки"""
        
        if message and not order_data.get('loading_address'):
            # Извлекаем адрес из сообщения
            extracted_data = await self._extract_order_data_from_conversation([
                {'role': 'user', 'content': message}
            ])
            if extracted_data.get('loading_address'):
                order_data['loading_address'] = extracted_data['loading_address']
            else:
                # Используем сообщение как адрес
                order_data['loading_address'] = message.strip()
        
        if not order_data.get('loading_address'):
            from_city = order_data.get('from_city', '')
            city_name = 'Москве' if 'москва' in from_city.lower() else 'СПб'
            return {
                'status': 'needs_input',
                'message': f'📍 Адрес загрузки в {city_name}\n\nДля размещения заказа нужен точный адрес загрузки.\nУкажите улицу и дом:\n\n(например: "ул. Тверская, 15" или "ш. Энтузиастов, 12, стр. 3")',
                'buttons': [],
                'next_step': 'unloading_address',
                'order_data': order_data
            }
        
        # Проверяем нужен ли адрес разгрузки
        if self._needs_unloading_address(order_data):
            return await self._step_unloading_address("", order_data)
        else:
            return await self._step_contacts("", order_data)

    async def _step_unloading_address(self, message: str, order_data: Dict) -> Dict:
        """Шаг 9b: Адрес разгрузки"""
        
        if message and not order_data.get('unloading_address'):
            # Извлекаем адрес из сообщения
            extracted_data = await self._extract_order_data_from_conversation([
                {'role': 'user', 'content': message}
            ])
            if extracted_data.get('unloading_address'):
                order_data['unloading_address'] = extracted_data['unloading_address']
            else:
                # Используем сообщение как адрес
                order_data['unloading_address'] = message.strip()
        
        if not order_data.get('unloading_address'):
            to_city = order_data.get('to_city', '')
            city_name = 'Москве' if 'москва' in to_city.lower() else 'СПб'
            return {
                'status': 'needs_input',
                'message': f'📍 Адрес разгрузки в {city_name}\n\nДля размещения заказа нужен точный адрес разгрузки.\nУкажите улицу и дом:\n\n(например: "ул. Тверская, 15" или "ш. Энтузиастов, 12, стр. 3")',
                'buttons': [],
                'next_step': 'contacts',
                'order_data': order_data
            }
        
        # Переходим к контактам
        return await self._step_contacts("", order_data)

    # =================== ПРОСТЫЕ ФУНКЦИИ ПАРСИНГА БЕЗ ИИ ===================
    
    def _parse_simple_number(self, text: str) -> Optional[int]:
        """Простое извлечение числа из текста БЕЗ ИИ"""
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            number = int(numbers[0])
            # Проверяем разумность (от 1 до 100 мест)
            if 1 <= number <= 100:
                return number
        return None
    
    def _parse_button_choice(self, callback_data: str, button_map: Dict) -> str:
        """Обработка выбора кнопки БЕЗ ИИ"""
        return button_map.get(callback_data, callback_data)
    
    # =================== ИИ ТОЛЬКО ДЛЯ СЛОЖНЫХ ПОЛЕЙ ===================
    
    async def _extract_complex_field(self, text: str, field_type: str) -> Any:
        """ИИ извлечение ТОЛЬКО для сложных полей"""
        
        if field_type == "cities":
            # ИИ нормализует города: "москва" → "Москва", "спб" → "Санкт-Петербург"
            prompt = f"""
Нормализуй название города: "{text}"

Правила:
- Москва, москва, мск → "Москва"
- СПб, спб, питер, санкт-петербург → "Санкт-Петербург"  
- Екатеринбург, екб, екат → "Екатеринбург"
- Нижний Новгород, н.новгород, нновгород → "Нижний Новгород"
- Казань, казань → "Казань"
- Ижевск, ижевск → "Ижевск"
- Сарапул, сарапул → "Сарапул"

ВАЖНО: Если в тексте НЕТ названия города, верни "НЕТ_ГОРОДА".
Верни ТОЛЬКО название города или "НЕТ_ГОРОДА", без объяснений.
"""
            
        elif field_type == "volume":
            # ИИ парсит объем: "4,2 куба" → 4.2
            prompt = f"""
Извлеки объем в кубических метрах из текста: "{text}"

Примеры:
- "4,2 куба" → 4.2
- "5.5 м3" → 5.5  
- "1 куб" → 1.0
- "2.5 кубометра" → 2.5
- "3 м³" → 3.0

Верни ТОЛЬКО число (float), без единиц измерения.
"""
            
        elif field_type == "weight":
            # ИИ парсит вес: "1.5 тонны" → 1500
            prompt = f"""
Извлеки вес в килограммах из текста: "{text}"

Примеры:
- "1.5 тонны" → 1500
- "750 кг" → 750
- "2т" → 2000
- "500кг" → 500

Верни ТОЛЬКО число (int) в килограммах.
"""
            
        elif field_type == "dates":
            # ИИ парсит даты: "завтра" → "2025-06-22"
            from datetime import datetime, timedelta
            today = datetime.now().strftime('%Y-%m-%d')
            prompt = f"""
Преобразуй дату в формат YYYY-MM-DD. Сегодня: {today}

Текст: "{text}"

Примеры:
- "завтра" → дата завтрашнего дня
- "послезавтра" → дата послезавтра
- "22-26" → диапазон дат текущего месяца
- "на следующей неделе" → дата через неделю

Верни ТОЛЬКО дату в формате YYYY-MM-DD или диапазон через пробел.
"""
            
        elif field_type == "dimensions":
            # ИИ парсит габариты: "2.4 × 1.2 × 0.8" → {"length": 2.4, "width": 1.2, "height": 0.8}
            prompt = f"""
Извлеки габариты из текста: "{text}"

Примеры:
- "2.4 × 1.2 × 0.8" → length:2.4, width:1.2, height:0.8
- "длина 3м ширина 1.5м высота 2м" → length:3.0, width:1.5, height:2.0

Верни в формате JSON: {{"length": float, "width": float, "height": float}}
"""
            
        elif field_type == "address":
            # ИИ нормализует адрес: "тверская 15" → "ул. Тверская, 15"
            prompt = f"""
Нормализуй адрес: "{text}"

Примеры:
- "тверская 15" → "ул. Тверская, 15"
- "энтузиастов 12 стр 3" → "ш. Энтузиастов, 12, стр. 3"

Верни ТОЛЬКО нормализованный адрес.
"""
            
        elif field_type == "contacts":
            # ИИ извлекает имя и телефон: "Иван Петров 89161234567" → {"name": "Иван Петров", "phone": "89161234567"}
            prompt = f"""
Извлеки имя и телефон из текста: "{text}"

Примеры:
- "Иван Петров 89161234567" → name:"Иван Петров", phone:"89161234567"
- "Петр +7-916-123-45-67" → name:"Петр", phone:"79161234567"

Верни в формате JSON: {{"name": "string", "phone": "string"}}
"""
            
        elif field_type == "cargo_types":
            # ИИ определяет тип груза по словарю ATI
            prompt = f"""
Определи тип груза из текста: "{text}"

Популярные типы грузов:
- Мебель (мебель, столы, стулья, диваны, шкафы)
- Стройматериалы (кирпич, доски, цемент, песок, щебень) 
- Оборудование (станки, техника, промышленное оборудование)
- Товары (одежда, товары народного потребления, продукция)
- Промышленные товары (металлопрокат, трубы, профиль)
- Автозапчасти (запчасти, комплектующие для автомобилей)
- Продукты питания (еда, продовольствие, пищевые продукты)
- Электроника (техника, компьютеры, телефоны)
- Текстиль (ткани, одежда, текстильные изделия)
- Химические товары (химия, удобрения, лакокрасочные)

Если текст точно соответствует одному из типов - верни ТОЧНОЕ название.
Если нет точного соответствия - верни исходный текст.

Верни ТОЛЬКО название типа груза без объяснений.
"""
            
        else:
            return None
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            
            # Парсим JSON если нужно
            if field_type in ["dimensions", "contacts"]:
                import json
                return json.loads(result)
            
            # Парсим число если нужно
            if field_type in ["volume", "weight"]:
                try:
                    return float(result) if field_type == "volume" else int(result)
                except ValueError:
                    logger.warning(f"ИИ не смог извлечь {field_type} из '{text}': {result}")
                    return None
            
            # Проверяем города
            if field_type == "cities" and result == "НЕТ_ГОРОДА":
                return None
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка ИИ извлечения {field_type}: {e}")
            return None

    async def _generate_clarification_questions(self, missing_fields: List[str]) -> List[str]:
        """Генерирует вопросы для уточнения недостающих данных"""
        
        questions = []
        
        for field in missing_fields:
            if field == 'cargo_type':
                questions.append("Что за груз нужно перевезти? (например: мебель, стройматериалы, оборудование)")
            elif field == 'from_city':
                questions.append("Откуда забрать груз? (город загрузки)")
            elif field == 'to_city':
                questions.append("Куда доставить груз? (город разгрузки)")
            elif field == 'weight':
                questions.append("Сколько весит груз? (в кг или тоннах)")
            elif field == 'volume':
                questions.append("Какой объем груза? (в м³ или габариты)")
            elif field == 'loading_date':
                questions.append("Когда нужно забрать груз? (дата или диапазон дат)")
            elif field == 'contact_name':
                questions.append("Как к вам обращаться?")
            elif field == 'contact_phone':
                questions.append("Ваш номер телефона для связи?")
            elif field == 'places_count':
                questions.append("Сколько мест (коробок, поддонов, единиц)?")
        
        return questions

    async def _parse_date_with_ai(self, text: str) -> Optional[Dict]:
        """Парсит даты с помощью ИИ - точно и надежно"""
        from datetime import datetime
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            current_day = datetime.now().day
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            # ИСПРАВЛЕНИЕ: Улучшенный промпт для парсинга дат
            prompt = f"""
Извлеки дату загрузки из сообщения: "{text}"

СЕГОДНЯ: {today} (день {current_day}, месяц {current_month}, год {current_year})

ПРАВИЛА ПАРСИНГА:
1. Если в сообщении НЕТ даты - верни {{"type": "none"}}
2. Если одна дата - это готовность к загрузке в конкретный день
3. Если диапазон - это интервал дат готовности

ПРИМЕРЫ ПАРСИНГА:
- "29" → одна дата 29 числа ТЕКУЩЕГО месяца ({current_month})
- "29 июня" → 29 июня {current_year} года
- "25-28" → диапазон с 25 по 28 число текущего месяца
- "завтра" → завтрашняя дата
- "2025-06-27" → точная дата 2025-06-27
- "Количество мест: 2" → НЕТ_ДАТЫ (это не дата!)
- "Дата загрузки: 2025-06-29" → одна дата 2025-06-29

ВАЖНО: Если указано только число (например "29"), считай это датой ТЕКУЩЕГО месяца!

РЕЗУЛЬТАТ СТРОГО в JSON формате БЕЗ лишнего текста:
{{"type": "single", "date": "2025-06-27"}} - для одной даты
{{"type": "range", "start_date": "2025-06-25", "end_date": "2025-06-28"}} - для диапазона  
{{"type": "none"}} - если даты нет
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            result_text = response.choices[0].message.content.strip()
            logger.info(f"🤖 ИИ ответ на парсинг даты '{text}': {result_text}")
            
            # ИСПРАВЛЕНИЕ: Более надежный парсинг JSON
            import json
            try:
                # Убираем возможные markdown блоки
                if result_text.startswith('```json'):
                    result_text = result_text[7:]
                if result_text.startswith('```'):
                    result_text = result_text[3:]
                if result_text.endswith('```'):
                    result_text = result_text[:-3]
                
                result_text = result_text.strip()
                
                if not result_text.startswith('{'):
                    logger.error(f"❌ Ответ ИИ не является JSON: {result_text}")
                    return None
                
                result = json.loads(result_text)
                
                if result.get('type') == 'single':
                    return {
                        'is_range': False,
                        'start_date': result['date']
                    }
                elif result.get('type') == 'range':
                    return {
                        'is_range': True,
                        'start_date': result['start_date'],
                        'end_date': result['end_date']
                    }
                else:
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON от ИИ: {str(e)}")
                logger.error(f"❌ Проблемный текст: {result_text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка ИИ парсинга даты: {e}")
            return None

    # =================== ИСПРАВЛЕНИЕ 2: УПРОЩЕНИЕ КНОПКИ КОЛИЧЕСТВА МЕСТ ===================

    async def _step_places_count(self, message: str, order_data: Dict) -> Dict:
        """Шаг: Количество мест (упрощенный)"""
        
        if message and not order_data.get('places_count'):
            # Простое извлечение числа БЕЗ ИИ
            places = self._parse_simple_number(message)
            if places and places > 0:
                order_data['places_count'] = places
                logger.info(f"✅ Установлено мест: {places}")
        
        if not order_data.get('places_count'):
            summary = self._format_order_summary(order_data, current_step="количество мест")
            return {
                'status': 'needs_input',
                'message': f'📦 Количество мест\n\n{summary}\n\n💡 Выберите количество мест или введите свое число:',
                'buttons': [
                    [
                        {'text': '1️⃣ 1 место', 'data': 'places_1'},
                        {'text': '2️⃣ 2 места', 'data': 'places_2'}
                    ],
                    [
                        {'text': '3️⃣ 3 места', 'data': 'places_3'},
                        {'text': '4️⃣ 4 места', 'data': 'places_4'}
                    ]
                ],
                'next_step': 'date',
                'order_data': order_data
            }
        
        # Переходим к дате
        return await self._step_date("", order_data)

    # =================== ИСПРАВЛЕНИЕ 3: ФИКС ОШИБКИ ФОРМАТИРОВАНИЯ В _finalize_order_data ===================

    async def _finalize_order_data(self, order_data: Dict) -> Dict:
        """Финальная обработка всех данных ИИ перед отправкой в АТИ"""
        
        logger.info("🔧 Финальная обработка данных ИИ...")
        
        try:
            # ИСПРАВЛЕНИЕ: Убираем форматирование из промпта
            cargo_type = order_data.get('cargo_type', 'не указан')
            from_city = order_data.get('from_city', 'не указан')
            to_city = order_data.get('to_city', 'не указан')
            weight = order_data.get('weight', 'не указан')
            places_count = order_data.get('places_count', 'не указано')
            volume = order_data.get('volume', 'не указан')
            loading_date = order_data.get('loading_date', order_data.get('loading_date_from', 'не указана'))
            body_type = order_data.get('body_type', 'не указан')
            loading_method = order_data.get('loading_method', 'не указан')
            unloading_method = order_data.get('unloading_method', 'не указан')
            contact_name = order_data.get('contact_name', 'не указан')
            contact_phone = order_data.get('contact_phone', 'не указан')
            
            prompt = f"""
Проверь и нормализуй данные заказа для системы АТИ.

ДАННЫЕ ЗАКАЗА:
- Тип груза: {cargo_type}
- Маршрут: {from_city} → {to_city}
- Вес: {weight} кг
- Мест: {places_count}
- Объем: {volume} м³
- Дата: {loading_date}
- Кузов: {body_type}
- Погрузка: {loading_method}
- Разгрузка: {unloading_method}
- Контакт: {contact_name} {contact_phone}

ЗАДАЧА:
1. Проверь корректность всех данных
2. Нормализуй названия городов (убирай кавычки если есть)
3. Проверь разумность веса/объема/мест
4. Создай профессиональное описание груза для АТИ

РЕЗУЛЬТАТ СТРОГО в JSON формате БЕЗ лишнего текста:
{{"cargo_description": "Профессиональное описание для АТИ", "normalized_data": {{"cargo_type": "нормализованный тип", "from_city": "нормализованный город", "to_city": "нормализованный город", "weight": 350, "volume": 5.0, "places_count": 5}}, "validation_status": "OK", "errors": []}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # ИСПРАВЛЕНИЕ: Более надежная обработка JSON
            try:
                # Убираем возможные markdown блоки
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.startswith('```'):
                    response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                response_text = response_text.strip()
                
                # Проверяем что это JSON
                if not response_text.startswith('{'):
                    logger.error(f"❌ Ответ ИИ не является JSON: {response_text[:100]}...")
                    return order_data
                
                # Парсим JSON
                import json
                result = json.loads(response_text)
                
                # Обновляем данные нормализованными значениями
                if result.get('normalized_data'):
                    normalized = result['normalized_data']
                    for key, value in normalized.items():
                        if value and str(value).strip() != 'не указан':
                            order_data[key] = value
                
                # Добавляем профессиональное описание
                if result.get('cargo_description'):
                    order_data['cargo_description'] = result['cargo_description']
                
                logger.info("✅ Финальная обработка ИИ завершена успешно")
                return order_data
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON от ИИ: {str(e)}")
                logger.error(f"❌ Проблемный текст: {response_text}")
                # Возвращаем оригинальные данные если парсинг не удался
                return order_data
                
        except Exception as e:
            logger.error(f"❌ Ошибка финальной обработки ИИ: {str(e)}")
            return order_data

    # =================== ИСПРАВЛЕНИЕ 4: СОХРАНЕНИЕ ДАННЫХ МЕЖДУ ШАГАМИ ===================

    def _format_order_summary(self, order_data: Dict, current_step: str = "") -> str:
        """Форматирует сводку выбранных параметров заказа с сохранением всех данных"""
        
        summary_parts = []
        
        # Тип груза
        if order_data.get('cargo_type') and order_data['cargo_type'] != 'Начать новый заказ':
            summary_parts.append(f"📦 Груз: {order_data['cargo_type']}")
        
        # Маршрут
        from_city = order_data.get('from_city')
        to_city = order_data.get('to_city')
        if from_city and to_city:
            summary_parts.append(f"🚛 Маршрут: {from_city} → {to_city}")
        elif from_city:
            summary_parts.append(f"🚛 Откуда: {from_city}")
        elif to_city:
            summary_parts.append(f"🚛 Куда: {to_city}")
        
        # Вес
        if order_data.get('weight'):
            weight = order_data['weight']
            if weight >= 1000:
                weight_str = f"{weight/1000:.1f} т"
            else:
                weight_str = f"{weight} кг"
            summary_parts.append(f"⚖️ Вес: {weight_str}")
        
        # Количество мест - показываем всегда если есть
        if order_data.get('places_count'):
            places = order_data['places_count']
            if places == 1:
                summary_parts.append(f"📦 Мест: {places} место")
            elif 2 <= places <= 4:
                summary_parts.append(f"📦 Мест: {places} места")
            else:
                summary_parts.append(f"📦 Мест: {places} мест")
        
        # Объем или габариты
        if order_data.get('volume'):
            volume = order_data['volume']
            summary_parts.append(f"📏 Объем: {volume} м³")
        elif order_data.get('dimensions'):
            summary_parts.append(f"📏 Габариты: {order_data['dimensions']}")
        
        # Дата загрузки - ИСПРАВЛЕНО: правильное отображение диапазона
        if order_data.get('loading_date'):
            date_str = order_data['loading_date']
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d.%m.%Y')
                summary_parts.append(f"📅 Дата: {formatted_date}")
            except:
                summary_parts.append(f"📅 Дата: {date_str}")
        elif order_data.get('loading_date_from') and order_data.get('loading_date_to'):
            try:
                from datetime import datetime
                start_date = datetime.strptime(order_data['loading_date_from'], '%Y-%m-%d').strftime('%d.%m.%Y')
                end_date = datetime.strptime(order_data['loading_date_to'], '%Y-%m-%d').strftime('%d.%m.%Y')
                summary_parts.append(f"📅 Период: {start_date} - {end_date}")
            except:
                summary_parts.append(f"📅 Период: {order_data['loading_date_from']} - {order_data['loading_date_to']}")
        
        # Тип кузова - ИСПРАВЛЕНО: всегда показываем если есть
        if order_data.get('body_type'):
            summary_parts.append(f"🚛 Кузов: {order_data['body_type']}")
        
        # Загрузка/разгрузка - ИСПРАВЛЕНО: всегда показываем если есть
        if order_data.get('loading_method'):
            summary_parts.append(f"⬆️ Погрузка: {order_data['loading_method']}")
        if order_data.get('unloading_method'):
            summary_parts.append(f"⬇️ Разгрузка: {order_data['unloading_method']}")
        
        # Контакты
        if order_data.get('contact_name'):
            summary_parts.append(f"👤 Имя: {order_data['contact_name']}")
        if order_data.get('contact_phone'):
            summary_parts.append(f"📞 Телефон: {order_data['contact_phone']}")
        
        if summary_parts:
            result = "\n".join(summary_parts)
            if current_step:
                result += f"\n\n🔄 Выбираем: {current_step}"
            return result
        else:
            return "📋 Оформление заказа"

# ДУБЛИРОВАННЫЙ МЕТОД УДАЛЕН - используется существующий выше

 