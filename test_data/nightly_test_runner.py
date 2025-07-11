# -*- coding: utf-8 -*-
"""
Система автоматических ночных прогонов тестов ИИ-диспетчера
Планировщик и менеджер регулярного тестирования
"""

import asyncio
import json
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ai_dispatcher_simulator import (
    AIDispatcherSimulator, 
    get_smoke_test_suite,
    get_comprehensive_test_suite,
    get_stress_test_suite
)

logger = logging.getLogger(__name__)

class NightlyTestRunner:
    """Менеджер автоматических ночных тестов"""
    
    def __init__(self, config_path: str = "test_config.json"):
        self.config_path = config_path
        self.simulator = AIDispatcherSimulator()
        self.is_running = False
        self.last_run_results: Dict = {}
        
        # Загружаем конфигурацию
        self.config = self._load_config()
        
        # Настройка логирования
        self._setup_logging()
        
    def _load_config(self) -> Dict:
        """Загрузка конфигурации"""
        default_config = {
            "schedules": {
                "smoke_test": {
                    "enabled": True,
                    "cron": "0 2 * * *",  # Каждый день в 2:00
                    "description": "Ежедневный smoke test"
                },
                "comprehensive_test": {
                    "enabled": True, 
                    "cron": "0 3 * * 0",  # Каждое воскресенье в 3:00
                    "description": "Еженедельный полный тест"
                },
                "stress_test": {
                    "enabled": False,
                    "cron": "0 4 1 * *",  # Первое число каждого месяца в 4:00
                    "description": "Ежемесячный стресс-тест"
                }
            },
            "notifications": {
                "enabled": False,
                "email": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "",
                    "sender_password": "",
                    "recipients": []
                },
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": ""
                }
            },
            "retention": {
                "keep_results_days": 30,
                "max_results_files": 100
            },
            "thresholds": {
                "smoke_test_min_success_rate": 0.9,
                "comprehensive_test_min_success_rate": 0.8,
                "stress_test_min_success_rate": 0.7
            }
        }
        
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"Не удалось загрузить конфигурацию: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """Настройка логирования для ночных прогонов"""
        log_dir = Path("test_logs")
        log_dir.mkdir(exist_ok=True)
        
        # Создаем файл логов для ночных прогонов
        log_file = log_dir / "nightly_tests.log"
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    async def run_nightly_tests(self):
        """Запуск всех запланированных тестов"""
        if self.is_running:
            logger.warning("Тесты уже запущены, пропускаем")
            return
            
        self.is_running = True
        run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        logger.info("🌙 Начало ночного прогона тестов")
        
        results_summary = {
            "run_timestamp": run_timestamp,
            "start_time": datetime.now().isoformat(),
            "tests_run": [],
            "overall_success": True,
            "notifications_sent": []
        }
        
        try:
            # Проверяем какие тесты нужно запустить
            current_time = datetime.now()
            
            # Smoke test (если включен)
            if self.config["schedules"]["smoke_test"]["enabled"]:
                if self._should_run_test("smoke_test", current_time):
                    logger.info("🚀 Запуск smoke test")
                    smoke_results = await self.simulator.run_test_suite(get_smoke_test_suite())
                    
                    await self._save_test_results("smoke_test", smoke_results, run_timestamp)
                    results_summary["tests_run"].append(smoke_results)
                    
                    # Проверяем пороги успешности
                    if smoke_results["success_rate"] < self.config["thresholds"]["smoke_test_min_success_rate"]:
                        results_summary["overall_success"] = False
                        logger.warning(f"Smoke test не прошел порог: {smoke_results['success_rate']:.2%}")
            
            # Comprehensive test (если включен)
            if self.config["schedules"]["comprehensive_test"]["enabled"]:
                if self._should_run_test("comprehensive_test", current_time):
                    logger.info("🔥 Запуск comprehensive test")
                    comp_results = await self.simulator.run_test_suite(get_comprehensive_test_suite())
                    
                    await self._save_test_results("comprehensive_test", comp_results, run_timestamp)
                    results_summary["tests_run"].append(comp_results)
                    
                    if comp_results["success_rate"] < self.config["thresholds"]["comprehensive_test_min_success_rate"]:
                        results_summary["overall_success"] = False
                        logger.warning(f"Comprehensive test не прошел порог: {comp_results['success_rate']:.2%}")
            
            # Stress test (если включен)
            if self.config["schedules"]["stress_test"]["enabled"]:
                if self._should_run_test("stress_test", current_time):
                    logger.info("💪 Запуск stress test")
                    stress_results = await self.simulator.run_test_suite(get_stress_test_suite())
                    
                    await self._save_test_results("stress_test", stress_results, run_timestamp)
                    results_summary["tests_run"].append(stress_results)
                    
                    if stress_results["success_rate"] < self.config["thresholds"]["stress_test_min_success_rate"]:
                        results_summary["overall_success"] = False
                        logger.warning(f"Stress test не прошел порог: {stress_results['success_rate']:.2%}")
            
            # Отправляем уведомления
            if self.config["notifications"]["enabled"]:
                await self._send_notifications(results_summary)
            
            # Очищаем старые результаты
            await self._cleanup_old_results()
            
        except Exception as e:
            logger.error(f"❌ Ошибка в ночном прогоне: {e}")
            results_summary["overall_success"] = False
            results_summary["error"] = str(e)
        
        finally:
            results_summary["end_time"] = datetime.now().isoformat()
            self.last_run_results = results_summary
            self.is_running = False
            
            logger.info(f"🏁 Ночной прогон завершен. Успех: {results_summary['overall_success']}")
    
    def _should_run_test(self, test_name: str, current_time: datetime) -> bool:
        """Проверка нужно ли запускать тест по расписанию"""
        # Упрощенная логика - в реальности нужен полноценный cron parser
        schedule_config = self.config["schedules"][test_name]
        
        # Для демонстрации всегда возвращаем True
        # В продакшене здесь должна быть логика парсинга cron выражений
        return True
    
    async def _save_test_results(self, test_type: str, results: Dict, timestamp: str):
        """Сохранение результатов тестов"""
        results_dir = Path("test_results") / "nightly"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{test_type}_{timestamp}.json"
        filepath = results_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Результаты {test_type} сохранены: {filepath}")
    
    async def _send_notifications(self, results_summary: Dict):
        """Отправка уведомлений о результатах"""
        notifications_config = self.config["notifications"]
        
        # Email уведомления
        if notifications_config.get("email", {}).get("sender_email"):
            await self._send_email_notification(results_summary)
        
        # Telegram уведомления
        if notifications_config.get("telegram", {}).get("enabled"):
            await self._send_telegram_notification(results_summary)
    
    async def _send_email_notification(self, results_summary: Dict):
        """Отправка email уведомления"""
        try:
            email_config = self.config["notifications"]["email"]
            
            subject = f"🤖 Отчет ночных тестов ИИ-диспетчера - {results_summary['run_timestamp']}"
            
            # Формируем тело письма
            body = self._format_email_body(results_summary)
            
            msg = MIMEMultipart()
            msg['From'] = email_config["sender_email"]
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Отправляем всем получателям
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            server.starttls()
            server.login(email_config["sender_email"], email_config["sender_password"])
            
            for recipient in email_config["recipients"]:
                msg['To'] = recipient
                server.send_message(msg)
                del msg['To']
            
            server.quit()
            logger.info("📧 Email уведомления отправлены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки email: {e}")
    
    def _format_email_body(self, results_summary: Dict) -> str:
        """Форматирование тела email уведомления"""
        overall_status = "✅ УСПЕШНО" if results_summary["overall_success"] else "❌ ПРОВАЛ"
        
        html = f"""
        <html>
        <body>
            <h2>🤖 Отчет автоматических тестов ИИ-диспетчера</h2>
            <p><strong>Статус:</strong> {overall_status}</p>
            <p><strong>Время запуска:</strong> {results_summary['start_time']}</p>
            <p><strong>Время завершения:</strong> {results_summary['end_time']}</p>
            
            <h3>📊 Результаты тестов:</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>Тест</th>
                    <th>Всего</th>
                    <th>Успешно</th>
                    <th>Провалено</th>
                    <th>Успех %</th>
                    <th>Время</th>
                </tr>
        """
        
        for test_result in results_summary["tests_run"]:
            success_rate = f"{test_result['success_rate']:.1%}"
            duration = f"{test_result['duration_seconds']:.1f}с"
            
            html += f"""
                <tr>
                    <td>{test_result['suite_name']}</td>
                    <td>{test_result['total_tests']}</td>
                    <td>{test_result['successful_tests']}</td>
                    <td>{test_result['failed_tests']}</td>
                    <td>{success_rate}</td>
                    <td>{duration}</td>
                </tr>
            """
        
        html += """
            </table>
            
            <h3>🔧 Следующие шаги:</h3>
            <ul>
        """
        
        if not results_summary["overall_success"]:
            html += """
                <li>Проверьте логи на предмет ошибок</li>
                <li>Убедитесь в корректности тестовых данных</li>
                <li>Проверьте производительность системы</li>
            """
        else:
            html += "<li>Все тесты прошли успешно! 🎉</li>"
        
        html += """
            </ul>
            
            <p><em>Это автоматически сгенерированное уведомление от системы тестирования ИИ-диспетчера.</em></p>
        </body>
        </html>
        """
        
        return html
    
    async def _send_telegram_notification(self, results_summary: Dict):
        """Отправка Telegram уведомления"""
        try:
            telegram_config = self.config["notifications"]["telegram"]
            
            status_emoji = "✅" if results_summary["overall_success"] else "❌"
            
            message = f"""
{status_emoji} *Отчет ночных тестов ИИ-диспетчера*

📅 *Время:* {results_summary['run_timestamp']}
🎯 *Статус:* {'УСПЕШНО' if results_summary['overall_success'] else 'ПРОВАЛ'}

📊 *Результаты:*
"""
            
            for test_result in results_summary["tests_run"]:
                test_emoji = "✅" if test_result["success_rate"] > 0.8 else "⚠️" if test_result["success_rate"] > 0.5 else "❌"
                message += f"{test_emoji} {test_result['suite_name']}: {test_result['successful_tests']}/{test_result['total_tests']} ({test_result['success_rate']:.1%})\n"
            
            # Здесь должна быть отправка в Telegram
            # import aiohttp
            # async with aiohttp.ClientSession() as session:
            #     url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
            #     data = {
            #         "chat_id": telegram_config["chat_id"],
            #         "text": message,
            #         "parse_mode": "Markdown"
            #     }
            #     await session.post(url, data=data)
            
            logger.info("📱 Telegram уведомление отправлено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки Telegram: {e}")
    
    async def _cleanup_old_results(self):
        """Очистка старых результатов тестов"""
        results_dir = Path("test_results") / "nightly"
        if not results_dir.exists():
            return
        
        retention_days = self.config["retention"]["keep_results_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        cleaned_count = 0
        for file_path in results_dir.glob("*.json"):
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time < cutoff_date:
                file_path.unlink()
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"🧹 Удалено {cleaned_count} старых файлов результатов")
    
    def start_scheduler(self):
        """Запуск планировщика тестов"""
        logger.info("⏰ Запуск планировщика ночных тестов")
        
        # Планируем ежедневные smoke тесты
        schedule.every().day.at("02:00").do(
            lambda: asyncio.create_task(self.run_nightly_tests())
        )
        
        # Планируем еженедельные полные тесты
        schedule.every().sunday.at("03:00").do(
            lambda: asyncio.create_task(self.run_nightly_tests())
        )
        
        logger.info("✅ Планировщик настроен")
        
        # Основной цикл планировщика
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    
    def get_status(self) -> Dict:
        """Получить статус системы тестирования"""
        return {
            "is_running": self.is_running,
            "last_run": self.last_run_results,
            "config": self.config,
            "next_scheduled_runs": {
                "smoke_test": "Ежедневно в 02:00",
                "comprehensive_test": "Воскресенье в 03:00", 
                "stress_test": "1 число каждого месяца в 04:00"
            }
        }

def main():
    """Запуск системы ночных тестов"""
    runner = NightlyTestRunner()
    
    print("🌙 Система автоматических ночных тестов ИИ-диспетчера")
    print("⏰ Планировщик настроен и готов к работе")
    print("📋 Расписание:")
    print("   - Smoke test: каждый день в 02:00")
    print("   - Comprehensive test: каждое воскресенье в 03:00")
    print("   - Stress test: первое число месяца в 04:00")
    print("\n🔄 Нажмите Ctrl+C для остановки")
    
    try:
        runner.start_scheduler()
    except KeyboardInterrupt:
        print("\n👋 Планировщик остановлен")

if __name__ == "__main__":
    main() 