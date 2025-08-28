"""
SQLAlchemy models for the Telegram Finance Bot
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    customer_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(255))
    phone = Column(String(50))
    language = Column(String(10), default="ar")
    is_registered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    requests = relationship("Request", back_populates="user")
    complaints = relationship("Complaint", back_populates="user")

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True)
    name_ar = Column(String(255), nullable=False)
    name_en = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
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
    request_type = Column(String(20), nullable=False)  # "deposit" or "withdraw"
    amount = Column(Float, nullable=False)
    reference = Column(Text)  # Transaction reference or address for withdrawals
    destination_address = Column(Text)  # For withdrawals only
    status = Column(String(20), default="pending")  # pending, approved, rejected
    admin_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="requests")
    company = relationship("Company", back_populates="requests")
    payment_method = relationship("PaymentMethod", back_populates="requests")

class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(255))
    message = Column(Text, nullable=False)
    status = Column(String(20), default="pending")  # pending, resolved
    admin_reply = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="complaints")

class Ad(Base):
    __tablename__ = "ads"
    
    id = Column(Integer, primary_key=True)
    title_ar = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=False)
    text_ar = Column(Text, nullable=False)
    text_en = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, nullable=False)  # Admin telegram_id
    created_at = Column(DateTime, default=datetime.utcnow)
    broadcast_at = Column(DateTime)  # When it was broadcasted