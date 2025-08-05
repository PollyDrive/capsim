#!/usr/bin/env python3
"""
Entry point для запуска CAPSIM через python -m capsim
"""

import sys
import argparse
from .cli.run_simulation import main as run_main


def main():
    """Main entry point для capsim модуля."""
    parser = argparse.ArgumentParser(
        description="CAPSIM 2.0 - Agent-based Discrete Event Simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Команда run
    run_parser = subparsers.add_parser('run', help='Запустить симуляцию')
    run_parser.add_argument("--agents", type=int, default=100, help="Количество агентов")
    run_parser.add_argument("--days", type=int, default=1, help="Продолжительность в днях")
    run_parser.add_argument("--minutes", type=int, help="Продолжительность в минутах (альтернатива --days)")
    run_parser.add_argument("--db-url", type=str, help="URL базы данных")
    run_parser.add_argument("--speed", type=float, default=240.0, help="Фактор скорости симуляции (240x = быстро, 1x = реальное время)")
    run_parser.add_argument("--240x", action="store_const", const=240.0, dest="speed", help="Быстрая симуляция (эквивалент --speed 240)")
    run_parser.add_argument("--test", action="store_true", help="Режим тестирования (короткая симуляция)")
    
    # Команда stop
    stop_parser = subparsers.add_parser('stop', help='Остановить активную симуляцию')
    stop_parser.add_argument('simulation_id', nargs='?', help='ID симуляции для остановки (опционально)')
    stop_parser.add_argument("--force", action="store_true", help="Принудительная остановка")
    stop_parser.add_argument("--db-url", type=str, help="URL базы данных")
    
    # Команда status
    status_parser = subparsers.add_parser('status', help='Показать статус активных симуляций')
    status_parser.add_argument("--db-url", type=str, help="URL базы данных")
    
    args = parser.parse_args()
    
    if args.command == 'run':
        # Преобразуем минуты в дни если указаны
        if args.minutes:
            args.days = args.minutes / 1440.0
        
        # Переходим на аргументы run_simulation
        sys.argv = [
            'run_simulation.py',
            '--agents', str(args.agents),
            '--speed', str(args.speed)
        ]
        
        # Добавляем дни только если не были переконвертированы из минут
        if args.minutes:
            sys.argv.extend(['--days', str(args.days)])
        else:
            sys.argv.extend(['--days', str(args.days)])
        
        if args.db_url:
            sys.argv.extend(['--db-url', args.db_url])
        
        if args.test:
            sys.argv.append('--test')
        
        run_main()
    
    elif args.command == 'stop':
        from .cli.stop_simulation import main as stop_main
        
        # Переходим на аргументы stop_simulation
        sys.argv = ['stop_simulation.py']
        
        if args.simulation_id:
            sys.argv.append(args.simulation_id)
        
        if args.force:
            sys.argv.append('--force')
            
        if args.db_url:
            sys.argv.extend(['--db-url', args.db_url])
        
        stop_main()
    
    elif args.command == 'status':
        from .cli.status_simulation import main as status_main
        
        # Переходим на аргументы status_simulation
        sys.argv = ['status_simulation.py']
        
        if args.db_url:
            sys.argv.extend(['--db-url', args.db_url])
        
        status_main()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 