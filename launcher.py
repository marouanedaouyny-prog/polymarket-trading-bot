"""
Trading Bot Launcher
"""

import os


def main() -> None:
    print("\n" + "=" * 60)
    print("  POLYMARKET TRADING BOT LAUNCHER")
    print("=" * 60)
    print("\nAvailable Options:")
    print("  1. Start Full Stack (API + Frontend)")
    print("  2. Start API only")
    print("  3. Run Enhanced Bot - Paper Trading (5 min)")
    print("  4. Run Production Bot - Paper Trading (5 min)")
    print("  5. Run Automated Tests (5 runs)")
    print("  6. Exit")
    print("=" * 60)

    choice = input("\nEnter choice (1-6): ").strip()

    if choice == "1":
        os.system("python run_full_stack.py")
    elif choice == "2":
        os.system("uvicorn src.api.main:app --host 127.0.0.1 --port 8000")
    elif choice == "3":
        os.system("python scripts/bots/enhanced_bot.py paper 5")
    elif choice == "4":
        os.system("python scripts/bots/production_bot.py paper 5")
    elif choice == "5":
        os.system("python scripts/tests/auto_test_trader.py")
    else:
        print("\nExiting...")


if __name__ == "__main__":
    main()
