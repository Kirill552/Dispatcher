"""
Универсальный AI клиент для работы с reasoning и обычными моделями
"""
from openai import AsyncOpenAI
from typing import Dict, List, Optional, Any, Union
from utils.config import settings
from utils.logger import ai_logger as logger


class ChatCompletions:
    """Совместимый интерфейс для chat.completions"""
    
    def __init__(self, parent_client):
        self.parent = parent_client
    
    async def create(self, model: str, messages: List[Dict], **kwargs):
        """Совместимый метод с chat.completions.create"""
        # Извлекаем параметры
        max_tokens = kwargs.get('max_tokens')
        temperature = kwargs.get('temperature', 0.7)
        
        # Вызываем универсальный метод
        response_text = await self.parent.create_completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Возвращаем объект совместимый с OpenAI API
        from types import SimpleNamespace
        
        choice = SimpleNamespace()
        choice.message = SimpleNamespace()
        choice.message.content = response_text
        
        response = SimpleNamespace()
        response.choices = [choice]
        
        return response


class Chat:
    """Совместимый интерфейс для chat"""
    
    def __init__(self, parent_client):
        self.completions = ChatCompletions(parent_client)


class UniversalAIClient:
    """Универсальный клиент для работы с разными типами OpenAI моделей"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        # Добавляем совместимый интерфейс
        self.chat = Chat(self)
    
    async def create_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        task_type: str = "default"
    ) -> str:
        """
        Универсальная функция для создания completion с автоматическим выбором API
        
        Args:
            model: Название модели
            messages: Список сообщений [{"role": "user", "content": "..."}]
            max_tokens: Максимальное количество токенов
            temperature: Температура (для обычных моделей)
            task_type: Тип задачи для логирования
        """
        try:
            if settings.is_reasoning_model(model):
                # Используем Responses API для reasoning моделей
                return await self._create_reasoning_completion(
                    model, messages, max_tokens, task_type
                )
            else:
                # Используем Chat Completions API для обычных моделей
                return await self._create_chat_completion(
                    model, messages, max_tokens, temperature, task_type
                )
        
        except Exception as e:
            logger.error(f"Ошибка AI completion для {task_type}: {e}")
            raise
    
    async def _create_reasoning_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        task_type: str
    ) -> str:
        """Создание completion через Responses API для reasoning моделей"""
        
        # Получаем параметры для Responses API (включая Flex Processing)
        api_params = settings.get_responses_api_params(model)
        
        # FLEX PROCESSING ПОКА НЕ ДОСТУПЕН В ПУБЛИЧНОМ API
        # use_flex = getattr(settings, 'use_flex_processing', True)  # По умолчанию включено
        # if use_flex and model.startswith(('o3', 'o4-mini')):
        #     api_params['processing'] = 'flex'  # Включает гибкую обработку
        #     logger.info(f"💰 Включена Flex Processing для {model} - экономия 50% стоимости!")
        
        # Используем max_output_tokens если указан
        if max_tokens:
            api_params['max_output_tokens'] = min(max_tokens, api_params.get('max_output_tokens', 25000))
        
        # Конвертируем messages в input для Responses API
        input_messages = [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in messages
        ]
        
        effort = api_params.get('reasoning', {}).get('effort', 'medium')
        
        logger.info(f"🧠 Используется reasoning модель {model} для задачи '{task_type}' (effort: {effort})")
        
        response = await self.client.responses.create(
            model=model,
            input=input_messages,
            **api_params
        )
        
        # Логируем использование токенов
        if hasattr(response, 'usage'):
            usage = response.usage
            reasoning_tokens = getattr(usage.output_tokens_details, 'reasoning_tokens', 0) if hasattr(usage, 'output_tokens_details') else 0
            logger.info(f"💰 Токены для {task_type}: вход={usage.input_tokens}, выход={usage.output_tokens}, reasoning={reasoning_tokens}")
        
        # Правильное извлечение текста из Responses API согласно документации
        result_text = ""
        
        # Способ 1: Основной способ - через output_text (документация OpenAI)
        if hasattr(response, 'output_text') and response.output_text:
            result_text = response.output_text
            logger.debug(f"✅ Получен текст через output_text: {len(result_text)} символов")
        
        # Способ 2: Если нет output_text, проверяем статус
        elif hasattr(response, 'status'):
            if response.status == "incomplete":
                # Модель не завершила генерацию
                incomplete_reason = getattr(response.incomplete_details, 'reason', 'unknown') if hasattr(response, 'incomplete_details') else 'unknown'
                logger.warning(f"⚠️ Неполный ответ от reasoning модели. Причина: {incomplete_reason}")
                
                # Возможно есть частичный текст в output_text
                if hasattr(response, 'output_text') and response.output_text:
                    result_text = response.output_text
                    logger.info(f"📝 Получен частичный текст: {len(result_text)} символов")
                else:
                    logger.error(f"❌ Нет текста в неполном ответе")
            
            elif response.status == "failed":
                logger.error(f"❌ Ошибка выполнения reasoning модели")
            
            else:
                logger.warning(f"⚠️ Неожиданный статус: {response.status}")
        
        # Способ 3: Если ничего не найдено, логируем для отладки
        if not result_text:
            logger.error(f"❌ Не удалось извлечь текст из ответа reasoning модели")
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response status: {getattr(response, 'status', 'no status')}")
            logger.debug(f"Has output_text: {hasattr(response, 'output_text')}")
            if hasattr(response, 'output_text'):
                logger.debug(f"output_text value: {repr(response.output_text)}")
        
        return result_text.strip() if result_text else ""
    
    async def _create_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int],
        temperature: float,
        task_type: str
    ) -> str:
        """Создание completion через Chat Completions API для обычных моделей"""
        
        # Подготавливаем параметры для вызова
        api_params = {
            "model": model,
            "messages": messages
        }
        
        # Для o4-mini используем max_completion_tokens и reasoning_effort (БЕЗ temperature!)
        if model.startswith('o4-mini'):
            if max_tokens:
                api_params["max_completion_tokens"] = max_tokens  # Правильный параметр для o4-mini
            api_params["reasoning_effort"] = settings.reasoning_effort
            # НЕ добавляем temperature для o4-mini - не поддерживается!
            logger.info(f"🧠 Используется reasoning модель {model} через Chat Completions API для задачи '{task_type}' (effort: {settings.reasoning_effort})")
        else:
            api_params["temperature"] = temperature  # Температура только для обычных моделей
            if max_tokens:
                api_params["max_tokens"] = max_tokens  # Обычный параметр для других моделей
            logger.info(f"💬 Используется обычная модель {model} для задачи '{task_type}'")
        
        response = await self.client.chat.completions.create(**api_params)
        
        # Логируем использование токенов
        if hasattr(response, 'usage'):
            usage = response.usage
            # Для o4-mini может быть reasoning_tokens
            reasoning_tokens = getattr(usage, 'reasoning_tokens', 0) if hasattr(usage, 'reasoning_tokens') else 0
            if reasoning_tokens > 0:
                logger.info(f"💰 Токены для {task_type}: вход={usage.prompt_tokens}, выход={usage.completion_tokens}, reasoning={reasoning_tokens}")
            else:
                logger.info(f"💰 Токены для {task_type}: вход={usage.prompt_tokens}, выход={usage.completion_tokens}")
        
        return response.choices[0].message.content.strip()


# Глобальный экземпляр клиента
ai_client = UniversalAIClient() 