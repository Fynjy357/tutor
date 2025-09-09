#!/usr/bin/env python3
import pytest
import sys
import os
import logging

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Настройка логирования для тестов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('payment_tests.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def run_tests():
    """Запуск всех тестов платежного модуля"""
    logger = logging.getLogger('TestRunner')
    logger.info("🚀 Запуск тестов платежного модуля")
    
    # Путь к тестам (исправляем путь)
    test_path = os.path.dirname(__file__)
    
    # Аргументы для pytest
    pytest_args = [
        test_path,
        "-v",           # Подробный вывод
        "--tb=short",   # Короткий traceback
        "--no-header",  # Без заголовка
        "--color=yes",  # Цветной вывод
        "-x"            # Остановка при первой ошибке
    ]
    
    # Запускаем тесты
    exit_code = pytest.main(pytest_args)
    
    # Анализируем результаты
    if exit_code == 0:
        logger.info("✅ Все тесты прошли успешно!")
    else:
        logger.error(f"❌ Тесты завершились с ошибкой. Код возврата: {exit_code}")
    
    return exit_code

def run_specific_test(test_file, test_function=None):
    """Запуск конкретного теста"""
    logger = logging.getLogger('TestRunner')
    
    test_path = os.path.join(os.path.dirname(__file__), test_file)
    
    if test_function:
        test_path += f"::{test_function}"
    
    logger.info(f"🔍 Запуск теста: {test_path}")
    
    pytest_args = [
        test_path,
        "-v",
        "--tb=short",
        "--no-header",
        "--color=yes"
    ]
    
    exit_code = pytest.main(pytest_args)
    return exit_code

def run_test_coverage():
    """Запуск тестов с покрытием кода"""
    logger = logging.getLogger('TestRunner')
    logger.info("📊 Запуск тестов с проверкой покрытия")
    
    test_path = os.path.dirname(__file__)
    source_path = os.path.join(os.path.dirname(__file__), '..')
    
    pytest_args = [
        test_path,
        "-v",
        "--tb=short",
        "--cov=" + source_path,
        "--cov-report=term",
        "--cov-report=html:coverage_report"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        logger.info("✅ Тесты с покрытия завершены успешно!")
        logger.info("📁 Отчет о покрытии: coverage_report/index.html")
    else:
        logger.error(f"❌ Тесты с покрытия завершились с ошибкой")
    
    return exit_code

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Запуск тестов платежного модуля')
    parser.add_argument('--test', '-t', help='Запустить конкретный тестовый файл')
    parser.add_argument('--function', '-f', help='Запустить конкретную тестовую функцию')
    parser.add_argument('--coverage', '-c', action='store_true', help='Запустить тесты с проверкой покрытия')
    parser.add_argument('--all', '-a', action='store_true', help='Запустить все тесты (по умолчанию)')
    
    args = parser.parse_args()
    
    if args.test:
        exit_code = run_specific_test(args.test, args.function)
    elif args.coverage:
        exit_code = run_test_coverage()
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)