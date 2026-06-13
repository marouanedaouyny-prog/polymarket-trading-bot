"""
SQLite Storage for Polymarket Trading Data
Persists market data, trades, and portfolio across crashes/restarts
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / 'data'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'trading.db'


class TradingDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Markets table
        c.execute('''
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                question TEXT,
                description TEXT,
                volume REAL,
                liquidity REAL,
                outcomePrices TEXT,
                createdDate TEXT,
                updatedDate TEXT,
                scraped_at TEXT
            )
        ''')
        
        # Trades table
        c.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                market_question TEXT,
                price REAL,
                bet REAL,
                won INTEGER,
                profit REAL,
                edge REAL,
                confidence REAL,
                win_prob REAL,
                opened TEXT,
                closed TEXT,
                session_id TEXT
            )
        ''')
        
        # Sessions table
        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                trades INTEGER,
                wins INTEGER,
                losses INTEGER,
                win_rate REAL,
                starting_balance REAL,
                ending_balance REAL,
                profit REAL
            )
        ''')
        
        # Portfolio table
        c.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                date TEXT PRIMARY KEY,
                balance REAL,
                total_value REAL,
                positions INTEGER,
                trades_today INTEGER,
                profit REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_market(self, market):
        """Save market data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO markets 
            (id, question, description, volume, liquidity, outcomePrices, createdDate, updatedDate, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            market.get('id'),
            market.get('question'),
            market.get('description'),
            market.get('volume'),
            market.get('liquidity'),
            market.get('outcomePrices'),
            market.get('createdDate'),
            market.get('updatedDate'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def save_trade(self, trade, session_id=None):
        """Save trade record"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO trades
            (market_id, market_question, price, bet, won, profit, edge, confidence, win_prob, opened, closed, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.get('market_id'),
            trade.get('market', '')[:200],
            trade.get('price'),
            trade.get('bet'),
            1 if trade.get('won') else 0,
            trade.get('profit'),
            trade.get('edge'),
            trade.get('confidence'),
            trade.get('win_prob'),
            trade.get('opened'),
            trade.get('closed', datetime.now().isoformat()),
            session_id
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_trades(self, limit=100):
        """Get recent trades"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM trades ORDER BY closed DESC LIMIT ?
        ''', (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return rows
    
    def get_session_stats(self, session_id):
        """Get session statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM sessions WHERE id = ?
        ''', (session_id,))
        
        result = c.fetchone()
        conn.close()
        
        return result
    
    def save_session(self, session):
        """Save session summary"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO sessions
            (id, start_time, end_time, trades, wins, losses, win_rate, starting_balance, ending_balance, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.get('id'),
            session.get('start_time'),
            session.get('end_time'),
            session.get('trades', 0),
            session.get('wins', 0),
            session.get('losses', 0),
            session.get('win_rate', 0),
            session.get('starting_balance'),
            session.get('ending_balance'),
            session.get('profit', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def save_portfolio_snapshot(self, portfolio):
        """Save portfolio state"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO portfolio
            (date, balance, total_value, positions, trades_today, profit)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().date().isoformat(),
            portfolio.get('balance', 0),
            portfolio.get('total_value', 0),
            portfolio.get('positions', 0),
            portfolio.get('trades_today', 0),
            portfolio.get('profit', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def get_trade_history(self, days=30):
        """Get trade history for last N days"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT COUNT(*) as total_trades,
                   SUM(won) as wins,
                   SUM(profit) as total_profit,
                   AVG(win_rate) as avg_win_rate
            FROM sessions
            WHERE datetime(end_time) > datetime('now', '-' || ? || ' days')
        ''', (days,))
        
        result = c.fetchone()
        conn.close()
        
        return result


# Global instance
db = TradingDB()


def get_db():
    return db