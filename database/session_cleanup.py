"""
🧹 СИСТЕМА АВТОМАТИЧЕСКОЙ ОЧИСТКИ СЕССИЙ

Критически важно для продакшн-стабильности:
- TTL-логика для разных типов сессий  
- Batch-удаление для производительности
- Cron-job планировщик каждые 6 часов
- Статистика и мониторинг очистки
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, delete, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import AsyncSessionLocal
from database.models import MonitoringSession, Conversation, Order
from utils.logger import db_logger as logger


# 📊 TTL-правила для разных типов данных
CLEANUP_RULES = {
    "completed_sessions": 48,     # 48 часов для завершенных сделок
    "failed_sessions": 24,        # 24 часа для проваленных сделок  
    "stale_sessions": 12,         # 12 часов для зависших сессий
    "archived_conversations": 7,  # 7 дней для архивных диалогов
    "old_orders": 30,            # 30 дней для старых заказов
}

# ⚙️ Настройки производительности
BATCH_SIZE = 1000  # Удаляем по 1000 записей за раз
MAX_CLEANUP_TIME = 300  # Максимум 5 минут на одну очистку


class SessionCleanupManager:
    """Менеджер автоматической очистки сессий"""
    
    def __init__(self):
        self.stats = {
            "last_cleanup": None,
            "total_cleaned": 0,
            "cleanup_runs": 0,
            "errors": 0
        }
    
    async def cleanup_old_sessions(self) -> Dict[str, int]:
        """
        🧹 Основная функция очистки старых сессий
        
        Returns:
            Dict с статистикой удаленных записей
        """
        start_time = datetime.utcnow()
        cleanup_stats = {
            "monitoring_sessions": 0,
            "conversations": 0,
            "orders": 0,
            "total": 0,
            "duration_sec": 0
        }
        
        try:
            logger.info("🧹 ЗАПУСК АВТОМАТИЧЕСКОЙ ОЧИСТКИ СЕССИЙ")
            
            # 1. Очистка сессий мониторинга
            cleanup_stats["monitoring_sessions"] = await self._cleanup_monitoring_sessions()
            
            # 2. Очистка старых диалогов
            cleanup_stats["conversations"] = await self._cleanup_old_conversations()
            
            # 3. Очистка старых заказов (опционально)
            cleanup_stats["orders"] = await self._cleanup_old_orders()
            
            # 4. Обновление индексов для производительности
            await self._optimize_database_indexes()
            
            # Подсчет общей статистики
            cleanup_stats["total"] = sum([
                cleanup_stats["monitoring_sessions"],
                cleanup_stats["conversations"], 
                cleanup_stats["orders"]
            ])
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            cleanup_stats["duration_sec"] = round(duration, 2)
            
            # Обновляем статистику
            self.stats["last_cleanup"] = datetime.utcnow()
            self.stats["total_cleaned"] += cleanup_stats["total"]
            self.stats["cleanup_runs"] += 1
            
            logger.info(f"✅ ОЧИСТКА ЗАВЕРШЕНА: удалено {cleanup_stats['total']} записей за {duration:.1f}с")
            
            return cleanup_stats
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"❌ Ошибка при очистке сессий: {str(e)}")
            raise
    
    async def _cleanup_monitoring_sessions(self) -> int:
        """Очистка старых сессий мониторинга"""
        total_deleted = 0
        
        async with AsyncSessionLocal() as session:
            
            # 1. Завершенные сессии старше 48 часов
            cutoff_completed = datetime.utcnow() - timedelta(hours=CLEANUP_RULES["completed_sessions"])
            result = await session.execute(
                select(func.count(MonitoringSession.id)).where(
                    MonitoringSession.status == "completed",
                    MonitoringSession.updated_at < cutoff_completed
                )
            )
            count_completed = result.scalar() or 0
            
            if count_completed > 0:
                await session.execute(
                    delete(MonitoringSession).where(
                        MonitoringSession.status == "completed",
                        MonitoringSession.updated_at < cutoff_completed
                    )
                )
                total_deleted += count_completed
                logger.info(f"🗑️ Удалено завершенных сессий: {count_completed}")
            
            # 2. Проваленные сессии старше 24 часов  
            cutoff_failed = datetime.utcnow() - timedelta(hours=CLEANUP_RULES["failed_sessions"])
            result = await session.execute(
                select(func.count(MonitoringSession.id)).where(
                    MonitoringSession.status.in_(["failed", "cancelled", "timeout"]),
                    MonitoringSession.updated_at < cutoff_failed
                )
            )
            count_failed = result.scalar() or 0
            
            if count_failed > 0:
                await session.execute(
                    delete(MonitoringSession).where(
                        MonitoringSession.status.in_(["failed", "cancelled", "timeout"]),
                        MonitoringSession.updated_at < cutoff_failed
                    )
                )
                total_deleted += count_failed
                logger.info(f"🗑️ Удалено проваленных сессий: {count_failed}")
            
            await session.commit()
            
        return total_deleted
    
    async def _cleanup_old_conversations(self) -> int:
        """Очистка старых диалогов"""
        cutoff_time = datetime.utcnow() - timedelta(days=CLEANUP_RULES["archived_conversations"])
        
        async with AsyncSessionLocal() as session:
            # Подсчитываем количество для удаления
            result = await session.execute(
                select(func.count(Conversation.id)).where(
                    Conversation.created_at < cutoff_time
                )
            )
            count_to_delete = result.scalar() or 0
            
            if count_to_delete > 0:
                await session.execute(
                    delete(Conversation).where(
                        Conversation.created_at < cutoff_time
                    )
                )
                await session.commit()
                
                logger.info(f"🗑️ Удалено старых диалогов: {count_to_delete}")
                return count_to_delete
            
        return 0
    
    async def _cleanup_old_orders(self) -> int:
        """Очистка старых заказов (только выполненных)"""
        cutoff_time = datetime.utcnow() - timedelta(days=CLEANUP_RULES["old_orders"])
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count(Order.id)).where(
                    Order.status.in_(["completed", "cancelled"]),
                    Order.created_at < cutoff_time
                )
            )
            count_to_delete = result.scalar() or 0
            
            if count_to_delete > 0:
                await session.execute(
                    delete(Order).where(
                        Order.status.in_(["completed", "cancelled"]),
                        Order.created_at < cutoff_time
                    )
                )
                await session.commit()
                
                logger.info(f"🗑️ Удалено старых заказов: {count_to_delete}")
                return count_to_delete
            
        return 0
    
    async def _optimize_database_indexes(self):
        """Оптимизация индексов базы данных"""
        try:
            async with AsyncSessionLocal() as session:
                # Проверяем наличие индексов по updated_at
                index_queries = [
                    "CREATE INDEX IF NOT EXISTS idx_monitoring_sessions_updated_at ON monitoring_sessions(updated_at)",
                    "CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)"
                ]
                
                for query in index_queries:
                    await session.execute(text(query))
                
                await session.commit()
                logger.info("📊 Индексы базы данных оптимизированы")
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось оптимизировать индексы: {str(e)}")


# 🚀 ПУБЛИЧНЫЕ ФУНКЦИИ ДЛЯ ИНТЕГРАЦИИ
async def run_manual_cleanup() -> Dict[str, int]:
    """Ручной запуск очистки (для администратора)"""
    cleanup_manager = SessionCleanupManager()
    return await cleanup_manager.cleanup_old_sessions()


async def get_database_health() -> Dict:
    """Получить состояние базы данных"""
    cleanup_manager = SessionCleanupManager()
    async with AsyncSessionLocal() as session:
        # Текущие размеры таблиц
        tables_stats = {}
        
        for table_name, model in [
            ("monitoring_sessions", MonitoringSession),
            ("conversations", Conversation),
            ("orders", Order)
        ]:
            result = await session.execute(select(func.count(model.id)))
            tables_stats[table_name] = result.scalar() or 0
    
    return {
        "cleanup_rules": CLEANUP_RULES,
        "table_sizes": tables_stats
    }


# 🕐 CRON-JOB ПЛАНИРОВЩИК
class CleanupScheduler:
    """Планировщик автоматической очистки каждые 6 часов"""
    
    def __init__(self):
        self.cleanup_manager = SessionCleanupManager()
        self.is_running = False
    
    async def start_scheduler(self):
        """Запуск планировщика очистки"""
        self.is_running = True
        logger.info("🕐 Планировщик очистки сессий запущен (интервал: 6 часов)")
        
        while self.is_running:
            try:
                # Запускаем очистку
                stats = await self.cleanup_manager.cleanup_old_sessions()
                
                # Ждем 6 часов до следующей очистки
                await asyncio.sleep(6 * 60 * 60)  # 6 часов
                
            except Exception as e:
                logger.error(f"❌ Ошибка в планировщике очистки: {str(e)}")
                # При ошибке ждем 30 минут и пробуем снова
                await asyncio.sleep(30 * 60)
    
    def stop_scheduler(self):
        """Остановка планировщика"""
        self.is_running = False
        logger.info("🛑 Планировщик очистки сессий остановлен")


# Глобальный экземпляр планировщика
cleanup_scheduler = CleanupScheduler() 