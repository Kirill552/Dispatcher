"""
Система команд для владельца для управления гибридными диалогами
Позволяет отвечать клиентам, переключать режимы и управлять сессиями
"""
import re
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database.crud import (
    get_monitoring_session_by_id,
    update_monitoring_session_by_id,
    get_monitoring_session_by_telegram_id
)
from bot.client_bot import send_telegram_message
from ai_services.dialog_manager import dialog_manager
from utils.logger import get_logger

logger = get_logger("OWNER_COMMANDS")


class OwnerCommandHandler:
    """Обработчик команд владельца для управления диалогами"""
    
    def __init__(self):
        self.owner_telegram_id = 408001372
    
    async def handle_owner_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Обрабатывает сообщения от владельца
        Возвращает True если сообщение было обработано как команда
        """
        
        user_id = update.effective_user.id
        if user_id != self.owner_telegram_id:
            return False
        
        message_text = update.message.text
        if not message_text:
            return False
        
        try:
            # Команда ответа клиенту: /reply_123 Ваш ответ клиенту
            if message_text.startswith('/reply_'):
                await self._handle_reply_command(update, context, message_text)
                return True
            
            # Команда переключения в авто режим: /auto_123
            elif message_text.startswith('/auto_'):
                await self._handle_auto_command(update, context, message_text)
                return True
            
            # Команда паузы диалога: /pause_123
            elif message_text.startswith('/pause_'):
                await self._handle_pause_command(update, context, message_text)
                return True
            
            # Команда просмотра активных диалогов: /dialogs
            elif message_text == '/dialogs':
                await self._handle_dialogs_command(update, context)
                return True
            
            # Команда получения статистики: /stats
            elif message_text == '/stats':
                await self._handle_stats_command(update, context)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка обработки команды владельца: {e}")
            await update.message.reply_text(f"❌ Ошибка выполнения команды: {str(e)}")
            return True
    
    async def _handle_reply_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обработка команды ответа клиенту: /reply_123 Текст ответа"""
        
        try:
            # Парсим команду
            match = re.match(r'/reply_(\d+)\s+(.*)', message_text, re.DOTALL)
            if not match:
                await update.message.reply_text(
                    "❌ Неверный формат команды.\n"
                    "Используйте: /reply_[ID] [текст ответа]"
                )
                return
            
            session_id = int(match.group(1))
            reply_text = match.group(2).strip()
            
            if not reply_text:
                await update.message.reply_text("❌ Текст ответа не может быть пустым")
                return
            
            # Получаем сессию
            session = await get_monitoring_session_by_id(session_id)
            if not session:
                await update.message.reply_text(f"❌ Сессия {session_id} не найдена")
                return
            
            client_telegram_id = session.get("client_telegram_id")
            if not client_telegram_id:
                await update.message.reply_text(f"❌ У сессии {session_id} нет Telegram ID клиента")
                return
            
            # Отправляем ответ клиенту
            await send_telegram_message(client_telegram_id, reply_text)
            
            # Обновляем сессию
            await update_monitoring_session_by_id(session_id, {
                "pending_owner_response": False,
                "owner_last_seen_at": datetime.now().isoformat(),
                "last_interaction_at": datetime.now().isoformat()
            })
            
            # Подтверждаем владельцу
            await update.message.reply_text(
                f"✅ Ответ отправлен клиенту\n"
                f"📋 Сессия: {session_id}\n"
                f"💬 Текст: {reply_text[:100]}{'...' if len(reply_text) > 100 else ''}"
            )
            
            logger.info(f"📤 Владелец ответил клиенту {client_telegram_id} в сессии {session_id}")
            
        except Exception as e:
            logger.error(f"Ошибка команды reply: {e}")
            await update.message.reply_text(f"❌ Ошибка отправки ответа: {str(e)}")
    
    async def _handle_auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обработка команды переключения в авто режим: /auto_123"""
        
        try:
            # Парсим команду
            match = re.match(r'/auto_(\d+)', message_text)
            if not match:
                await update.message.reply_text(
                    "❌ Неверный формат команды.\n"
                    "Используйте: /auto_[ID]"
                )
                return
            
            session_id = int(match.group(1))
            
            # Получаем сессию
            session = await get_monitoring_session_by_id(session_id)
            if not session:
                await update.message.reply_text(f"❌ Сессия {session_id} не найдена")
                return
            
            client_telegram_id = session.get("client_telegram_id")
            if not client_telegram_id:
                await update.message.reply_text(f"❌ У сессии {session_id} нет Telegram ID клиента")
                return
            
            # Переключаем в автоматический режим
            success = await dialog_manager.switch_to_auto_mode(client_telegram_id)
            
            if success:
                # Обновляем статус сессии
                await update_monitoring_session_by_id(session_id, {
                    "status": "auto_mode",
                    "owner_last_seen_at": datetime.now().isoformat()
                })
                
                # Уведомляем клиента
                await send_telegram_message(
                    client_telegram_id,
                    "🤖 Диалог переведен в автоматический режим. ИИ-диспетчер снова обрабатывает ваши сообщения."
                )
                
                # Подтверждаем владельцу
                await update.message.reply_text(
                    f"✅ Диалог переключен в автоматический режим\n"
                    f"📋 Сессия: {session_id}\n"
                    f"🤖 ИИ снова обрабатывает сообщения клиента"
                )
                
                logger.info(f"🔄 Диалог {client_telegram_id} переключен в авто режим владельцем")
            else:
                await update.message.reply_text(f"❌ Ошибка переключения сессии {session_id}")
            
        except Exception as e:
            logger.error(f"Ошибка команды auto: {e}")
            await update.message.reply_text(f"❌ Ошибка переключения: {str(e)}")
    
    async def _handle_pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обработка команды паузы диалога: /pause_123"""
        
        try:
            # Парсим команду
            match = re.match(r'/pause_(\d+)', message_text)
            if not match:
                await update.message.reply_text(
                    "❌ Неверный формат команды.\n"
                    "Используйте: /pause_[ID]"
                )
                return
            
            session_id = int(match.group(1))
            
            # Получаем сессию
            session = await get_monitoring_session_by_id(session_id)
            if not session:
                await update.message.reply_text(f"❌ Сессия {session_id} не найдена")
                return
            
            client_telegram_id = session.get("client_telegram_id")
            
            # Приостанавливаем диалог
            await update_monitoring_session_by_id(session_id, {
                "status": "paused",
                "dialog_mode": "paused",
                "owner_handling": False,
                "pending_owner_response": False,
                "owner_last_seen_at": datetime.now().isoformat()
            })
            
            # Уведомляем клиента
            if client_telegram_id:
                await send_telegram_message(
                    client_telegram_id,
                    "⏸️ Диалог временно приостановлен. Мы скоро с вами свяжемся."
                )
            
            # Подтверждаем владельцу
            await update.message.reply_text(
                f"⏸️ Диалог приостановлен\n"
                f"📋 Сессия: {session_id}\n"
                f"👤 Клиент уведомлен о паузе"
            )
            
            logger.info(f"⏸️ Диалог {session_id} приостановлен владельцем")
            
        except Exception as e:
            logger.error(f"Ошибка команды pause: {e}")
            await update.message.reply_text(f"❌ Ошибка приостановки: {str(e)}")
    
    async def _handle_dialogs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды просмотра активных диалогов: /dialogs"""
        
        try:
            # Здесь нужно будет добавить функцию в CRUD для получения всех активных сессий
            # Пока заглушка
            
            message = """📋 АКТИВНЫЕ ДИАЛОГИ

🤖 Автоматический режим:
• Сессия 123: Мебель, Москва → СПб
• Сессия 124: Стройматериалы, Казань → Уфа

👨‍💼 Ручной режим:
• Сессия 125: Оборудование, Воронеж → Тамбов (ожидает ответа)

⏸️ Приостановленные:
• Сессия 126: Груз, город → город

💡 Используйте команды:
/reply_[ID] [текст] - ответить
/auto_[ID] - в авто режим  
/pause_[ID] - приостановить"""

            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка команды dialogs: {e}")
            await update.message.reply_text(f"❌ Ошибка получения диалогов: {str(e)}")
    
    async def _handle_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды статистики: /stats"""
        
        try:
            # Заглушка статистики
            message = """📊 СТАТИСТИКА ГИБРИДНОГО УПРАВЛЕНИЯ

🤖 ИИ-режим:
• Активных диалогов: 15
• Обработано сегодня: 42
• Успешность: 87%

👨‍💼 Ручной режим:
• Активных диалогов: 3  
• Переключений сегодня: 8
• Среднее время ответа: 12 мин

🔄 Автопереключения:
• По цене: 5 (62%)
• По сложности: 2 (25%) 
• По ошибкам: 1 (13%)

💰 Эффективность:
• Закрыто ИИ: 12 сделок
• Закрыто вручную: 4 сделки
• Конверсия: 78%"""

            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Ошибка команды stats: {e}")
            await update.message.reply_text(f"❌ Ошибка получения статистики: {str(e)}")


# Глобальный экземпляр обработчика команд владельца
owner_command_handler = OwnerCommandHandler() 