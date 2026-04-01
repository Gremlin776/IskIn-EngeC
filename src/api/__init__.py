# -*- coding: utf-8 -*-
"""
FastAPI приложение
"""

from src.api.main import app, run
from src.api.deps import get_db, get_current_user, get_current_user_optional
from src.api.router import api_router

__all__ = [
    "app",
    "run",
    "get_db",
    "get_current_user",
    "get_current_user_optional",
    "api_router",
]
