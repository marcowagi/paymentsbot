"""
Handlers package initialization
Aggregates all bot handlers
"""

from aiogram import Router
from . import start, user_settings, finance, complaints, admin, companies, broadcast, announcements, reports, backups

def setup_handlers() -> Router:
    """Setup and return router with all handlers"""
    router = Router()
    
    # Include all handler routers
    router.include_router(start.router)
    router.include_router(user_settings.router)
    router.include_router(finance.router)
    router.include_router(complaints.router)
    router.include_router(admin.router)
    router.include_router(companies.router)
    router.include_router(broadcast.router)
    router.include_router(announcements.router)
    router.include_router(reports.router)
    router.include_router(backups.router)
    
    return router