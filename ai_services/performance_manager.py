"""
⚡ PERFORMANCE MANAGER - ЗАЩИТА ОТ LATENCY-СПАЙКОВ

Критически важно для продакшн-стабильности:
- Rate-limiter для o4-mini (max 5 одновременных)
- Кэш повторяющихся возражений  
- Back-pressure защита Telegram
- Graceful degradation при перегрузке
"""

import asyncio
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass

from utils.logger import logger
from utils.config import settings


@dataclass
class CacheEntry:
    """Запись в кэше ответов"""
    response: str
    created_at: datetime
    hit_count: int = 0
    confidence: float = 0.8


@dataclass
class QueuedRequest:
    """Запрос в очереди на обработку"""
    client_id: str
    message: str
    created_at: datetime
    future: asyncio.Future
    priority: int = 0  # 0 = обычный, 1 = VIP


class PerformanceManager:
    """Менеджер производительности и защиты от перегрузок"""
    
    def __init__(self):
        # 🎯 Rate-limiter для o4-mini
        self.o4_mini_limiter = {
            "concurrent_limit": 5,        # Максимум 5 одновременных вызовов
            "queue_size": 50,             # Очередь на 50 запросов
            "timeout": 30,                # Таймаут 30 секунд
            "fallback": "gpt-4.1-mini"    # Fallback на GPT-4.1 при перегрузке
        }
        
        # 📊 Кэш повторяющихся возражений
        self.objection_cache = {
            "ttl": 3600,                  # 1 час жизни кэша
            "max_size": 1000,             # До 1000 кэшированных ответов
            "hit_rate_target": 0.40       # Цель: 40% попаданий в кэш
        }
        
        # 🚦 Управление состоянием
        self.active_o4_requests = 0
        self.request_queue = asyncio.Queue(maxsize=self.o4_mini_limiter["queue_size"])
        self.cache_storage: Dict[str, CacheEntry] = {}
        self.stats = {
            "requests_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "queue_overflows": 0,
            "fallback_used": 0,
            "avg_response_time": 0.0
        }
        
        # 📈 Мониторинг производительности
        self.response_times = deque(maxlen=100)  # Последние 100 ответов
        self.telegram_rate_limiter = TelegramRateLimiter()
        
    async def process_ai_request(
        self, 
        request_type: str,
        prompt: str,
        client_id: str,
        priority: int = 0,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        ⚡ Основная функция обработки ИИ-запросов с защитой от перегрузок
        
        Args:
            request_type: тип запроса (objection_handling, order_analysis, etc)
            prompt: промпт для ИИ
            client_id: ID клиента
            priority: приоритет (0=обычный, 1=VIP)
            use_cache: использовать ли кэш
            
        Returns:
            Dict с ответом ИИ и метаданными
        """
        start_time = time.time()
        
        try:
            # 1. 📊 Проверяем кэш (если включен)
            if use_cache and request_type in ["objection_handling", "price_negotiation"]:
                cache_result = await self._check_cache(prompt)
                if cache_result:
                    self.stats["cache_hits"] += 1
                    logger.info(f"🎯 Cache HIT для клиента {client_id}: {cache_result['confidence']:.0%} уверенности")
                    return {
                        "response": cache_result["response"],
                        "source": "cache",
                        "confidence": cache_result["confidence"],
                        "processing_time": time.time() - start_time
                    }
            
            # 2. 🚦 Проверяем нагрузку и решаем какую модель использовать
            model_choice = await self._choose_optimal_model(request_type)
            
            # 3. ⚡ Обрабатываем запрос в зависимости от модели
            if model_choice["model"] == "o4-mini":
                response = await self._process_o4_mini_request(prompt, client_id, priority)
            else:
                response = await self._process_fallback_request(prompt, model_choice["model"])
                self.stats["fallback_used"] += 1
            
            # 4. 💾 Сохраняем в кэш (если подходит)
            if use_cache and request_type in ["objection_handling"] and len(response) > 20:
                await self._update_cache(prompt, response)
            
            # 5. 📊 Обновляем статистику
            processing_time = time.time() - start_time
            self.response_times.append(processing_time)
            self.stats["requests_processed"] += 1
            self.stats["avg_response_time"] = sum(self.response_times) / len(self.response_times)
            
            if use_cache:
                self.stats["cache_misses"] += 1
            
            logger.info(f"✅ Запрос обработан ({model_choice['model']}): {processing_time:.2f}с")
            
            return {
                "response": response,
                "source": model_choice["model"],
                "confidence": model_choice.get("confidence", 0.9),
                "processing_time": processing_time,
                "queue_size": self.request_queue.qsize()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка в PerformanceManager: {str(e)}")
            raise
    
    async def _choose_optimal_model(self, request_type: str) -> Dict[str, Any]:
        """
        🧠 Выбор оптимальной модели на основе текущей нагрузки
        
        Returns:
            Dict с выбранной моделью и метаданными
        """
        # Проверяем нагрузку на o4-mini
        current_load = self.active_o4_requests / self.o4_mini_limiter["concurrent_limit"]
        queue_load = self.request_queue.qsize() / self.o4_mini_limiter["queue_size"]
        
        # Средняя скорость ответа за последние запросы
        avg_response_time = self.stats["avg_response_time"]
        
        # 🚦 Логика выбора модели
        if current_load < 0.8 and queue_load < 0.6 and avg_response_time < 20:
            # Система не перегружена - используем o4-mini
            return {
                "model": "o4-mini",
                "confidence": 0.95,
                "reason": "optimal_conditions"
            }
        
        elif request_type in ["simple_extraction", "order_readiness"] or avg_response_time > 25:
            # Простые задачи или перегрузка - используем GPT-4.1
            return {
                "model": "gpt-4.1-mini",
                "confidence": 0.85,
                "reason": "load_balancing"
            }
        
        else:
            # Пограничный случай - пробуем o4-mini с коротким таймаутом
            return {
                "model": "o4-mini",
                "confidence": 0.90,
                "reason": "limited_queue"
            }
    
    async def _process_o4_mini_request(self, prompt: str, client_id: str, priority: int) -> str:
        """⚡ Обработка запроса через o4-mini с rate-limiting"""
        
        # Проверяем лимиты
        if self.active_o4_requests >= self.o4_mini_limiter["concurrent_limit"]:
            if self.request_queue.full():
                self.stats["queue_overflows"] += 1
                logger.warning(f"🚨 Очередь o4-mini переполнена! Используем fallback для {client_id}")
                return await self._process_fallback_request(prompt, "gpt-4.1-mini")
            
            # Добавляем в очередь
            future = asyncio.Future()
            queued_request = QueuedRequest(
                client_id=client_id,
                message=prompt,
                priority=priority,
                created_at=datetime.utcnow(),
                future=future
            )
            
            await self.request_queue.put(queued_request)
            logger.info(f"⏳ Запрос {client_id} добавлен в очередь (размер: {self.request_queue.qsize()})")
            
            # Ждем обработки
            try:
                return await asyncio.wait_for(future, timeout=self.o4_mini_limiter["timeout"])
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Таймаут для запроса {client_id}, используем fallback")
                return await self._process_fallback_request(prompt, "gpt-4.1-mini")
        
        # Обрабатываем немедленно
        return await self._execute_o4_mini_call(prompt)
    
    async def _execute_o4_mini_call(self, prompt: str) -> str:
        """Выполнение вызова o4-mini с подсчетом активных запросов"""
        self.active_o4_requests += 1
        
        try:
            # Импортируем ИИ клиент
            from ai_services.ai_client import UniversalAIClient
            
            ai_client = UniversalAIClient()
            response = await ai_client.create_completion(
                model="o4-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.7,
                task_type="performance_managed"
            )
            
            return response
            
        finally:
            self.active_o4_requests -= 1
            
            # Обрабатываем следующий запрос из очереди
            if not self.request_queue.empty():
                asyncio.create_task(self._process_next_in_queue())
    
    async def _process_next_in_queue(self):
        """Обработка следующего запроса из очереди"""
        try:
            queued_request = await self.request_queue.get()
            
            if not queued_request.future.cancelled():
                response = await self._execute_o4_mini_call(queued_request.message)
                queued_request.future.set_result(response)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки очереди: {str(e)}")
    
    async def _process_fallback_request(self, prompt: str, fallback_model: str) -> str:
        """Обработка через fallback модель"""
        try:
            from ai_services.ai_client import UniversalAIClient
            
            ai_client = UniversalAIClient()
            response = await ai_client.create_completion(
                model=fallback_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.6,
                task_type="fallback"
            )
            
            logger.info(f"🔄 Использован fallback: {fallback_model}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка fallback обработки: {str(e)}")
            return "Извините, возникла техническая проблема. Попробуйте через минуту."
    
    async def _check_cache(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Проверка кэша ответов"""
        cache_key = self._generate_cache_key(prompt)
        
        if cache_key in self.cache_storage:
            entry = self.cache_storage[cache_key]
            
            # Проверяем TTL
            if (datetime.utcnow() - entry.created_at).total_seconds() < self.objection_cache["ttl"]:
                entry.hit_count += 1
                return {
                    "response": entry.response,
                    "confidence": entry.confidence
                }
            else:
                # Удаляем устаревшую запись
                del self.cache_storage[cache_key]
        
        return None
    
    async def _update_cache(self, prompt: str, response: str):
        """Обновление кэша новым ответом"""
        cache_key = self._generate_cache_key(prompt)
        
        # Очищаем старые записи если кэш переполнен
        if len(self.cache_storage) >= self.objection_cache["max_size"]:
            await self._cleanup_cache()
        
        # Добавляем новую запись
        self.cache_storage[cache_key] = CacheEntry(
            response=response,
            created_at=datetime.utcnow(),
            confidence=0.8
        )
    
    def _generate_cache_key(self, prompt: str) -> str:
        """Генерация ключа кэша"""
        # Упрощаем промпт для лучшего кэширования
        simplified = prompt.lower()
        
        # Удаляем специфичные данные (цены, даты, имена)
        import re
        simplified = re.sub(r'\d+[.,]?\d*\s*(?:рубл|₽)', '[PRICE]', simplified)
        simplified = re.sub(r'\d{1,2}\.\d{1,2}\.\d{4}', '[DATE]', simplified)
        simplified = re.sub(r'@\w+', '[USERNAME]', simplified)
        
        return hashlib.md5(simplified.encode()).hexdigest()
    
    async def _cleanup_cache(self):
        """Очистка старого кэша"""
        # Удаляем 20% самых старых записей
        entries_to_remove = int(len(self.cache_storage) * 0.2)
        
        sorted_entries = sorted(
            self.cache_storage.items(),
            key=lambda x: (x[1].hit_count, x[1].created_at)
        )
        
        for key, _ in sorted_entries[:entries_to_remove]:
            del self.cache_storage[key]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Получить статистику производительности"""
        cache_hit_rate = 0
        if self.stats["cache_hits"] + self.stats["cache_misses"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"])
        
        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "active_o4_requests": self.active_o4_requests,
            "queue_size": self.request_queue.qsize(),
            "cache_size": len(self.cache_storage),
            "avg_response_time": round(self.stats["avg_response_time"], 2)
        }


class TelegramRateLimiter:
    """Rate-limiter для Telegram сообщений"""
    
    def __init__(self):
        self.message_timestamps = defaultdict(deque)
        self.max_messages_per_minute = 10
    
    async def can_send_message(self, chat_id: int) -> bool:
        """Проверка возможности отправки сообщения"""
        now = time.time()
        
        # Очищаем старые записи
        user_timestamps = self.message_timestamps[chat_id]
        while user_timestamps and now - user_timestamps[0] > 60:
            user_timestamps.popleft()
        
        # Проверяем лимит
        if len(user_timestamps) < self.max_messages_per_minute:
            user_timestamps.append(now)
            return True
        
        return False


# Глобальный экземпляр
performance_manager = PerformanceManager() 