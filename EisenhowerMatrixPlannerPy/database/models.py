from sqlalchemy import Column, Integer, String, DateTime, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    importance = Column(Integer, nullable=False)   # ۱ تا ۱۰
    urgency = Column(Integer, nullable=False)      # ۱ تا ۱۰
    canvas_x = Column(Float)                       # موقعیت واقعی روی کانواس
    canvas_y = Column(Float)
    deadline = Column(DateTime, nullable=True)
    status = Column(String, default="pending")     # pending, in_progress, done
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.title} ({self.importance}/{self.urgency})>"