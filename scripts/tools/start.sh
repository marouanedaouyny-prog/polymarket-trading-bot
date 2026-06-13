#!/bin/bash
# Start Trading Bot

echo "=========================================="
echo "  POLYMARKET TRADING BOT"
echo "=========================================="
echo ""
echo "Options:"
echo "  1. Start Full Stack (API + Frontend)"
echo "  2. Start API only"
echo "  3. Run Enhanced Bot (5 min)"
echo "  4. Run Production Bot (5 min)"
echo "  5. Run Auto Tests (5 runs)"
echo ""
echo -n "Select option: "
read opt

case $opt in
    1) python run_full_stack.py ;;
    2) python api_server.py ;;
    3) python enhanced_bot.py paper 5 ;;
    4) python production_bot.py paper 5 ;;
    5) python auto_test_trader.py ;;
    *) echo "Invalid option" ;;
esac
