"""
Конфигурация приложения ИИ-диспетчера
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения"""
    
    model_config = {"extra": "allow", "env_file": ".env", "env_file_encoding": "utf-8"}
    
    # ATI.SU API
    ati_api_token: str = Field("test_ati_token", env="ATI_API_TOKEN")
    ati_api_url: str = Field("https://api.ati.su/v1.0", env="ATI_API_URL")
    ati_api_timeout: int = Field(30, env="ATI_API_TIMEOUT")
    
    # Telegram Bot
    telegram_bot_token: str = Field("test_telegram_token", env="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field("ai_dispatcherBot", env="TELEGRAM_BOT_USERNAME")
    telegram_webhook_url: Optional[str] = Field(None, env="TELEGRAM_WEBHOOK_URL")
    
    # Telegram API (для мониторинга каналов)
    telegram_api_id: Optional[str] = Field(None, env="TELEGRAM_API_ID")
    telegram_api_hash: Optional[str] = Field(None, env="TELEGRAM_API_HASH")
    telegram_phone: Optional[str] = Field(None, env="TELEGRAM_PHONE")
    
    # AI Services - НОВАЯ ГИБКАЯ СИСТЕМА МОДЕЛЕЙ
    openai_api_key: str = Field("test_openai_key", env="OPENAI_API_KEY")
    
    # Основная модель (для совместимости со старым кодом)
    openai_model: str = Field("gpt-4.1-mini-2025-04-14", env="OPENAI_MODEL")
    
    # СПЕЦИАЛИЗИРОВАННЫЕ МОДЕЛИ ПО ЗАДАЧАМ
    # ИИ-продажник (сложная логика, работа с возражениями)
    ai_sales_model: str = Field("o4-mini", env="AI_SALES_MODEL")
    
    # Простые задачи (извлечение данных, валидация)
    ai_simple_model: str = Field("gpt-4.1-mini-2025-04-14", env="AI_SIMPLE_MODEL")
    
    # Анализ данных и диалогов
    ai_analysis_model: str = Field("gpt-4.1-mini-2025-04-14", env="AI_ANALYSIS_MODEL")
    
    # Генерация текстов (уведомления, сообщения)
    ai_text_generation_model: str = Field("gpt-4.1-mini-2025-04-14", env="AI_TEXT_GENERATION_MODEL")
    
    # Диспетчерская логика (основная обработка заказов)
    ai_dispatcher_model: str = Field("o4-mini", env="AI_DISPATCHER_MODEL")
    
    # НАСТРОЙКИ ДЛЯ ГИБКОЙ ОБРАБОТКИ (FLEX PROCESSING) - В 2 РАЗА ДЕШЕВЛЕ!
    # Включает гибкую обработку для экономии 50% стоимости токенов
    use_flex_processing: bool = Field(True, env="USE_FLEX_PROCESSING")
    
    # Настройки для reasoning моделей (o4-mini, o3)
    reasoning_effort: str = Field("medium", env="REASONING_EFFORT")  # low, medium, high
    reasoning_use_responses_api: bool = Field(True, env="REASONING_USE_RESPONSES_API")
    reasoning_max_output_tokens: int = Field(25000, env="REASONING_MAX_OUTPUT_TOKENS")
    
    # Настройки для o3 (если решите переключиться обратно)
    o3_use_flexible_processing: bool = Field(True, env="O3_USE_FLEXIBLE_PROCESSING")
    o3_thinking_time: str = Field("medium", env="O3_THINKING_TIME")  # low, medium, high
    
    # Настройки для нового Responses API (o3, o4-mini)
    o3_use_responses_api: bool = Field(True, env="O3_USE_RESPONSES_API")
    o3_reasoning_effort: str = Field("medium", env="O3_REASONING_EFFORT")  # low, medium, high
    o3_max_output_tokens: int = Field(25000, env="O3_MAX_OUTPUT_TOKENS")
    o3_reasoning_summary: str = Field("none", env="O3_REASONING_SUMMARY")  # auto, detailed, concise, none
    
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    # Database
    database_url: str = Field("sqlite:///./logistics_ai.db", env="DATABASE_URL")
    database_echo: bool = Field(False, env="DATABASE_ECHO")
    
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # Logging
    log_level: str = "DEBUG"  # DEBUG, INFO, WARNING, ERROR (временно для отладки commission)
    log_file: str = Field("logs/app.log", env="LOG_FILE")
    
    # Business Logic
    default_commission_percent: int = Field(40, env="DEFAULT_COMMISSION_PERCENT")
    min_order_amount: int = Field(5000, env="MIN_ORDER_AMOUNT")
    max_order_amount: int = Field(500000, env="MAX_ORDER_AMOUNT")
    
    # Monitoring
    monitoring_interval_seconds: int = Field(300, env="MONITORING_INTERVAL_SECONDS")
    max_concurrent_orders: int = Field(50, env="MAX_CONCURRENT_ORDERS")
    
    # Contact Info
    dispatcher_phone: str = Field("+7XXXXXXXXXX", env="DISPATCHER_PHONE")
    dispatcher_telegram: str = Field("@your_telegram", env="DISPATCHER_TELEGRAM")
    dispatcher_email: str = Field("dispatcher@yourdomain.com", env="DISPATCHER_EMAIL")
    
    # Advertising APIs
    yandex_direct_token: str = Field(default="", env="YANDEX_DIRECT_TOKEN")
    google_ads_credentials: Optional[str] = Field(None, env="GOOGLE_ADS_CREDENTIALS")
    
    # Development
    debug: bool = Field(True, env="DEBUG")
    testing: bool = Field(False, env="TESTING")
    
    # Yandex Direct API
    yandex_direct_sandbox_token: str = Field(default="your_yandex_direct_sandbox_token", env="YANDEX_DIRECT_SANDBOX_TOKEN")
    
    # ATI.SU Integration (дополнительные настройки)
    ati_refresh_interval: int = Field(default=300, env="ATI_REFRESH_INTERVAL")
    markup_percent: float = Field(40.0, env="MARKUP_PERCENT")
    
    # НАСТРОЙКИ УМНОГО ИИ-ПРОДАЖНИКА (LAER + Re-CAP)
    # Многоходовая работа с возражениями
    max_price_attempts: int = Field(3, env="MAX_PRICE_ATTEMPTS")  # сколько раундов ведёт ИИ
    min_margin_pct: float = Field(0.25, env="MIN_MARGIN_PCT")  # нельзя ронять маржу ниже 25%
    max_discount_pct: float = Field(0.10, env="MAX_DISCOUNT_PCT")  # макс. уступка 10% клиенту
    
    # Техники продаж
    use_laer_technique: bool = Field(True, env="USE_LAER_TECHNIQUE")  # использовать LAER + Re-CAP
    use_social_proof: bool = Field(True, env="USE_SOCIAL_PROOF")  # использовать соц. доказательства
    
    # Ценовая политика
    price_flexibility_enabled: bool = Field(True, env="PRICE_FLEXIBILITY_ENABLED")  # гибкое ценообразование
    discount_step_pct: float = Field(0.03, env="DISCOUNT_STEP_PCT")  # шаг скидки 3%
    
    # Эскалация к владельцу
    auto_escalation_on_margin_breach: bool = Field(True, env="AUTO_ESCALATION_ON_MARGIN_BREACH")
    auto_escalation_on_max_attempts: bool = Field(True, env="AUTO_ESCALATION_ON_MAX_ATTEMPTS")
    
    # Защита от обещаний несуществующих услуг
    filter_forbidden_promises: bool = Field(True, env="FILTER_FORBIDDEN_PROMISES")
    forbidden_keywords: list = Field(
        default=[
            "страхов", "мониторинг", "ATI", "ati.su", 
            "круглосуточн", "24/7", "гарантия возмещения"
        ], 
        env="FORBIDDEN_KEYWORDS"
    )
    
    # МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ ПОДХОДЯЩИХ МОДЕЛЕЙ
    def get_model_for_task(self, task_type: str) -> str:
        """
        Получить подходящую модель для конкретной задачи
        
        Args:
            task_type: Тип задачи ('sales', 'simple', 'analysis', 'text_generation', 'dispatcher')
        """
        model_mapping = {
            'sales': self.ai_sales_model,
            'simple': self.ai_simple_model, 
            'analysis': self.ai_analysis_model,
            'text_generation': self.ai_text_generation_model,
            'dispatcher': self.ai_dispatcher_model,
            'default': self.openai_model
        }
        
        return model_mapping.get(task_type, self.openai_model)
    
    def get_model_params_for_reasoning(self, model: str) -> dict:
        """Получить параметры для reasoning моделей (o4-mini, o3)"""
        if not self.is_reasoning_model(model):
            return {}
        
        # Для o4-mini используем Responses API
        if model.startswith('o4-mini'):
            return {
                'use_responses_api': True,
                'reasoning_effort': self.reasoning_effort,
                'max_output_tokens': self.reasoning_max_output_tokens
            }
        
        # Для o3 используем старые параметры или новые
        if model.startswith('o3'):
            if self.o3_use_responses_api:
                return {
                    'use_responses_api': True,
                    'reasoning_effort': self.o3_reasoning_effort,
                    'max_output_tokens': self.o3_max_output_tokens,
                    'reasoning_summary': self.o3_reasoning_summary
                }
            else:
                # Старая гибкая обработка для o3
                return {'reasoning_effort': self.o3_thinking_time} if self.o3_use_flexible_processing else {}
        
        return {}
    
    def get_model_params_for_o3(self) -> dict:
        """Получить параметры для o3 модели с гибкой обработкой (совместимость)"""
        return self.get_model_params_for_reasoning('o3')
    
    def is_reasoning_model(self, model: str) -> bool:
        """Проверить является ли модель reasoning моделью (o3, o4-mini, o1)"""
        # o4-mini работает через Responses API, как показано в документации OpenAI
        reasoning_models = ['o3', 'o4-mini', 'o1', 'o1-mini', 'o3-mini']
        return any(model.startswith(rm) for rm in reasoning_models)
    
    def get_responses_api_params(self, model: str) -> dict:
        """Получить параметры для Responses API (o3, o4-mini)"""
        if not self.is_reasoning_model(model):
            return {}
        
        if model.startswith('o4-mini'):
            return {
                'reasoning': {'effort': self.reasoning_effort},
                'max_output_tokens': self.reasoning_max_output_tokens
            }
        
        if model.startswith('o3'):
            reasoning_params = {
                'effort': self.o3_reasoning_effort
            }
            
            # Добавляем summary только если не "none" (требует верификации)
            if self.o3_reasoning_summary != "none":
                reasoning_params['summary'] = self.o3_reasoning_summary
            
            return {
                'reasoning': reasoning_params,
                'max_output_tokens': self.o3_max_output_tokens
            }
        
        return {}


# Глобальный экземпляр настроек
settings = Settings()


def get_settings() -> Settings:
    """Получить настройки приложения"""
    return settings 