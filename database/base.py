# database/base.py

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from config import DB_PATH

logger = logging.getLogger(__name__)

# --- Настройка БД (общая с EN_FAE) ---
DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Список подразделений ---
DEPARTMENTS = ['ЖК Высокое', 'ЖK Бобров', 'ЖК Петропавловка']
