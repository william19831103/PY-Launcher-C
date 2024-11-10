from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    security_password = Column(String(255), nullable=False)
    email = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_banned = Column(Boolean, default=False)

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    name = Column(String(50), unique=True, nullable=False)
    level = Column(Integer, default=1)
    class_id = Column(Integer)
    race_id = Column(Integer)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class ServerAnnouncement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True)
    content = Column(String(500), nullable=False)
    priority = Column(Integer, default=0)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_active = Column(Boolean, default=True) 