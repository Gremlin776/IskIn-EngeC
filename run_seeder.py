#!/usr/bin/env python3
"""
Скрипт для запуска seeder базы данных

Использование:
    python run_seeder.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PATH
sys.path.insert(0, str(Path(__file__).parent))

from src.core.seeder import main as seed_main


def main():
    """Точка входа для CLI"""
    print("=" * 60)
    print("  Инженерный ИскИн — Seeder тестовых данных")
    print("=" * 60)
    print()
    
    try:
        asyncio.run(seed_main())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
