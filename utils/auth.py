"""
Authentication and authorization utilities
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Role, AdminRole, AuditLog
from config import ADMINS

logger = logging.getLogger(__name__)

# Define available permissions
class Permissions:
    MANAGE_USERS = "ManageUsers"
    MANAGE_PAYMENTS = "ManagePayments"
    APPROVE_TX = "ApproveTx"
    REPORTS = "Reports"
    BROADCAST = "Broadcast"
    SETTINGS = "Settings"
    MANAGE_ADMINS = "ManageAdmins"  # Super admin only
    
    ALL_PERMISSIONS = [
        MANAGE_USERS, MANAGE_PAYMENTS, APPROVE_TX, 
        REPORTS, BROADCAST, SETTINGS, MANAGE_ADMINS
    ]

async def is_super_admin(telegram_id: int) -> bool:
    """Check if user is a super admin (defined in .env ADMINS)"""
    return telegram_id in ADMINS

async def get_user_permissions(session: AsyncSession, telegram_id: int) -> List[str]:
    """Get all permissions for a user"""
    # Super admins have all permissions
    if await is_super_admin(telegram_id):
        return Permissions.ALL_PERMISSIONS
    
    # Get user and their roles
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_admin:
        return []
    
    # Get all roles for this user
    roles_result = await session.execute(
        select(Role).join(AdminRole).where(AdminRole.user_id == user.id)
    )
    roles = roles_result.scalars().all()
    
    # Collect all permissions from all roles
    permissions = set()
    for role in roles:
        if role.permissions:
            permissions.update(role.permissions)
    
    return list(permissions)

async def has_permission(session: AsyncSession, telegram_id: int, permission: str) -> bool:
    """Check if user has a specific permission"""
    user_permissions = await get_user_permissions(session, telegram_id)
    return permission in user_permissions

async def require_permission(session: AsyncSession, telegram_id: int, permission: str) -> bool:
    """Raise exception if user doesn't have required permission"""
    if not await has_permission(session, telegram_id, permission):
        raise PermissionError(f"User {telegram_id} does not have permission: {permission}")
    return True

async def is_guest_mode(session: AsyncSession, telegram_id: int) -> bool:
    """Check if user is in guest mode (not registered)"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    return user is None or not user.is_registered

async def create_audit_log(
    session: AsyncSession,
    actor_telegram_id: int,
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None
) -> None:
    """Create an audit log entry"""
    try:
        # Get the actor user
        result = await session.execute(
            select(User).where(User.telegram_id == actor_telegram_id)
        )
        actor_user = result.scalar_one_or_none()
        
        if not actor_user:
            logger.warning(f"Cannot create audit log: user {actor_telegram_id} not found")
            return
        
        audit_log = AuditLog(
            actor_user_id=actor_user.id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            before=before,
            after=after
        )
        
        session.add(audit_log)
        await session.commit()
        
        logger.info(f"Audit log created: {action} on {entity} by user {actor_telegram_id}")
        
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        await session.rollback()

async def ensure_default_roles(session: AsyncSession) -> None:
    """Ensure default roles exist in the database"""
    try:
        # Check if roles already exist
        result = await session.execute(select(Role))
        existing_roles = result.scalars().all()
        
        if existing_roles:
            return  # Roles already exist
        
        # Create default roles
        default_roles = [
            {
                "name": "Super Admin",
                "permissions": Permissions.ALL_PERMISSIONS
            },
            {
                "name": "Finance Manager", 
                "permissions": [Permissions.MANAGE_PAYMENTS, Permissions.APPROVE_TX, Permissions.REPORTS]
            },
            {
                "name": "User Manager",
                "permissions": [Permissions.MANAGE_USERS, Permissions.REPORTS]
            },
            {
                "name": "Support Agent",
                "permissions": [Permissions.MANAGE_USERS, Permissions.BROADCAST]
            },
            {
                "name": "Viewer",
                "permissions": [Permissions.REPORTS]
            }
        ]
        
        for role_data in default_roles:
            role = Role(
                name=role_data["name"],
                permissions=role_data["permissions"]
            )
            session.add(role)
        
        await session.commit()
        logger.info("Default roles created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create default roles: {e}")
        await session.rollback()
        raise