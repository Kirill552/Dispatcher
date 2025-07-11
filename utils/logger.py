"""
Система логирования для ИИ-диспетчера
"""
import os
import sys
import re
from loguru import logger
from utils.config import settings


def secure_scrubber(record):
    """
    🛡️ SECURITY SCRUBBER - очищает чувствительную информацию из логов
    Предотвращает утечку API ключей, токенов и паролей
    """
    message = record["message"]
    
    # Список паттернов для очистки
    sensitive_patterns = [
        # API ключи различных форматов
        (r'api_key[\s=:]+[\w\-]+', 'api_key=***'),
        (r'apikey[\s=:]+[\w\-]+', 'apikey=***'),
        (r'api-key[\s=:]+[\w\-]+', 'api-key=***'),
        
        # OpenAI ключи  
        (r'sk-[A-Za-z0-9]{48,}', 'sk-***'),
        (r'openai[_\-]?key[\s=:]+[\w\-]+', 'openai_key=***'),
        
        # ATI токены
        (r'ati[_\-]?token[\s=:]+[\w\-]+', 'ati_token=***'),
        (r'ati[_\-]?api[_\-]?key[\s=:]+[\w\-]+', 'ati_api_key=***'),
        
        # Telegram токены
        (r'telegram[_\-]?token[\s=:]+[\w\-:]+', 'telegram_token=***'),
        (r'bot[_\-]?token[\s=:]+[\w\-:]+', 'bot_token=***'),
        (r'\d{8,10}:[A-Za-z0-9_\-]{35}', '***:***'),  # Telegram bot token format
        
        # Общие токены и ключи
        (r'token[\s=:]+[\w\-]+', 'token=***'),
        (r'bearer[\s]+[\w\-\.]+', 'bearer ***'),
        (r'authorization[\s=:]+[\w\s\-\.]+', 'authorization=***'),
        
        # Пароли
        (r'password[\s=:]+[\w\-]+', 'password=***'),
        (r'passwd[\s=:]+[\w\-]+', 'passwd=***'),
        
        # Приватные ключи
        (r'-----BEGIN.*?PRIVATE.*?KEY-----.*?-----END.*?PRIVATE.*?KEY-----', '-----BEGIN PRIVATE KEY-----***-----END PRIVATE KEY-----'),
        
        # Номера телефонов (частично)
        (r'\+7\d{10}', '+7**********'),
        (r'8\d{10}', '8**********'),
    ]
    
    # Применяем все паттерны
    for pattern, replacement in sensitive_patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE | re.DOTALL)
    
    # Обновляем сообщение в записи
    record["message"] = message
    
    return True


def setup_logger():
    """Настройка системы логирования"""
    
    # Создаем директорию для логов если не существует
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Консольный вывод (с security scrubber)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=settings.log_level,
        colorize=True,
        filter=secure_scrubber  # 🛡️ Применяем security scrubber
    )
    
    # Файловый лог (с security scrubber)
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.log_level,
        rotation="100 MB",
        retention="30 days",
        compression="zip",
        filter=secure_scrubber  # 🛡️ Применяем security scrubber
    )
    
    # Отдельный файл для ошибок (с security scrubber)
    logger.add(
        settings.log_file.replace('.log', '_errors.log'),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="50 MB",
        retention="90 days",
        compression="zip",
        filter=secure_scrubber  # 🛡️ Применяем security scrubber
    )
    
    return logger


# Инициализируем логгер
setup_logger()


def get_logger(name: str = None):
    """Получить экземпляр логгера"""
    if name:
        return logger.bind(name=name)
    return logger


# Специализированные логгеры для разных компонентов
ati_logger = get_logger("ATI_API")
bot_logger = get_logger("TELEGRAM_BOT") 
ai_logger = get_logger("AI_SERVICE")
db_logger = get_logger("DATABASE")
monitor_logger = get_logger("MONITORING") 