"""
Умное ценообразование через in-context learning с o4-mini
Этап 1: Передача исторических данных в промпте для поиска паттернов
"""
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from utils.logger import ai_logger as logger
from utils.config import settings
from ai_services.ai_client import ai_client
# from database.crud import get_historical_pricing_data  # Пока не реализована

class SmartPricingEngine:
    """Умное ценообразование с использованием o4-mini и исторических данных"""
    
    def __init__(self):
        self.default_margin = 0.40  # 40% базовая наценка
        self.min_margin = 0.25      # 25% минимальная маржа
        self.max_margin = 0.60      # 60% максимальная маржа
        
    async def calculate_optimal_price(self, order_data: Dict, carrier_price: int, context: Dict = None) -> Dict:
        """
        Рассчитывает оптимальную цену на основе исторических данных и o4-mini анализа
        
        Args:
            order_data: Данные заказа (маршрут, груз, вес и т.д.)
            carrier_price: Цена перевозчика
            context: Дополнительный контекст (день недели, сезон и т.д.)
            
        Returns:
            Dict с рекомендованной ценой и анализом
        """
        try:
            # Получаем исторические данные для анализа
            historical_data = await self._get_relevant_historical_data(order_data)
            
            # Если мало данных - используем базовую наценку + легкий анализ
            if len(historical_data) < 3:
                logger.info("📊 Мало исторических данных, используем базовую наценку + быстрый анализ")
                return await self._basic_pricing_with_context(order_data, carrier_price, context)
            
            # Используем o4-mini для анализа паттернов
            logger.info(f"🧠 Анализ {len(historical_data)} исторических сделок через o4-mini")
            return await self._intelligent_pricing_analysis(order_data, carrier_price, historical_data, context)
            
        except Exception as e:
            logger.error(f"❌ Ошибка умного ценообразования: {e}")
            # Fallback на стандартную наценку
            return self._fallback_pricing(carrier_price)
    
    async def _get_relevant_historical_data(self, order_data: Dict) -> List[Dict]:
        """Получает релевантные исторические данные для анализа"""
        try:
            # Критерии поиска похожих заказов
            search_criteria = {
                "route_similarity": True,      # Похожие маршруты
                "cargo_similarity": True,      # Похожие грузы  
                "weight_range": True,          # Схожий вес
                "recent_months": 6             # За последние 6 месяцев
            }
            
            # ВРЕМЕННО: Используем моковые данные пока нет реальной истории сделок
            # После накопления данных заменить на: get_historical_pricing_data(order_data)
            mock_historical_data = [
                {
                    "route": "Москва→Санкт-Петербург",
                    "cargo_type": "мебель",
                    "weight": 2000,
                    "carrier_price": 48000,
                    "client_price": 67000,
                    "accepted": True,
                    "negotiation_rounds": 2,
                    "final_discount": 0.04,
                    "day_of_week": "среда",
                    "created_at": "2025-06-15"
                },
                {
                    "route": "Москва→Санкт-Петербург", 
                    "cargo_type": "оборудование",
                    "weight": 1800,
                    "carrier_price": 52000,
                    "client_price": 75000,
                    "accepted": False,
                    "rejection_reason": "price_too_high",
                    "day_of_week": "пятница",
                    "created_at": "2025-06-10"
                },
                {
                    "route": "Москва→Санкт-Петербург",
                    "cargo_type": "стройматериалы", 
                    "weight": 3000,
                    "carrier_price": 45000,
                    "client_price": 63000,
                    "accepted": True,
                    "negotiation_rounds": 1,
                    "final_discount": 0.0,
                    "day_of_week": "понедельник",
                    "created_at": "2025-06-20"
                }
            ]
            
            # Фильтруем по релевантности
            relevant_data = []
            for record in mock_historical_data:
                relevance_score = self._calculate_relevance_score(order_data, record)
                if relevance_score > 0.5:  # Минимальный порог релевантности
                    record["relevance_score"] = relevance_score
                    relevant_data.append(record)
            
            # Сортируем по релевантности  
            relevant_data.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return relevant_data[:10]  # Топ-10 самых релевантных
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения исторических данных: {e}")
            return []
    
    def _calculate_relevance_score(self, current_order: Dict, historical_record: Dict) -> float:
        """Рассчитывает релевантность исторической записи к текущему заказу"""
        score = 0.0
        
        # Маршрут (40% важности)
        if current_order.get("from_city") == historical_record.get("route", "").split("→")[0]:
            score += 0.2
        if current_order.get("to_city") == historical_record.get("route", "").split("→")[-1]:
            score += 0.2
            
        # Тип груза (30% важности)
        current_cargo = current_order.get("cargo_type", "").lower()
        historical_cargo = historical_record.get("cargo_type", "").lower()
        if current_cargo in historical_cargo or historical_cargo in current_cargo:
            score += 0.3
            
        # Вес (20% важности)  
        current_weight = current_order.get("cargo_weight", 0)
        historical_weight = historical_record.get("weight", 0)
        if current_weight > 0 and historical_weight > 0:
            weight_diff = abs(current_weight - historical_weight) / max(current_weight, historical_weight)
            weight_score = max(0, 1 - weight_diff)  # Чем ближе вес, тем выше оценка
            score += 0.2 * weight_score
            
        # Актуальность (10% важности)
        # Более свежие данные важнее
        try:
            record_date = datetime.strptime(historical_record.get("created_at", ""), "%Y-%m-%d")
            days_ago = (datetime.now() - record_date).days
            recency_score = max(0, 1 - (days_ago / 180))  # 180 дней = максимальная давность
            score += 0.1 * recency_score
        except:
            pass
            
        return min(1.0, score)
    
    async def _intelligent_pricing_analysis(self, order_data: Dict, carrier_price: int, 
                                          historical_data: List[Dict], context: Dict) -> Dict:
        """Умный анализ ценообразования через o4-mini"""
        
        # Подготавливаем данные для анализа
        analysis_context = self._prepare_analysis_context(order_data, carrier_price, historical_data, context)
        
        # Промпт для o4-mini с историческими данными
        system_prompt = """Ты - эксперт по ценообразованию в B2B логистике. 
Анализируй исторические данные о принятых/отвергнутых ценах для оптимального ценообразования.

ТВОЯ ЗАДАЧА:
1. Найти паттерны в исторических данных
2. Предсказать оптимальную цену для текущего заказа
3. Оценить вероятность принятия разных ценовых уровней

ПРИНЦИПЫ АНАЛИЗА:
- Принятые сделки показывают "потолок" приемлемых цен
- Отвергнутые сделки показывают "красные линии" 
- Учитывай день недели, срочность, тип груза
- Балансируй между прибыльностью и конверсией

ФОРМАТ ОТВЕТА СТРОГО JSON:
{
  "recommended_price": число,
  "confidence": 0.0-1.0,
  "margin_percent": 0.0-1.0,
  "acceptance_probability": 0.0-1.0,
  "key_insights": ["инсайт1", "инсайт2"],
  "risk_factors": ["риск1", "риск2"],
  "pricing_strategy": "aggressive|balanced|conservative"
}"""

        user_prompt = f"""АНАЛИЗ ЦЕНООБРАЗОВАНИЯ:

ТЕКУЩИЙ ЗАКАЗ:
{json.dumps(analysis_context["current_order"], ensure_ascii=False, indent=2)}

ЦЕНА ПЕРЕВОЗЧИКА: {carrier_price:,}₽

ИСТОРИЧЕСКИЕ ДАННЫЕ ({len(historical_data)} записей):
{json.dumps(historical_data, ensure_ascii=False, indent=2)}

КОНТЕКСТ:
{json.dumps(analysis_context["context"], ensure_ascii=False, indent=2)}

Проанализируй данные и предложи оптимальную цену."""

        try:
            # Вызываем o4-mini для анализа
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await ai_client.create_completion(
                model="o4-mini",  # Используем o4-mini напрямую
                messages=messages,
                max_tokens=4000,  # Большой лимит для reasoning (включает reasoning + output токены)
                task_type="pricing_analysis"
            )
            
            # Парсим ответ
            analysis_result = json.loads(response.strip())
            
            # Валидируем и дополняем результат
            result = self._validate_and_enhance_result(analysis_result, carrier_price)
            
            logger.info(f"🎯 Умная цена: {result['recommended_price']:,}₽ (уверенность: {result['confidence']:.1%})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа o4-mini: {e}")
            # Fallback на контекстное ценообразование
            return await self._basic_pricing_with_context(order_data, carrier_price, context)
    
    async def _basic_pricing_with_context(self, order_data: Dict, carrier_price: int, context: Dict) -> Dict:
        """Базовое ценообразование с учетом контекста (без исторических данных)"""
        
        base_margin = self.default_margin
        
        # Простые корректировки на основе контекста
        if context:
            day_of_week = context.get("day_of_week", "").lower()
            urgency = context.get("urgency", "normal")
            
            # Пятница и срочные заказы - дороже
            if day_of_week in ["friday", "пятница"] or urgency == "urgent":
                base_margin += 0.05
                
            # Понедельник и обычные заказы - базовая цена
            
        recommended_price = int(carrier_price * (1 + base_margin))
        
        return {
            "recommended_price": recommended_price,
            "confidence": 0.7,
            "margin_percent": base_margin,
            "acceptance_probability": 0.75,
            "key_insights": ["Базовое ценообразование", "Недостаточно исторических данных"],
            "risk_factors": ["Нет исторических паттернов"],
            "pricing_strategy": "balanced",
            "method": "basic_context"
        }
    
    def _fallback_pricing(self, carrier_price: int) -> Dict:
        """Fallback ценообразование при ошибках"""
        recommended_price = int(carrier_price * (1 + self.default_margin))
        
        return {
            "recommended_price": recommended_price,
            "confidence": 0.6,
            "margin_percent": self.default_margin,
            "acceptance_probability": 0.7,
            "key_insights": ["Стандартная наценка"],
            "risk_factors": ["Ошибка анализа"],
            "pricing_strategy": "conservative",
            "method": "fallback"
        }
    
    def _prepare_analysis_context(self, order_data: Dict, carrier_price: int, 
                                historical_data: List[Dict], context: Dict) -> Dict:
        """Подготавливает контекст для анализа o4-mini"""
        
        current_order = {
            "route": f"{order_data.get('from_city', '')}→{order_data.get('to_city', '')}",
            "cargo_type": order_data.get("cargo_type", ""),
            "weight": order_data.get("cargo_weight", 0),
            "carrier_price": carrier_price
        }
        
        analysis_context = {
            "current_order": current_order,
            "context": context or {},
            "historical_count": len(historical_data),
            "analysis_date": datetime.now().isoformat()
        }
        
        return analysis_context
    
    def _validate_and_enhance_result(self, analysis_result: Dict, carrier_price: int) -> Dict:
        """Валидирует и дополняет результат анализа o4-mini"""
        
        # 🛡️ HARD FLOOR PROTECTION - КРИТИЧНАЯ ЗАЩИТА ОТ УБЫТКОВ
        # НИКОГДА не позволяем цене быть ниже 25% маржи
        hard_floor_price = int(carrier_price * 1.25)  # carrier_price × 1.25 = 25% маржа минимум
        
        # Проверяем границы цены
        min_price = int(carrier_price * (1 + self.min_margin))  # 25% минимум
        max_price = int(carrier_price * (1 + self.max_margin))  # 60% максимум
        
        recommended_price = analysis_result.get("recommended_price", min_price)
        
        # 🚨 КРИТИЧЕСКАЯ ПРОВЕРКА: даже если ML/ИИ глючит - НЕ УХОДИМ В МИНУС!
        if recommended_price < hard_floor_price:
            logger.warning(f"🛡️ ЗАЩИТА ОТ УБЫТКОВ: ИИ предложил {recommended_price:,}₽, "
                         f"но это ниже hard floor {hard_floor_price:,}₽. Корректируем!")
            recommended_price = hard_floor_price
        
        # Дополнительно ограничиваем максимумом
        recommended_price = min(max_price, recommended_price)
        
        # Пересчитываем реальную маржу
        actual_margin = (recommended_price - carrier_price) / carrier_price
        
        # Проверяем что не нарушили минимум (double-check)
        if actual_margin < 0.24:  # 24% = 0.24, чуть ниже 25% из-за округления
            logger.error(f"🚨 КРИТИЧЕСКАЯ ОШИБКА: маржа {actual_margin:.1%} ниже 25%! "
                        f"Цена: {recommended_price:,}₽, Перевозчик: {carrier_price:,}₽")
            # Принудительно устанавливаем минимум
            recommended_price = hard_floor_price
            actual_margin = 0.25
        
        # Обновляем результат
        analysis_result.update({
            "recommended_price": recommended_price,
            "margin_percent": actual_margin,
            "carrier_price": carrier_price,
            "min_price": min_price,
            "max_price": max_price,
            "hard_floor_price": hard_floor_price,
            "is_hard_floor_applied": recommended_price == hard_floor_price,
            "method": "intelligent_o4mini_protected"
        })
        
        return analysis_result

# Глобальный экземпляр
smart_pricing = SmartPricingEngine() 