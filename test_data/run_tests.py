#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт ручного запуска тестов ИИ-диспетчера
Удобный интерфейс командной строки для тестирования
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ai_dispatcher_simulator import (
    AIDispatcherSimulator,
    get_smoke_test_suite,
    get_comprehensive_test_suite, 
    get_stress_test_suite
)

from nightly_test_runner import NightlyTestRunner

def print_banner():
    """Печать красивого баннера"""
    print("""
╔══════════════════════════════════════════════════╗
║            🤖 ИИ-ДИСПЕТЧЕР АВТОТЕСТЫ             ║
║        Система тестирования грузоперевозок        ║
╚══════════════════════════════════════════════════╝
    """)

def print_test_results_summary(results: Dict):
    """Красивый вывод результатов тестов"""
    print("\n" + "="*60)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {results['suite_name']}")
    print("="*60)
    
    # Общая статистика
    success_rate = results['success_rate']
    status_emoji = "✅" if success_rate >= 0.8 else "⚠️" if success_rate >= 0.5 else "❌"
    
    print(f"{status_emoji} Общий статус: {success_rate:.1%} успешно")
    print(f"⏱️  Время выполнения: {results['duration_seconds']:.2f} сек")
    print(f"📋 Тестов выполнено: {results['total_tests']}")
    print(f"✅ Успешных: {results['successful_tests']}")
    print(f"❌ Проваленных: {results['failed_tests']}")
    
    # Детальная статистика по тестам
    if results.get('results'):
        print(f"\n📝 ДЕТАЛИ ТЕСТОВ:")
        print("-"*60)
        
        for i, test_result in enumerate(results['results'], 1):
            test_status = "✅" if test_result['success'] else "❌"
            duration = test_result['duration_seconds']
            
            print(f"{i:2d}. {test_status} {test_result['scenario_type']:<20} ({duration:.2f}с)")
            
            if test_result.get('errors'):
                for error in test_result['errors']:
                    print(f"     ⚠️  {error}")
            
            if test_result.get('performance_metrics'):
                metrics = test_result['performance_metrics']
                if 'ai_response_time' in metrics:
                    print(f"     ⚡ AI ответ: {metrics['ai_response_time']:.2f}с")
                if 'offers_received' in metrics or 'offers_count' in metrics:
                    offers = metrics.get('offers_received', metrics.get('offers_count', 0))
                    print(f"     📦 Предложений: {offers}")
    
    print("="*60)

def print_help():
    """Печать справки по командам"""
    print("""
🔧 ДОСТУПНЫЕ КОМАНДЫ:

1. Быстрые тесты:
   python run_tests.py smoke               # Быстрый smoke test (3 теста)
   python run_tests.py quick               # То же что smoke

2. Полное тестирование:
   python run_tests.py full                # Полный набор тестов (~20 тестов)
   python run_tests.py comprehensive       # То же что full

3. Стресс-тестирование:
   python run_tests.py stress              # 50 случайных тестов
   python run_tests.py load                # То же что stress

4. Специальные тесты:
   python run_tests.py dialog              # Только тесты диалогов
   python run_tests.py performance         # Только тесты производительности
   python run_tests.py integration         # Только интеграционные тесты

5. Управление:
   python run_tests.py status              # Статус системы тестирования
   python run_tests.py report              # Отчет по последним тестам
   python run_tests.py clean               # Очистка старых результатов

6. Системные:
   python run_tests.py --help              # Эта справка
   python run_tests.py --version           # Версия системы

🔄 ПРИМЕРЫ:
   python run_tests.py smoke --save        # Smoke test с сохранением
   python run_tests.py full --verbose      # Полный тест с подробным выводом
   python run_tests.py stress --parallel   # Параллельный стресс-тест
    """)

async def run_dialog_tests():
    """Запуск только тестов диалогов"""
    from client_dialog_scenarios import ClientType, CLIENT_DIALOG_SCENARIOS
    
    tests = []
    for client_type in ClientType:
        scenarios = CLIENT_DIALOG_SCENARIOS[client_type]["conversations"]
        for i, scenario in enumerate(scenarios[:1]):  # По 1 сценарию на тип
            tests.append({
                "name": f"dialog_{client_type.value}_{i+1}",
                "type": "client_dialog",
                "scenario": (client_type, scenario)
            })
    
    return {
        "name": "dialog_only_test",
        "description": "Тестирование только диалогов с клиентами",
        "tests": tests
    }

async def run_performance_tests():
    """Запуск только тестов производительности"""
    return {
        "name": "performance_only_test", 
        "description": "Тестирование только производительности",
        "tests": [
            {"name": "performance_1", "type": "performance_check"},
            {"name": "performance_2", "type": "performance_check"},
            {"name": "performance_3", "type": "performance_check"}
        ]
    }

async def run_integration_tests():
    """Запуск только интеграционных тестов"""
    return {
        "name": "integration_only_test",
        "description": "Тестирование только полного цикла интеграции", 
        "tests": [
            {"name": "integration_1", "type": "integration_full_cycle"},
            {"name": "integration_2", "type": "integration_full_cycle"},
            {"name": "integration_3", "type": "integration_full_cycle"}
        ]
    }

def show_status():
    """Показать статус системы тестирования"""
    runner = NightlyTestRunner()
    status = runner.get_status()
    
    print("\n🔍 СТАТУС СИСТЕМЫ ТЕСТИРОВАНИЯ")
    print("="*50)
    
    print(f"🔄 Система запущена: {'Да' if status['is_running'] else 'Нет'}")
    
    if status['last_run']:
        last_run = status['last_run']
        print(f"🕐 Последний запуск: {last_run.get('run_timestamp', 'N/A')}")
        print(f"✅ Статус: {'УСПЕШНО' if last_run.get('overall_success') else 'ПРОВАЛ'}")
        print(f"📊 Тестов выполнено: {len(last_run.get('tests_run', []))}")
    else:
        print("📭 Тесты еще не запускались")
    
    print("\n⏰ РАСПИСАНИЕ:")
    for test_name, schedule in status['next_scheduled_runs'].items():
        enabled = status['config']['schedules'][test_name]['enabled']
        status_text = "✅ Включен" if enabled else "❌ Выключен"
        print(f"   {test_name}: {schedule} ({status_text})")

def show_report():
    """Показать отчет по последним тестам"""
    results_dir = Path("test_results")
    if not results_dir.exists():
        print("📭 Результаты тестов не найдены")
        return
    
    # Находим последние файлы результатов
    result_files = list(results_dir.glob("*.json"))
    if not result_files:
        print("📭 Файлы результатов не найдены")
        return
    
    # Сортируем по времени модификации
    result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print("\n📊 ОТЧЕТ ПО ПОСЛЕДНИМ ТЕСТАМ")
    print("="*60)
    
    # Показываем последние 5 результатов
    for i, file_path in enumerate(result_files[:5]):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                results = json.load(f)
            
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            success_rate = results.get('success_rate', 0)
            status_emoji = "✅" if success_rate >= 0.8 else "⚠️" if success_rate >= 0.5 else "❌"
            
            print(f"{i+1}. {status_emoji} {results.get('suite_name', 'unknown')} - {success_rate:.1%}")
            print(f"   🕐 {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   📋 {results.get('total_tests', 0)} тестов, {results.get('duration_seconds', 0):.1f}с")
            print()
            
        except Exception as e:
            print(f"⚠️  Ошибка чтения {file_path.name}: {e}")

def clean_old_results():
    """Очистка старых результатов"""
    results_dir = Path("test_results")
    if not results_dir.exists():
        print("📭 Директория результатов не найдена")
        return
    
    result_files = list(results_dir.glob("*.json"))
    if not result_files:
        print("📭 Файлы результатов не найдены")
        return
    
    print(f"🧹 Найдено {len(result_files)} файлов результатов")
    
    # Удаляем файлы старше 7 дней
    cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
    cleaned = 0
    
    for file_path in result_files:
        if file_path.stat().st_mtime < cutoff_time:
            file_path.unlink()
            cleaned += 1
    
    print(f"✅ Удалено {cleaned} старых файлов")
    print(f"📋 Осталось {len(result_files) - cleaned} файлов")

async def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description="Система автотестирования ИИ-диспетчера",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command', 
        nargs='?',
        choices=[
            'smoke', 'quick',
            'full', 'comprehensive', 
            'stress', 'load',
            'dialog', 'performance', 'integration',
            'status', 'report', 'clean', 'help'
        ],
        help='Команда для выполнения'
    )
    
    parser.add_argument('--save', action='store_true', help='Сохранить результаты')
    parser.add_argument('--verbose', action='store_true', help='Подробный вывод')
    parser.add_argument('--parallel', action='store_true', help='Параллельное выполнение')
    parser.add_argument('--version', action='version', version='AI Dispatcher Tests v1.0')
    
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        print_banner()
        print_help()
        return
    
    # Системные команды
    if args.command == 'status':
        show_status()
        return
    elif args.command == 'report':
        show_report()
        return
    elif args.command == 'clean':
        clean_old_results()
        return
    
    # Команды тестирования
    print_banner()
    
    simulator = AIDispatcherSimulator()
    suite_config = None
    
    # Определяем набор тестов
    if args.command in ['smoke', 'quick']:
        print("🚀 Запуск быстрого smoke test...")
        suite_config = get_smoke_test_suite()
        
    elif args.command in ['full', 'comprehensive']:
        print("🔥 Запуск полного набора тестов...")
        suite_config = get_comprehensive_test_suite()
        
    elif args.command in ['stress', 'load']:
        print("💪 Запуск стресс-тестирования...")
        suite_config = get_stress_test_suite()
        
    elif args.command == 'dialog':
        print("💬 Запуск тестов диалогов...")
        suite_config = await run_dialog_tests()
        
    elif args.command == 'performance':
        print("⚡ Запуск тестов производительности...")
        suite_config = await run_performance_tests()
        
    elif args.command == 'integration':
        print("🔗 Запуск интеграционных тестов...")
        suite_config = await run_integration_tests()
    
    if not suite_config:
        print("❌ Не удалось определить набор тестов")
        return 1
    
    # Запускаем тесты
    try:
        print(f"📋 Будет выполнено тестов: {len(suite_config['tests'])}")
        
        if args.verbose:
            print("🔍 Подробный режим включен")
        
        results = await simulator.run_test_suite(suite_config)
        
        # Выводим результаты
        print_test_results_summary(results)
        
        # Сохраняем результаты
        if args.save:
            results_dir = Path("test_results")
            results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{results['suite_name']}_{timestamp}.json"
            filepath = results_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Результаты сохранены: {filepath}")
        
        # Возвращаем код выхода
        return 0 if results['success_rate'] >= 0.8 else 1
        
    except KeyboardInterrupt:
        print("\n🛑 Тестирование прервано пользователем")
        return 130
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении тестов: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 