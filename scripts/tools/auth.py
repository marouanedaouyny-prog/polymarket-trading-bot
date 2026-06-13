"""
Authentication & Security Module
Simple API key + session based auth for dashboard
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
import os

SECRET_KEY = os.getenv("SECRET_KEY", "polymarket-secret-key-change-in-production")
API_KEY_FILE = "data/auth/api_keys.json"
SESSION_FILE = "data/auth/sessions.json"

os.makedirs("data/auth", exist_ok=True)

security = HTTPBearer(auto_error=False)

class AuthManager:
    def __init__(self):
        self.api_keys = self.load_api_keys()
        self.sessions = self.load_sessions()

    def load_api_keys(self) -> Dict[str, dict]:
        try:
            with open(API_KEY_FILE, 'r') as f:
                return json.load(f)
        except:
            # Default admin key
            default = {"admin": {"key": self.hash_key("admin"), "name": "Admin", "created": datetime.now().isoformat()}}
            self.save_api_keys(default)
            return default

    def save_api_keys(self, keys: Dict[str, dict]):
        with open(API_KEY_FILE, 'w') as f:
            json.dump(keys, f, indent=2)

    def load_sessions(self) -> Dict[str, dict]:
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}

    def save_sessions(self, sessions: Dict[str, dict]):
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)

    def hash_key(self, raw: str) -> str:
        return hashlib.sha256((raw + SECRET_KEY).encode()).hexdigest()

    def verify_api_key(self, raw_key: str) -> Optional[dict]:
        hashed = self.hash_key(raw_key)
        for user_id, data in self.api_keys.items():
            if data['key'] == hashed:
                return {"id": user_id, **data}
        return None

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(days=7)).isoformat()
        self.sessions[token] = {"user_id": user_id, "expires": expires}
        self.save_sessions(self.sessions)
        return token

    def verify_session(self, token: str) -> Optional[dict]:
        session = self.sessions.get(token)
        if not session:
            return None
        if datetime.fromisoformat(session['expires']) < datetime.now():
            del self.sessions[token]
            self.save_sessions(self.sessions)
            return None
        return session

auth_manager = AuthManager()

# Dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate API key or session token"""
    if credentials:
        # Try session token first
        session = auth_manager.verify_session(credentials.credentials)
        if session:
            return session

        # Try API key
        user = auth_manager.verify_api_key(credentials.credentials)
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Optional auth (doesn't fail if not provided)
async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except:
        return None
