from sqlalchemy import Column, String, DateTime, Date, Integer, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    biological_sex = Column(String(1), CheckConstraint("biological_sex IN ('M', 'F')"), nullable=False)
    creation_date = Column(DateTime, default=func.now())

class Test(Base):
    __tablename__ = "Tests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('Users.id'))
    test_name = Column(String, index=True)
    url = Column(String)
    submission_date = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="tests")

User.tests = relationship("Test", order_by=Test.id, back_populates="user")
