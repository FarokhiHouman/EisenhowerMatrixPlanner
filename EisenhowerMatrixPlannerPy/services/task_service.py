from database.db import SessionLocal
from database.models import Task
from datetime import datetime, timedelta

def get_session():
    return SessionLocal()

def create_task(title: str, importance: int = 5, urgency: int = 5, canvas_x=None, canvas_y=None):
    session = get_session()
    try:
        task = Task(title=title, importance=importance, urgency=urgency,
                    canvas_x=canvas_x, canvas_y=canvas_y)
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    finally:
        session.close()

# افزایش خودکار urgency وقتی deadline نزدیک است
def increase_urgency_for_near_deadlines():
    session = get_session()
    try:
        now = datetime.utcnow()
        soon = now + timedelta(days=2)
        tasks = session.query(Task).filter(Task.deadline != None,
                                          Task.deadline <= soon,
                                          Task.urgency < 10).all()
        for t in tasks:
            t.urgency = min(10, t.urgency + 2)
            t.updated_at = now
        session.commit()
    finally:
        session.close()