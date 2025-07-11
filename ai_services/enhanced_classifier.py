"""
Улучшенная двухслойная система классификации сообщений клиентов
Этап 1: Быстрые ключевые слова + семантический анализ o4-mini
"""
import json
import time
from typing import Dict, List, Optional, Tuple
from utils.logger import ai_logger as logger
from utils.config import settings
from ai_services.ai_client import ai_client


class EnhancedClassifier:
    """Двухслойная система классификации с кэшированием и обучением"""
    
    # ПЕРВЫЙ СЛОЙ: Быстрые ключевые слова (0ms, высокая точность на очевидных фразах)
    FAST_KEYWORDS = {
        "price_objection": [
            "дорого", "дороговато", "много", "высокая цена", "превышает бюджет",
            "возил дешевле", "было дешевле", "раньше стоило", "покупал дешевле",
            "конкурент дешевле", "у других дешевле", "предлагают за", "другая компания дешевле"
        ],
        "agreement": [
            "да", "согласен", "согласна", "подходит", "устраивает", "берем", "оформляем",
            "заказываем", "хорошо", "отлично", "давайте", "подтверждаем"
        ],
        "rejection": [
            "нет", "не подходит", "не нужно", "отказываюсь", "не интересно",
            "не устраивает", "откажемся", "не берем"
        ],
        "manager_request": [
            "руководитель", "начальник", "директор", "менеджер", "руководство",
            "хочу с руководителем", "дайте начальника", "свяжите с руководством"
        ]
    }
    
    # ПОДТИПЫ ценовых возражений для детального анализа
    PRICE_SUBTYPES = {
        "past_cheaper": ["возил дешевле", "было дешевле", "раньше стоило", "покупал дешевле"],
        "competitor_cheaper": ["конкурент", "у других", "предлагают за", "другая компания"],
        "budget_cap": ["дорого", "дороговато", "много", "высокая цена", "превышает бюджет"],
        "generic": ["цена", "стоимость"]
    }
    
    # SENTIMENT GUARD: Детекция гнева для автоэскалации (ЭТАП 2)
    ANGER_KEYWORDS = [
        # Прямые оскорбления
        "дураки", "идиоты", "придурки", "кретины", "дебилы", 
        # Эмоциональные выражения
        "бесят", "достали", "надоели", "задолбали", "замучили",
        # Обвинения в мошенничестве  
        "обман", "развод", "мошенники", "кидалы", "наглость",
        # Крайнее недовольство
        "кошмар", "ужас", "издеваетесь", "безобразие", "возмутительно",
        # Угрозы и жалобы
        "жаловаться", "в суд", "роспотребнадзор", "прокуратура"
    ]
    
    def __init__(self):
        # Кэш для часто встречающихся фраз (экономия токенов)
        self.semantic_cache = {}
        # Статистика для обучения
        self.classification_stats = {
            "fast_layer_hits": 0,
            "semantic_layer_calls": 0,
            "total_classifications": 0
        }
    
    async def classify_message(self, message: str, context: Dict = None) -> Dict:
        """
        Главная функция классификации с двухслойным анализом
        
        Returns:
            Dict с полной информацией о классификации
        """
        start_time = time.time()
        self.classification_stats["total_classifications"] += 1
        
        message_lower = message.lower().strip()
        
        # SENTIMENT GUARD: Первоочередная проверка на гнев (КРИТИЧНО!)
        anger_check = self._check_for_anger(message_lower)
        if anger_check["is_angry"]:
            classification_time = time.time() - start_time
            logger.warning(f"😡 ДЕТЕКТИРОВАН ГНЕВ КЛИЕНТА: {anger_check['matched_keywords']} - АВТОЭСКАЛАЦИЯ!")
            
            return {
                "intent": "angry_escalation",
                "emotion": "angry", 
                "confidence": anger_check["confidence"],
                "matched_keywords": anger_check["matched_keywords"],
                "sales_stage": "escalation",
                "classification_method": "sentiment_guard",
                "classification_time_ms": classification_time * 1000,
                "tokens_used": 0,
                "requires_immediate_escalation": True,
                "escalation_reason": "client_anger_detected"
            }
        
        # ПЕРВЫЙ СЛОЙ: Быстрые ключевые слова (0ms)
        fast_result = self._fast_keyword_classification(message_lower)
        
        if fast_result["confidence"] >= 0.8:
            # Высокая уверенность - используем быстрый результат
            self.classification_stats["fast_layer_hits"] += 1
            classification_time = time.time() - start_time
            
            logger.info(f"⚡ Быстрая классификация: {fast_result['intent']} ({classification_time*1000:.0f}ms)")
            
            return {
                **fast_result,
                "classification_method": "fast_keywords",
                "classification_time_ms": classification_time * 1000,
                "tokens_used": 0
            }
        
        # ВТОРОЙ СЛОЙ: Семантический анализ o4-mini
        # Проверяем кэш
        cache_key = hash(message_lower)
        if cache_key in self.semantic_cache:
            cached_result = self.semantic_cache[cache_key]
            logger.info(f"💾 Из кэша: {cached_result['intent']}")
            return cached_result
        
        # Вызываем o4-mini для сложного анализа
        semantic_result = await self._semantic_classification(message, context, fast_result)
        self.classification_stats["semantic_layer_calls"] += 1
        
        # Кэшируем результат
        self.semantic_cache[cache_key] = semantic_result
        
        classification_time = time.time() - start_time
        logger.info(f"🧠 Семантическая классификация: {semantic_result['intent']} ({classification_time*1000:.0f}ms)")
        
        return {
            **semantic_result,
            "classification_time_ms": classification_time * 1000
        }
    
    def _fast_keyword_classification(self, message_lower: str) -> Dict:
        """Первый слой: быстрая классификация по ключевым словам"""
        
        # ПРИОРИТЕТНАЯ ПРОВЕРКА на отказы (чтобы избежать конфликтов)
        rejection_patterns = [
            "нет, не подходит", "нет не подходит", "не подходит нам", 
            "не устраивает", "не нужно", "отказываюсь", "не интересно"
        ]
        
        for pattern in rejection_patterns:
            if pattern in message_lower:
                return {
                    "intent": "rejection",
                    "confidence": 0.9,
                    "objection_subtype": None,
                    "matched_keywords": [pattern],
                    "emotion": "negative",
                    "sales_stage": "decision"
                }
        
        # Обычная проверка по категориям (кроме rejection, уже проверили)
        for intent, keywords in self.FAST_KEYWORDS.items():
            if intent == "rejection":  # Пропускаем, уже проверили выше
                continue
                
            matched_keywords = [kw for kw in keywords if kw in message_lower]
            
            if matched_keywords:
                # Дополнительная проверка на конфликты с отказами
                if intent == "agreement" and any(neg in message_lower for neg in ["нет", "не подходит", "не устраивает"]):
                    continue  # Пропускаем agreement если есть отрицание
                
                confidence = 0.9 if len(matched_keywords) > 1 else 0.8
                
                # Для ценовых возражений определяем подтип
                objection_subtype = None
                if intent == "price_objection":
                    objection_subtype = self._classify_price_subtype(message_lower)
                
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "objection_subtype": objection_subtype,
                    "matched_keywords": matched_keywords,
                    "emotion": self._estimate_emotion_from_keywords(matched_keywords),
                    "sales_stage": self._estimate_sales_stage(intent)
                }
        
        # Не найдено точных совпадений
        return {
            "intent": "unclear",
            "confidence": 0.3,
            "objection_subtype": None,
            "matched_keywords": [],
            "emotion": "neutral",
            "sales_stage": "evaluation"
        }
    
    def _classify_price_subtype(self, message_lower: str) -> str:
        """Классификация подтипа ценового возражения"""
        for subtype, keywords in self.PRICE_SUBTYPES.items():
            if any(kw in message_lower for kw in keywords):
                return subtype
        return "generic"
    
    def _estimate_emotion_from_keywords(self, keywords: List[str]) -> str:
        """Оценка эмоции по ключевым словам"""
        negative_words = ["дорого", "нет", "не подходит", "отказываюсь"]
        positive_words = ["да", "согласен", "подходит", "отлично"]
        
        if any(word in " ".join(keywords) for word in negative_words):
            return "negative"
        elif any(word in " ".join(keywords) for word in positive_words):
            return "positive"
        else:
            return "neutral"
    
    def _estimate_sales_stage(self, intent: str) -> str:
        """Оценка этапа продаж по intent"""
        stage_map = {
            "price_objection": "negotiation",
            "agreement": "decision",
            "rejection": "decision", 
            "manager_request": "escalation",
            "information_request": "discovery",
            "unclear": "evaluation"
        }
        return stage_map.get(intent, "evaluation")
    
    def _check_for_anger(self, message_lower: str) -> Dict:
        """SENTIMENT GUARD: Быстрая детекция гнева для защиты репутации"""
        
        matched_anger_words = [word for word in self.ANGER_KEYWORDS if word in message_lower]
        
        if matched_anger_words:
            # Уровень гнева зависит от количества найденных слов
            anger_intensity = len(matched_anger_words)
            confidence = min(0.95, 0.8 + (anger_intensity * 0.05))  # 80-95%
            
            return {
                "is_angry": True,
                "confidence": confidence,
                "matched_keywords": matched_anger_words,
                "anger_intensity": anger_intensity
            }
        
        return {
            "is_angry": False,
            "confidence": 0.0,
            "matched_keywords": [],
            "anger_intensity": 0
        }
    
    async def _semantic_classification(self, message: str, context: Dict, fast_result: Dict) -> Dict:
        """Второй слой: семантический анализ через o4-mini"""
        
        system_prompt = f"""Ты эксперт по анализу клиентских сообщений в B2B логистике.

КОНТЕКСТ БЫСТРОГО АНАЛИЗА:
- Предварительная классификация: {fast_result['intent']}
- Уверенность: {fast_result['confidence']:.1%}
- Найденные ключевые слова: {fast_result.get('matched_keywords', [])}

ЗАДАЧА: Проведи глубокий семантический анализ и уточни классификацию.

ВОЗМОЖНЫЕ НАМЕРЕНИЯ:
- agreement: согласие на предложение
- price_objection: возражение по цене  
- conditions_objection: возражения по условиям/срокам
- information_request: запрос дополнительной информации
- manager_request: просьба связаться с руководителем
- rejection: отказ от предложения
- unclear: неопределенное сообщение

ПОДТИПЫ ЦЕНОВЫХ ВОЗРАЖЕНИЙ:
- past_cheaper: клиент ссылается на прошлый опыт
- competitor_cheaper: сравнение с конкурентами  
- budget_cap: превышение бюджета
- generic: общее возражение по цене

ОТВЕТЬ СТРОГО JSON:
{{
  "intent": "название_намерения",
  "confidence": 0.95,
  "objection_subtype": "подтип_или_null",
  "emotion": "positive|neutral|negative",
  "sales_stage": "discovery|evaluation|negotiation|decision|escalation",
  "key_phrases": ["ключевые", "фразы"],
  "reasoning": "краткое объяснение классификации",
  "semantic_nuances": ["нюансы", "которые", "ключевые", "слова", "пропустили"]
}}"""

        try:
            # Используем o4-mini для семантического анализа
            model = settings.get_model_for_task('sales')
            
            response = await ai_client.create_completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f'Проанализируй сообщение: "{message}"'}
                ],
                max_tokens=2000,
                temperature=0.1,
                task_type="semantic_classification"
            )
            
            # Парсим JSON ответ
            try:
                if "```json" in response:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    response = response[json_start:json_end].strip()
                elif "{" in response:
                    json_start = response.find("{")
                    json_end = response.rfind("}") + 1
                    response = response[json_start:json_end]
                
                semantic_result = json.loads(response)
                
                # Добавляем метаданные
                semantic_result.update({
                    "classification_method": "semantic_o4mini",
                    "fast_layer_result": fast_result,
                    "tokens_used": "estimated_200"  # Примерная оценка
                })
                
                return semantic_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON семантического анализа: {e}")
                # Fallback к быстрому результату с улучшенной уверенностью
                return {
                    **fast_result,
                    "classification_method": "fallback_fast",
                    "confidence": fast_result["confidence"] * 0.8,
                    "reasoning": "Ошибка семантического анализа, используется быстрая классификация"
                }
                
        except Exception as e:
            logger.error(f"Ошибка семантической классификации: {e}")
            # Fallback к быстрому результату
            return {
                **fast_result,
                "classification_method": "fallback_error",
                "reasoning": f"Ошибка o4-mini: {str(e)}"
            }
    
    def get_classification_stats(self) -> Dict:
        """Получить статистику классификации для оптимизации"""
        stats = self.classification_stats.copy()
        
        if stats["total_classifications"] > 0:
            stats["fast_layer_hit_rate"] = stats["fast_layer_hits"] / stats["total_classifications"]
            stats["semantic_layer_usage_rate"] = stats["semantic_layer_calls"] / stats["total_classifications"]
            stats["cache_size"] = len(self.semantic_cache)
        
        return stats
    
    def clear_cache(self):
        """Очистить кэш (для управления памятью)"""
        self.semantic_cache.clear()
        logger.info("🧹 Кэш семантической классификации очищен")


# Глобальный экземпляр классификатора
enhanced_classifier = EnhancedClassifier() 