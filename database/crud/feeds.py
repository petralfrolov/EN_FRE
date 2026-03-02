# database/crud/feeds.py

import json
import datetime
import logging
import difflib
from ..base import get_db
from ..models import CompoundFeed, CustomFeed

logger = logging.getLogger(__name__)

# --- Комбикорма ---

def create_compound_feed(user_username: str, department: str, name: str, composition: dict, nutrients: dict):
    """Сохраняет новый комбикорм в БД."""
    with get_db() as db:
        try:
            new_feed = CompoundFeed(
                name=name,
                department=department,
                user_username=user_username,
                composition_data=json.dumps(composition),
                nutrients_data=json.dumps(nutrients),
                timestamp=datetime.datetime.utcnow()
            )
            db.add(new_feed)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating compound feed: {e}")
            return False


def get_department_compound_feeds(department: str = None) -> list[CompoundFeed]:
    """Возвращает список комбикормов. Если department=None, возвращает все."""
    with get_db() as db:
        query = db.query(CompoundFeed)
        if department:
            query = query.filter(CompoundFeed.department == department)
        return query.order_by(CompoundFeed.name).all()


def delete_compound_feed(feed_id: int):
    """Удаляет комбикорм по ID."""
    with get_db() as db:
        feed = db.query(CompoundFeed).filter_by(id=feed_id).first()
        if feed:
            db.delete(feed)
            db.commit()


# --- Свои корма (Custom Feeds) ---

def create_custom_feed(user_username: str, department: str, name: str, nutrients: dict, feed_type: str = "Другое"):
    """Сохраняет новый пользовательский корм в БД."""
    with get_db() as db:
        try:
            new_feed = CustomFeed(
                name=name,
                department=department,
                user_username=user_username,
                feed_type=feed_type,
                nutrients_data=json.dumps(nutrients),
                timestamp=datetime.datetime.utcnow()
            )
            db.add(new_feed)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating custom feed: {e}")
            return False


def get_department_custom_feeds(department: str = None) -> list[CustomFeed]:
    """Возвращает список своих кормов. Если department=None, возвращает все."""
    with get_db() as db:
        query = db.query(CustomFeed)
        if department:
            query = query.filter(CustomFeed.department == department)
        return query.order_by(CustomFeed.name).all()


def delete_custom_feed(feed_id: int):
    """Удаляет свой корм по ID."""
    with get_db() as db:
        feed = db.query(CustomFeed).filter_by(id=feed_id).first()
        if feed:
            db.delete(feed)
            db.commit()


def find_feed_data_by_name(name: str) -> dict | None:
    """
    Ищет корм по названию в таблицах CustomFeed и CompoundFeed.
    Возвращает словарь с данными или None, если не найдено.
    """
    with get_db() as db:
        # 1. Сначала ищем в CustomFeed
        custom = db.query(CustomFeed).filter(CustomFeed.name == name).first()
        if custom:
            return {
                'id': custom.id,
                'name': custom.name,
                'type': 'custom',
                'nutrients_data': custom.nutrients_data
            }

        # 2. Затем в CompoundFeed
        compound = db.query(CompoundFeed).filter(CompoundFeed.name == name).first()
        if compound:
            return {
                'id': compound.id,
                'name': compound.name,
                'type': 'compound',
                'nutrients_data': compound.nutrients_data
            }

    return None


def get_all_db_feed_names() -> list[str]:
    """
    Возвращает список всех названий кормов из БД (CustomFeed + CompoundFeed)
    для реализации функции подсказок.
    """
    with get_db() as db:
        custom_names = [row[0] for row in db.query(CustomFeed.name).all()]
        compound_names = [row[0] for row in db.query(CompoundFeed.name).all()]
    return custom_names + compound_names


def get_feed_by_type_and_id(feed_type: str, feed_id: int) -> dict | None:
    """
    Ищет корм по ID и типу ('custom' или 'compound').
    Возвращает словарь с данными или None.
    """
    with get_db() as db:
        obj = None
        if feed_type == 'custom':
            obj = db.query(CustomFeed).filter(CustomFeed.id == feed_id).first()
        elif feed_type == 'compound':
            obj = db.query(CompoundFeed).filter(CompoundFeed.id == feed_id).first()

        if obj:
            return {
                'id': obj.id,
                'name': obj.name,
                'nutrients_data': obj.nutrients_data
            }
    return None


def find_similar_feeds(name: str, n: int = 3, cutoff: float = 0.4) -> list[str]:
    """
    Ищет похожие корма по названию в БД (CustomFeed + CompoundFeed).
    Использует difflib для fuzzy matching.
    """
    db_names = get_all_db_feed_names()
    close_matches = difflib.get_close_matches(name, db_names, n=n, cutoff=cutoff)
    return [f"[БД] {match}" for match in close_matches]
