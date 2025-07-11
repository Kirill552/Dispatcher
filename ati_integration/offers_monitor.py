#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мониторинг встречных предложений на грузы ATI.SU
Проверяет каждые 10 минут, передает в ИИ-продажника при наличии 3+ предложений
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from utils.logger import get_logger
from utils.config import settings
from ati_integration.ati_client_v2 import ATIClientV2
from ai_services.sales_agent import sales_agent
from database.crud import get_orders_by_ati_cargo_ids, update_order_status, create_commission

logger = get_logger("OFFERS_MONITOR")


@dataclass
class CargoOffers:
    """Данные груза с предложениями"""
    cargo_id: str
    cargo_number: str
    cargo_name: str
    route: str
    offers: List[Dict]
    external_id: str
    created_at: datetime
    last_check: datetime
    offers_count: int
    best_offer_price: float
    client_id: Optional[int] = None


class OffersMonitor:
    """Мониторинг встречных предложений с ИИ-продажником"""
    
    def __init__(self):
        self.ati_client = ATIClientV2()
        self.is_running = False
        self.monitoring_interval = 300  # 5 минут - разумный интервал для ATI предложений
        self.min_offers_for_sale = 3    # Минимум предложений для запуска продаж
        self.api_delay = 0.1           # 100мс между запросами (соблюдаем лимит)
        
        # Кэш для отслеживания грузов
        self.monitored_cargos: Dict[str, CargoOffers] = {}
        
        # Флаг для однократного сброса тестового груза (сброшен для повторного теста)
        self.test_reset_done = False
        
    async def start_monitoring(self):
        """Запуск мониторинга в фоновом режиме"""
        if self.is_running:
            logger.warning("⚠️ Мониторинг уже запущен")
            return
            
        self.is_running = True
        logger.info("🚀 Запуск мониторинга встречных предложений")
        
        try:
            while self.is_running:
                await self._monitor_cycle()
                await asyncio.sleep(self.monitoring_interval)
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка мониторинга: {e}")
            self.is_running = False
            
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        logger.info("🛑 Остановка мониторинга встречных предложений")
        self.is_running = False
        
    async def _monitor_cycle(self):
        """Один цикл мониторинга"""
        logger.info("🔄 Начинаем цикл мониторинга")
        
        try:
            # 1. Получаем все грузы компании
            all_loads = await self.ati_client.get_all_company_loads()
            await asyncio.sleep(self.api_delay)
            
            if not all_loads:
                logger.warning("⚠️ Нет грузов для мониторинга")
                return
                
            logger.info(f"📦 Получено {len(all_loads)} грузов для проверки")
            
            # 2. Фильтруем активные грузы (созданные нашим ИИ)
            active_cargos = await self._filter_active_cargos(all_loads)
            logger.info(f"🎯 Активных грузов ИИ: {len(active_cargos)}")
            
            # 3. Проверяем предложения для каждого груза
            for cargo in active_cargos:
                await self._check_cargo_offers(cargo)
                await asyncio.sleep(self.api_delay)  # Соблюдаем лимиты API
                
            # 3.5. ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА ТЕСТОВОГО ГРУЗА (только если нет активных)
            if not active_cargos and all_loads and not self.test_reset_done:
                for load in all_loads:
                    if load.get("Id") == "bc0d4af9-ffd1-43f4-8183-acb9f7d95eb0":
                        logger.info("🧪 ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА ТЕСТОВОГО ГРУЗА (ОДНОКРАТНО)")
                        
                        # Сбрасываем статус сессии для повторного тестирования
                        from database.crud import update_monitoring_session
                        
                        logger.info("🔄 Сбрасываем статус сессии для повторного тестирования ИИ-продажника")
                        await update_monitoring_session("bc0d4af9-ffd1-43f4-8183-acb9f7d95eb0", {
                            "status": "monitoring",
                            "first_offer_sent_at": None
                        })
                        
                        # Устанавливаем флаг что сброс уже сделан
                        self.test_reset_done = True
                        
                        await self._check_cargo_offers(load)
                        await asyncio.sleep(self.api_delay)
                        break
                
            # 4. Запускаем ИИ-продажника для готовых грузов
            await self._process_ready_offers()
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
            
    async def _filter_active_cargos(self, all_loads: List[Dict]) -> List[Dict]:
        """Фильтрация активных грузов созданных ИИ"""
        from database.crud import get_monitoring_session_by_cargo_id
        
        active_cargos = []
        current_time = datetime.now()
        
        for load in all_loads:
            # Проверяем что груз создан нашим ИИ (по external_id)
            external_id = load.get("ExternalId", "")
            cargo_id = load.get("Id", "")
            
            logger.info(f"🔍 Проверяем груз {cargo_id}: external_id='{external_id}', IsArchived={load.get('IsArchived', False)}")
            
            # ВРЕМЕННОЕ ИСКЛЮЧЕНИЕ ДЛЯ ТЕСТИРОВАНИЯ: добавляем конкретный груз
            is_ai_cargo = (external_id.startswith("AI_") or 
                          cargo_id == "bc0d4af9-ffd1-43f4-8183-acb9f7d95eb0")
            
            if is_ai_cargo:
                # Проверяем что груз активен и не в архиве
                if not load.get("IsArchived", False):
                    
                    # НОВАЯ ПРОВЕРКА: проверяем, есть ли уже активная сессия для этого груза
                    try:
                        existing_session = await get_monitoring_session_by_cargo_id(cargo_id)
                        logger.info(f"🔍 Проверка сессии для груза {cargo_id}: {existing_session}")
                        
                        if existing_session and existing_session.get("status") in ["offer_sent", "in_dialog", "completed"]:
                            logger.info(f"⏭️ Пропускаем груз {cargo_id} - уже есть активная сессия (статус: {existing_session.get('status')})")
                            continue
                        elif existing_session:
                            logger.info(f"✅ Груз {cargo_id} имеет сессию со статусом {existing_session.get('status')} - продолжаем обработку")
                        else:
                            logger.info(f"✅ Груз {cargo_id} не имеет активной сессии - добавляем к обработке")
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка проверки сессии для груза {cargo_id}: {e}")
                    
                    # Проверяем срок действия груза по LastDate
                    last_date_str = load.get("LastDate")
                    if last_date_str:
                        try:
                            # Парсим дату в формате ISO (с Z в конце)
                            last_date = datetime.fromisoformat(last_date_str.replace("Z", ""))
                            
                            # Проверяем что груз еще актуален
                            if last_date > current_time:
                                active_cargos.append(load)
                                logger.debug(f"✅ Груз {load.get('Id')} активен до {last_date}")
                            else:
                                logger.info(f"⏰ Груз {load.get('Id')} просрочен (до {last_date})")
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка парсинга даты для груза {load.get('Id')}: {e}")
                            # В случае ошибки парсинга - добавляем груз (лучше обработать чем пропустить)
                            active_cargos.append(load)
                    else:
                        # Если нет LastDate - считаем груз активным
                        active_cargos.append(load)
                        
        logger.info(f"📋 Отфильтровано {len(active_cargos)} активных грузов из {len(all_loads)} общих")
        return active_cargos
        
    async def _check_cargo_offers(self, cargo: Dict):
        """Проверка предложений для конкретного груза"""
        cargo_id = cargo.get("Id")
        if not cargo_id:
            return
            
        try:
            logger.info(f"🔍 Проверяем предложения для груза {cargo_id}")
            
            # Получаем встречные предложения
            offers = await self.ati_client.get_cargo_responses_new(cargo_id)
            
            logger.info(f"📊 Груз {cargo_id}: {len(offers) if offers else 0} предложений получено")
            
            if not offers:
                logger.info(f"⚠️ Нет предложений для груза {cargo_id} - пропускаем")
                return
                
            # Обновляем данные в кэше
            cargo_offers = self._update_cargo_cache(cargo, offers)
            
            logger.info(f"📊 Груз {cargo_id}: {len(offers)} предложений добавлено в кэш")
            
            # Проверяем готовность к продаже
            if len(offers) >= self.min_offers_for_sale:
                logger.info(f"🎯 Груз {cargo_id} готов к продаже ({len(offers)} предложений >= {self.min_offers_for_sale})")
            else:
                logger.info(f"⏳ Груз {cargo_id} еще не готов ({len(offers)} предложений < {self.min_offers_for_sale})")
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки предложений для груза {cargo_id}: {e}")
            
    def _update_cargo_cache(self, cargo: Dict, offers: List[Dict]) -> CargoOffers:
        """Обновление кэша данных груза"""
        cargo_id = cargo.get("Id")
        
        # Находим лучшее предложение (минимальная цена)
        best_price = min(offer.get("Price", float('inf')) for offer in offers) if offers else 0
        
        # Формируем маршрут
        from_city = cargo.get("FromCityName", "")
        to_city = cargo.get("ToCityName", "")
        route = f"{from_city} → {to_city}"
        
        # Создаем/обновляем запись в кэше
        cargo_offers = CargoOffers(
            cargo_id=cargo_id,
            cargo_number=cargo.get("Number", ""),
            cargo_name=cargo.get("CargoName", ""),
            route=route,
            offers=offers,
            external_id=cargo.get("ExternalId", ""),
            created_at=datetime.fromisoformat(cargo.get("DateAdded", "").replace("Z", "")) if cargo.get("DateAdded") else datetime.now(),
            last_check=datetime.now(),
            offers_count=len(offers),
            best_offer_price=best_price
        )
        
        self.monitored_cargos[cargo_id] = cargo_offers
        return cargo_offers
        
    async def _process_ready_offers(self):
        """Обработка грузов готовых к продаже"""
        ready_cargos = [
            cargo for cargo in self.monitored_cargos.values()
            if cargo.offers_count >= self.min_offers_for_sale
        ]
        
        if not ready_cargos:
            return
            
        logger.info(f"🎯 Найдено {len(ready_cargos)} грузов готовых к продаже")
        
        for cargo_offers in ready_cargos:
            try:
                await self._start_ai_sales_process(cargo_offers)
            except Exception as e:
                logger.error(f"❌ Ошибка запуска продаж для груза {cargo_offers.cargo_id}: {e}")
                
    async def _start_ai_sales_process(self, cargo_offers: CargoOffers):
        """Запуск процесса продаж через ИИ"""
        logger.info(f"🤖 Запуск ИИ-продажника для груза {cargo_offers.cargo_id}")
        
        try:
            # 1. Проверяем, есть ли уже активная сессия мониторинга для этого груза
            from database.crud import get_monitoring_session_by_cargo_id
            existing_session = await get_monitoring_session_by_cargo_id(cargo_offers.cargo_id)
            
            if existing_session and existing_session.get("status") in ["offer_sent", "in_dialog", "completed"]:
                logger.info(f"⚠️ Предложение для груза {cargo_offers.cargo_id} уже отправлено клиенту (статус: {existing_session.get('status')})")
                return
            
            # 2. Находим заказ в базе данных
            orders = await get_orders_by_ati_cargo_ids([cargo_offers.cargo_id])
            if not orders:
                logger.warning(f"⚠️ Заказ не найден в БД для груза {cargo_offers.cargo_id}")
                return
            order = orders[0]  # Берем первый заказ
                
            # 3. Выбираем лучшее предложение
            best_offer = await self._select_best_offer(cargo_offers.offers)
            if not best_offer:
                logger.warning(f"⚠️ Не удалось выбрать лучшее предложение для груза {cargo_offers.cargo_id}")
                return
                
            # 4. Рассчитываем цену для клиента
            carrier_price = best_offer.get("Price", 0)
            pricing = await self.ati_client.calculate_client_price(carrier_price, 40.0)
            
            # 5. Формируем данные заказа для ИИ
            order_data = {
                "cargo_id": cargo_offers.cargo_id,
                "cargo_description": cargo_offers.cargo_name,
                "route": cargo_offers.route,
                "from_city": order.from_city,
                "to_city": order.to_city,
                "cargo_type": order.cargo_type,
                "weight": order.weight,
                "volume": order.volume,
                "loading_date": order.loading_date.isoformat() if order.loading_date else None
            }
            
            # 6. Генерируем предложение через ИИ
            offer_message = await sales_agent.generate_price_offer_message(
                order_data=order_data,
                carrier_price=carrier_price,
                our_price=pricing["client_price"]
            )
            
            # 7. Отправляем предложение клиенту
            await self._send_offer_to_client(order, offer_message, best_offer, pricing, cargo_offers)
            
            # 8. Обновляем статус заказа
            await update_order_status(order.id, "offer_sent")
            
            logger.info(f"✅ Предложение отправлено клиенту для груза {cargo_offers.cargo_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска ИИ-продаж: {e}")
            
    async def _select_best_offer(self, offers: List[Dict]) -> Optional[Dict]:
        """Выбор лучшего предложения из списка"""
        if not offers:
            return None
        
        try:
            # Сортируем предложения по цене (по возрастанию)
            sorted_offers = sorted(offers, key=lambda x: x.get("Price", float('inf')))
            
            # Берём 3 самых дешевых предложения
            top_3_offers = sorted_offers[:3]
            
            # Дополнительный анализ надежности перевозчиков для топ-3
            analyzed_offers = []
            
            for offer in top_3_offers:
                company_id = offer.get("CompanyId")
                if company_id:
                    # Получаем информацию о компании
                    company_info = await self.ati_client.get_firm_contacts_summary(company_id)
                    
                    if company_info and company_info.get("contacts"):
                        contact = company_info["contacts"][0]
                        rating = contact.get("Rating", 0)
                        
                        # Критерии отбора: цена + надежность
                        score = (
                            (1 / max(offer.get("Price", 1), 1)) * 1000 +  # Чем дешевле, тем лучше
                            rating * 100  # Бонус за высокий рейтинг
                        )
                        
                        analyzed_offers.append({
                            "offer": offer,
                            "company_info": company_info,
                            "score": score,
                            "rating": rating
                        })
                        
                        logger.info(f"📊 {contact.get('CompanyName', 'N/A')}: ⭐{rating} 💰{offer.get('Price', 0):,.0f}₽ 🏆{score:.1f}")
            
            if not analyzed_offers:
                # Если не удалось получить информацию о компаниях, возвращаем самое дешевое
                best_offer = sorted_offers[0]
                logger.info(f"🏆 Выбрано самое дешевое предложение: {best_offer.get('Price', 0):,.0f}₽")
                return best_offer
            
            # Выбираем предложение с лучшим соотношением цена/качество
            best_analyzed = max(analyzed_offers, key=lambda x: x["score"])
            best_offer = best_analyzed["offer"]
            
            logger.info("🏆 Выбрано самое дешевое предложение:")
            logger.info(f"   🏢 Фирма: {best_analyzed['company_info']['contacts'][0].get('CompanyName', 'N/A')}")
            logger.info(f"   💰 Цена: {best_offer.get('Price', 0):,.0f} руб")
            logger.info(f"   🎯 Из {len(offers)} предложений выбрано самое дешевое")
            
            return best_offer
            
        except Exception as e:
            logger.error(f"❌ Ошибка выбора лучшего предложения: {e}")
            # В случае ошибки возвращаем самое дешевое
            if offers:
                cheapest = min(offers, key=lambda x: x.get("Price", float('inf')))
                logger.info(f"🏆 Fallback: выбрано самое дешевое предложение за {cheapest.get('Price', 0):,.0f}₽")
                return cheapest
            return None
        
    async def _send_offer_to_client(self, order, offer_message: str, best_offer: Dict, pricing: Dict, cargo_offers: CargoOffers):
        """Отправка предложения клиенту"""
        try:
            # Если у клиента есть Telegram ID - отправляем туда
            # Получаем клиента через отдельный запрос чтобы избежать проблем с сессией
            if order.client_id:
                from database.crud import get_client_by_telegram_id
                # Пока пропускаем отправку клиенту, так как нет связи telegram_id с order
                logger.info(f"📱 Клиент ID: {order.client_id} - отправка в Telegram пока не настроена")
                
            # Если есть телефон - можно отправить SMS (если настроено)
            if order.contact_phone:
                logger.info(f"📱 Можно отправить SMS на {order.contact_phone}")
                
            # ИСПОЛЬЗУЕМ УЖЕ СГЕНЕРИРОВАННОЕ ИИ-СООБЩЕНИЕ
            # Отправляем предложение клиенту в Telegram
            success = await self._send_offer_to_telegram_client(order, offer_message, best_offer, pricing)
            
            if success:
                # УСПЕШНАЯ ОТПРАВКА - НО ВЛАДЕЛЬЦА НЕ УВЕДОМЛЯЕМ ПОКА!
                logger.info(f"✅ ИИ-предложение отправлено клиенту для груза {cargo_offers.cargo_id}")
                logger.info("⏳ Ожидаем ответа клиента. Владелец будет уведомлен только при согласии.")
            else:
                # НЕУДАЧНАЯ ОТПРАВКА - записываем в БД
                logger.info(f"❌ Не удалось отправить предложение клиенту для груза {cargo_offers.cargo_id}")
                
                # Формируем данные для записи неудачной сделки
                order_data_for_failed_deal = {
                    "id": order.id,
                    "ati_cargo_id": cargo_offers.cargo_id,
                    "cargo_type": order.cargo_type,
                    "from_city": order.from_city,
                    "to_city": order.to_city,
                    "weight": order.weight,
                    "volume": order.volume,
                    "contact_name": order.contact_name,
                    "contact_phone": order.contact_phone,
                    "loading_date": order.loading_date.isoformat() if order.loading_date else None
                }
                
                await sales_agent.record_failed_deal(
                    order_data=order_data_for_failed_deal,
                    best_offer=best_offer,
                    pricing=pricing,
                    failure_reason="delivery_failed",
                    failure_details="Не удалось доставить предложение клиенту"
                )
            
            logger.info(f"📤 Предложение отправлено клиенту через ИИ-продажника")
            
            # === ЗАКОММЕНТИРОВАННОЕ УВЕДОМЛЕНИЕ ВЛАДЕЛЬЦА ===
            # Будет отправляться только после успешной продажи через sales_agent
            """
            # Также уведомляем владельца бизнеса
            if order.owner_id:
                # Получаем контакты перевозчика
                carrier_contacts = ""
                firm_contacts = best_offer.get("firm_contacts")
                # firm_contacts - это список контактов, а не словарь
                if firm_contacts and isinstance(firm_contacts, list) and len(firm_contacts) > 0:
                    contact = firm_contacts[0]  # Берем первый контакт
                    phone = contact.get("phone") or contact.get("mobile_phone", "не указан")
                    email = contact.get("email", "не указан")
                    carrier_contacts = f"📞 Телефон: {phone}\n📧 Email: {email}"
                else:
                    carrier_contacts = "📞 Контакты уточняются"
                
                owner_message = f'''💼 НОВАЯ СДЕЛКА В РАБОТЕ

📦 ГРУЗ: {order.cargo_type}
🚛 МАРШРУТ: {order.from_city} → {order.to_city}
💰 ФИНАНСЫ:
• Цена перевозчика: {best_offer.get('Price', 0):,} руб
• Цена клиенту: {pricing['client_price']:,} руб  
• Ваша прибыль: {pricing['profit']:,} руб

🚛 ПЕРЕВОЗЧИК: {best_offer.get('FirmName', 'N/A')}
{carrier_contacts}

👤 КЛИЕНТ: {order.contact_name} ({order.contact_phone})'''
                
                await self._send_telegram_offer(order.owner_id, owner_message)
            """
                
            # Сохраняем комиссию в базе
            commission_data = {
                "order_id": order.id,
                "carrier_price": int(best_offer.get("Price", 0)),
                "total_price": int(pricing["client_price"]),
                "commission_amount": int(pricing["profit"]),
                "commission_percent": pricing["markup_percent"]
            }
            await create_commission(commission_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки предложения: {e}")
            
    async def _send_telegram_offer(self, telegram_id: int, message: str):
        """Отправка предложения в Telegram"""
        try:
            from bot.client_bot import send_telegram_message
            
            success = await send_telegram_message(telegram_id, message)
            
            if success:
                logger.info(f"✅ Предложение отправлено в Telegram: {telegram_id}")
            else:
                raise Exception("Не удалось отправить сообщение")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram {telegram_id}: {e}")
            raise

    async def _send_offer_to_telegram_client(self, order, offer_message: str, best_offer: Dict, pricing: Dict) -> bool:
        """Отправка предложения клиенту в Telegram"""
        try:
            from database.crud import get_client_by_id, create_monitoring_session, get_monitoring_session_by_cargo_id, update_monitoring_session
            from datetime import datetime, timedelta
            
            # Получаем клиента
            client = await get_client_by_id(order.client_id)
            
            if not client or not client.telegram_id:
                logger.warning(f"❌ У клиента {order.client_id} нет Telegram ID")
                return False
            
            client_telegram_id = client.telegram_id
            
            # Проверяем, что это не тестовый случай с владельцем (ID 408001372)
            if client_telegram_id == 408001372:
                logger.info("🧪 Тестовый режим: отправляем предложение владельцу")
            
            # Проверяем, есть ли уже сессия мониторинга для этого груза
            existing_session = await get_monitoring_session_by_cargo_id(order.ati_cargo_id)
            
            if existing_session:
                # Проверяем время последней отправки
                first_offer_sent_at_str = existing_session.get("first_offer_sent_at")
                if first_offer_sent_at_str:
                    try:
                        first_offer_sent_at = datetime.fromisoformat(first_offer_sent_at_str.replace('Z', ''))
                        time_since_last_offer = datetime.utcnow() - first_offer_sent_at
                        
                        # Если прошло меньше 5 минут с последней отправки - не отправляем повторно
                        if time_since_last_offer < timedelta(minutes=5):
                            logger.info(f"⏰ Предложение для груза {order.ati_cargo_id} уже отправлено {time_since_last_offer.total_seconds()/60:.1f} мин назад")
                            return True  # Возвращаем True, потому что предложение уже отправлено
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка парсинга времени отправки: {e}")
                
                # Обновляем существующую сессию
                logger.info(f"♻️ Обновляем существующую сессию мониторинга для груза {order.ati_cargo_id}")
                
                update_data = {
                    "ai_offer_message": offer_message,
                    "client_telegram_id": client_telegram_id,
                    "status": "offer_sent",
                    "best_offer_data": best_offer,
                    "pricing_data": pricing
                }
                
                success_update = await update_monitoring_session(order.ati_cargo_id, update_data)
                
                if not success_update:
                    logger.error(f"❌ Не удалось обновить сессию мониторинга для груза {order.ati_cargo_id}")
                    return False
                    
                # НЕ отправляем сообщение повторно - только обновляем сессию
                logger.info(f"✅ Сессия мониторинга обновлена для груза {order.ati_cargo_id} (сообщение уже отправлено)")
                return True
                    
            else:
                # Создаем новую сессию мониторинга только если её нет
                logger.info(f"🆕 Создаем новую сессию мониторинга для груза {order.ati_cargo_id}")
                
                session_data = {
                    "ati_cargo_id": order.ati_cargo_id,
                    "order_id": order.id,
                    "cargo_data": {
                        "cargo_type": order.cargo_type,
                        "from_city": order.from_city,
                        "to_city": order.to_city,
                        "weight": order.weight,
                        "volume": order.volume
                    },
                    "best_offer_data": best_offer,
                    "pricing_data": pricing,
                    "ai_offer_message": offer_message,
                    "client_telegram_id": client_telegram_id,
                    "first_offer_sent_at": datetime.utcnow(),
                    "status": "offer_sent",
                    "offers_count": len(best_offer) if isinstance(best_offer, list) else 1,
                    "min_offers_threshold": 3
                }
                
                monitoring_session = await create_monitoring_session(session_data)
                
                if not monitoring_session:
                    logger.error(f"❌ Не удалось создать сессию мониторинга")
                    return False
                
                # Отправляем предложение в Telegram ТОЛЬКО при создании новой сессии
                await self._send_telegram_offer(client_telegram_id, offer_message)
                
                logger.info(f"✅ ИИ-предложение отправлено клиенту {client_telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка отправки предложения клиенту в Telegram: {e}")
            return False
            
    async def get_monitoring_stats(self) -> Dict:
        """Получение статистики мониторинга"""
        total_cargos = len(self.monitored_cargos)
        ready_for_sale = len([c for c in self.monitored_cargos.values() if c.offers_count >= self.min_offers_for_sale])
        total_offers = sum(c.offers_count for c in self.monitored_cargos.values())
        
        return {
            "is_running": self.is_running,
            "total_monitored_cargos": total_cargos,
            "ready_for_sale": ready_for_sale,
            "total_offers": total_offers,
            "monitoring_interval": self.monitoring_interval,
            "min_offers_threshold": self.min_offers_for_sale,
            "last_check": datetime.now().isoformat()
        }


# Глобальный экземпляр мониторинга
offers_monitor = OffersMonitor() 