# database/crud/users.py

import json
import os
import bcrypt
from sqlalchemy.exc import IntegrityError
from ..base import get_db
from ..models import User
from config import DB_PATH

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def check_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_user(fio: str, username: str, password: str, department: str, is_admin: bool = False) -> User | None:
    hashed = hash_password(password)
    new_user = User(fio=fio, username=username, hashed_password=hashed, department=department, is_admin=is_admin)
    with get_db() as db:
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
        except IntegrityError:
            db.rollback()
            return None
        except Exception:
            db.rollback()
            raise


def get_user(username: str) -> User | None:
    with get_db() as db:
        return db.query(User).filter(User.username == username).first()


def get_user_settings(username: str) -> dict:
    """Получить настройки пользователя. Возвращает dict с дефолтами если настройки не заданы."""
    default_settings = {
        "excel_file_path": None,
        "limits_file_path": None,
        "target_ranges": None,
        "column_mappings": {},
        "sheet_mapping": None,
    }
    if not os.path.exists(DB_PATH):
        return default_settings
        
    with get_db() as db:
        user = db.query(User).filter(User.username == username).first()
        if user and user.settings:
            try:
                saved = json.loads(user.settings)
                # Мержим с дефолтами
                for key in default_settings:
                    if key not in saved:
                        saved[key] = default_settings[key]
                return saved
            except Exception:
                return default_settings
        return default_settings


def update_user_settings(username: str, settings: dict) -> bool:
    """Обновить настройки пользователя."""
    if not os.path.exists(DB_PATH):
        return True

    with get_db() as db:
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False
            user.settings = json.dumps(settings)
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False


def update_user_profile(username: str, fio: str, department: str) -> bool:
    """Обновить ФИО и подразделение пользователя."""
    with get_db() as db:
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return False
            user.fio = fio
            user.department = department
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
