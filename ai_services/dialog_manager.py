"""
Система управления гибридными диалогами
Переключение между ИИ и ручным режимом управления
"""
import json
from datetime import datetime
from typing import Dict, Optional, List
from database.crud import (
    get_monitoring_session_by_telegram_id, 
    update_monitoring_session_by_id,
    get_monitoring_session_by_id
)
from utils.logger import get_logger
from utils.config import settings

logger = get_logger("DIALOG_MANAGER")


class DialogManager:
    """Менеджер для управления режимами диалогов"""
    
    def __init__(self):
        self.owner_telegram_id = 408001372  # ID владельца
        
    async def should_switch_to_manual(
        self, 
        analysis: Dict, 
        client_message: str, 
        order_data: Dict,
        force_switch: bool = False
    ) -> Dict:
        """
        УЛУЧШЕННАЯ логика переключения с учетом многоходовой работы с возражениями
        
        Возвращает:
        {
            "should_switch": bool,
            "reason": str,
            "priority": "high|medium|low", 
            "auto_message": str  # сообщение для автопереключения
        }
        """
        
        try:
            switch_reasons = []
            priority = "low"
            
            # Принудительное переключение (когда ИИ исчерпал попытки)
            if force_switch:
                switch_reasons.append("forced_switch")
                priority = "high"
            
            # 1. СЦЕНАРИЙ: УБИРАЕМ автопереключение при первом ценовом возражении
            # Теперь ценовые возражения обрабатывает многоходовая логика в sales_agent.py
            # Переключение происходит только когда исчерпаны попытки или достигнут лимит маржи
            
            # 2. СЦЕНАРИЙ: Запросы информации которой у ИИ нет
            restricted_topics = ["страховка", "лицензия", "документы", "договор", "юридические", "отслеживание"]
            if any(topic in client_message.lower() for topic in restricted_topics):
                switch_reasons.append("restricted_topic_request")
                priority = "high"
            
            # 3. СЦЕНАРИЙ: Эмоционально негативные сообщения
            if analysis.get("emotion") == "negative" and analysis.get("confidence", 0) > 0.7:
                switch_reasons.append("negative_emotion_detected")
                priority = "medium"
            
            # 4. СЦЕНАРИЙ: ИИ не уверен в анализе
            if analysis.get("confidence", 1.0) < 0.5:
                switch_reasons.append("low_ai_confidence")
                priority = "medium"
            
            # 5. СЦЕНАРИЙ: Клиент просит связаться с руководителем
            manager_requests = ["руководител", "директор", "начальник", "главный", "ответственный"]
            if any(request in client_message.lower() for request in manager_requests):
                switch_reasons.append("manager_requested")
                priority = "high"
            
            should_switch = len(switch_reasons) > 0
            
            # Формируем сообщение для автопереключения
            auto_message = ""
            if should_switch:
                if "forced_switch" in switch_reasons:
                    auto_message = "Передаю ваш вопрос руководителю для персонального обсуждения."
                elif "restricted_topic_request" in switch_reasons:
                    auto_message = "Для ответа на ваш вопрос свяжу вас с руководителем, который предоставит всю необходимую информацию."
                elif "manager_requested" in switch_reasons:
                    auto_message = "Конечно! Передаю ваш запрос руководителю. Он свяжется с вами в ближайшее время."
                else:
                    auto_message = "Передаю ваш вопрос руководителю для персонального обсуждения."
            
            return {
                "should_switch": should_switch,
                "reasons": switch_reasons,
                "priority": priority,
                "auto_message": auto_message,
                "analysis_data": analysis
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа переключения: {e}")
            return {
                "should_switch": True,  # В случае ошибки лучше передать человеку
                "reasons": ["analysis_error"],
                "priority": "high",
                "auto_message": "Передаю ваш запрос руководителю.",
                "analysis_data": {}
            }
    
    async def switch_to_manual_mode(
        self, 
        client_telegram_id: int, 
        reason: str, 
        analysis_data: Dict = None,
        auto_message: str = None
    ) -> bool:
        """Переключает диалог в ручной режим"""
        
        try:
            session = await get_monitoring_session_by_telegram_id(client_telegram_id)
            if not session:
                logger.error(f"Сессия не найдена для клиента {client_telegram_id}")
                return False
            
            # Обновляем сессию
            update_data = {
                "dialog_mode": "manual",
                "owner_handling": True,
                "manual_takeover_at": datetime.now().isoformat(),
                "auto_switch_reason": reason,
                "pending_owner_response": True,
                "ai_analysis_data": json.dumps(analysis_data) if analysis_data else None
            }
            
            await update_monitoring_session_by_id(session["id"], update_data)
            
            # Уведомляем владельца
            await self._notify_owner_manual_takeover(session, reason, analysis_data, auto_message)
            
            logger.info(f"✅ Диалог переключен в ручной режим: {client_telegram_id}, причина: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка переключения в ручной режим: {e}")
            return False
    
    async def switch_to_auto_mode(self, client_telegram_id: int) -> bool:
        """Переключает диалог обратно в автоматический режим"""
        
        try:
            session = await get_monitoring_session_by_telegram_id(client_telegram_id)
            if not session:
                return False
            
            update_data = {
                "dialog_mode": "auto",
                "owner_handling": False,
                "pending_owner_response": False,
                "owner_last_seen_at": datetime.now().isoformat()
            }
            
            await update_monitoring_session_by_id(session["id"], update_data)
            
            logger.info(f"✅ Диалог переключен в автоматический режим: {client_telegram_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка переключения в авто режим: {e}")
            return False
    
    async def is_manual_mode(self, client_telegram_id: int) -> bool:
        """Проверяет находится ли диалог в ручном режиме"""
        
        try:
            session = await get_monitoring_session_by_telegram_id(client_telegram_id)
            if not session:
                return False
            
            return session.get("dialog_mode") == "manual" and session.get("owner_handling", False)
            
        except Exception as e:
            logger.error(f"Ошибка проверки режима: {e}")
            return False
    
    async def get_pending_dialogs(self) -> List[Dict]:
        """Получает список диалогов ожидающих ответа владельца"""
        
        try:
            # Здесь должен быть запрос к БД для получения всех сессий в ручном режиме
            # Пока возвращаем пустой список, реализуем позже в CRUD
            return []
            
        except Exception as e:
            logger.error(f"Ошибка получения ожидающих диалогов: {e}")
            return []
    
    async def _notify_owner_manual_takeover(
        self, 
        session: Dict, 
        reason: str, 
        analysis_data: Dict,
        auto_message: str = None
    ):
        """Уведомляет владельца о переключении в ручной режим"""
        
        try:
            # Получаем данные о заказе и клиенте
            order_data = session.get("cargo_data", {})
            client_id = session.get("client_telegram_id")
            
            # Формируем причину переключения
            reason_texts = {
                "complex_price_objection": "🏷️ Сложные возражения по цене",
                "restricted_topic_request": "📋 Запрос информации вне компетенции ИИ", 
                "negative_emotion_detected": "😠 Негативная эмоциональная реакция",
                "low_ai_confidence": "🤔 ИИ не уверен в анализе",
                "manager_requested": "👨‍💼 Клиент просит связаться с руководителем",
                "analysis_error": "⚠️ Ошибка анализа ИИ"
            }
            
            reason_text = reason_texts.get(reason, f"❓ {reason}")
            
            # Анализ ИИ для контекста
            ai_analysis = ""
            if analysis_data:
                intent = analysis_data.get("intent", "неизвестно")
                confidence = analysis_data.get("confidence", 0)
                objection_type = analysis_data.get("objection_type")
                
                ai_analysis = f"""
🤖 Анализ ИИ:
• Намерение: {intent}
• Уверенность: {confidence:.1%}
• Тип возражения: {objection_type or 'отсутствует'}"""
            
            message = f"""🚨 ТРЕБУЕТСЯ РУЧНОЕ УПРАВЛЕНИЕ

📦 ГРУЗ: {order_data.get('cargo_type', 'N/A')}
🚛 МАРШРУТ: {order_data.get('from_city', 'N/A')} → {order_data.get('to_city', 'N/A')}
👤 КЛИЕНТ: @{client_id}

🔄 ПРИЧИНА ПЕРЕКЛЮЧЕНИЯ: {reason_text}

💬 ПОСЛЕДНЕЕ СООБЩЕНИЕ КЛИЕНТА:
"{session.get('client_response', 'Не указано')}"

{ai_analysis}

{"🤖 Авто-ответ отправлен: " + auto_message if auto_message else ""}

⚡ УПРАВЛЕНИЕ:
/manual_{session.get('id')}_respond - Ответить клиенту
/manual_{session.get('id')}_auto - Вернуть ИИ
/manual_{session.get('id')}_pause - Приостановить"""

            # Отправляем через глобальную функцию
            from bot.client_bot import send_telegram_message
            await send_telegram_message(self.owner_telegram_id, message)
            
            logger.info(f"✅ Уведомление о ручном режиме отправлено владельцу")
            
        except Exception as e:
            logger.error(f"Ошибка уведомления владельца: {e}")


# Глобальный экземпляр менеджера диалогов
dialog_manager = DialogManager() 