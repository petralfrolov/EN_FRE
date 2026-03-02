# database/crud/rations.py

import json
import datetime
import logging
from ..base import get_db
from ..models import SavedRation

logger = logging.getLogger(__name__)

def autosave_ration(user_username: str, department: str, ration_data_dict: dict):
    with get_db() as db:
        try:
            existing = db.query(SavedRation).filter_by(user_username=user_username, is_autosave=True).first()
            ration_json = json.dumps(ration_data_dict)
            now = datetime.datetime.utcnow()
            if existing:
                existing.ration_data = ration_json
                existing.timestamp = now
                existing.ration_name = f"Автосохранение от {now.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                new_save = SavedRation(
                    user_username=user_username, department=department,
                    ration_name=f"Автосохранение от {now.strftime('%Y-%m-%d %H:%M:%S')}",
                    ration_data=ration_json, timestamp=now, is_autosave=True
                )
                db.add(new_save)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Autosave error: {e}")


def create_manual_save(user_username: str, department: str, ration_name: str, 
                       ration_data_dict: dict, predictions_dict: dict = None):
    """Сохраняет рацион вручную с опциональными прогнозами."""
    with get_db() as db:
        try:
            ration_json = json.dumps(ration_data_dict)
            predictions_json = json.dumps(predictions_dict) if predictions_dict else None
            new_ration = SavedRation(
                user_username=user_username, department=department, ration_name=ration_name,
                ration_data=ration_json, predictions_data=predictions_json,
                is_autosave=False, timestamp=datetime.datetime.utcnow()
            )
            db.add(new_ration)
            db.commit()
        except Exception as e:
            db.rollback()
            raise


def get_user_autosave(user_username: str) -> SavedRation | None:
    with get_db() as db:
        return db.query(SavedRation).filter_by(user_username=user_username, is_autosave=True).first()


def get_user_manual_saves(user_username: str) -> list[SavedRation]:
    with get_db() as db:
        return db.query(SavedRation).filter_by(user_username=user_username, is_autosave=False).order_by(
            SavedRation.timestamp.desc()).all()


def get_department_saves(department: str, current_username: str) -> list[SavedRation]:
    with get_db() as db:
        return db.query(SavedRation).filter(
            SavedRation.department == department,
            SavedRation.user_username != current_username
        ).order_by(SavedRation.timestamp.desc()).all()


def get_colleague_saves(departments: list[str], current_username: str) -> list[SavedRation]:
    """Возвращает сохранения коллег из списка подразделений (хозяйства)."""
    with get_db() as db:
        return db.query(SavedRation).filter(
            SavedRation.department.in_(departments),
            SavedRation.user_username != current_username
        ).order_by(SavedRation.timestamp.desc()).all()


def load_ration_data(ration_id: int) -> dict | None:
    with get_db() as db:
        ration = db.query(SavedRation).filter_by(id=ration_id).first()
        if ration:
            try:
                return json.loads(ration.ration_data)
            except Exception:
                return None
        return None


def delete_saved_ration(ration_id: int) -> bool:
    """Удаляет сохраненный рацион по ID.
    
    Returns:
        bool: True если удаление успешно, False иначе.
    """
    with get_db() as db:
        try:
            ration = db.query(SavedRation).filter_by(id=ration_id).first()
            if ration:
                db.delete(ration)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting saved ration: {e}")
            return False


def get_rations_with_predictions(department: str = None) -> list[SavedRation]:
    """
    Возвращает рационы с сохраненными прогнозами.
    
    Args:
        department: Опционально фильтрует по подразделению
    
    Returns:
        Список SavedRation с непустым predictions_data
    """
    with get_db() as db:
        query = db.query(SavedRation).filter(
            SavedRation.predictions_data.isnot(None),
            SavedRation.is_autosave == False
        )
        if department:
            query = query.filter(SavedRation.department == department)
        return query.order_by(SavedRation.timestamp.desc()).all()
