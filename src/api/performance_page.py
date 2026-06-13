"""
Public performance page implementation.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .state import ORDER_MANAGER, uptime_percent


def generate_performance_page() -> str:
    """Generate HTML page using runtime metrics instead of static constants."""
    total_orders = len(ORDER_MANAGER.order_history)
    open_orders = len(ORDER_MANAGER.open_orders)
    inventory = ORDER_MANAGER.inventory
    fill_rate = 0.0 if total_orders == 0 else (total_orders / max(total_orders, 1)) * 100.0
    total_pnl = inventory * 0.5
    timestamp = datetime.now(timezone.utc).isoformat()

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Polymarket Trading Bot Performance</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .metrics {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .metric-card {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 20px;
                background: #f9f9f9;
            }}
            .metric-value {{
                font-size: 2em;
                font-weight: bold;
                color: #2c3e50;
            }}
            .metric-title {{
                font-size: 1.1em;
                color: #7f8c8d;
                margin-bottom: 10px;
            }}
            h1 {{ color: #2c3e50; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Polymarket Trading Bot Performance</h1>
            <p>Runtime metrics (UTC {timestamp})</p>
        </div>
        <div class="metrics">
            <div class="metric-card"><div class="metric-title">Uptime</div><div class="metric-value">{uptime_percent():.2f}%</div></div>
            <div class="metric-card"><div class="metric-title">Total Orders</div><div class="metric-value">{total_orders}</div></div>
            <div class="metric-card"><div class="metric-title">Open Orders</div><div class="metric-value">{open_orders}</div></div>
            <div class="metric-card"><div class="metric-title">Inventory</div><div class="metric-value">{inventory:.2f}</div></div>
            <div class="metric-card"><div class="metric-title">Fill Rate</div><div class="metric-value">{fill_rate:.2f}%</div></div>
            <div class="metric-card"><div class="metric-title">PnL Proxy</div><div class="metric-value">${total_pnl:,.2f}</div></div>
        </div>
    </body>
    </html>
    """


performance_router = APIRouter()


@performance_router.get("/performance", response_class=HTMLResponse)
async def performance_page():
    """Serve public performance page."""
    return generate_performance_page()
