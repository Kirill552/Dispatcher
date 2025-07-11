#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер автоматического обновления грузов ATI.SU
Отслеживает время ограничений и обновляет грузы для поддержания высокой позиции
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from ati_integration.ati_client_v2 import ATIClientV2
from database.crud import get_orders_by_ati_cargo_ids, update_order_status
from utils.logger import get_logger

logger = get_logger("CARGO_RENEWAL_MANAGER")


class CargoRenewalManager:
    """Менеджер автоматического обновления грузов"""
    
    def __init__(self):
        self.ati_client = ATIClientV2()
        self.is_running = False
        self.renewal_schedule: Dict[str, datetime] = {}
        self.renewal_interval_minutes = 60  # ATI.SU позволяет обновлять раз в час
        self.check_interval_seconds = 3600  # Проверяем раз в час, а не каждые 5 минут
        
    async def start_monitoring(self):
        """Запуск системы автоматического обновления грузов"""
        if self.is_running:
            logger.warning("⚠️ Мониторинг обновления грузов уже запущен")
            return
            
        self.is_running = True
        logger.info("🚀 Запуск системы автоматического обновления грузов ATI.SU")
        
        # Запуск основного цикла мониторинга
        while self.is_running:
            try:
                await self._renewal_cycle()
                await asyncio.sleep(self.check_interval_seconds)
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле обновления грузов: {str(e)}")
                await asyncio.sleep(60)
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        logger.info("⏹️ Остановка системы обновления грузов")
    
    async def _renewal_cycle(self):
        """Один цикл проверки и обновления грузов"""
        logger.info("🔄 Проверяем грузы для обновления")
        
        # Получаем грузы готовые к обновлению
        renewable_loads = await self.ati_client.get_renewable_loads()
        
        if renewable_loads:
            cargo_ids = [load.get("Id") for load in renewable_loads if load.get("Id")]
            
            if cargo_ids:
                logger.info(f"📈 Обновляем {len(cargo_ids)} грузов")
                results = await self.ati_client.renew_multiple_cargos(cargo_ids)
                
                success_count = 0
                for cargo_id, result in results.items():
                    status = result.get("Status", -1)
                    message = result.get("Message", "")
                    
                    if status == 0:
                        logger.info(f"✅ Груз {cargo_id} успешно обновлен")
                        success_count += 1
                        # Обновляем статус в БД
                        await self._update_db_status(cargo_id, "cargo_renewed")
                        
                    elif status == 2:
                        logger.info(f"⏳ Груз {cargo_id} - еще рано обновлять: {message}")
                    else:
                        logger.warning(f"❌ Груз {cargo_id}: {message} (код: {status})")
                
                logger.info(f"📊 Обновлено грузов: {success_count}/{len(cargo_ids)}")
        else:
            logger.info("📭 Нет грузов готовых к обновлению")
    
    async def _update_db_status(self, cargo_id: str, status: str):
        """Обновление статуса в базе данных"""
        try:
            # Находим заказ по ATI cargo ID
            orders = await get_orders_by_ati_cargo_ids([cargo_id])
            
            for order in orders:
                await update_order_status(order.id, status)
                logger.debug(f"📝 Обновлен статус заказа {order.id}: {status}")
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить статус в БД для груза {cargo_id}: {str(e)}")
    
    async def add_cargo_for_renewal(self, cargo_id: str, initial_delay_minutes: int = 0):
        """
        Добавить груз в систему автоматического обновления
        
        Args:
            cargo_id: ID груза
            initial_delay_minutes: Начальная задержка перед первым обновлением
        """
        if initial_delay_minutes > 0:
            next_renewal = datetime.now() + timedelta(minutes=initial_delay_minutes)
            self.renewal_schedule[cargo_id] = next_renewal
            logger.info(f"➕ Груз {cargo_id} добавлен для обновления через {initial_delay_minutes} мин")
        else:
            logger.info(f"➕ Груз {cargo_id} добавлен для немедленного обновления")
    
    async def remove_cargo_from_renewal(self, cargo_id: str):
        """Удалить груз из системы автоматического обновления"""
        if cargo_id in self.renewal_schedule:
            del self.renewal_schedule[cargo_id]
            logger.info(f"➖ Груз {cargo_id} удален из системы обновления")
    
    async def get_renewal_status(self) -> Dict:
        """Получить статус системы обновления"""
        current_time = datetime.now()
        
        # Подсчитываем статистику
        ready_now = sum(1 for time in self.renewal_schedule.values() if time <= current_time)
        scheduled_future = len(self.renewal_schedule) - ready_now
        
        # Получаем информацию о текущих грузах
        try:
            company_loads = await self.ati_client.get_all_company_loads(limit=50)
            renewable_loads = await self.ati_client.get_renewable_loads()
        except Exception as e:
            logger.error(f"❌ Ошибка получения данных грузов: {str(e)}")
            company_loads = []
            renewable_loads = []
        
        return {
            "is_running": self.is_running,
            "total_cargos_tracked": len(self.renewal_schedule),
            "ready_for_renewal": ready_now,
            "scheduled_for_future": scheduled_future,
            "company_loads_count": len(company_loads),
            "renewable_loads_count": len(renewable_loads),
            "next_renewal_times": [
                {
                    "cargo_id": cargo_id,
                    "scheduled_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "minutes_until_renewal": max(0, int((time - current_time).total_seconds() / 60))
                }
                for cargo_id, time in sorted(self.renewal_schedule.items(), key=lambda x: x[1])[:10]
            ],
            "renewal_interval_minutes": self.renewal_interval_minutes,
            "check_interval_seconds": self.check_interval_seconds
        }


# Глобальный экземпляр менеджера
cargo_renewal_manager = CargoRenewalManager() 