"""
Telegram бот для общения с клиентами
"""
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from typing import Dict, Any, Optional, List
import logging
import traceback
from ai_services.sales_agent import sales_agent
from ai_services.ai_dispatcher_logic import AIDispatcherLogic
from ai_services.message_processor import message_processor
from database.models import Client, Order
from database.crud import create_client, get_client_by_telegram_id, create_order
from utils.config import settings
from utils.logger import bot_logger as logger

# Глобальная функция для отправки сообщений в Telegram
async def send_telegram_message(chat_id: int, text: str, reply_markup=None):
    """Глобальная функция для отправки сообщений в Telegram"""
    try:
        from telegram import Bot
        
        # Создаем временный экземпляр бота для отправки
        bot = Bot(token=settings.telegram_bot_token)
        
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Сообщение отправлено в Telegram: {chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram {chat_id}: {e}")
        return False



class ClientBot:
    """Telegram бот для клиентов"""
    
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.app = None
        self.ai_dispatcher = AIDispatcherLogic()
        # Хранилище для связи клиентов с заказами
        self.client_orders = {}  # {telegram_id: {'order_id': str, 'phone': str, 'name': str}}
        
    async def start_bot(self):
        """Запуск бота"""
        try:
            self.app = Application.builder().token(self.token).build()
            
            # Обработчики команд
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("new_order", self.new_order_command))
            self.app.add_handler(CommandHandler("my_orders", self.my_orders_command))
            # self.app.add_handler(CommandHandler("contact", self.contact_command))     # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            
            # Обработчик текстовых сообщений
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Обработчик кнопок
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            
            logger.info("🤖 Запуск Telegram бота для клиентов")
            
            # Простой запуск без создания отдельного event loop
            logger.info("✅ Telegram бот инициализирован")
            
            # Запускаем в фоновой задаче
            import asyncio
            loop = asyncio.get_running_loop()
            self.bot_task = loop.create_task(self._run_bot_polling())
            logger.info("✅ Telegram бот запущен в фоновом режиме")
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {str(e)}")
            raise
    
    async def _run_bot_polling(self):
        """Запуск polling в отдельной задаче"""
        try:
            # Инициализируем приложение
            await self.app.initialize()
            await self.app.start()
            
            # Запускаем polling
            await self.app.updater.start_polling()
            
            logger.info("✅ Telegram бот успешно запущен")
            
            # Ждем бесконечно
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Ошибка в polling: {str(e)}")
        finally:
            try:
                if self.app.updater.running:
                    await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except Exception as e:
                logger.error(f"Ошибка остановки бота: {str(e)}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        
        user = update.effective_user
        
        # Проверяем параметр start (токен заказа)
        if context.args:
            start_param = context.args[0]
            
            # Если это токен заказа
            if start_param.startswith('ORDER_'):
                await self._handle_order_token(update, context, start_param)
                return
        
        # Проверяем, существует ли уже клиент
        existing_client = await get_client_by_telegram_id(user.id)
        
        if not existing_client:
            # Создаем нового клиента
            client_data = {
                'telegram_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            await create_client(client_data)
            logger.info(f"✅ Создан новый клиент: {user.id} (@{user.username})")
        else:
            logger.info(f"👤 Клиент уже существует: {user.id} (@{user.username})")
        
        logger.info(f"Пользователь {user.id} (@{user.username}) запустил бота")
        
        # Приветственное сообщение 2025 с ИИ (без кнопок)
        welcome_text = f"""🎯 Добро пожаловать{f', {user.first_name}' if user.first_name else ''}! 

🚛 ИИ-Диспетчер Логистики 2025 — ваш персональный помощник в организации грузоперевозок

✨ Что я делаю:
🔍 Нахожу лучших перевозчиков среди проверенных компаний
💰 Рассчитываю оптимальную стоимость доставки
🛡️ Обеспечиваю полное сопровождение сделки
📊 Контролирую выполнение заказа от А до Я

⚖️ Специализация: грузы от 200 кг
⏱️ Время поиска: обычно 15-30 минут
🌍 География: межгород по всей России (доставка по одному городу не выполняется)

💬 Как обращаться:
• Для заказа: "Нужно перевезти груз" или "Заказать перевозку"
• Для справки: "Помощь" или "Как это работает?"
• Для статуса: "Мои заказы" или "Где мой груз?"
• Для контактов: "Контакты" или "Как с вами связаться?"

Просто напишите что вам нужно!"""
        
        # Кнопки главного меню (ЗАКОММЕНТИРОВАНО - заменено на ИИ)
        # keyboard = [
        #     [InlineKeyboardButton("🚀 Новый заказ", callback_data="new_order")],
        # ]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        
        help_text = f"""📚 Помощь по работе с ИИ-Диспетчером 2025

🚀 **КАК ЗАКАЗАТЬ ПЕРЕВОЗКУ (МЕЖГОРОД):**
1️⃣ Нажмите "🚀 Новый заказ"
2️⃣ Выберите тип груза из списка
3️⃣ Укажите маршрут (откуда → куда)
4️⃣ Введите вес и объем/габариты
5️⃣ Выберите дату загрузки
6️⃣ Укажите тип кузова и способы погрузки
7️⃣ Оставьте контактные данные

💬 **ПРИМЕР БЫСТРОГО ЗАКАЗА (межгород):**
"Мебель из Сарапула в Ижевск, 500 кг, 2.5 куба, 25-28 числа"

🔍 **ПРОЦЕСС ПОИСКА (только межгород):**
• Автоматически размещаем груз среди проверенных перевозчиков
• Получаете уведомления о найденных вариантах
• Выбираете лучшее предложение прямо в боте
• Обычно поиск занимает 15-30 минут

💰 **ОПЛАТА:**
• Оплата только после загрузки груза
• Перевод на карту или наличными
• Безналичный расчет с НДС и без

📞 **ПОДДЕРЖКА 24/7:**
• Телефон: {settings.dispatcher_phone}
• Telegram: {settings.dispatcher_telegram}

❓ Есть вопросы? Просто напишите мне!"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def new_order_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/new_order теперь запускает тот же пошаговый сценарий, что и кнопка '🚀 Новый заказ'."""

        # Сброс предыдущих данных заказа
        context.user_data['step_data'] = {}
        context.user_data['current_step'] = 'start'

        # Стартуем первый шаг (выбор типа груза)
        result = await self.ai_dispatcher.handle_step_by_step_order(
            message="",
            user_data={'order_data': {}},
            step='start'
        )

        # Отправляем клиенту первый вопрос с кнопками
        await self._send_step_response_from_message(update, result, context)
    
    async def my_orders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /my_orders"""
        
        user_id = update.effective_user.id
        
        # Проверяем активные заказы в базе данных
        try:
            from database.crud import get_orders_by_telegram_id
            
            active_orders = await get_orders_by_telegram_id(user_id)
            
            if active_orders:
                # Есть активные заказы
                orders_list = []
                for order in active_orders:
                    status_emoji = {
                        'pending': '⏳',
                        'searching': '🔍', 
                        'offers_found': '📋',
                        'completed': '✅',
                        'cancelled': '❌'
                    }.get(order.get('status', 'pending'), '⏳')
                    
                    status_text = {
                        'pending': 'Ожидает обработки',
                        'searching': 'Ищем перевозчиков',
                        'offers_found': 'Найдены предложения',
                        'completed': 'Завершен',
                        'cancelled': 'Отменен'
                    }.get(order.get('status', 'pending'), 'В обработке')
                    
                    order_info = f"""
{status_emoji} **Заказ #{order.get('id', 'N/A')}**
🚛 {order.get('from_city', 'N/A')} → {order.get('to_city', 'N/A')}
📦 {order.get('cargo_type', 'N/A')}, {order.get('weight', 'N/A')} кг
📅 {order.get('loading_date', order.get('loading_date_from', 'N/A'))}
📱 Статус: {status_text}"""
                    orders_list.append(order_info)
                
                orders_text = f"""📋 Ваши заказы

{''.join(orders_list)}

💬 Как только найдем подходящие предложения - сразу уведомлю!"""
            else:
                orders_text = """📋 Ваши заказы

У вас пока нет активных заказов.

📦 Для создания нового заказа нажмите "🚀 Новый заказ" или просто опишите что нужно перевезти."""
        
        except Exception as e:
            logger.error(f"Ошибка получения заказов: {e}")
            orders_text = """📋 Ваши заказы

Не удалось загрузить информацию о заказах.

📦 Для создания нового заказа нажмите "🚀 Новый заказ"."""
        
        await update.message.reply_text(orders_text, parse_mode='Markdown')
    
    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /contact"""
        
        contact_text = f"""📞 Контакты для связи

👨‍💼 Диспетчер: {settings.dispatcher_phone}
💬 Telegram: {settings.dispatcher_telegram}
📧 Email: {settings.dispatcher_email}

🕐 Часы работы: 24/7

⚡ Срочные вопросы: лучше звонить
💬 Обычные вопросы: пишите в чат"""
        
        await update.message.reply_text(contact_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений с ИИ"""
        user = update.effective_user
        # Поддержка передачи контакта через кнопку «Поделиться номером»
        if update.message.contact:
            contact = update.message.contact
            phone_number = contact.phone_number
            full_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()

            # Сохраняем в step_data, чтобы логика могла сверить ФИО
            step_data = context.user_data.get('step_data', {})
            step_data['contact_phone'] = phone_number
            if full_name:
                step_data['contact_tg_name'] = full_name
            context.user_data['step_data'] = step_data

            # Очищаем message_text, чтобы AI попросил ФИО отдельно
            message_text = ""
            # Убираем клавиатуру с кнопкой контакта
            await update.message.reply_text("☎️ Спасибо, номер получен.", reply_markup=ReplyKeyboardRemove())
        else:
            message_text = update.message.text
        
        logger.info(f"Сообщение от {user.id}: {message_text[:50]}...")
        
        try:
            # НУЛЕВОЙ ПРИОРИТЕТ: Проверяем команды владельца
            from bot.owner_commands import owner_command_handler
            
            if await owner_command_handler.handle_owner_message(update, context):
                # Сообщение обработано как команда владельца
                return
            
            # ПЕРВЫЙ ПРИОРИТЕТ: Проверяем находится ли диалог в ручном режиме
            from ai_services.dialog_manager import dialog_manager
            
            if await dialog_manager.is_manual_mode(user.id):
                # Диалог в ручном режиме - перенаправляем владельцу
                await self._handle_manual_mode_message(update, context, message_text)
                return
            
            # Проверяем, ждем ли мы ввод даты после выбора месяца
            if context.user_data.get('waiting_for_date_input'):
                await self._handle_date_input(update, context, message_text)
                return
            
            # Проверяем наличие токена заказа в сообщении
            if message_text and len(message_text) == 8 and message_text.isalnum():
                await self._handle_order_token(update, context, message_text)
                return
            
            # ОБРАБОТКА ПРОСТЫХ ТЕКСТОВЫХ КОМАНД (не слэши)
            lower_msg = message_text.lower().strip()
            if lower_msg in ["главное меню", "меню", "main menu"]:
                await self._show_main_menu_from_message(update, context)
                return
            if lower_msg in ["помощь", "help", "/help"]:
                await self.help_command(update, context)
                return
            if lower_msg in ["мои заказы", "статус", "где мой груз", "/my_orders"]:
                await self.my_orders_command(update, context)
                return
            
            # --- НОВОЕ: если уже идёт пошаговый сценарий (есть current_step), обрабатываем сразу
            # и не запускаем message_processor, чтобы не ловить ложные intents типа contact
            if context.user_data.get('current_step'):
                await self._handle_step_message(update, context, message_text)
                return
            
            # НОВОЕ: Сначала пробуем обработать сообщение через ИИ-классификатор
            ai_result = await message_processor.process_message(message_text, user.id)

            if ai_result:
                if ai_result['action'] == 'respond':
                    # ИИ дал готовый ответ
                    await update.message.reply_text(ai_result['text'])
                    return
                elif ai_result['action'] == 'new_order':
                    # Если пользователь уже находится в процессе создания заказа, игнорируем повторный new_order
                    if context.user_data.get('step_data'):
                        # Продолжаем существующий пошаговый сценарий
                        pass  # просто выходим из блока, ниже шаг обработается
                    else:
                        # Иначе запускаем новый заказ
                        await self._handle_new_order_callback_from_message(update, context)
                        return
                elif ai_result['action'] == 'main_menu':
                    # ИИ отправляет пользователя в главное меню
                    await self._show_main_menu_from_message(update, context)
                    return

            # Если ИИ не распознал намерение, проверяем, не является ли это ответом на предложение ИИ-продажника
            if await self._is_response_to_ai_offer(user.id, message_text):
                await self._handle_ai_sales_response(update, context, message_text)
                return

            # В остальных случаях — продолжаем пошаговый диалог
            await self._handle_step_message(update, context, message_text)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")
            await update.message.reply_text(
                "Произошла ошибка. Попробуйте еще раз или начните сначала с /start",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Новый заказ", callback_data="new_order")
                ]])
            )

    async def _handle_date_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обработка ввода даты после выбора месяца"""
        from datetime import datetime
        
        try:
            selected_month = context.user_data.get('selected_month')
            selected_year = context.user_data.get('selected_year')
            
            if not selected_month or not selected_year:
                await update.message.reply_text("Сначала выберите месяц")
                return
                
            # Парсим введенную дату
            if '-' in message_text:
                # Диапазон дат
                try:
                    start_day, end_day = map(int, message_text.split('-'))
                    
                    start_date = f"{selected_year}-{selected_month:02d}-{start_day:02d}"
                    end_date = f"{selected_year}-{selected_month:02d}-{end_day:02d}"
                    
                    # Проверяем корректность дат
                    datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.strptime(end_date, '%Y-%m-%d')
                    
                    processed_message = f"{start_day}-{end_day}"
                    
                except ValueError:
                    await update.message.reply_text("Неверный формат диапазона. Используйте формат: 21-27")
                    return
            else:
                # Одна дата
                try:
                    day = int(message_text.strip())
                    date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
                    
                    # Проверяем корректность даты
                    datetime.strptime(date_str, '%Y-%m-%d')
                    
                    # ИСПРАВЛЕНИЕ: Передаем просто число для корректного парсинга ИИ
                    processed_message = f"{day}"
                    
                except ValueError:
                    await update.message.reply_text("Неверный день месяца. Введите число от 1 до 31")
                    return
            
            # Сбрасываем флаг ожидания ввода
            context.user_data['waiting_for_date_input'] = False
            
            # Передаем дату в пошаговую логику
            order_data = context.user_data.get('step_data', {})
            result = await self.ai_dispatcher.handle_step_by_step_order(
                message=processed_message,
                user_data={'order_data': order_data},
                step='date'
            )
            
            # Обновляем данные
            if result.get('order_data'):
                order_data.update(result['order_data'])
                context.user_data['step_data'] = order_data
            
            # Создаем фиктивный query для _send_step_response
            class FakeQuery:
                def __init__(self, message):
                    self.message = message
                
                async def edit_message_text(self, *args, **kwargs):
                    # Отправляем новое сообщение вместо редактирования
                    return await self.message.reply_text(*args, **kwargs)
            
            fake_query = FakeQuery(update.message)
            await self._send_step_response(fake_query, result, context)
            
        except Exception as e:
            logger.error(f"Ошибка обработки ввода даты: {str(e)}")
            await update.message.reply_text("Ошибка обработки даты. Попробуйте еще раз")
    
    async def _handle_order_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE, token: str):
        """Обработка токена заказа из лендинга (упрощенная версия)"""
        
        user = update.effective_user
        
        # Поскольку токены больше не используются, направляем к созданию нового заказа
        await update.message.reply_text(
            "🚀 Добро пожаловать!\n\n"
            "Нажмите кнопку ниже, чтобы создать новый заказ:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🚀 Создать заказ", callback_data="new_order")
            ]])
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        user_id = query.from_user.id
        
        logger.info(f"Кнопка нажата: {callback_data} пользователем {user_id}")
        
        # Игнорируем отключенные кнопки
        if callback_data == "ignore":
            return
        
        # Обработка различных типов кнопок
        try:
            if callback_data == "new_order":
                await self._handle_new_order_callback(query, context)
            # elif callback_data == "my_orders":                                      # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            #     await self._handle_my_orders_callback(query, context)               # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            # elif callback_data == "contact":                                        # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            #     await self._handle_contact_callback(query, context)                 # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            # elif callback_data == "help":                                           # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            #     await self._handle_help_callback(query, context)                    # ЗАКОММЕНТИРОВАНО - заменено на ИИ
            elif callback_data == "main_menu":
                await self._handle_main_menu_callback(query, context)
            elif callback_data == "date_show_calendar":
                await self._show_calendar(query, context)
            elif callback_data.startswith("month_"):
                await self._handle_month_selection(query, callback_data, context)
            elif callback_data.startswith("date_select_"):
                date_str = callback_data.replace("date_select_", "")
                if date_str != "ignore":
                    processed_message = f"Дата загрузки: {date_str}"
                    await self._handle_step_button(query, processed_message, context)
            elif callback_data == "date_range_mode":
                await self._handle_date_range_mode(query, context)
            elif callback_data.startswith("range_date_"):
                date_str = callback_data.replace("range_date_", "")
                await self._handle_range_date_selection(query, date_str, context)
            elif callback_data == "date_back":
                # Возвращаемся к выбору дат кнопками
                await self._handle_step_button(query, "", context)
            elif callback_data.startswith("cal_"):
                await self._handle_calendar_navigation(query, callback_data, context)
            elif callback_data == "confirm_order":
                await self._handle_step_button(query, callback_data, context)
            elif callback_data.startswith(("cargo_", "route_", "weight_", "body_", "loading_", "unloading_", "places_")):
                # Обработка пошаговых кнопок
                await self._handle_step_button(query, callback_data, context)
            elif callback_data in ("name_confirm_ok", "name_confirm_edit"):
                if callback_data == "name_confirm_edit":
                    # Сброс введённого ФИО и запрос заново
                    order_data.pop('contact_name', None)
                    context.user_data['step_data'] = order_data
                    result = await self.ai_dispatcher.handle_step_by_step_order(
                        message="",
                        user_data={'order_data': order_data},
                        step='contacts'
                    )
                else:
                    # Имя подтверждено, переходим к финальному шагу
                    result = await self.ai_dispatcher.handle_step_by_step_order(
                        message="",
                        user_data={'order_data': order_data},
                        step='final'
                    )
                await self._send_step_response(query, result, context)
                return
            else:
                # Неизвестная кнопка
                await query.edit_message_text("Неизвестная команда. Попробуйте /start")
                
        except Exception as e:
            logger.error(f"Ошибка обработки кнопки {callback_data}: {str(e)}")
            await query.edit_message_text("Произошла ошибка. Попробуйте еще раз или начните сначала с /start")

    async def _handle_month_selection(self, query, callback_data: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора месяца"""
        
        today = datetime.now()
        
        if callback_data == "month_current":
            selected_month = today.month
            selected_year = today.year
            month_name = today.strftime('%B')
        else:  # month_next
            next_month_date = (today + timedelta(days=32)).replace(day=1)
            selected_month = next_month_date.month
            selected_year = next_month_date.year
            month_name = next_month_date.strftime('%B')
        
        # Сохраняем выбранный месяц в контексте
        context.user_data['selected_month'] = selected_month
        context.user_data['selected_year'] = selected_year
        
        message_text = (
            f"📅 Выбран месяц: {month_name} {selected_year}\n\n"
            f"Теперь укажите дату или диапазон дат:\n\n"
            f"Примеры:\n"
            f"• Для одной даты: 21\n"
            f"• Для диапазона: 21-27\n\n"
            f"Просто напишите цифры в следующем сообщении"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Выбрать другой месяц", callback_data="date_show_calendar")],
                            # Кнопка "Назад" убрана
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message_text, reply_markup=reply_markup)
        
        # Устанавливаем флаг ожидания ввода даты
        context.user_data['waiting_for_date_input'] = True

    async def _handle_new_order_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Новый заказ'"""
        # Очищаем данные предыдущего заказа
        context.user_data['step_data'] = {}
        context.user_data['current_step'] = 'start'
        
        # Начинаем с первого шага - выбор типа груза
        result = await self.ai_dispatcher.handle_step_by_step_order(
            message="",  # Пустое сообщение для начала
            user_data={'order_data': {}},
            step='start'
        )
        
        await self._send_step_response(query, result, context)

    async def _handle_new_order_callback_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка создания заказа из ИИ-сообщения"""
        
        # Очищаем данные предыдущего заказа
        context.user_data['step_data'] = {}
        context.user_data['current_step'] = 'start'
        
        # Начинаем с первого шага - выбор типа груза
        result = await self.ai_dispatcher.handle_step_by_step_order(
            message="",  # Пустое сообщение для начала
            user_data={'order_data': {}},
            step='start'
        )
        
        # Отправляем ответ как обычное сообщение
        await self._send_step_response_from_message(update, result, context)
    
    async def _show_main_menu_from_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ главного меню из ИИ-сообщения"""
        
        user = update.effective_user
        
        # Очищаем данные пошагового диалога
        context.user_data.clear()
        
        # Приветственное сообщение
        welcome_text = f"""🎯 Добро пожаловать{f', {user.first_name}' if user.first_name else ''}! 

🚛 ИИ-Диспетчер Логистики 2025 — ваш персональный помощник в организации грузоперевозок

✨ Что я делаю:
🔍 Нахожу лучших перевозчиков среди проверенных компаний
💰 Рассчитываю оптимальную стоимость доставки
🛡️ Обеспечиваю полное сопровождение сделки
📊 Контролирую выполнение заказа от А до Я

⚖️ Специализация: грузы от 200 кг
⏱️ Время поиска: обычно 15-30 минут
🌍 География: межгород по всей России (доставка по одному городу не выполняется)

💬 Как обращаться:
• Для заказа: "Нужно перевезти груз" или "Заказать перевозку"
• Для справки: "Помощь" или "Как это работает?"
• Для статуса: "Мои заказы" или "Где мой груз?"
• Для контактов: "Контакты" или "Как с вами связаться?"

Просто напишите что вам нужно!"""
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')

    async def _handle_my_orders_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Мои заказы'"""
        user_id = query.from_user.id
        
        # Проверяем активные заказы в базе данных
        try:
            from database.crud import get_orders_by_telegram_id
            
            active_orders = await get_orders_by_telegram_id(user_id)
            
            if active_orders:
                # Есть активные заказы
                orders_list = []
                for order in active_orders:
                    status_emoji = {
                        'pending': '⏳',
                        'searching': '🔍', 
                        'offers_found': '📋',
                        'completed': '✅',
                        'cancelled': '❌'
                    }.get(order.get('status', 'pending'), '⏳')
                    
                    status_text = {
                        'pending': 'Ожидает обработки',
                        'searching': 'Ищем перевозчиков',
                        'offers_found': 'Найдены предложения',
                        'completed': 'Завершен',
                        'cancelled': 'Отменен'
                    }.get(order.get('status', 'pending'), 'В обработке')
                    
                    order_info = f"""
{status_emoji} **Заказ #{order.get('id', 'N/A')}**
🚛 {order.get('from_city', 'N/A')} → {order.get('to_city', 'N/A')}
📦 {order.get('cargo_type', 'N/A')}, {order.get('weight', 'N/A')} кг
📅 {order.get('loading_date', order.get('loading_date_from', 'N/A'))}
📱 Статус: {status_text}"""
                    orders_list.append(order_info)
                
                orders_text = f"""📋 Ваши заказы

{''.join(orders_list)}

💬 Как только найдем подходящие предложения - сразу уведомлю!"""
            else:
                orders_text = """📋 Ваши заказы

У вас пока нет активных заказов.

📦 Для создания нового заказа нажмите "🚀 Новый заказ" или просто опишите что нужно перевезти."""
        
        except Exception as e:
            logger.error(f"Ошибка получения заказов в callback: {e}")
            orders_text = """📋 Ваши заказы

Не удалось загрузить информацию о заказах.

📦 Для создания нового заказа нажмите "🚀 Новый заказ"."""
        
        await query.edit_message_text(orders_text, parse_mode='Markdown')

    async def _handle_contact_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Контакты'"""
        contact_text = f"""📞 Контакты для связи

👨‍💼 **Диспетчер**: {settings.dispatcher_phone}
💬 **Telegram**: {settings.dispatcher_telegram}
📧 **Email**: {settings.dispatcher_email}

🕐 **Часы работы**: 24/7

⚡ **Срочные вопросы**: лучше звонить
💬 **Обычные вопросы**: пишите в чат"""
        
        await query.edit_message_text(contact_text)

    async def _handle_help_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Помощь'"""
        help_text = f"""📚 Помощь по работе с ИИ-Диспетчером 2025

🚀 **КАК ЗАКАЗАТЬ ПЕРЕВОЗКУ (МЕЖГОРОД):**
1️⃣ Нажмите "🚀 Новый заказ"
2️⃣ Выберите тип груза из списка
3️⃣ Укажите маршрут (откуда → куда)
4️⃣ Введите вес и объем/габариты
5️⃣ Выберите дату загрузки
6️⃣ Укажите тип кузова и способы погрузки
7️⃣ Оставьте контактные данные

💬 **ПРИМЕР БЫСТРОГО ЗАКАЗА (межгород):**
"Мебель из Сарапула в Ижевск, 500 кг, 2.5 куба, 25-28 числа"

🔍 **ПРОЦЕСС ПОИСКА (только межгород):**
• Автоматически размещаем груз среди проверенных перевозчиков
• Получаете уведомления о найденных вариантах
• Выбираете лучшее предложение прямо в боте
• Обычно поиск занимает 15-30 минут

💰 **ОПЛАТА:**
• Оплата только после загрузки груза
• Перевод на карту или наличными
• Безналичный расчет с НДС и без

📞 **ПОДДЕРЖКА 24/7:**
• Телефон: {settings.dispatcher_phone}
• Telegram: {settings.dispatcher_telegram}

❓ Есть вопросы? Просто напишите мне!"""
        
        await query.edit_message_text(help_text)

    async def _handle_main_menu_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки 'Главное меню' - возврат к стартовому экрану"""
        user = query.from_user
        
        # Очищаем данные пошагового диалога
        context.user_data.clear()
        
        # Приветственное сообщение как в start_command (без кнопок, только ИИ)
        welcome_text = f"""🎯 Добро пожаловать{f', {user.first_name}' if user.first_name else ''}! 

🚛 ИИ-Диспетчер Логистики 2025 — ваш персональный помощник в организации грузоперевозок

✨ Что я делаю:
🔍 Нахожу лучших перевозчиков среди проверенных компаний
💰 Рассчитываю оптимальную стоимость доставки
🛡️ Обеспечиваю полное сопровождение сделки
📊 Контролирую выполнение заказа от А до Я

⚖️ Специализация: грузы от 200 кг
⏱️ Время поиска: обычно 15-30 минут
🌍 География: межгород по всей России (доставка по одному городу не выполняется)

💬 Как обращаться:
• Для заказа: "Нужно перевезти груз" или "Заказать перевозку"
• Для справки: "Помощь" или "Как это работает?"
• Для статуса: "Мои заказы" или "Где мой груз?"
• Для контактов: "Контакты" или "Как с вами связаться?"

Просто напишите что вам нужно!"""
        
        # Кнопки главного меню (ЗАКОММЕНТИРОВАНО - заменено на ИИ)
        # keyboard = [
        #     [InlineKeyboardButton("🚀 Новый заказ", callback_data="new_order")],
        # ]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(welcome_text, parse_mode='Markdown')

    async def _handle_step_button(self, query, callback_data: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопок пошагового диалога"""
        
        # Правильно получаем данные заказа
        order_data = context.user_data.get('step_data', {})
        current_step = context.user_data.get('current_step', 'start')
        
        # Обрабатываем выбор пользователя и сразу сохраняем в order_data
        if callback_data.startswith('cargo_'):
            cargo_map = {
                'cargo_furniture': 'Мебель',
                'cargo_materials': 'Стройматериалы',
                'cargo_equipment': 'Оборудование', 
                'cargo_goods': 'Товары',
                'cargo_industrial': 'Промышленные товары',
                'cargo_other': 'Другой тип'
            }
            order_data['cargo_type'] = cargo_map.get(callback_data, callback_data.replace('cargo_', ''))
            processed_message = f"Тип груза: {order_data['cargo_type']}"
            
        elif callback_data.startswith('places_'):
            if callback_data == 'places_other':
                processed_message = "Количество мест: другое"
            else:
                places_map = {
                    'places_1': 1,
                    'places_2': 2,
                    'places_3': 3,
                    'places_4': 4
                }
                order_data['places_count'] = places_map.get(callback_data, 1)
                processed_message = f"Количество мест: {order_data['places_count']}"
        
        elif callback_data.startswith('volume_'):
            volume_value = callback_data.replace('volume_', '')
            try:
                order_data['volume'] = float(volume_value)
                processed_message = f"Объем: {order_data['volume']} м³"
                logger.info(f"✅ Установлен объем: {order_data['volume']} м³")
            except ValueError as e:
                logger.error(f"Ошибка парсинга объема '{volume_value}': {e}")
                order_data['volume'] = 1.0  # Устанавливаем значение по умолчанию
                processed_message = f"Объем: {order_data['volume']} м³"
                

        
        elif callback_data.startswith('route_'):
            route_map = {
                'route_msk_spb': ('Москва', 'Санкт-Петербург'),
                'route_spb_msk': ('Санкт-Петербург', 'Москва'),
                'route_msk_ekb': ('Москва', 'Екатеринбург'),
                'route_ekb_msk': ('Екатеринбург', 'Москва')
            }
            if callback_data in route_map:
                order_data['from_city'], order_data['to_city'] = route_map[callback_data]
                processed_message = f"Маршрут: {order_data['from_city']} → {order_data['to_city']}"
            else:
                processed_message = self._process_button_choice(callback_data, order_data)
                
        elif callback_data.startswith('weight_'):
            weight_map = {
                'weight_500': 500,
                'weight_1000': 1000, 
                'weight_2000': 2000,
                'weight_5000': 5000
            }
            order_data['weight'] = weight_map.get(callback_data, 500)
            processed_message = f"Вес: {order_data['weight']} кг"
            
        elif callback_data.startswith('date_'):
            
            if callback_data == 'date_show_calendar':
                # Показываем календарь
                await self._show_calendar(query, context)
                return
            elif callback_data.startswith('date_select_'):
                # Выбрана конкретная дата из календаря
                date_str = callback_data.replace('date_select_', '')
                
                # Проверяем режим выбора диапазона
                if context.user_data.get('date_range_mode'):
                    await self._handle_range_date_selection(query, date_str, context)
                    return
                else:
                    order_data['loading_date'] = date_str
                    order_data['loading_readiness_type'] = 'ready'
                    processed_message = f"Дата загрузки: {date_str}"
            elif callback_data.startswith('date_range_'):
                # Выбран диапазон дат
                range_str = callback_data.replace('date_range_', '')
                start_date, end_date = range_str.split('_')
                order_data['loading_date_from'] = start_date
                order_data['loading_date_to'] = end_date
                order_data['loading_readiness_type'] = 'interval'
                processed_message = f"Диапазон загрузки: {start_date} - {end_date}"
            else:
                processed_message = self._process_button_choice(callback_data, order_data)
                
        elif callback_data.startswith('body_'):
            body_map = {
                'body_tent': 'тентованный',
                'body_van': 'фургон',
                'body_platform': 'бортовой',
                'body_refrigerator': 'рефрижератор',
                'body_lowframe': 'низкорамный',
                'body_dump': 'самосвал',
                'body_isothermal': 'изотермический',
                'body_container': 'контейнеровоз'
            }
            order_data['body_type'] = body_map.get(callback_data, callback_data.replace('body_', ''))
            processed_message = f"Тип кузова: {order_data['body_type']}"
        
        elif callback_data.startswith('loading_'):
            loading_map = {
                'loading_top': 'верхняя',
                'loading_side': 'боковая',
                'loading_rear': 'задняя',
                'loading_full': 'с полной растентовкой',
                'loading_side2': 'боковая с 2-х сторон',
                'loading_pour': 'налив'
            }
            order_data['loading_method'] = loading_map.get(callback_data, callback_data.replace('loading_', ''))
            processed_message = f"Способ погрузки: {order_data['loading_method']}"
        
        elif callback_data.startswith('unloading_'):
            unloading_map = {
                'unloading_top': 'верхняя',
                'unloading_side': 'боковая',
                'unloading_rear': 'задняя', 
                'unloading_full': 'с полной растентовкой',
                'unloading_side2': 'боковая с 2-х сторон',
                'unloading_hydroboard': 'гидроборт'
            }
            order_data['unloading_method'] = unloading_map.get(callback_data, callback_data.replace('unloading_', ''))
            processed_message = f"Способ разгрузки: {order_data['unloading_method']}"
        
        elif callback_data == 'confirm_order':
            # Пользователь подтвердил заказ - размещаем на ATI
            logger.info(f"🚀 Пользователь {query.from_user.id} подтвердил заказ")
            await self._handle_order_confirmation(query, order_data, context)
            return
            
        elif callback_data == 'edit_order':
            # Пользователь хочет изменить данные - возвращаем к началу
            context.user_data['step_data'] = {}
            result = await self.ai_dispatcher.handle_step_by_step_order(
                message="Начать заказ заново",
                user_data={},
                step='start'
            )
            await self._send_step_response(query, result, context)
            return
            
        elif callback_data == 'cancel_order':
            # Отмена заказа (только в финальном подтверждении)
            await query.edit_message_text("❌ Заказ отменен. Если передумаете - просто напишите мне!")
            context.user_data['step_data'] = {}
            return
        
        else:
            # Для остальных кнопок используем старую логику
            processed_message = self._process_button_choice(callback_data, order_data)
        
        # Сохраняем обновленные данные заказа
        context.user_data['step_data'] = order_data
        
        # Получаем следующий шаг - передаем order_data напрямую как user_data
        result = await self.ai_dispatcher.handle_step_by_step_order(
            message=processed_message,
            user_data={'order_data': order_data},
            step=current_step
        )
        
        # Обновляем order_data из результата ИИ
        if result.get('order_data'):
            order_data.update(result['order_data'])
            context.user_data['step_data'] = order_data
        
        await self._send_step_response(query, result, context)

    def _process_button_choice(self, callback_data: str, order_data: Dict) -> str:
        """Обрабатывает выбор пользователя через кнопки"""
        
        # Маппинг кнопок на человекочитаемый текст
        button_map = {
            # Типы груза
            "cargo_furniture": "Мебель", 
            "cargo_materials": "Стройматериалы",
            "cargo_equipment": "Оборудование",
            "cargo_goods": "Товары",
            "cargo_industrial": "Промышленные товары", 
            "cargo_other": "Другой тип",
            
            # Количество мест
            "places_1": "1 место",
            "places_2": "2 места", 
            "places_3": "3 места",
            "places_4": "4 места",
            "places_other": "другое количество",
            

            
            # Маршруты
            "route_msk_spb": "Москва → СПб",
            "route_spb_msk": "СПб → Москва", 
            "route_msk_ekb": "Москва → Екатеринбург",
            "route_ekb_msk": "Екатеринбург → Москва",
            
            # Вес (только ≥200 кг)
            "weight_500": "500 кг",
            "weight_1000": "1 тонна",
            "weight_2000": "2 тонны", 
            "weight_5000": "5 тонн",
            
            # Даты
            "date_today": "сегодня",
            "date_tomorrow": "завтра",
            "date_day_after": "послезавтра",
            "date_next_week": "на следующей неделе",
            
            # Типы кузова
            "body_tent": "тентованный",
            "body_van": "фургон",
            "body_platform": "бортовой",
            "body_refrigerator": "рефрижератор",
            "body_lowframe": "низкорамный",
            "body_dump": "самосвал",
            "body_isothermal": "изотермический",
            "body_container": "контейнеровоз",
            
            # Методы загрузки/разгрузки
            "loading_top": "верхняя",
            "loading_side": "боковая",
            "loading_rear": "задняя",
            "loading_full": "с полной растентовкой",
            "loading_side2": "боковая с 2-х сторон",
            "loading_pour": "налив",
            "unloading_top": "верхняя",
            "unloading_side": "боковая",
            "unloading_rear": "задняя",
            "unloading_full": "с полной растентовкой",
            "unloading_side2": "боковая с 2-х сторон",
            "unloading_hydroboard": "гидроборт",
            
            # Типы упаковки
            "pack_pallets": "на поддонах",
            "pack_boxes": "в коробках",
            "pack_bags": "в мешках",
            "pack_loose": "навалом"
        }
        
        return button_map.get(callback_data, callback_data)

    async def _show_calendar(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Простой выбор месяца для загрузки груза"""
        
        today = datetime.now()
        current_month = today.strftime('%B %Y')
        next_month = (today + timedelta(days=32)).replace(day=1).strftime('%B %Y')
        
        keyboard = [
            [InlineKeyboardButton(f"📅 {current_month}", callback_data=f"month_current")],
            [InlineKeyboardButton(f"📅 {next_month}", callback_data=f"month_next")],
                            # Кнопка "Назад" убрана
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            f"📅 Готовность груза для загрузки\n\n"
            f"Выберите месяц, затем укажите конкретную дату или диапазон:\n\n"
            f"Примеры ввода:\n"
            f"• Одна дата: 21\n"
            f"• Диапазон: 21-27\n"
            f"• Несколько дней в разных месяцах: сначала выберите месяц, введите дату, затем выберите другой месяц"
        )
        
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup
        )

    async def _handle_calendar_navigation(self, query, callback_data: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка навигации по календарю"""
        
        if callback_data.startswith('cal_prev_'):
            # Переход к предыдущему месяцу
            parts = callback_data.split('_')
            month = int(parts[2])
            year = int(parts[3])
            context.user_data['calendar_month'] = month
            context.user_data['calendar_year'] = year
            await self._show_calendar(query, context)
            
        elif callback_data.startswith('cal_next_'):
            # Переход к следующему месяцу
            parts = callback_data.split('_')
            month = int(parts[2])
            year = int(parts[3])
            context.user_data['calendar_month'] = month
            context.user_data['calendar_year'] = year
            await self._show_calendar(query, context)

    

    async def _handle_range_date_selection(self, query, date_str: str, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора дат с задержкой"""
        from datetime import datetime
        import asyncio
        
        user_data = context.user_data.get('step_data', {})
        order_data = user_data.get('order_data', {})
        
        if not context.user_data.get('range_start_date'):
            # Первая дата
            context.user_data['range_start_date'] = date_str
            context.user_data['waiting_for_second_date'] = True
            
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d.%m.%Y')
            except:
                formatted_date = date_str
            
            await query.edit_message_text(
                f"📅 Выбор периода\n\n"
                f"✅ Первая дата: {formatted_date}\n"
                f"⏳ Ждем 3 секунды...\n"
                f"💡 Нажмите вторую дату или ждите",
                parse_mode='Markdown'
            )
            
            # Показываем календарь для выбора второй даты
            await asyncio.sleep(1)
            await self._show_calendar(query, context)
            
        else:
            # Выбираем вторую дату
            start_date_str = context.user_data['range_start_date']
            end_date_str = date_str
            
            # Проверяем правильность порядка дат
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if end_date < start_date:
                # Показываем ошибку и позволяем выбрать заново
                try:
                    start_formatted = datetime.strptime(start_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
                    end_formatted = datetime.strptime(end_date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
                except:
                    start_formatted = start_date_str
                    end_formatted = end_date_str
                
                await query.edit_message_text(
                    f"❌ **ОШИБКА В ДАТАХ**\n\n"
                    f"Вы выбрали:\n"
                    f"🗓️ Первая дата: {start_formatted}\n"
                    f"🗓️ Вторая дата: {end_formatted}\n\n"
                    f"⚠️ **Последняя дата не может быть раньше первой!**\n\n"
                    f"🔄 Выберите другую дату или начните заново",
                    parse_mode='Markdown'
                )
                
                # Показываем календарь снова
                await asyncio.sleep(2)
                await self._show_calendar(query, context)
                return
            
            # Сохраняем диапазон
            order_data['loading_date_from'] = start_date_str
            order_data['loading_date_to'] = end_date_str
            order_data['loading_readiness_type'] = 'interval'
            
            # Очищаем режим диапазона
            context.user_data['date_range_mode'] = False
            context.user_data['range_start_date'] = None
            context.user_data['range_end_date'] = None
            
            # Обновляем данные
            user_data['order_data'] = order_data
            context.user_data['step_data'] = user_data
            
            # Показываем подтверждение
            try:
                start_formatted = start_date.strftime('%d.%m.%Y')
                end_formatted = end_date.strftime('%d.%m.%Y')
                days_count = (end_date - start_date).days + 1
            except:
                start_formatted = start_date_str
                end_formatted = end_date_str
                days_count = "?"
            
            # Продолжаем пошаговый диалог
            result = await self.ai_dispatcher.handle_step_by_step_order(
                message=f"Диапазон загрузки: {start_formatted} - {end_formatted} ({days_count} дней)",
                user_data=user_data,
                step=user_data.get('current_step', 'date')
            )
            
            await self._send_step_response(query, result, context)

    async def _send_step_response(self, query, result: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Отправка ответа на шаг пошагового диалога"""
        
        try:
            # Сохраняем данные заказа и обновляем их
            step_data = context.user_data.get('step_data', {})
            order_data = result.get('order_data', {})
            
            # Объединяем существующие данные с новыми
            step_data.update(order_data)
            context.user_data['step_data'] = step_data
            
            status = result.get('status', 'needs_input')
            message = result.get('message', 'Продолжаем оформление заказа...')
            buttons = result.get('buttons', [])
            
            # Всегда показываем краткое превью текущих данных в начале сообщения
            preview = self._build_order_preview(step_data)
            if preview:
                message = f"{preview}\n\n{message}"
            
            # Если необходимо запросить контакт
            if result.get('contact_request'):
                contact_keyboard = ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
                await query.message.reply_text(message, reply_markup=contact_keyboard)
                return
            
            # Создаем клавиатуру с поддержкой горизонтального расположения
            keyboard = []
            if buttons:
                for button_row in buttons:
                    if isinstance(button_row, list):
                        # Горизонтальная строка кнопок
                        keyboard.append([InlineKeyboardButton(btn['text'], callback_data=btn['data']) for btn in button_row])
                    else:
                        # Одиночная кнопка (вертикально)
                        keyboard.append([InlineKeyboardButton(button_row['text'], callback_data=button_row['data'])])
            
            # Кнопки навигации убраны - пользователи лучше воспринимают простой интерфейс без отмены
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # Специальная обработка для разных статусов
            if status == 'weight_rejected':
                # Для отказа по весу - показываем новое сообщение
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup
                )
            elif status == 'ready_to_submit':
                # Финальное подтверждение
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                # Обычный шаг
                await query.edit_message_text(
                    message,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Ошибка отправки ответа: {str(e)}")
            if hasattr(query, 'edit_message_text'):
                await query.edit_message_text(
                    "Произошла ошибка. Попробуйте еще раз.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🚀 Начать заново", callback_data="new_order")
                    ]])
                )
            else:
                logger.error(f"query не поддерживает edit_message_text: {type(query)}")

    async def _send_step_response_from_message(self, update: Update, result: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Отправка ответа пошагового диалога из обычного сообщения"""
        try:
            # Сохраняем данные заказа и обновляем их
            step_data = context.user_data.get('step_data', {})
            order_data = result.get('order_data', {})
            
            # Объединяем существующие данные с новыми
            step_data.update(order_data)
            context.user_data['step_data'] = step_data
            
            status = result.get('status', 'needs_input')
            message = result.get('message', 'Продолжаем оформление заказа...')
            buttons = result.get('buttons', [])
            
            # Всегда показываем краткое превью текущих данных в начале сообщения
            preview = self._build_order_preview(step_data)
            if preview:
                message = f"{preview}\n\n{message}"
            
            # Если требуется запрос контакта – показываем кнопку и выходим
            if result.get('contact_request'):
                contact_keyboard = ReplyKeyboardMarkup(
                    [[KeyboardButton("📱 Поделиться номером", request_contact=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
                await update.message.reply_text(
                    message,
                    reply_markup=contact_keyboard
                )
                return

            # Создаем клавиатуру с поддержкой горизонтального расположения
            keyboard = []
            if buttons:
                for button_row in buttons:
                    if isinstance(button_row, list):
                        # Горизонтальная строка кнопок
                        keyboard.append([InlineKeyboardButton(btn['text'], callback_data=btn['data']) for btn in button_row])
                    else:
                        # Одиночная кнопка (вертикально)
                        keyboard.append([InlineKeyboardButton(button_row['text'], callback_data=button_row['data'])])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            # Отправляем новое сообщение вместо редактирования
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='Markdown' if status == 'ready_to_submit' else None
            )
                
        except Exception as e:
            logger.error(f"Ошибка отправки ответа из сообщения: {str(e)}")
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз или начните сначала с /start")

    def _build_order_preview(self, step_data: Dict) -> str:
        """Строит краткое превью заказа без звездочек"""
        
        preview_parts = []
        
        # Добавляем только заполненные поля
        if step_data.get('cargo_type'):
            preview_parts.append(f"📦 {step_data['cargo_type']}")
            
        if step_data.get('from_city') and step_data.get('to_city'):
            preview_parts.append(f"🚛 {step_data['from_city']} → {step_data['to_city']}")
        elif step_data.get('from_city'):
            preview_parts.append(f"🚛 Откуда: {step_data['from_city']}")
        elif step_data.get('to_city'):
            preview_parts.append(f"🚛 Куда: {step_data['to_city']}")
            
        if step_data.get('weight'):
            weight = step_data['weight']
            if weight >= 1000:
                preview_parts.append(f"⚖️ {weight/1000:.1f} т")
            else:
                preview_parts.append(f"⚖️ {weight} кг")
                
        if step_data.get('places_count'):
            preview_parts.append(f"📦 {step_data['places_count']} мест")
            
        if step_data.get('volume'):
            preview_parts.append(f"📏 {step_data['volume']} м³")
            
        if step_data.get('loading_date'):
            date_str = step_data['loading_date']
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d.%m')
                preview_parts.append(f"📅 {formatted_date}")
            except:
                preview_parts.append(f"📅 {date_str}")
                
        if step_data.get('body_type'):
            preview_parts.append(f"🚚 {step_data['body_type']}")
            
        if step_data.get('loading_method'):
            preview_parts.append(f"⬆️ {step_data['loading_method']}")
            
        if step_data.get('unloading_method'):
            preview_parts.append(f"⬇️ {step_data['unloading_method']}")
        
        if preview_parts:
            return "📋 " + " • ".join(preview_parts)
        else:
            return ""

    async def _handle_step_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обработка сообщения в пошаговом диалоге"""
        
        order_data = context.user_data.get('step_data', {})
        current_step = context.user_data.get('current_step', 'start')
        
        # Обрабатываем сообщение через пошаговый диалог
        result = await self.ai_dispatcher.handle_step_by_step_order(
            message=message_text,
            user_data={'order_data': order_data},
            step=current_step
        )
        
        # Отправляем ответ через обычное сообщение (не edit_message_text)
        # Формируем клавиатуру с поддержкой горизонтального расположения
        keyboard = []
        buttons = result.get('buttons', [])
        if buttons:
            for button_row in buttons:
                if isinstance(button_row, list):
                    # Горизонтальная строка кнопок
                    keyboard.append([InlineKeyboardButton(btn['text'], callback_data=btn['data']) for btn in button_row])
                else:
                    # Одиночная кнопка (вертикально)
                    keyboard.append([InlineKeyboardButton(button_row['text'], callback_data=button_row['data'])])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Отправляем новое сообщение
        await update.message.reply_text(
            result['message'], 
            reply_markup=reply_markup,
            parse_mode='Markdown' if '**' in result['message'] else None
        )
        
        # Сохраняем данные
        if 'order_data' in result:
            order_data.update(result['order_data'])
            context.user_data['step_data'] = order_data
            context.user_data['current_step'] = result.get('next_step', 'unknown')

    async def send_notification(self, telegram_id: int, message: str, reply_markup=None):
        """Отправка уведомления клиенту"""
        try:
            if self.app and self.app.bot:
                await self.app.bot.send_message(
                    chat_id=telegram_id, 
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"Уведомление отправлено клиенту {telegram_id}")
            else:
                logger.error("Бот не инициализирован для отправки уведомлений")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {str(e)}")
    
    async def notify_client_search_started(self, phone: str, order_data: Dict):
        """Уведомление клиента о начале поиска"""
        
        # Ищем клиента по телефону
        telegram_id = None
        for tid, client_info in self.client_orders.items():
            if client_info.get('phone') == phone:
                telegram_id = tid
                break
        
        if telegram_id:
            message = f"""✅ Отлично! Все данные получены.

🔍 Начинаем поиск наилучшего варианта перевозки среди проверенных перевозчиков.
⏱️ Обычно это занимает 15-30 минут.

📦 Ваш груз: {order_data.get('cargo_type', 'Не указан')}
🚛 Маршрут: {order_data.get('from_city', '')} → {order_data.get('to_city', '')}

Как только найдем лучшие предложения - сразу свяжемся с вами!"""
            
            await self.send_notification(telegram_id, message)
    
    async def notify_client_offer_found(self, phone: str, offer_data: Dict):
        """Уведомление клиента о найденном предложении"""
        
        # Ищем клиента по телефону
        telegram_id = None
        for tid, client_info in self.client_orders.items():
            if client_info.get('phone') == phone:
                telegram_id = tid
                break
        
        if telegram_id:
            # Создаем кнопки для ответа
            keyboard = [
                [InlineKeyboardButton("✅ Подтверждаю заказ", callback_data=f"confirm_order_{offer_data.get('offer_id')}")],
                [InlineKeyboardButton("❓ Есть вопросы", callback_data="ask_question")],
                [InlineKeyboardButton("📞 Связаться с диспетчером", callback_data="contact")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = offer_data.get('message', 'Найдено предложение по вашему грузу!')
            
            await self.send_notification(telegram_id, message, reply_markup)
    
    async def find_client_by_phone(self, phone: str) -> int:
        """Поиск Telegram ID клиента по номеру телефона"""
        
        for telegram_id, client_info in self.client_orders.items():
            if client_info.get('phone') == phone:
                return telegram_id
        return None
    
    async def _handle_order_confirmation(self, query, order_data: Dict, context: ContextTypes.DEFAULT_TYPE):
        """Обработка подтверждения заказа - размещение на ATI"""
        
        try:
            user_id = query.from_user.id
            
            # Сначала показываем что заказ принят
            await query.edit_message_text("""
🚀   Отлично! Заказ принят!

🔍 Размещаем ваш груз среди проверенных перевозчиков...
⏱️ Это займет несколько минут.

📱 Как только найдем подходящие варианты - сразу уведомлю в этом чате!

✅ Статус: В обработке
""")
            
            # Извлекаем и дополняем данные для ATI
            enhanced_order_data = await self._prepare_order_for_ati(order_data, user_id)
            
            logger.info(f"📦 Подготовленные данные заказа: {enhanced_order_data}")
            
            # Размещаем заказ напрямую через АТИ (минуя старую логику process_client_order)
            result = await self.ai_dispatcher._place_order_on_ati(enhanced_order_data)
            
            if result.get('success'):
                # Успешно размещен
                logger.info(f"✅ Заказ пользователя {user_id} успешно размещен на ATI")
                
                # Сохраняем в память активных заказов
                self.client_orders[user_id] = {
                    'order_id': result.get('order_id'),
                    'cargo_id': result.get('cargo_id'),
                    'phone': enhanced_order_data.get('contact_phone'),
                    'name': enhanced_order_data.get('contact_name'),
                    'created_at': datetime.now().isoformat()
                }
                
                # Обновляем сообщение с успехом
                success_message = f"""
✅ Заказ успешно размещен!

🆔 ID заказа: {result.get('order_id', 'N/A')}
📦 Груз: {enhanced_order_data.get('cargo_type')}
🚛 Маршрут: {enhanced_order_data.get('from_city')} → {enhanced_order_data.get('to_city')}

🔍 Что происходит дальше:
1. Ищем лучшие предложения от перевозчиков
2. Анализируем надежность и цены
3. Отправляем вам ТОП-3 варианта

⏱️ Время поиска: обычно 15-30 минут
📱 Уведомления: придут в этот чат

💰 Оплата: частичная предоплата

💬 Для возврата к началу напишите "Главное меню"
📋 Для статуса заказов напишите "Мои заказы"
📞 Для контактов напишите "Контакты"
"""
                
                # Кнопки после успешного заказа (ЗАКОММЕНТИРОВАНО - заменено на ИИ)
                # keyboard = [
                #     [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
                #     [InlineKeyboardButton("📋 Мои заказы", callback_data="my_orders"),
                #      InlineKeyboardButton("📞 Контакты", callback_data="contact")]
                # ]
                # reply_markup = InlineKeyboardMarkup(keyboard)
                # await query.edit_message_text(success_message, reply_markup=reply_markup)
                
                await query.edit_message_text(success_message)
                
            else:
                # Ошибка размещения
                error_msg = result.get('error', 'Неизвестная ошибка')
                logger.error(f"❌ Ошибка размещения заказа пользователя {user_id}: {error_msg}")
                
                # Получаем username для отчета владельцу
                username = query.effective_user.username if query.effective_user else "неизвестен"
                
                # Не упоминаем ATI в сообщениях пользователю
                user_error_message = "❌ **Временные неполадки с размещением заказа**\n\n" \
                                    "Пожалуйста, попробуйте снова через несколько минут или обратитесь к нашему диспетчеру:\n" \
                                    "📞 +7 (499) 112-13-14"
                
                await self.send_notification(
                    user_id,
                    user_error_message,
                    reply_markup=None  # Убираем клавиатуру для упрощения
                )
                
                # Уведомляем владельца о технической ошибке
                owner_message = f"""
🚨 **ТЕХНИЧЕСКАЯ ОШИБКА РАЗМЕЩЕНИЯ ЗАКАЗА**

👤 **Клиент:** {user_id} (@{username})
📦 **Данные заказа:** {order_data}
❌ **Ошибка:** {error_msg}

⚠️ Клиент получил сообщение о временных неполадках.
🔧 Требуется проверка системы размещения заказов.
"""
                
                try:
                    from bot.client_bot import send_telegram_message
                    await send_telegram_message(408001372, owner_message)
                except:
                    logger.error("Не удалось отправить уведомление владельцу о технической ошибке")
            
            # Очищаем данные шагов
            context.user_data['step_data'] = {}
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка подтверждения заказа: {e}")
            await query.message.reply_text("""
❌ Произошла техническая ошибка

Мы уже работаем над ее устранением.
Пожалуйста, попробуйте создать заказ заново или свяжитесь с диспетчером.

📞 https://t.me/kroVik
""")

    async def _prepare_order_for_ati(self, order_data: Dict, user_id: int) -> Dict:
        """Подготовка данных заказа для размещения на ATI"""
        
        # Базовые данные из пошагового диалога
        enhanced_data = {
            'cargo_type': order_data.get('cargo_type', 'Груз'),
            'from_city': order_data.get('from_city'),
            'to_city': order_data.get('to_city'),
            'weight': order_data.get('weight', 0),
            'volume': order_data.get('volume', 0),
            'places_count': order_data.get('places_count', 1),
            'body_type': order_data.get('body_type', 'тентованный'),
            'loading_method': order_data.get('loading_method', 'вручную'),
            'unloading_method': order_data.get('unloading_method', 'вручную'),
            'contact_name': order_data.get('contact_name', 'Клиент'),
            'contact_phone': order_data.get('contact_phone'),
            'telegram_id': user_id,
            'source': 'telegram_bot'
        }
        
        # Обрабатываем даты
        if order_data.get('loading_date'):
            enhanced_data['loading_date'] = order_data['loading_date']
            enhanced_data['loading_readiness_type'] = 'ready'
        elif order_data.get('loading_date_from') and order_data.get('loading_date_to'):
            enhanced_data['loading_date_from'] = order_data['loading_date_from']
            enhanced_data['loading_date_to'] = order_data['loading_date_to']
            enhanced_data['loading_readiness_type'] = 'interval'
        else:
            # По умолчанию - завтра
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            enhanced_data['loading_date'] = tomorrow
            enhanced_data['loading_readiness_type'] = 'ready'
        
        # Если нет объема - рассчитываем примерно
        if not enhanced_data.get('volume') and enhanced_data.get('weight'):
            # Примерный расчет объема по весу и типу груза
            weight = enhanced_data['weight']
            cargo_type = enhanced_data['cargo_type'].lower()
            
            if 'мебель' in cargo_type:
                enhanced_data['volume'] = weight * 0.002  # 500 кг/м³
            elif 'стройматериалы' in cargo_type:
                enhanced_data['volume'] = weight * 0.001  # 1000 кг/м³
            else:
                enhanced_data['volume'] = weight * 0.0015  # 650 кг/м³ среднее
        
        # Адреса (если есть)
        if order_data.get('loading_address'):
            enhanced_data['loading_address'] = order_data['loading_address']
        if order_data.get('unloading_address'):
            enhanced_data['unloading_address'] = order_data['unloading_address']
        
        return enhanced_data

    async def stop_bot(self):
        """Остановка бота"""
        try:
            if hasattr(self, 'bot_task'):
                self.bot_task.cancel()
            if self.app:
                await self.app.stop()
            logger.info("🛑 Telegram бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки бота: {str(e)}")


    async def _is_response_to_ai_offer(self, telegram_id: int, message_text: str) -> bool:
        """Проверяем, является ли сообщение ответом на предложение ИИ-продажника"""
        try:
            from database.crud import get_monitoring_session_by_telegram_id
            
            # Ищем активную сессию мониторинга для этого клиента
            session = await get_monitoring_session_by_telegram_id(telegram_id)
            
            if session and session.get("status") in ["offer_sent", "in_dialog"]:
                logger.info(f"🎯 Обнаружен ответ на ИИ-предложение от {telegram_id}: {message_text[:30]}...")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки ответа на ИИ-предложение: {e}")
            return False

    async def _handle_manual_mode_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """Обработка сообщения в ручном режиме - перенаправление владельцу"""
        
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or update.effective_user.first_name
            
            # Получаем сессию мониторинга для контекста
            from database.crud import get_monitoring_session_by_telegram_id, update_monitoring_session_by_id
            session = await get_monitoring_session_by_telegram_id(user_id)
            
            if not session:
                logger.error(f"Сессия не найдена для клиента в ручном режиме: {user_id}")
                await update.message.reply_text("Произошла ошибка. Обратитесь к @KroVik")
                return
            
            # Получаем данные о грузе для контекста
            order_data = session.get("cargo_data", {})
            
            # Отправляем клиенту подтверждение
            await update.message.reply_text(
                "✅ Ваше сообщение передано руководителю.\n"
                "Он ответит в ближайшее время."
            )
            
            # Уведомляем владельца о новом сообщении
            owner_message = f"""💬 НОВОЕ СООБЩЕНИЕ В РУЧНОМ РЕЖИМЕ

👤 КЛИЕНТ: @{username} (ID: {user_id})
📦 ГРУЗ: {order_data.get('cargo_type', 'N/A')} 
🚛 МАРШРУТ: {order_data.get('from_city', 'N/A')} → {order_data.get('to_city', 'N/A')}

💬 СООБЩЕНИЕ:
"{message_text}"

⚡ БЫСТРЫЕ ДЕЙСТВИЯ:
/reply_{session.get('id')} [текст] - Ответить клиенту
/auto_{session.get('id')} - Вернуть ИИ управление

📋 ID сессии: {session.get('id')}"""

            await send_telegram_message(408001372, owner_message)
            
            # Обновляем время последнего сообщения
            await update_monitoring_session_by_id(session["id"], {
                "client_response": message_text,
                "pending_owner_response": True,
                "last_interaction_at": datetime.now().isoformat()
            })
            
            logger.info(f"📤 Сообщение в ручном режиме от {user_id} передано владельцу")
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения в ручном режиме: {e}")
            await update.message.reply_text(
                "Произошла ошибка. Обратитесь напрямую к @KroVik"
            )

    async def _handle_ai_sales_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
        """УЛУЧШЕННАЯ обработка ответа клиента на предложение ИИ-продажника с многоходовой логикой"""
        try:
            user_id = update.effective_user.id
            
            # Получаем сессию мониторинга
            from database.crud import get_monitoring_session_by_telegram_id, update_monitoring_session_by_id
            session = await get_monitoring_session_by_telegram_id(user_id)
            
            if not session:
                await update.message.reply_text("Сессия не найдена. Обратитесь к @KroVik")
                return
            
            # Получаем данные из сессии
            order_data = session.get("cargo_data", {})
            pricing = session.get("pricing_data", {})
            best_offer = session.get("best_offer_data", {})
            
            # НОВОЕ: Подготавливаем session_data для многоходовой логики
            session_data = {
                "objection_attempts": session.get("objection_attempts", 0),
                "objection_type": session.get("objection_type"),
                "last_price_discount": session.get("last_price_discount", 0.0),
                "margin_threshold_reached": session.get("margin_threshold_reached", False),
                "sales_technique_used": session.get("sales_technique_used", "standard")
            }
            
            logger.info(f"🎯 Обработка ответа клиента {user_id}, попытка #{session_data['objection_attempts'] + 1}")
            
            # Обрабатываем ответ через УЛУЧШЕННОГО ИИ-продажника
            from ai_services.sales_agent import SalesAgent
            sales_agent = SalesAgent()
            
            response_result = await sales_agent.handle_client_response_to_offer(
                client_message=message_text,
                order_data=order_data,
                pricing=pricing,
                session_data=session_data  # НОВЫЙ параметр!
            )
            
            # Отправляем ответ клиенту
            await update.message.reply_text(response_result["response_message"])
            
            # НОВОЕ: Обновляем данные многоходовой логики в БД
            session_update_data = {
                "client_response": message_text,
                "last_interaction_at": datetime.now().isoformat()
            }
            
            # Обновляем поля умного ИИ-продажника если они есть в результате
            if "objection_attempts" in response_result:
                session_update_data["objection_attempts"] = response_result["objection_attempts"]
                
            if "objection_type" in response_result:
                session_update_data["objection_type"] = response_result["objection_type"]
                
            if "updated_pricing" in response_result:
                session_update_data["pricing_data"] = response_result["updated_pricing"]
                session_update_data["last_price_discount"] = response_result["updated_pricing"].get("discount_applied", 0.0)
                
            if "price_flexibility" in response_result:
                if response_result["price_flexibility"].get("min_margin_reached"):
                    session_update_data["margin_threshold_reached"] = True
                    
            if "sales_technique_used" in response_result:
                session_update_data["sales_technique_used"] = response_result["sales_technique_used"]
            
            # Если клиент согласился - уведомляем владельца
            if response_result.get("should_notify_owner", False) and response_result.get("deal_status") == "success":
                await sales_agent.notify_owner_about_successful_sale(
                    order_data=order_data,
                    best_offer=best_offer,
                    pricing=response_result.get("updated_pricing", pricing),
                    owner_telegram_id=408001372  # ID владельца
                )
                
                # Обновляем статус сессии
                session_update_data.update({
                    "status": "deal_closed",
                    "deal_closed_at": datetime.now().isoformat()
                })
                
                # Сохраняем комиссию
                from database.crud import create_commission
                await create_commission({
                    "order_id": order_data.get("id"),
                    "carrier_price": int(best_offer.get("Price", 0)),
                    "commission_percent": pricing.get("markup_percent", 40),
                    "commission_amount": int(pricing.get("profit", 0)),
                    "total_price": int(pricing.get("client_price", 0)),
                    "status": "confirmed"
                })
                
                logger.info(f"🎉 Сделка закрыта! Клиент {user_id} согласился на предложение")
                
            # Если клиент отказался - записываем неудачную сделку
            elif response_result.get("should_close_deal", False) and response_result.get("deal_status") == "failed":
                await sales_agent.record_failed_deal(
                    order_data=order_data,
                    best_offer=best_offer,
                    pricing=response_result.get("updated_pricing", pricing),
                    failure_reason=response_result.get("failure_reason", "client_rejected"),
                    failure_details=f"Клиент отказался: {message_text}"
                )
                
                # Уведомляем владельца краткой сводкой о неудачной сделке
                await sales_agent.notify_owner_about_failed_deal(
                    order_data=order_data,
                    best_offer=best_offer,
                    pricing=response_result.get("updated_pricing", pricing),
                    failure_reason=response_result.get("failure_reason", "client_rejected"),
                    owner_telegram_id=408001372
                )
                
                # Завершаем сессию мониторинга
                session_update_data.update({
                    "status": "deal_failed",
                    "deal_closed_at": datetime.now().isoformat()
                })
                
                logger.info(f"❌ Сделка провалена. Клиент {user_id} отказался: {message_text}")
                
            # НОВАЯ ЛОГИКА: Проверяем нужно ли переключиться в ручной режим
            elif response_result.get("switch_to_manual", False):
                # Переключаемся в ручной режим через dialog_manager
                from ai_services.dialog_manager import dialog_manager
                
                switch_success = await dialog_manager.switch_to_manual_mode(
                    client_telegram_id=user_id,
                    reason=response_result.get("switch_reason", "unknown"),
                    analysis_data=response_result.get("analysis", {}),
                    auto_message=response_result["response_message"]
                )
                
                if switch_success:
                    logger.info(f"🔄 Диалог {user_id} переключен в ручной режим по причине: {response_result.get('switch_reason')}")
                    
                    # Обновляем статус сессии (dialog_manager уже обновил режим)
                    session_update_data.update({
                        "status": "manual_mode",
                        "auto_switch_reason": response_result.get("switch_reason", "unknown")
                    })
                else:
                    logger.error(f"❌ Ошибка переключения в ручной режим для {user_id}")
                    
            # Если нужно вмешательство человека (старая логика для совместимости)
            elif response_result["needs_human_intervention"]:
                # Уведомляем владельца о необходимости вмешательства
                owner_message = f"""⚠️ ТРЕБУЕТСЯ ВМЕШАТЕЛЬСТВО

📦 Груз: {order_data.get('cargo_type', 'N/A')}
🚛 Маршрут: {order_data.get('from_city', 'N/A')} → {order_data.get('to_city', 'N/A')}
👤 Клиент: @{update.effective_user.username or update.effective_user.first_name}

💬 Сообщение клиента: "{message_text}"

🤖 Анализ ИИ: {response_result["analysis"].get("intent", "неясно")}
📊 Тип возражения: {response_result["analysis"].get("objection_type", "не определен")}

Свяжитесь с клиентом для решения вопроса."""

                from bot.client_bot import send_telegram_message
                await send_telegram_message(408001372, owner_message)
                
                # Обновляем статус сессии
                await update_monitoring_session_by_id(session["id"], {
                    "status": "needs_human",
                    "client_response": message_text,
                    "human_intervention_requested_at": datetime.now().isoformat()
                })
                
            else:
                # Обычный диалог продолжается
                session_update_data.update({
                    "status": "in_dialog"  # Меняем статус на активный диалог
                })
                
                logger.info(f"💬 Диалог с клиентом {user_id} продолжается, попыток возражений: {session_update_data.get('objection_attempts', 0)}")
            
            # ВАЖНО: Применяем все изменения в БД одним запросом
            await update_monitoring_session_by_id(session["id"], session_update_data)
                
        except Exception as e:
            logger.error(f"Ошибка обработки ответа на ИИ-предложение: {e}")
            await update.message.reply_text(
                "Произошла ошибка. Передаю ваш запрос руководителю @KroVik"
            )


# Создаем глобальный экземпляр бота
client_bot = ClientBot() 

