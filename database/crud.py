"""
CRUD операции для работы с базой данных
"""
from typing import Dict, List, Optional, Any
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timedelta

from database.database import AsyncSessionLocal
from database.models import Client, Order, Conversation, Commission, Carrier
from utils.logger import db_logger as logger


# === CRUD для клиентов ===

async def create_client(client_data: Dict) -> Client:
    """Создать нового клиента"""
    
    async with AsyncSessionLocal() as session:
        try:
            client = Client(**client_data)
            session.add(client)
            await session.commit()
            await session.refresh(client)
            
            logger.info(f"✅ Создан клиент: {client.telegram_id}")
            return client
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка создания клиента: {str(e)}")
            raise


async def get_client_by_telegram_id(telegram_id: int) -> Optional[Client]:
    """Получить клиента по Telegram ID"""
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Client).where(Client.telegram_id == telegram_id)
            )
            client = result.scalar_one_or_none()
            
            if client:
                logger.info(f"👤 Найден клиент: {telegram_id}")
            
            return client
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска клиента: {str(e)}")
            return None


async def get_client_by_id(client_id: int) -> Optional[Client]:
    """Получить клиента по ID"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()
            
            if client:
                logger.info(f"👤 Найден клиент: {client.first_name} (ID: {client.id})")
            
            return client
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска клиента по ID: {str(e)}")
            return None


async def update_client(telegram_id: int, update_data: Dict) -> Optional[Client]:
    """Обновить данные клиента"""
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                update(Client)
                .where(Client.telegram_id == telegram_id)
                .values(**update_data)
                .returning(Client)
            )
            
            client = result.scalar_one_or_none()
            await session.commit()
            
            if client:
                logger.info(f"✅ Обновлен клиент: {telegram_id}")
            
            return client
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка обновления клиента: {str(e)}")
            return None


# === CRUD для заказов ===

async def create_order(order_data: Dict) -> Order:
    """Создать новый заказ"""
    
    async with AsyncSessionLocal() as session:
        try:
            order = Order(**order_data)
            session.add(order)
            await session.commit()
            await session.refresh(order)
            
            logger.info(f"✅ Создан заказ: {order.id} ({order.from_city} → {order.to_city})")
            return order
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка создания заказа: {str(e)}")
            raise


async def get_orders_by_client(client_id: int) -> List[Order]:
    """Получить заказы клиента"""
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Order).where(Order.client_id == client_id)
            )
            orders = result.scalars().all()
            
            logger.info(f"📋 Найдено заказов для клиента {client_id}: {len(orders)}")
            return list(orders)
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска заказов: {str(e)}")
            return []


async def get_orders_by_telegram_id(telegram_id: int) -> List[Dict]:
    """Получить заказы клиента по Telegram ID"""
    
    async with AsyncSessionLocal() as session:
        try:
            # Сначала находим клиента
            client_result = await session.execute(
                select(Client.id).where(Client.telegram_id == telegram_id)
            )
            client = client_result.scalar_one_or_none()
            
            if not client:
                logger.info(f"👤 Клиент с telegram_id {telegram_id} не найден")
                return []
            
            # Получаем активные заказы клиента
            result = await session.execute(
                select(Order).where(
                    Order.client_id == client,
                    Order.status.in_(["pending", "searching", "offers_found"])
                ).order_by(Order.created_at.desc())
            )
            orders = result.scalars().all()
            
            # Конвертируем в словари
            orders_data = []
            for order in orders:
                order_dict = {
                    'id': order.id,
                    'cargo_type': order.cargo_type,
                    'from_city': order.from_city,
                    'to_city': order.to_city,
                    'weight': order.weight,
                    'volume': order.volume,
                    'loading_date': order.loading_date,
                    'loading_date_from': getattr(order, 'loading_date_from', None),
                    'status': order.status,
                    'created_at': order.created_at
                }
                orders_data.append(order_dict)
            
            logger.info(f"📋 Найдено активных заказов для telegram_id {telegram_id}: {len(orders_data)}")
            return orders_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска заказов по telegram_id: {str(e)}")
            return []


async def update_order_status(order_id: int, status: str, **additional_data) -> Optional[Order]:
    """Обновить статус заказа"""
    
    async with AsyncSessionLocal() as session:
        try:
            update_data = {"status": status, **additional_data}
            
            result = await session.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(**update_data)
                .returning(Order)
            )
            
            order = result.scalar_one_or_none()
            await session.commit()
            
            if order:
                logger.info(f"✅ Обновлен статус заказа {order_id}: {status}")
            
            return order
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка обновления статуса заказа: {str(e)}")
            return None


async def get_pending_orders() -> List[Order]:
    """Получить все необработанные заказы"""
    
    async with AsyncSessionLocal() as session:
        try:
            # Безопасный запрос - получаем только основные поля
            result = await session.execute(
                select(
                    Order.id,
                    Order.client_id,
                    Order.from_city,
                    Order.to_city,
                    Order.cargo_description,
                    Order.weight,
                    Order.volume,
                    Order.cargo_type,
                    Order.client_price,
                    Order.carrier_price,
                    Order.our_commission,
                    Order.loading_date,
                    Order.delivery_date,
                    Order.created_at,
                    Order.status,
                    Order.loading_contact,
                    Order.delivery_contact,
                    Order.ati_cargo_id,
                    Order.ati_order_id,
                    Order.carrier_info
                ).where(Order.status.in_(["new", "pending", "clarification_needed"]))
            )
            orders = result.all()
            
            logger.info(f"📋 Найдено необработанных заказов: {len(orders)}")
            return list(orders)
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска необработанных заказов: {str(e)}")
            return []


# === УДАЛЕНЫ CRUD функции для мониторинга чужих грузов ===
# Функции create_monitored_cargo, get_processed_cargo_ids, mark_cargo_as_processed, 
# update_monitored_cargo_status использовались для старой логики "холодных продаж"
# Новая логика: работаем только с заказами клиентов через функции выше


# === CRUD для переписки ===

async def save_conversation_message(
    client_id: int,
    sender_type: str,
    message_text: str,
    order_id: Optional[int] = None,
    telegram_message_id: Optional[int] = None
) -> Conversation:
    """Сохранить сообщение в переписке"""
    
    async with AsyncSessionLocal() as session:
        try:
            conversation = Conversation(
                client_id=client_id,
                order_id=order_id,
                sender_type=sender_type,
                message_text=message_text,
                telegram_message_id=telegram_message_id,
                created_at=datetime.utcnow()
            )
            
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            
            logger.info(f"💬 Сохранено сообщение: {sender_type} → клиент {client_id}")
            return conversation
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка сохранения сообщения: {str(e)}")
            raise


async def get_conversation_history(client_id: int, limit: int = 50) -> List[Conversation]:
    """Получить историю переписки с клиентом"""
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Conversation)
                .where(Conversation.client_id == client_id)
                .order_by(Conversation.created_at.desc())
                .limit(limit)
            )
            
            messages = list(result.scalars().all())
            messages.reverse()  # Хронологический порядок
            
            logger.info(f"💬 Загружена история переписки клиента {client_id}: {len(messages)} сообщений")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории переписки: {str(e)}")
            return []


# === Статистические функции ===

async def get_daily_stats(date: datetime) -> Dict[str, Any]:
    """Получить статистику за день"""
    
    async with AsyncSessionLocal() as session:
        try:
            # Количество новых клиентов
            new_clients_result = await session.execute(
                select(Client).where(Client.created_at >= date)
            )
            new_clients_count = len(new_clients_result.scalars().all())
            
            # Количество новых заказов
            new_orders_result = await session.execute(
                select(Order).where(Order.created_at >= date)
            )
            new_orders_count = len(new_orders_result.scalars().all())
            
            # Количество завершенных заказов
            completed_orders_result = await session.execute(
                select(Order).where(Order.created_at >= date, Order.status == "completed")
            )
            completed_orders_count = len(completed_orders_result.scalars().all())
            
            stats = {
                "date": date.date(),
                "new_clients": new_clients_count,
                "new_orders": new_orders_count,
                "completed_orders": completed_orders_count
            }
            
            logger.info(f"📊 Статистика за {date.date()}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {str(e)}")
            return {}


async def cleanup_old_data(days_to_keep: int = 90):
    """Очистка старых данных"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    async with AsyncSessionLocal() as session:
        try:
            # Удаляем старые сообщения переписки
            await session.execute(
                delete(Conversation).where(Conversation.created_at < cutoff_date)
            )
            
            # Удаляем старые сообщения
            await session.execute(
                delete(Conversation).where(Conversation.created_at < cutoff_date)
            )
            
            await session.commit()
            
            logger.info(f"🧹 Очистка данных старше {days_to_keep} дней завершена")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка очистки данных: {str(e)}")
            raise


# === CRUD для комиссий ===

async def create_commission(commission_data: Dict) -> Commission:
    """Создать запись о комиссии"""
    
    async with AsyncSessionLocal() as session:
        try:
            # DEBUG: логируем входящие данные
            logger.debug(f"🔍 Создание комиссии с данными: {commission_data}")
            commission = Commission(**commission_data)
            session.add(commission)
            await session.commit()
            await session.refresh(commission)
            
            logger.info(f"✅ Создана комиссия: {commission.total_price}₽")
            return commission
            
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка создания комиссии: {str(e)}")
            raise


async def get_orders_by_ati_cargo_ids(cargo_ids: List[str]) -> List[Order]:
    """
    Получить заказы по списку ATI cargo ID
    
    Args:
        cargo_ids: Список ID грузов в ATI.SU
        
    Returns:
        Список заказов с указанными ATI cargo ID
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Order).where(Order.ati_cargo_id.in_(cargo_ids))
            )
            orders = result.scalars().all()
            
            logger.info(f"📋 Найдено заказов по ATI cargo IDs: {len(orders)}")
            return list(orders)
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска заказов по ATI cargo IDs: {str(e)}")
            return []


async def get_order_by_ati_cargo_id(cargo_id: str) -> Optional[Order]:
    """
    Получить заказ по ATI cargo ID
    
    Args:
        cargo_id: ID груза в ATI.SU
        
    Returns:
        Заказ с указанным ATI cargo ID или None
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(Order).where(Order.ati_cargo_id == cargo_id)
            )
            order = result.scalar_one_or_none()
            
            if order:
                logger.info(f"📋 Найден заказ по ATI cargo ID {cargo_id}: {order.id}")
            
            return order
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска заказа по ATI cargo ID: {str(e)}")
            return None


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С ПРЕДЛОЖЕНИЯМИ ПЕРЕВОЗЧИКОВ =====

async def create_carrier_offer(offer_data: Dict) -> Optional[Dict]:
    """Создание предложения перевозчика"""
    try:
        from database.models import CarrierOffer
        
        async with AsyncSessionLocal() as session:
            # Вычисляем прибыль
            carrier_price = offer_data.get('carrier_price_rub', 0)
            markup_percent = offer_data.get('markup_percent', 40.0)
            client_price = carrier_price * (1 + markup_percent / 100)
            profit = client_price - carrier_price
            
            offer_data.update({
                'client_price_rub': client_price,
                'profit_rub': profit
            })
            
            offer = CarrierOffer(**offer_data)
            session.add(offer)
            await session.commit()
            await session.refresh(offer)
            
            logger.info(f"💼 Создано предложение перевозчика: {offer.id} ({offer.from_city}→{offer.to_city}, {offer.carrier_price_rub}₽)")
            
            return {
                "id": offer.id,
                "order_id": offer.order_id,
                "from_city": offer.from_city,
                "to_city": offer.to_city,
                "carrier_price_rub": offer.carrier_price_rub,
                "client_price_rub": offer.client_price_rub,
                "profit_rub": offer.profit_rub,
                "carrier_company_name": offer.carrier_company_name,
                "status": offer.status
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания предложения перевозчика: {e}")
        return None


async def get_offers_by_order_id(order_id: str) -> List[Dict]:
    """Получение всех предложений по заказу"""
    try:
        from database.models import CarrierOffer
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CarrierOffer).where(CarrierOffer.order_id == order_id)
            )
            offers = result.scalars().all()
            
            offers_list = []
            for offer in offers:
                offers_list.append({
                    "id": offer.id,
                    "order_id": offer.order_id,
                    "ati_cargo_id": offer.ati_cargo_id,
                    "from_city": offer.from_city,
                    "to_city": offer.to_city,
                    "cargo_type": offer.cargo_type,
                    "weight_kg": offer.weight_kg,
                    "carrier_company_name": offer.carrier_company_name,
                    "carrier_phone": offer.carrier_phone,
                    "carrier_rating": offer.carrier_rating,
                    "carrier_price_rub": offer.carrier_price_rub,
                    "client_price_rub": offer.client_price_rub,
                    "profit_rub": offer.profit_rub,
                    "body_type": offer.body_type,
                    "loading_method": offer.loading_method,
                    "payment_type": offer.payment_type,
                    "delivery_days": offer.delivery_days,
                    "status": offer.status,
                    "is_selected": offer.is_selected,
                    "received_at": offer.received_at
                })
            
            logger.info(f"📋 Найдено предложений для заказа {order_id}: {len(offers_list)}")
            return offers_list
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения предложений для заказа {order_id}: {e}")
        return []


async def update_offer_status(offer_id: int, status: str, notes: str = None) -> bool:
    """Обновление статуса предложения"""
    try:
        from database.models import CarrierOffer
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CarrierOffer).where(CarrierOffer.id == offer_id)
            )
            offer = result.scalar_one_or_none()
            
            if not offer:
                logger.error(f"❌ Предложение {offer_id} не найдено")
                return False
            
            offer.status = status
            if notes:
                offer.notes = notes
                
            if status == "sent_to_client":
                offer.sent_to_client_at = datetime.utcnow()
            elif status in ["accepted", "rejected"]:
                offer.client_response_at = datetime.utcnow()
                if status == "accepted":
                    offer.is_selected = True
            
            await session.commit()
            logger.info(f"✅ Статус предложения {offer_id} обновлен на: {status}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса предложения {offer_id}: {e}")
        return False


async def get_price_statistics(from_city: str, to_city: str, cargo_type: str = None) -> Dict:
    """Получение статистики цен по маршруту"""
    try:
        from database.models import CarrierOffer
        from sqlalchemy import func
        
        async with AsyncSessionLocal() as session:
            query = select(
                func.count(CarrierOffer.id).label('offers_count'),
                func.avg(CarrierOffer.carrier_price_rub).label('avg_price'),
                func.min(CarrierOffer.carrier_price_rub).label('min_price'),
                func.max(CarrierOffer.carrier_price_rub).label('max_price')
            ).where(
                CarrierOffer.from_city == from_city,
                CarrierOffer.to_city == to_city
            )
            
            if cargo_type:
                query = query.where(CarrierOffer.cargo_type == cargo_type)
            
            result = await session.execute(query)
            stats = result.first()
            
            if stats and stats.offers_count > 0:
                return {
                    "offers_count": stats.offers_count,
                    "avg_price": round(stats.avg_price, 2) if stats.avg_price else 0,
                    "min_price": stats.min_price,
                    "max_price": stats.max_price,
                    "route": f"{from_city} → {to_city}",
                    "cargo_type": cargo_type
                }
            else:
                return {
                    "offers_count": 0,
                    "avg_price": 0,
                    "min_price": 0,
                    "max_price": 0,
                    "route": f"{from_city} → {to_city}",
                    "cargo_type": cargo_type
                }
                
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики цен для {from_city}→{to_city}: {e}")
        return {
            "offers_count": 0,
            "avg_price": 0,
            "min_price": 0,
            "max_price": 0,
            "route": f"{from_city} → {to_city}",
            "cargo_type": cargo_type
        }


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С НЕУДАЧНЫМИ СДЕЛКАМИ =====

async def create_failed_deal(failed_deal_data: Dict) -> Optional[Dict]:
    """Создание записи о неудачной сделке"""
    try:
        from database.models import FailedDeal
        
        async with AsyncSessionLocal() as session:
            failed_deal = FailedDeal(**failed_deal_data)
            session.add(failed_deal)
            await session.commit()
            await session.refresh(failed_deal)
            
            logger.info(f"❌ Записана неудачная сделка: {failed_deal.id} ({failed_deal.from_city}→{failed_deal.to_city}, причина: {failed_deal.failure_reason})")
            
            return {
                "id": failed_deal.id,
                "order_id": failed_deal.order_id,
                "ati_cargo_id": failed_deal.ati_cargo_id,
                "cargo_type": failed_deal.cargo_type,
                "from_city": failed_deal.from_city,
                "to_city": failed_deal.to_city,
                "potential_profit": failed_deal.potential_profit,
                "failure_reason": failed_deal.failure_reason,
                "failed_at": failed_deal.failed_at
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания записи о неудачной сделке: {e}")
        return None


async def get_failed_deals_stats(days: int = 30) -> Dict:
    """Получение статистики неудачных сделок за период"""
    try:
        from database.models import FailedDeal
        from sqlalchemy import func
        
        async with AsyncSessionLocal() as session:
            date_threshold = datetime.utcnow() - timedelta(days=days)
            
            # Общая статистика
            total_query = select(
                func.count(FailedDeal.id).label('total_failed'),
                func.sum(FailedDeal.potential_profit).label('lost_profit')
            ).where(FailedDeal.failed_at >= date_threshold)
            
            total_result = await session.execute(total_query)
            total_stats = total_result.first()
            
            # Статистика по причинам
            reasons_query = select(
                FailedDeal.failure_reason,
                func.count(FailedDeal.id).label('count'),
                func.sum(FailedDeal.potential_profit).label('lost_profit_by_reason')
            ).where(
                FailedDeal.failed_at >= date_threshold
            ).group_by(FailedDeal.failure_reason)
            
            reasons_result = await session.execute(reasons_query)
            reasons_stats = reasons_result.all()
            
            return {
                "period_days": days,
                "total_failed_deals": total_stats.total_failed or 0,
                "total_lost_profit": total_stats.lost_profit or 0,
                "failure_reasons": [
                    {
                        "reason": reason.failure_reason,
                        "count": reason.count,
                        "lost_profit": reason.lost_profit_by_reason or 0
                    }
                    for reason in reasons_stats
                ]
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики неудачных сделок: {e}")
        return {
            "period_days": days,
            "total_failed_deals": 0,
            "total_lost_profit": 0,
            "failure_reasons": []
        }


# ===== ФУНКЦИИ ДЛЯ РАБОТЫ С СЕССИЯМИ МОНИТОРИНГА =====

async def create_monitoring_session(session_data: Dict) -> Optional[Dict]:
    """Создание новой сессии мониторинга"""
    try:
        from database.models import MonitoringSession
        from datetime import datetime
        
        async with AsyncSessionLocal() as session:
            # Преобразуем строки дат в объекты datetime
            datetime_fields = [
                'first_offer_sent_at', 'deal_closed_at', 'human_intervention_requested_at',
                'monitoring_started_at', 'sales_started_at', 'completed_at', 'created_at', 'updated_at'
            ]
            
            for field in datetime_fields:
                if field in session_data and session_data[field] is not None:
                    if isinstance(session_data[field], str):
                        try:
                            session_data[field] = datetime.fromisoformat(session_data[field].replace('Z', ''))
                        except:
                            session_data[field] = datetime.utcnow()
            
            # Устанавливаем значения по умолчанию если не указаны
            if 'created_at' not in session_data:
                session_data['created_at'] = datetime.utcnow()
            if 'updated_at' not in session_data:
                session_data['updated_at'] = datetime.utcnow()
            if 'monitoring_started_at' not in session_data:
                session_data['monitoring_started_at'] = datetime.utcnow()
            
            monitoring_session = MonitoringSession(**session_data)
            session.add(monitoring_session)
            await session.commit()
            await session.refresh(monitoring_session)
            
            logger.info(f"✅ Создана сессия мониторинга: {monitoring_session.id} для груза {monitoring_session.ati_cargo_id}")
            
            return {
                "id": monitoring_session.id,
                "ati_cargo_id": monitoring_session.ati_cargo_id,
                "status": monitoring_session.status,
                "created_at": monitoring_session.created_at.isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания сессии мониторинга: {e}")
        return None


async def get_monitoring_session_by_cargo_id(ati_cargo_id: str) -> Optional[Dict]:
    """Получение сессии мониторинга по ID груза"""
    try:
        from database.models import MonitoringSession
        
        async with AsyncSessionLocal() as session:
            query = select(MonitoringSession).where(MonitoringSession.ati_cargo_id == ati_cargo_id)
            result = await session.execute(query)
            monitoring_session = result.scalar_one_or_none()
            
            if monitoring_session:
                return {
                    "id": monitoring_session.id,
                    "ati_cargo_id": monitoring_session.ati_cargo_id,
                    "order_id": monitoring_session.order_id,
                    "cargo_data": monitoring_session.cargo_data,
                    "offers_data": monitoring_session.offers_data,
                    "best_offer_data": monitoring_session.best_offer_data,
                    "pricing_data": monitoring_session.pricing_data,
                    "ai_offer_message": monitoring_session.ai_offer_message,
                    "status": monitoring_session.status,
                    "offers_count": monitoring_session.offers_count,
                    "monitoring_started_at": monitoring_session.monitoring_started_at.isoformat() if monitoring_session.monitoring_started_at else None,
                    "sales_started_at": monitoring_session.sales_started_at.isoformat() if monitoring_session.sales_started_at else None,
                    "sale_result": monitoring_session.sale_result,
                    "failure_reason": monitoring_session.failure_reason,
                    "client_telegram_id": monitoring_session.client_telegram_id,
                    "first_offer_sent_at": monitoring_session.first_offer_sent_at.isoformat() if monitoring_session.first_offer_sent_at else None
                }
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения сессии мониторинга для груза {ati_cargo_id}: {e}")
        return None


async def update_monitoring_session(ati_cargo_id: str, update_data: Dict) -> bool:
    """Обновление сессии мониторинга"""
    try:
        from database.models import MonitoringSession
        
        async with AsyncSessionLocal() as session:
            query = select(MonitoringSession).where(MonitoringSession.ati_cargo_id == ati_cargo_id)
            result = await session.execute(query)
            monitoring_session = result.scalar_one_or_none()
            
            if not monitoring_session:
                logger.warning(f"⚠️ Сессия мониторинга не найдена для груза {ati_cargo_id}")
                return False
            
            # Обновляем поля
            for key, value in update_data.items():
                if hasattr(monitoring_session, key):
                    setattr(monitoring_session, key, value)
            
            monitoring_session.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"✅ Обновлена сессия мониторинга для груза {ati_cargo_id}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка обновления сессии мониторинга для груза {ati_cargo_id}: {e}")
        return False


async def get_active_monitoring_sessions() -> List[Dict]:
    """Получение всех активных сессий мониторинга"""
    try:
        from database.models import MonitoringSession
        
        async with AsyncSessionLocal() as session:
            query = select(MonitoringSession).where(
                MonitoringSession.status.in_(["monitoring", "ready_for_sale", "selling"])
            )
            result = await session.execute(query)
            sessions = result.scalars().all()
            
            return [
                {
                    "id": sess.id,
                    "ati_cargo_id": sess.ati_cargo_id,
                    "order_id": sess.order_id,
                    "status": sess.status,
                    "offers_count": sess.offers_count,
                    "monitoring_started_at": sess.monitoring_started_at.isoformat(),
                    "cargo_data": sess.cargo_data
                }
                for sess in sessions
            ]
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения активных сессий мониторинга: {e}")
        return []

async def get_monitoring_session_by_id(session_id: int) -> Optional[Dict]:
    """Получение сессии мониторинга по ID"""
    try:
        from database.models import MonitoringSession
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MonitoringSession).where(MonitoringSession.id == session_id)
            )
            
            monitoring_session = result.scalar_one_or_none()
            
            if monitoring_session:
                return {
                    "id": monitoring_session.id,
                    "ati_cargo_id": monitoring_session.ati_cargo_id,
                    "order_id": monitoring_session.order_id,
                    "cargo_data": monitoring_session.cargo_data,
                    "offers_data": monitoring_session.offers_data,
                    "best_offer_data": monitoring_session.best_offer_data,
                    "pricing_data": monitoring_session.pricing_data,
                    "status": monitoring_session.status,
                    "client_telegram_id": monitoring_session.client_telegram_id,
                    "created_at": monitoring_session.created_at.isoformat() if monitoring_session.created_at else None,
                    "first_offer_sent_at": monitoring_session.first_offer_sent_at.isoformat() if monitoring_session.first_offer_sent_at else None,
                    "client_response": monitoring_session.client_response,
                    "deal_closed_at": monitoring_session.deal_closed_at.isoformat() if monitoring_session.deal_closed_at else None,
                    "dialog_mode": getattr(monitoring_session, 'dialog_mode', 'auto'),
                    "owner_handling": getattr(monitoring_session, 'owner_handling', False),
                    "pending_owner_response": getattr(monitoring_session, 'pending_owner_response', False),
                    "objection_attempts": getattr(monitoring_session, 'objection_attempts', 0),
                    "last_price_discount": getattr(monitoring_session, 'last_price_discount', 0.0),
                    "objection_type": getattr(monitoring_session, 'objection_type', None),
                    "price_negotiation_data": getattr(monitoring_session, 'price_negotiation_data', None),
                    "margin_threshold_reached": getattr(monitoring_session, 'margin_threshold_reached', False),
                    "sales_technique_used": getattr(monitoring_session, 'sales_technique_used', 'standard')
                }
            
            return None
            
    except Exception as e:
        logger.error(f"Ошибка получения сессии мониторинга по ID {session_id}: {e}")
        return None

async def get_monitoring_session_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Получение активной сессии мониторинга по Telegram ID"""
    try:
        from database.models import MonitoringSession
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MonitoringSession).where(
                    MonitoringSession.client_telegram_id == telegram_id,
                    MonitoringSession.status.in_(["offer_sent", "in_dialog"])
                ).order_by(MonitoringSession.created_at.desc())
            )
            
            monitoring_session = result.scalar_one_or_none()
            
            if monitoring_session:
                return {
                    "id": monitoring_session.id,
                    "ati_cargo_id": monitoring_session.ati_cargo_id,
                    "order_id": monitoring_session.order_id,
                    "cargo_data": monitoring_session.cargo_data,
                    "offers_data": monitoring_session.offers_data,
                    "best_offer_data": monitoring_session.best_offer_data,
                    "pricing_data": monitoring_session.pricing_data,
                    "status": monitoring_session.status,
                    "client_telegram_id": monitoring_session.client_telegram_id,
                    "created_at": monitoring_session.created_at.isoformat(),
                    "first_offer_sent_at": monitoring_session.first_offer_sent_at,
                    "client_response": monitoring_session.client_response,
                    "deal_closed_at": monitoring_session.deal_closed_at
                }
            
            return None
            
    except Exception as e:
        logger.error(f"Ошибка получения сессии мониторинга по Telegram ID {telegram_id}: {e}")
        return None

async def update_monitoring_session_by_id(session_id: int, update_data: Dict) -> bool:
    """Обновление сессии мониторинга по ID"""
    try:
        from database.models import MonitoringSession
        from datetime import datetime
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MonitoringSession).where(MonitoringSession.id == session_id)
            )
            
            monitoring_session = result.scalar_one_or_none()
            
            if monitoring_session:
                # Обрабатываем datetime поля
                datetime_fields = ['deal_closed_at', 'human_intervention_requested_at', 'last_interaction_at', 'completed_at', 'updated_at']
                
                for key, value in update_data.items():
                    if hasattr(monitoring_session, key):
                        # Если это datetime поле и передана строка, конвертируем в datetime
                        if key in datetime_fields and isinstance(value, str):
                            try:
                                # Убираем 'Z' и парсим ISO формат
                                value = datetime.fromisoformat(value.replace('Z', ''))
                            except:
                                # Если не удалось спарсить, используем текущее время
                                value = datetime.utcnow()
                        
                        setattr(monitoring_session, key, value)
                
                # Обновляем updated_at
                monitoring_session.updated_at = datetime.utcnow()
                
                await session.commit()
                logger.info(f"✅ Обновлена сессия мониторинга {session_id}")
                return True
            
            logger.warning(f"⚠️ Сессия мониторинга {session_id} не найдена")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка обновления сессии мониторинга {session_id}: {e}")
        return False


async def complete_monitoring_session(ati_cargo_id: str, result: str, failure_reason: str = None) -> bool:
    """Завершение сессии мониторинга"""
    try:
        from database.models import MonitoringSession
        
        async with AsyncSessionLocal() as session:
            query = select(MonitoringSession).where(MonitoringSession.ati_cargo_id == ati_cargo_id)
            result_obj = await session.execute(query)
            monitoring_session = result_obj.scalar_one_or_none()
            
            if not monitoring_session:
                return False
            
            monitoring_session.status = "completed"
            monitoring_session.sale_result = result
            monitoring_session.failure_reason = failure_reason
            monitoring_session.completed_at = datetime.utcnow()
            monitoring_session.updated_at = datetime.utcnow()
            
            await session.commit()
            
            logger.info(f"✅ Завершена сессия мониторинга для груза {ati_cargo_id}: {result}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка завершения сессии мониторинга для груза {ati_cargo_id}: {e}")
        return False