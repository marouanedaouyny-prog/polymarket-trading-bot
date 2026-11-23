from datetime import date, timedelta

from agent_trading_system import TradingAgentSystem


class _FakeRiskManager:
    def __init__(self):
        self.reset_calls = []

    def reset_daily(self, balance):
        self.reset_calls.append(balance)


def _bare_system(**attrs):
    system = TradingAgentSystem.__new__(TradingAgentSystem)
    system.trades_today = 20
    system.daily_start = 10.0
    system.balance = 25.0
    system.risk_manager = None
    system._session_date = date.today() - timedelta(days=1)
    for key, value in attrs.items():
        setattr(system, key, value)
    return system


def test_roll_daily_state_resets_counters_on_new_day():
    system = _bare_system()
    system._roll_daily_state()
    assert system.trades_today == 0
    assert system.daily_start == 25.0
    assert system._session_date == date.today()


def test_roll_daily_state_resets_risk_manager():
    rm = _FakeRiskManager()
    system = _bare_system(risk_manager=rm)
    system._roll_daily_state()
    assert rm.reset_calls == [25.0]


def test_roll_daily_state_is_idempotent_within_day():
    rm = _FakeRiskManager()
    system = _bare_system(risk_manager=rm, _session_date=date.today())
    system.trades_today = 7
    system.daily_start = 20.0
    system._roll_daily_state()
    assert system.trades_today == 7
    assert system.daily_start == 20.0
    assert rm.reset_calls == []
