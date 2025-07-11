#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Удобный запускатель тестов упрощенной логики ИИ-диспетчера
Запускает все необходимые проверки для новой упрощенной схемы работы
"""

import asyncio
import sys
import subprocess
from pathlib import Path

def print_banner():
    """Красивый баннер"""
    print("""
╔══════════════════════════════════════════════════╗
║          🤖 ТЕСТЫ УПРОЩЕННОЙ ЛОГИКИ              ║
║         ИИ-диспетчер → Предложение → Готово      ║
╚══════════════════════════════════════════════════╝
    """)

def print_help():
    """Справка по командам"""
    print("""
🔧 ДОСТУПНЫЕ КОМАНДЫ:

1. Основные тесты:
   python run_simplified_tests.py logic     # Тест упрощенной логики ИИ
   python run_simplified_tests.py telegram  # Тест Telegram уведомлений
   python run_simplified_tests.py all       # Все тесты упрощенной логики

2. Классические тесты (обновленные):
   python run_simplified_tests.py smoke     # Быстрый smoke test
   python run_simplified_tests.py dialog    # Только тесты диалогов

3. Справка:
   python run_simplified_tests.py help      # Эта справка

🎯 РЕКОМЕНДУЕМАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ:
   1. python run_simplified_tests.py logic     # Проверка основной логики
   2. python run_simplified_tests.py telegram  # Проверка уведомлений
   3. python run_simplified_tests.py dialog    # Проверка диалогов
    """)

async def run_logic_test():
    """Запуск теста упрощенной логики"""
    print("🤖 Запуск теста упрощенной логики ИИ-диспетчера...")
    try:
        result = subprocess.run([
            sys.executable, "test_simplified_logic.py"
        ], capture_output=True, text=True, encoding='utf-8')
        
        print(result.stdout)
        if result.stderr:
            print("⚠️ Предупреждения/ошибки:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка запуска теста логики: {e}")
        return False

async def run_telegram_test():
    """Запуск теста Telegram уведомлений"""
    print("📱 Запуск теста Telegram уведомлений...")
    try:
        result = subprocess.run([
            sys.executable, "test_telegram_notification.py"
        ], capture_output=True, text=True, encoding='utf-8')
        
        print(result.stdout)
        if result.stderr:
            print("⚠️ Предупреждения/ошибки:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка запуска теста Telegram: {e}")
        return False

async def run_smoke_test():
    """Запуск обновленного smoke теста"""
    print("🚀 Запуск обновленного smoke теста...")
    try:
        result = subprocess.run([
            sys.executable, "run_tests.py", "smoke", "--save"
        ], capture_output=True, text=True, encoding='utf-8')
        
        print(result.stdout)
        if result.stderr:
            print("⚠️ Предупреждения/ошибки:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка запуска smoke теста: {e}")
        return False

async def run_dialog_test():
    """Запуск обновленных тестов диалогов"""
    print("💬 Запуск обновленных тестов диалогов...")
    try:
        result = subprocess.run([
            sys.executable, "run_tests.py", "dialog", "--save"
        ], capture_output=True, text=True, encoding='utf-8')
        
        print(result.stdout)
        if result.stderr:
            print("⚠️ Предупреждения/ошибки:")
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка запуска тестов диалогов: {e}")
        return False

async def run_all_tests():
    """Запуск всех тестов упрощенной логики"""
    print("🔥 Запуск всех тестов упрощенной логики...\n")
    
    tests = [
        ("Тест упрощенной логики", run_logic_test),
        ("Тест Telegram уведомлений", run_telegram_test),
        ("Обновленный smoke test", run_smoke_test),
        ("Тесты диалогов", run_dialog_test)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"📋 {test_name}")
        print('='*60)
        
        success = await test_func()
        results.append((test_name, success))
        
        if success:
            print(f"✅ {test_name} ПРОЙДЕН")
        else:
            print(f"❌ {test_name} ПРОВАЛЕН")
    
    print(f"\n{'='*60}")
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print('='*60)
    
    for test_name, success in results:
        status = "✅ ПРОЙДЕН" if success else "❌ ПРОВАЛЕН"
        print(f"{status:<12} {test_name}")
    
    passed_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\n🎯 Итого: {passed_count}/{total_count} тестов пройдено")
    
    if passed_count == total_count:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("💥 НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ!")
        return False

async def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print_banner()
        print_help()
        return 0
    
    command = sys.argv[1].lower()
    
    print_banner()
    
    if command == "help":
        print_help()
        return 0
    elif command == "logic":
        success = await run_logic_test()
    elif command == "telegram":
        success = await run_telegram_test()
    elif command == "smoke":
        success = await run_smoke_test()
    elif command == "dialog":
        success = await run_dialog_test()
    elif command == "all":
        success = await run_all_tests()
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Используйте 'help' для справки")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 