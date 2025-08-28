"""
SQLAlchemy models for the Telegram Finance Bot
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON, Enum, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class SupportChannelType(enum.Enum):
    telegram = "telegram"
    whatsapp = "whatsapp"
    email = "email"
    website = "website"

class RequestStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class ComplaintStatus(enum.Enum):
    pending = "pending"
    resolved = "resolved"

class RequestType(enum.Enum):
    deposit = "deposit"
    withdraw = "withdraw"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    customer_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255))
    phone = Column(String(50))
    language = Column(String(10), default="ar")
    currency = Column(String(10), default="SAR")
    is_registered = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requests = relationship("Request", back_populates="user")
    complaints = relationship("Complaint", back_populates="user")
    admin_roles = relationship("AdminRole", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="actor_user", foreign_keys="AuditLog.actor_user_id")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    permissions = Column(JSON, nullable=False)  # List of permissions like ["ManageUsers", "ManagePayments"]
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    admin_roles = relationship("AdminRole", back_populates="role")

class AdminRole(Base):
    __tablename__ = "admin_roles"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="admin_roles")
    role = relationship("Role", back_populates="admin_roles")

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=False)
    default_currency = Column(String(10), default="SAR")
    is_active = Column(Boolean, default=True)
    company_metadata = Column(JSON)  # For additional company-specific settings (renamed to avoid conflict)
    company_withdraw_from = Column(Text)  # Internal company withdrawal address
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    payment_methods = relationship("PaymentMethod", back_populates="company")
    requests = relationship("Request", back_populates="company")

class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # "bank", "crypto", "wallet", etc.
    fields_schema = Column(JSON)  # Dynamic fields for this payment method
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="payment_methods")
    requests = relationship("Request", back_populates="payment_method")

class Request(Base):
    __tablename__ = "requests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    payment_method_id = Column(Integer, ForeignKey("payment_methods.id"), nullable=False)
    request_type = Column(Enum(RequestType), nullable=False)
    amount = Column(DECIMAL(precision=15, scale=2), nullable=False)
    currency = Column(String(10), nullable=False, default="SAR")
    reference = Column(Text)  # Transaction reference
    user_withdraw_to = Column(Text)  # User's withdrawal address
    status = Column(Enum(RequestStatus), default=RequestStatus.pending)
    notes = Column(Text)  # User notes
    admin_notes = Column(Text)  # Admin notes
    approved_by = Column(Integer, ForeignKey("users.id"))  # Admin who approved/rejected
    client_token = Column(String(100))  # For idempotency
    attachment_path = Column(String(500))  # Path to uploaded receipt/document
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="requests", foreign_keys=[user_id])
    company = relationship("Company", back_populates="requests")
    payment_method = relationship("PaymentMethod", back_populates="requests")
    approver = relationship("User", foreign_keys=[approved_by])

class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    attachment_path = Column(String(500))  # Path to uploaded attachment
    status = Column(Enum(ComplaintStatus), default=ComplaintStatus.pending)
    admin_reply = Column(Text)
    resolved_by = Column(Integer, ForeignKey("users.id"))  # Admin who resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="complaints", foreign_keys=[user_id])
    resolver = relationship("User", foreign_keys=[resolved_by])

class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    text_ar = Column(Text, nullable=False)
    text_en = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SupportChannel(Base):
    __tablename__ = "support_channels"
    
    id = Column(Integer, primary_key=True)
    kind = Column(Enum(SupportChannelType), nullable=False)
    value = Column(String(255), nullable=False)  # URL, username, email, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)  # "approve_request", "create_user", etc.
    entity = Column(String(50), nullable=False)  # "request", "user", "company", etc.
    entity_id = Column(Integer)  # ID of the affected entity
    before = Column(JSON)  # State before change
    after = Column(JSON)  # State after change
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    actor_user = relationship("User", back_populates="audit_logs", foreign_keys=[actor_user_id])