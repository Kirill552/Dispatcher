"""
Мониторинг Telegram каналов логистики для поиска заказов
"""
import asyncio
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from utils.config import settings
from utils.logger import get_logger
from ai_services.sales_agent import sales_agent

logger = get_logger("TELEGRAM_MONITOR")


class TelegramLogisticsMonitor:
    """Мониторинг Telegram каналов с грузами"""
    
    def __init__(self):
        # Для работы с Telegram API нужны отдельные токены
        self.api_id = settings.telegram_api_id  # Добавить в конфиг
        self.api_hash = settings.telegram_api_hash  # Добавить в конфиг
        self.phone = settings.telegram_phone  # Добавить в конфиг
        
        self.client = None
        self.monitored_channels = [
            # Популярные каналы логистики
            "gruzoperevozki_rf",
            "atilogistics", 
            "cargo_exchange",
            "truckers_russia",
            "logistics_channel",
            "gruz_transport"
        ]
        
        # Паттерны для поиска грузов
        self.cargo_patterns = [
            r'(?i)(груз|перевоз|доставк)\s+.+?(\d+\s*тонн?|\d+\s*кг)',
            r'(?i)(москва|спб|питер|екатеринбург|новосибирск).+?(\d{4,6})\s*руб',
            r'(?i)требуется\s+(автомобиль|транспорт|машина)',
            r'(?i)ищем\s+(перевозчика|водителя|транспорт)'
        ]
        
        self.price_pattern = r'(\d{1,3}(?:\s*\d{3})*)\s*руб'
        self.route_pattern = r'([А-Яа-я\-]+)\s*[-–—]\s*([А-Яа-я\-]+)'
        
    async def start_monitoring(self):
        """Запуск мониторинга Telegram каналов"""
        
        try:
            logger.info("🚀 Запуск мониторинга Telegram каналов")
            
            # Инициализация клиента
            self.client = TelegramClient('session_name', self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            
            # Регистрируем обработчик новых сообщений
            @self.client.on(events.NewMessage)
            async def handle_new_message(event):
                await self._process_channel_message(event)
            
            # Подписываемся на каналы
            await self._subscribe_to_channels()
            
            logger.info("✅ Мониторинг Telegram каналов запущен")
            
            # Держим клиент активным
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга Telegram: {str(e)}")
            raise
    
    async def _subscribe_to_channels(self):
        """Подписка на каналы логистики"""
        
        for channel in self.monitored_channels:
            try:
                # Пытаемся присоединиться к каналу
                await self.client(JoinChannelRequest(channel))
                logger.info(f"✅ Подписка на канал @{channel}")
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось подписаться на @{channel}: {str(e)}")
    
    async def _process_channel_message(self, event):
        """Обработка сообщения из канала"""
        
        try:
            message_text = event.message.message
            channel_name = event.chat.username if event.chat.username else "unknown"
            
            # Фильтруем только релевантные сообщения
            if not self._is_cargo_message(message_text):
                return
            
            logger.info(f"📦 Найдено потенциальное объявление о грузе в @{channel_name}")
            
            # Извлекаем информацию о грузе
            cargo_info = self._extract_cargo_info(message_text, channel_name)
            
            if cargo_info and cargo_info.get('price', 0) >= settings.min_order_amount:
                # Анализируем качество лида
                lead_analysis = await sales_agent.analyze_lead_quality(cargo_info)
                
                if lead_analysis.get('priority') in ['высокий', 'средний']:
                    # Генерируем и отправляем отклик
                    await self._send_telegram_response(event, cargo_info)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {str(e)}")
    
    def _is_cargo_message(self, text: str) -> bool:
        """Проверка, содержит ли сообщение информацию о грузе"""
        
        if not text:
            return False
        
        # Ищем паттерны грузов
        for pattern in self.cargo_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _extract_cargo_info(self, text: str, channel: str) -> Dict:
        """Извлечение информации о грузе из текста"""
        
        cargo_info = {
            'source': f'telegram:@{channel}',
            'raw_text': text,
            'found_at': datetime.now()
        }
        
        # Извлекаем цену
        price_match = re.search(self.price_pattern, text)
        if price_match:
            price_str = price_match.group(1).replace(' ', '')
            cargo_info['price'] = int(price_str)
        
        # Извлекаем маршрут
        route_match = re.search(self.route_pattern, text)
        if route_match:
            cargo_info['route'] = f"{route_match.group(1)} - {route_match.group(2)}"
        
        # Ищем контактную информацию
        contact_info = self._extract_contact_info(text)
        cargo_info['contact_info'] = contact_info
        
        # Определяем тип груза
        cargo_info['cargo_type'] = self._determine_cargo_type(text)
        
        return cargo_info
    
    def _extract_contact_info(self, text: str) -> Dict:
        """Извлечение контактной информации"""
        
        contact_info = {}
        
        # Ищем телефон
        phone_pattern = r'[\+]?[7-8][\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            contact_info['phone'] = phone_match.group(0)
        
        # Ищем имя
        name_pattern = r'(?i)(звонить|обращаться)\s+([А-Яа-я]+(?:\s+[А-Яа-я]+)?)'
        name_match = re.search(name_pattern, text)
        if name_match:
            contact_info['name'] = name_match.group(2)
        
        return contact_info
    
    def _determine_cargo_type(self, text: str) -> str:
        """Определение типа груза по тексту"""
        
        cargo_types = {
            'мебель': ['мебель', 'диван', 'кровать', 'шкаф'],
            'стройматериалы': ['кирпич', 'цемент', 'плитка', 'доска'],
            'продукты': ['продукт', 'овощи', 'фрукты', 'мясо'],
            'техника': ['техника', 'компьютер', 'холодильник', 'стиральная'],
            'документы': ['документы', 'бумаги', 'договор']
        }
        
        text_lower = text.lower()
        
        for cargo_type, keywords in cargo_types.items():
            if any(keyword in text_lower for keyword in keywords):
                return cargo_type
        
        return 'общий груз'
    
    async def _send_telegram_response(self, event, cargo_info: Dict):
        """Отправка отклика в Telegram"""
        
        try:
            # Генерируем персональное предложение
            target_info = {
                'name': cargo_info.get('contact_info', {}).get('name', 'коллега'),
                'cargo_type': cargo_info.get('cargo_type', 'груз'),
                'route': cargo_info.get('route', 'маршрут'),
                'budget': cargo_info.get('price', 0)
            }
            
            response_text = await sales_agent.generate_cold_outreach(
                target_info=target_info,
                platform='telegram'
            )
            
            # Отправляем ответ в канал или в личные сообщения
            await event.reply(response_text)
            
            logger.info(f"💬 Отправлен отклик на груз: {cargo_info.get('route', 'неизвестный маршрут')}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки отклика: {str(e)}")
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        
        if self.client:
            await self.client.disconnect()
            logger.info("🛑 Мониторинг Telegram каналов остановлен")


class TelegramChannelParser:
    """Парсер для ручного анализа истории каналов"""
    
    def __init__(self, api_id: str, api_hash: str, phone: str):
        self.client = TelegramClient('parser_session', api_id, api_hash)
        self.phone = phone
    
    async def parse_channel_history(self, channel_username: str, days_back: int = 7) -> List[Dict]:
        """Парсинг истории канала за последние дни"""
        
        try:
            await self.client.start(phone=self.phone)
            
            # Получаем канал
            channel = await self.client.get_entity(channel_username)
            
            # Определяем дату начала
            start_date = datetime.now() - timedelta(days=days_back)
            
            # Получаем сообщения
            messages = []
            async for message in self.client.iter_messages(channel, offset_date=start_date):
                if message.message:
                    messages.append({
                        'text': message.message,
                        'date': message.date,
                        'id': message.id
                    })
            
            # Фильтруем релевантные сообщения
            cargo_messages = []
            monitor = TelegramLogisticsMonitor()
            
            for msg in messages:
                if monitor._is_cargo_message(msg['text']):
                    cargo_info = monitor._extract_cargo_info(msg['text'], channel_username)
                    cargo_info.update(msg)
                    cargo_messages.append(cargo_info)
            
            logger.info(f"📊 Найдено {len(cargo_messages)} сообщений о грузах в @{channel_username}")
            
            return cargo_messages
            
        except Exception as e:
            logger.error(f"Ошибка парсинга канала: {str(e)}")
            return []
        
        finally:
            await self.client.disconnect()


# Глобальные экземпляры
telegram_monitor = TelegramLogisticsMonitor() 