#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ИИ-агент для анализа надежности перевозчиков
Анализирует репутацию, отзывы и историю компаний
"""

from openai import AsyncOpenAI
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("CARRIER_ANALYZER")


class CarrierAnalyzer:
    """ИИ-агент для анализа надежности перевозчиков"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        
        # Профессиональная роль агента
        self.agent_persona = """
Ты - эксперт по анализу надежности транспортных компаний с 15-летним опытом в логистике.

Твоя задача: оценивать добросовестность перевозчиков на основе:
- Рейтинга в системе ATI.SU (звезды)
- Количества претензий и рекомендаций
- Упоминаний в списке недобросовестных партнеров
- Опыта работы и профиля деятельности
- Организационно-правовой формы

Критерии оценки:
🟢 ВЫСОКАЯ НАДЕЖНОСТЬ (8-10 баллов):
- Рейтинг 4+ звезд
- Рекомендации >> претензий (соотношение 3:1+)
- Нет упоминаний в "черных списках"
- ООО/ИП с опытом работы
- Специализация в грузоперевозках

🟡 СРЕДНЯЯ НАДЕЖНОСТЬ (5-7 баллов):
- Рейтинг 2-4 звезды
- Примерно равное количество рекомендаций и претензий
- Единичные негативные упоминания
- Новые компании без истории

🔴 НИЗКАЯ НАДЕЖНОСТЬ (1-4 балла):
- Рейтинг менее 2 звезд
- Претензий больше чем рекомендаций
- Множественные упоминания в "черных списках"
- Подозрительные данные

Всегда обосновывай свою оценку конкретными фактами.
"""
    
    async def analyze_carrier_reliability(self, carrier_offer: Dict, firm_data: Optional[List[Dict]] = None) -> Dict:
        """
        Анализ надежности перевозчика
        
        Args:
            carrier_offer: Предложение перевозчика от ATI.SU
            firm_data: Данные о фирме из API /v1.0/firms/{atiId}/contacts/summary
            
        Returns:
            Результат анализа с оценкой надежности
        """
        try:
            # Извлекаем основные данные из предложения
            firm_name = carrier_offer.get("FirmName", "N/A")
            firm_id = carrier_offer.get("FirmId", "N/A")
            price = carrier_offer.get("Price", 0)
            rating = carrier_offer.get("Rating", 0)
            
            # Формируем данные для анализа
            analysis_data = {
                "firm_name": firm_name,
                "firm_id": firm_id,
                "price": price,
                "basic_rating": rating,
                "has_detailed_data": firm_data is not None
            }
            
            # Если есть детальные данные о фирме
            if firm_data and len(firm_data) > 0:
                contact = firm_data[0]  # Берем первый контакт
                analysis_data.update({
                    "score": contact.get("score", 0),
                    "claims_count": contact.get("claims_count", 0),
                    "recommendations_count": contact.get("recommendations_count", 0),
                    "bad_partner_mentions": contact.get("bad_partner_mentions_count", 0),
                    "firm_type": contact.get("firm_type", ""),
                    "ownership": contact.get("ownership", ""),
                    "city": contact.get("city", "")
                })
            
            # Генерируем анализ через ИИ
            reliability_score = await self._generate_reliability_analysis(analysis_data)
            
            return reliability_score
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа надежности перевозчика: {e}")
            return {
                "reliability_score": 5,  # Средняя оценка при ошибке
                "reliability_level": "unknown",
                "analysis": "Не удалось провести анализ надежности",
                "risk_factors": ["Ошибка анализа"],
                "positive_factors": [],
                "recommendation": "Требуется дополнительная проверка"
            }
    
    async def _generate_reliability_analysis(self, analysis_data: Dict) -> Dict:
        """Генерация анализа надежности через ИИ"""
        
        try:
            # Формируем промпт для анализа
            firm_info = f"""
АНАЛИЗ НАДЕЖНОСТИ ПЕРЕВОЗЧИКА

ОСНОВНЫЕ ДАННЫЕ:
- Название: {analysis_data.get('firm_name')}
- Базовый рейтинг: {analysis_data.get('basic_rating', 0)}
- Цена предложения: {analysis_data.get('price', 0):,} руб
"""
            
            if analysis_data.get("has_detailed_data"):
                firm_info += f"""
ДЕТАЛЬНАЯ РЕПУТАЦИЯ:
- Рейтинг ATI: {analysis_data.get('score', 0)} звезд
- Рекомендации: {analysis_data.get('recommendations_count', 0)}
- Претензии: {analysis_data.get('claims_count', 0)}
- Упоминания в "черных списках": {analysis_data.get('bad_partner_mentions', 0)}
- Тип деятельности: {analysis_data.get('firm_type', 'N/A')}
- Организационная форма: {analysis_data.get('ownership', 'N/A')}
- Город: {analysis_data.get('city', 'N/A')}
"""
            else:
                firm_info += "\nДетальные данные о репутации недоступны - анализ только по базовым показателям."
            
            prompt = f"""
{self.agent_persona}

{firm_info}

ЗАДАЧА:
Проведи профессиональный анализ надежности этого перевозчика и дай оценку от 1 до 10.

ОТВЕТ В ФОРМАТЕ JSON:
{{
  "reliability_score": число_от_1_до_10,
  "reliability_level": "high/medium/low/unknown",
  "analysis": "подробный_анализ_2-3_предложения",
  "risk_factors": ["фактор1", "фактор2"],
  "positive_factors": ["фактор1", "фактор2"],
  "recommendation": "краткая_рекомендация"
}}
"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.agent_persona},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Парсим JSON ответ
            import json
            try:
                # Ищем JSON в ответе
                if "```json" in analysis_text:
                    json_start = analysis_text.find("```json") + 7
                    json_end = analysis_text.find("```", json_start)
                    analysis_text = analysis_text[json_start:json_end].strip()
                elif "{" in analysis_text and "}" in analysis_text:
                    json_start = analysis_text.find("{")
                    json_end = analysis_text.rfind("}") + 1
                    analysis_text = analysis_text[json_start:json_end]
                
                result = json.loads(analysis_text)
                
                # Проверяем корректность данных
                if not isinstance(result.get("reliability_score"), (int, float)):
                    result["reliability_score"] = 5
                
                if result["reliability_score"] > 10:
                    result["reliability_score"] = 10
                elif result["reliability_score"] < 1:
                    result["reliability_score"] = 1
                
                logger.info(f"🔍 Анализ надежности '{analysis_data.get('firm_name')}': {result['reliability_score']}/10 ({result['reliability_level']})")
                
                return result
                
            except Exception as parse_error:
                logger.warning(f"⚠️ Ошибка парсинга JSON анализа: {parse_error}")
                # Fallback анализ
                return self._fallback_analysis(analysis_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации анализа надежности: {e}")
            return self._fallback_analysis(analysis_data)
    
    def _fallback_analysis(self, analysis_data: Dict) -> Dict:
        """Fallback анализ при ошибке ИИ"""
        
        score = analysis_data.get("score", 0)
        claims = analysis_data.get("claims_count", 0)
        recommendations = analysis_data.get("recommendations_count", 0)
        bad_mentions = analysis_data.get("bad_partner_mentions", 0)
        
        # Простой алгоритм оценки
        reliability_score = 5  # Базовая оценка
        
        if analysis_data.get("has_detailed_data"):
            # Анализ по рейтингу
            if score >= 4:
                reliability_score += 2
            elif score >= 2:
                reliability_score += 0
            else:
                reliability_score -= 2
            
            # Анализ соотношения рекомендации/претензии
            if recommendations > 0 and claims == 0:
                reliability_score += 2
            elif recommendations > claims * 2:
                reliability_score += 1
            elif claims > recommendations * 2:
                reliability_score -= 2
            
            # Упоминания в черных списках
            if bad_mentions > 0:
                reliability_score -= bad_mentions
        
        # Ограничиваем диапазон
        reliability_score = max(1, min(10, reliability_score))
        
        # Определяем уровень надежности
        if reliability_score >= 8:
            level = "high"
        elif reliability_score >= 5:
            level = "medium"
        else:
            level = "low"
        
        return {
            "reliability_score": reliability_score,
            "reliability_level": level,
            "analysis": f"Автоматический анализ: оценка {reliability_score}/10 на основе доступных данных",
            "risk_factors": ["Ограниченные данные для анализа"],
            "positive_factors": ["Присутствует в системе ATI.SU"],
            "recommendation": "Стандартная проверка при заключении договора"
        }


# Глобальный экземпляр анализатора
carrier_analyzer = CarrierAnalyzer() 