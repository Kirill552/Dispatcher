#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мониторинг заказов клиентов и их обработка через ИИ-диспетчера
Новая логика: не мониторим чужие грузы, а обрабатываем заказы наших клиентов
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from ai_services.ai_dispatcher_logic import AIDispatcherLogic
from database.models import Order
from database.crud import get_pending_orders, update_order_status
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("CARGO_MONITOR")

class CargoMonitor:
    """Мониторинг и обработка заказов клиентов через ИИ-диспетчера"""
    
    def __init__(self):
        self.ai_dispatcher = AIDispatcherLogic()
        self.is_running = False
        
    async def start_monitoring(self):
        """Запуск системы мониторинга заказов"""
        if self.is_running:
            logger.warning("Мониторинг уже запущен")
            return
            
        self.is_running = True
        logger.info("🚀 Запуск мониторинга заказов клиентов")
        
        # Запуск основного цикла мониторинга
        while self.is_running:
            try:
                await self._monitor_cycle()
                await asyncio.sleep(settings.monitoring_interval_seconds)
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {str(e)}")
                await asyncio.sleep(60)  # Пауза перед повтором
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        logger.info("⏹️ Остановка мониторинга заказов")
    
    async def _monitor_cycle(self):
        """Один цикл мониторинга заказов клиентов"""
        logger.info("🔍 Начинаем цикл обработки заказов клиентов")
        
        processed_orders = 0
        
        try:
            # Получаем все необработанные заказы
            pending_orders = await get_pending_orders()
            
            for order in pending_orders:
                try:
                    await self._process_client_order(order)
                    processed_orders += 1
                    
                    # Небольшая пауза между обработкой заказов
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки заказа {order.id}: {str(e)}")
                    continue
            
            logger.info(f"✅ Цикл завершен. Обработано заказов: {processed_orders}")
            
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {str(e)}")
    
    async def _process_client_order(self, order: Order):
        """Обработка заказа клиента через ИИ-диспетчера"""
        try:
            logger.info(f"📦 Обрабатываем заказ {order.id}: {order.from_city} - {order.to_city}")
            
            # Формируем данные клиента для ИИ-диспетчера
            client_data = {
                "order_id": order.id,
                "from_city": order.from_city,
                "to_city": order.to_city,
                "cargo_type": order.cargo_type,
                "cargo_description": order.cargo_description,
                "weight": order.weight,
                "volume": order.volume,
                "loading_date": order.loading_date.isoformat() if order.loading_date else None,
                "loading_contact": order.loading_contact,
                "delivery_contact": order.delivery_contact,
                "status": order.status
            }
            
            # Обрабатываем через ИИ-диспетчера
            result = await self.ai_dispatcher.process_client_order(client_data)
            
            if result.get("success"):
                logger.info(f"✅ Заказ {order.id} успешно обработан")
                
                # Обновляем статус заказа
                new_status = result.get("order_status", "processing")
                await update_order_status(order.id, new_status)
                
            else:
                logger.warning(f"⚠️ Заказ {order.id} требует дополнительной обработки: {result.get('message', 'N/A')}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки заказа {order.id}: {str(e)}")
            # Помечаем заказ как проблемный
            await update_order_status(order.id, "error")
    
    async def get_monitoring_stats(self) -> Dict:
        """Получить статистику мониторинга"""
        try:
            pending_orders = await get_pending_orders()
            ai_stats = await self.ai_dispatcher.get_statistics()
            
            return {
                "is_running": self.is_running,
                "pending_orders": len(pending_orders),
                "interval_seconds": settings.monitoring_interval_seconds,
                "ai_dispatcher_stats": ai_stats
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {str(e)}")
            return {
                "is_running": self.is_running,
                "error": str(e)
            }


# Глобальный экземпляр мониторинга
cargo_monitor = CargoMonitor() 