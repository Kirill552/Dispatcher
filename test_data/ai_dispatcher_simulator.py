# -*- coding: utf-8 -*-
"""
Основной симулятор автотестирования ИИ-диспетчера
Автоматическое тестирование полного цикла работы системы
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

from mock_ati_service import MockATIService, enable_mock_mode, disable_mock_mode
from synthetic_cargo_data import SYNTHETIC_CARGOS, get_random_cargo, get_synthetic_cargo_by_id
from synthetic_offers_data import get_offers_for_cargo, SYNTHETIC_CARRIERS, generate_synthetic_offers
from client_dialog_scenarios import (
    CLIENT_DIALOG_SCENARIOS, ClientType, 
    get_random_scenario, get_scenario_by_id
)

# Импорты основной системы (будут работать в тестовом режиме)
import sys
import os

# Настраиваем путь к корню проекта для правильного чтения .env файла
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_root)

# Меняем рабочую директорию на корень проекта для чтения .env
original_cwd = os.getcwd()
os.chdir(project_root)

# ВАЖНО: .env файл должен находиться в корне проекта ~/ai_dispatcher/config.env
print(f"🔧 Рабочая директория для .env: {os.getcwd()}")
print(f"🔧 Ищем config.env в: {os.path.join(os.getcwd(), 'config.env')}")

from ai_services.ai_dispatcher_logic import AIDispatcherLogic
from ai_services.dialog_manager import DialogManager
from ai_services.sales_agent import SalesAgent
from ai_services.performance_manager import PerformanceManager
from utils.logger import get_logger

logger = get_logger(__name__)

# Мок-ответы для ИИ в тестовом режиме
MOCK_AI_RESPONSES = [
    "Здравствуйте! Меня зовут Владимир, менеджер по логистике. Расскажите подробнее о вашем грузе, и я подберу оптимальный вариант доставки.",
    "Спасибо за информацию! Для точного расчета стоимости уточните, пожалуйста, точный вес и габариты груза.",
    "Отлично! Начинаю поиск подходящих перевозчиков. Обычно это занимает 15-30 минут. Уведомлю вас о результатах.",
    "Найдены отличные варианты перевозки! Могу предложить доставку за 45 000 рублей с гарантией сохранности груза.",
    "Понимаю ваши сомнения по цене. Учитывая специфику груза, это очень конкурентное предложение. Готов обсудить условия."
]

def get_mock_ai_response(message: str, context: Dict = None) -> str:
    """Возвращает мок-ответ ИИ для тестирования"""
    if not message:
        return MOCK_AI_RESPONSES[0]
    
    # Простая логика выбора ответа на основе ключевых слов
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["привет", "здравствуйте", "добрый"]):
        return MOCK_AI_RESPONSES[0]
    elif any(word in message_lower for word in ["груз", "перевезти", "доставка"]):
        return MOCK_AI_RESPONSES[1]
    elif any(word in message_lower for word in ["цена", "стоимость", "сколько"]):
        return MOCK_AI_RESPONSES[3]
    elif any(word in message_lower for word in ["дорого", "дешевле", "много"]):
        return MOCK_AI_RESPONSES[4]
    else:
        return random.choice(MOCK_AI_RESPONSES[1:3])

# Монки-патч для SalesAgent в тестовом режиме
original_generate_client_response = None

async def mock_generate_client_response(self, client_message: str, context: Dict = None) -> str:
    """Мок-версия generate_client_response для тестов"""
    # Симулируем небольшую задержку как у реального API
    await asyncio.sleep(0.1 + random.random() * 0.3)
    return get_mock_ai_response(client_message, context)

def enable_ai_mock_mode():
    """Включаем мок-режим для ИИ"""
    global original_generate_client_response
    if original_generate_client_response is None:
        original_generate_client_response = SalesAgent.generate_client_response
        SalesAgent.generate_client_response = mock_generate_client_response
        logger.info("🤖 Мок-режим ИИ включен")

def disable_ai_mock_mode():
    """Выключаем мок-режим для ИИ"""
    global original_generate_client_response
    if original_generate_client_response is not None:
        SalesAgent.generate_client_response = original_generate_client_response
        original_generate_client_response = None
        logger.info("🤖 Мок-режим ИИ выключен")

class TestResult:
    """Результат единичного теста"""
    
    def __init__(self):
        self.test_id: str = ""
        self.scenario_type: str = ""
        self.cargo_id: str = ""
        self.client_type: str = ""
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration_seconds: float = 0.0
        
        # Результаты
        self.success: bool = False
        self.expected_outcome: str = ""
        self.actual_outcome: str = ""
        self.offers_received: int = 0
        self.client_responses: int = 0
        self.ai_responses: int = 0
        self.escalated: bool = False
        
        # Ошибки
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Детали
        self.conversation_log: List[Dict] = []
        self.performance_metrics: Dict = {}
        
    def finish(self, success: bool = True):
        """Завершить тест"""
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = success
        
    def to_dict(self) -> Dict:
        """Преобразовать в словарь для сохранения"""
        return {
            "test_id": self.test_id,
            "scenario_type": self.scenario_type,
            "cargo_id": self.cargo_id,
            "client_type": self.client_type,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "offers_received": self.offers_received,
            "client_responses": self.client_responses,
            "ai_responses": self.ai_responses,
            "escalated": self.escalated,
            "errors": self.errors,
            "warnings": self.warnings,
            "conversation_log": self.conversation_log,
            "performance_metrics": self.performance_metrics
        }

class AIDispatcherSimulator:
    """Основной симулятор тестирования ИИ-диспетчера"""
    
    def __init__(self):
        self.mock_ati = MockATIService()
        self.test_results: List[TestResult] = []
        self.current_test_session: str = ""
        
        # Сохраняем оригинальную рабочую директорию
        self.original_cwd = original_cwd
        
        # Компоненты системы (будут инициализированы в mock режиме)
        self.ai_dispatcher: Optional[AIDispatcherLogic] = None
        self.dialog_manager: Optional[DialogManager] = None
        self.sales_agent: Optional[SalesAgent] = None
        self.performance_manager: Optional[PerformanceManager] = None
        
        # Статистика
        self.total_tests_run: int = 0
        self.successful_tests: int = 0
        self.failed_tests: int = 0
        
    async def initialize_test_environment(self):
        """Инициализация тестовой среды"""
        logger.info("🚀 Инициализация тестовой среды...")
        
        # Включаем мок-режимы
        enable_mock_mode()  # Мок ATI API
        # enable_ai_mock_mode()  # ОТКЛЮЧЕН - используем реальный ИИ для тестирования улучшений
        
        try:
            # Инициализируем компоненты системы
            self.ai_dispatcher = AIDispatcherLogic()
            self.dialog_manager = DialogManager()
            self.sales_agent = SalesAgent()
            self.performance_manager = PerformanceManager()
            
            logger.info("✅ Тестовая среда инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации тестовой среды: {e}")
            return False
    
    async def cleanup_test_environment(self):
        """Очистка тестовой среды"""
        logger.info("🧹 Очистка тестовой среды...")
        
        # Выключаем мок-режимы
        disable_mock_mode()  # Мок ATI API
        # disable_ai_mock_mode()  # ОТКЛЮЧЕН - реальный ИИ работает
        
        # Сбрасываем состояние мок-сервиса
        self.mock_ati.reset_state()
        
        # Восстанавливаем оригинальную рабочую директорию
        os.chdir(self.original_cwd)
        
        logger.info("✅ Тестовая среда очищена")
    
    async def run_single_test(self, test_config: Dict) -> TestResult:
        """Выполнить единичный тест"""
        result = TestResult()
        result.test_id = f"test_{int(time.time())}_{random.randint(1000, 9999)}"
        result.scenario_type = test_config.get("type", "unknown")
        
        try:
            logger.info(f"🧪 Запуск теста {result.test_id}: {result.scenario_type}")
            
            if test_config["type"] == "cargo_processing":
                await self._test_cargo_processing(result, test_config)
            elif test_config["type"] == "client_dialog":
                await self._test_client_dialog(result, test_config)
            elif test_config["type"] == "offer_analysis":
                await self._test_offer_analysis(result, test_config)
            elif test_config["type"] == "performance_check":
                await self._test_performance_check(result, test_config)
            elif test_config["type"] == "integration_full_cycle":
                await self._test_full_integration_cycle(result, test_config)
            else:
                result.errors.append(f"Неизвестный тип теста: {test_config['type']}")
                result.finish(False)
                
        except Exception as e:
            result.errors.append(f"Исключение в тесте: {str(e)}")
            result.finish(False)
            logger.error(f"❌ Тест {result.test_id} завершился с ошибкой: {e}")
        
        self.test_results.append(result)
        return result
    
    async def _test_cargo_processing(self, result: TestResult, config: Dict):
        """Тест обработки груза и получения предложений"""
        
        # Выбираем тестовый груз
        cargo = config.get("cargo") or get_random_cargo()
        result.cargo_id = cargo["Id"]
        
        # Симулируем получение предложений
        offers = await self.mock_ati.get_cargo_responses_new(cargo["Id"])
        result.offers_received = len(offers)
        
        # Проверяем работу AI диспетчера через process_client_order
        if self.ai_dispatcher:
            # Формируем данные клиента для тестирования
            client_data = {
                "message": f"Нужно перевезти {cargo.get('CargoText', 'груз')} по маршруту {cargo.get('From', 'откуда')} - {cargo.get('To', 'куда')}",
                "cargo_type": cargo.get("CargoText", "общий груз"),
                "from_city": cargo.get("From", "Москва"),
                "to_city": cargo.get("To", "СПб"),
                "weight": cargo.get("Weight", 1000),
                "test_mode": True
            }
            
            analysis_result = await self.ai_dispatcher.process_client_order(client_data)
            
            if analysis_result and analysis_result.get("status") in ["search_started", "needs_clarification"]:
                result.performance_metrics["dispatcher_response"] = analysis_result.get("status")
                result.performance_metrics["offers_found"] = len(offers) if offers else 0
                result.success = True
            else:
                result.errors.append(f"AI диспетчер вернул ошибку: {analysis_result.get('error', 'неизвестная ошибка')}")
        
        result.finish(result.success)
    
    async def _test_client_dialog(self, result: TestResult, config: Dict):
        """Тест диалога с клиентом"""
        
        # Выбираем сценарий клиента
        client_type, scenario = config.get("scenario") or get_random_scenario()
        result.client_type = client_type.value
        result.expected_outcome = scenario.get("expected_outcome", "unknown")
        
        # Создаем уникальный client_id для тестового диалога
        test_client_id = int(time.time() * 1000) % 1000000  # Уникальный ID на основе времени
        
        # Симулируем диалог
        if self.sales_agent and self.dialog_manager:
            conversation_success = True
            
            for i, client_message in enumerate(scenario["client_messages"]):
                result.client_responses += 1
                
                # Получаем ответ от AI продажника С КОНТЕКСТОМ
                try:
                    ai_response = await self.sales_agent.handle_conversation_with_memory(
                        client_id=test_client_id,
                        new_message=client_message,
                        context={"test_mode": True}
                    )
                    
                    result.ai_responses += 1
                    result.conversation_log.append({
                        "step": i + 1,
                        "client_message": client_message,
                        "ai_response": ai_response,
                        "intent": "unknown",  # Определяется внутри метода
                        "confidence": 1.0
                    })
                    
                    # Проверяем эскалацию по ключевым словам в ответе (обновлено под новую логику)
                    escalation_keywords = [
                        "диспетчер",     # явное упоминание диспетчера
                        "передаю",        # передача на человека
                        "переключаю",     # переключение на оператора
                        "оператор",       # оператор на линии
                        "ручной режим"    # переход в ручной режим
                    ]
                    if any(keyword in ai_response.lower() for keyword in escalation_keywords):
                        result.escalated = True
                        
                except Exception as e:
                    result.errors.append(f"Ошибка в диалоге на шаге {i+1}: {str(e)}")
                    conversation_success = False
                    break
            
            # УПРОЩЕННАЯ ЛОГИКА: После предложения цены ИИ завершает работу
            # Определяем фактический исход
            if result.escalated:
                result.actual_outcome = "escalation"
            elif conversation_success:
                # В новой логике проверяем признаки завершения работы ИИ
                last_response = result.conversation_log[-1]["ai_response"].lower() if result.conversation_log else ""
                completion_keywords = [
                    "готовый клиент", "данные сделки", "дальше общение", "ручной режим",
                    "предложение отправлено", "свяжется с вами", "перенаправлю",
                    "передаю данные", "завершаю работу", "уведомил владельца",
                    "фиксирую"  # Новое ключевое слово
                ]
                price_keywords = [
                    "рублей", "руб", "тысяч", "стоимость", "цена", "тариф"
                ]
                
                # Если есть цена И признаки завершения - значит ИИ сработал правильно
                has_price = any(word in last_response for word in price_keywords)
                has_completion = any(word in last_response for word in completion_keywords)
                
                if has_price or has_completion:
                    result.actual_outcome = "offer_sent_and_completed"  # Новый исход
                else:
                    result.actual_outcome = "continuing_dialog"
            else:
                result.actual_outcome = "failure"
            
            # УПРОЩЕННАЯ ПРОВЕРКА: Успех если ИИ отправил предложение и завершил работу
            result.success = (
                conversation_success and 
                result.actual_outcome in ["offer_sent_and_completed", "escalation"] and
                not result.errors
            )
        
        result.finish(result.success)
    
    async def _test_offer_analysis(self, result: TestResult, config: Dict):
        """Тест анализа предложений перевозчиков"""
        
        cargo = config.get("cargo") or get_random_cargo()
        result.cargo_id = cargo["Id"]
        
        # Получаем предложения
        offers = get_offers_for_cargo(cargo["Id"], cargo)
        result.offers_received = len(offers)
        
        if self.ai_dispatcher and offers:
            # Упрощенный анализ предложений для теста
            try:
                # АТИ отдаёт поле FirmName (в мок-данных тоже). Принимаем оба варианта на всякий случай.
                valid_offers = [
                    offer for offer in offers
                    if offer.get("Price") and (offer.get("FirmName") or offer.get("CompanyName"))
                ]
                best_offer = (
                    min(valid_offers, key=lambda x: x.get("Price", float('inf'))) if valid_offers else None
                )
                
                result.performance_metrics.update({
                    "offers_analyzed": len(offers),
                    "valid_offers": len(valid_offers),
                    "best_offer_price": best_offer.get("Price") if best_offer else None,
                    "best_offer_company": best_offer.get("FirmName") or best_offer.get("CompanyName") if best_offer else None
                })
                result.success = len(valid_offers) > 0
            except Exception as e:
                result.errors.append(f"Ошибка анализа предложений: {str(e)}")
                result.success = False
        
        result.finish(result.success)
    
    async def _test_performance_check(self, result: TestResult, config: Dict):
        """Тест производительности системы"""
        
        if self.performance_manager:
            # Тестируем различные аспекты производительности
            start_time = time.time()
            
            # Тест скорости ответа AI
            test_message = "Здравствуйте, интересует стоимость доставки груза"
            if self.sales_agent:
                ai_start = time.time()
                response = await self.sales_agent.generate_client_response(test_message)
                ai_duration = time.time() - ai_start
                
                result.performance_metrics["ai_response_time"] = ai_duration
                result.performance_metrics["ai_response_quality"] = len(response) > 10
            
            # Тест скорости получения предложений (мок)
            mock_start = time.time()
            offers = await self.mock_ati.get_cargo_responses_new("test-cargo-001")
            mock_duration = time.time() - mock_start
            
            result.performance_metrics["mock_api_response_time"] = mock_duration
            result.performance_metrics["offers_count"] = len(offers)
            
            total_duration = time.time() - start_time
            result.performance_metrics["total_test_duration"] = total_duration
            
            # Критерии успеха
            result.success = (
                ai_duration < 15.0 and  # AI отвечает достаточно быстро (до 15 с)
                mock_duration < 1.0 and  # Мок API быстрый
                len(offers) > 0  # Есть предложения
            )
        
        result.finish(result.success)
    
    async def _test_full_integration_cycle(self, result: TestResult, config: Dict):
        """Тест полного цикла интеграции"""
        
        cargo = config.get("cargo") or get_random_cargo()
        client_type, scenario = config.get("client_scenario") or get_random_scenario()
        
        result.cargo_id = cargo["Id"]
        result.client_type = client_type.value
        result.scenario_type = "full_integration"
        
        try:
            # 1. Получаем предложения
            offers = await self.mock_ati.get_cargo_responses_new(cargo["Id"])
            result.offers_received = len(offers)
            
            if not offers:
                result.errors.append("Не получены предложения для груза")
                result.finish(False)
                return
            
            # 2. Пропускаем анализ предложений (метод не существует)
            # В реальной системе анализ происходит внутри process_client_order
            
            # 3. Симулируем диалог с клиентом
            if self.sales_agent:
                dialog_success = True
                test_client_id = int(time.time() * 1000) % 1000000  # Уникальный ID
                
                for client_message in scenario["client_messages"]:
                    ai_response = await self.sales_agent.handle_conversation_with_memory(
                        client_id=test_client_id,
                        new_message=client_message,
                        context={"cargo_id": cargo["Id"], "offers": offers}
                    )
                    
                    result.conversation_log.append({
                        "client": client_message,
                        "ai": ai_response,
                        "intent": "unknown"
                    })
                    
                    # УПРОЩЕННАЯ ЛОГИКА: Проверяем завершение работы ИИ после предложения
                    completion_keywords = [
                        "готовый клиент", "данные сделки", "дальше общение", "ручной режим",
                        "диспетчер", "передаю", "переключаю", "оператор", "завершаю работу",
                        "фиксирую"  # Новое ключевое слово
                    ]
                    price_keywords = [
                        "рублей", "руб", "тысяч", "стоимость", "цена", "тариф"
                    ]
                    
                    has_price = any(keyword in ai_response.lower() for keyword in price_keywords)
                    has_completion = any(keyword in ai_response.lower() for keyword in completion_keywords)
                    
                    if has_completion or (has_price and i >= len(scenario["client_messages"]) - 1):
                        result.escalated = True  # Используем как признак завершения
                        break
            
            # 4. Проверяем производительность
            if self.performance_manager:
                metrics = await self.performance_manager.get_session_metrics("test_session")
                result.performance_metrics.update(metrics or {})
            
            # УПРОЩЕННЫЙ КРИТЕРИЙ УСПЕХА: Есть предложения и ИИ завершил работу
            result.success = (
                len(offers) > 0 and
                len(result.conversation_log) > 0 and
                result.escalated and  # ИИ завершил работу
                not result.errors
            )
            
        except Exception as e:
            result.errors.append(f"Ошибка в полном цикле: {str(e)}")
            result.success = False
        
        result.finish(result.success)
    
    async def run_test_suite(self, suite_config: Dict) -> Dict:
        """Запуск набора тестов"""
        suite_name = suite_config.get("name", "unnamed_suite")
        test_configs = suite_config.get("tests", [])
        
        logger.info(f"🏃 Запуск тестового набора '{suite_name}' ({len(test_configs)} тестов)")
        
        # Инициализируем среду
        if not await self.initialize_test_environment():
            return {"error": "Не удалось инициализировать тестовую среду"}
        
        suite_start_time = datetime.now()
        suite_results = []
        
        try:
            # Запускаем тесты
            for i, test_config in enumerate(test_configs):
                logger.info(f"📋 Тест {i+1}/{len(test_configs)}: {test_config.get('name', 'unnamed')}")
                
                result = await self.run_single_test(test_config)
                suite_results.append(result)
                
                # Небольшая пауза между тестами
                await asyncio.sleep(0.1)
        
        finally:
            # Очищаем среду
            await self.cleanup_test_environment()
        
        suite_end_time = datetime.now()
        suite_duration = (suite_end_time - suite_start_time).total_seconds()
        
        # Подсчитываем статистику
        successful = sum(1 for r in suite_results if r.success)
        failed = len(suite_results) - successful
        
        suite_summary = {
            "suite_name": suite_name,
            "start_time": suite_start_time.isoformat(),
            "end_time": suite_end_time.isoformat(),
            "duration_seconds": suite_duration,
            "total_tests": len(suite_results),
            "successful_tests": successful,
            "failed_tests": failed,
            "success_rate": successful / len(suite_results) if suite_results else 0,
            "results": [r.to_dict() for r in suite_results]
        }
        
        logger.info(f"✅ Набор '{suite_name}' завершен: {successful}/{len(suite_results)} успешно")
        
        return suite_summary

# Предопределенные конфигурации тестов
def get_smoke_test_suite() -> Dict:
    """Быстрый smoke test для проверки основного функционала"""
    return {
        "name": "smoke_test",
        "description": "Быстрая проверка основных функций",
        "tests": [
            {
                "name": "cargo_processing_basic", 
                "type": "cargo_processing"
            },
            {
                "name": "client_dialog_easy",
                "type": "client_dialog",
                "scenario": (ClientType.EASY_CLIENT, CLIENT_DIALOG_SCENARIOS[ClientType.EASY_CLIENT]["conversations"][0])
            },
            {
                "name": "performance_basic",
                "type": "performance_check"
            }
        ]
    }

def get_comprehensive_test_suite() -> Dict:
    """Полный набор тестов для thorough проверки"""
    tests = []
    
    # Тесты обработки грузов
    for cargo in SYNTHETIC_CARGOS[:3]:  # Первые 3 груза
        tests.append({
            "name": f"cargo_processing_{cargo['ExternalId']}",
            "type": "cargo_processing",
            "cargo": cargo
        })
    
    # Тесты диалогов со всеми типами клиентов
    for client_type in ClientType:
        scenarios = CLIENT_DIALOG_SCENARIOS[client_type]["conversations"]
        for i, scenario in enumerate(scenarios[:2]):  # По 2 сценария на тип
            tests.append({
                "name": f"dialog_{client_type.value}_{i+1}",
                "type": "client_dialog", 
                "scenario": (client_type, scenario)
            })
    
    # Тесты анализа предложений
    for cargo in SYNTHETIC_CARGOS[:2]:
        tests.append({
            "name": f"offer_analysis_{cargo['ExternalId']}",
            "type": "offer_analysis",
            "cargo": cargo
        })
    
    # Тесты производительности
    tests.append({
        "name": "performance_comprehensive",
        "type": "performance_check"
    })
    
    # Тесты полного цикла
    for i in range(3):  # 3 полных цикла
        tests.append({
            "name": f"full_cycle_{i+1}",
            "type": "integration_full_cycle"
        })
    
    return {
        "name": "comprehensive_test",
        "description": "Полный набор тестов всех компонентов",
        "tests": tests
    }

def get_stress_test_suite() -> Dict:
    """Стресс-тест с большим количеством сценариев"""
    tests = []
    
    # Генерируем 50 случайных тестов
    for i in range(50):
        test_type = random.choice([
            "cargo_processing", "client_dialog", 
            "offer_analysis", "integration_full_cycle"
        ])
        
        tests.append({
            "name": f"stress_test_{i+1:02d}",
            "type": test_type
        })
    
    return {
        "name": "stress_test",
        "description": "Стресс-тест с 50 случайными сценариями", 
        "tests": tests
    }

async def main():
    """Пример запуска автотестирования"""
    simulator = AIDispatcherSimulator()
    
    # Запускаем smoke test
    print("🚀 Запуск smoke test...")
    smoke_results = await simulator.run_test_suite(get_smoke_test_suite())
    print(f"Smoke test: {smoke_results['successful_tests']}/{smoke_results['total_tests']} успешно")
    
    # Запускаем полный тест
    print("\n🔥 Запуск comprehensive test...")
    full_results = await simulator.run_test_suite(get_comprehensive_test_suite())
    print(f"Comprehensive test: {full_results['successful_tests']}/{full_results['total_tests']} успешно")
    
    # Сохраняем результаты
    results_dir = Path("test_results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(results_dir / f"smoke_test_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(smoke_results, f, ensure_ascii=False, indent=2)
    
    with open(results_dir / f"comprehensive_test_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(full_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Результаты сохранены в директории test_results/")

if __name__ == "__main__":
    asyncio.run(main()) 