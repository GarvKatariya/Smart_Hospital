from sqlalchemy import Column, String, Boolean, DateTime
from app.db.base import Base, BaseModel
from datetime import datetime
import uuid

class User(Base, BaseModel):
    __tablename__ = 'users'
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # patient, doctor, admin
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
