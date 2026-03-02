# database/crud/milk.py

import datetime
import logging
from ..base import get_db
from ..models import MilkAnalysis

logger = logging.getLogger(__name__)

# Все поля ЖК в модели MilkAnalysis
_ALL_ACID_FIELDS = [
    'butyric', 'caproic', 'caprylic', 'capric', 'decenoic',
    'lauric', 'myristic', 'myristoleic',
    'palmitic', 'palmitoleic', 'stearic', 'oleic',
    'linoleic', 'linolenic', 'arachidic', 'behenic',
]


def save_milk_analyses(analyses_list: list[dict], department: str, user_username: str) -> tuple[int, int]:
    """
    Сохраняет анализы молока с дедупликацией.
    Подразделение берётся из каждой записи (поле 'department'),
    если оно отсутствует — используется значение аргумента department.
    """
    added, skipped = 0, 0
    
    with get_db() as db:
        try:
            for analysis in analyses_list:
                # Проверяем существование записи с таким же ration_name и датой
                existing = db.query(MilkAnalysis).filter(
                    MilkAnalysis.ration_name == analysis['ration_name'],
                    MilkAnalysis.analysis_date == analysis['analysis_date']
                ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                # Подразделение: из строки Excel или fallback
                row_dept = analysis.get('department') or department
                
                kwargs = {
                    'ration_name': analysis['ration_name'],
                    'analysis_date': analysis['analysis_date'],
                    'department': row_dept,
                    'user_username': user_username,
                }
                # Добавляем все кислоты
                for field in _ALL_ACID_FIELDS:
                    kwargs[field] = analysis.get(field)
                
                new_analysis = MilkAnalysis(**kwargs)
                db.add(new_analysis)
                added += 1
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving milk analyses: {e}")
            raise
    
    return added, skipped


def get_analyses_for_ration(ration_name: str) -> list[MilkAnalysis]:
    """Возвращает все анализы для заданного рациона."""
    with get_db() as db:
        return db.query(MilkAnalysis).filter(
            MilkAnalysis.ration_name == ration_name
        ).order_by(MilkAnalysis.analysis_date.desc()).all()


def get_latest_analysis_for_ration(ration_name: str) -> MilkAnalysis | None:
    """Возвращает последний анализ для заданного рациона (по дате)."""
    with get_db() as db:
        return db.query(MilkAnalysis).filter(
            MilkAnalysis.ration_name == ration_name
        ).order_by(MilkAnalysis.analysis_date.desc()).first()


def get_all_milk_analyses(department: str = None) -> list[MilkAnalysis]:
    """Возвращает все анализы молока, опционально фильтруя по подразделению."""
    with get_db() as db:
        query = db.query(MilkAnalysis)
        if department:
            query = query.filter(MilkAnalysis.department == department)
        return query.order_by(MilkAnalysis.analysis_date.desc()).all()


def get_analyses_by_department_period(
    department: str = None,
    date_from: datetime.date = None,
    date_to: datetime.date = None,
) -> list[MilkAnalysis]:
    """Возвращает анализы с фильтрацией по подразделению и периоду."""
    with get_db() as db:
        query = db.query(MilkAnalysis)
        if department:
            query = query.filter(MilkAnalysis.department == department)
        if date_from:
            query = query.filter(MilkAnalysis.analysis_date >= datetime.datetime.combine(date_from, datetime.time.min))
        if date_to:
            query = query.filter(MilkAnalysis.analysis_date <= datetime.datetime.combine(date_to, datetime.time.max))
        return query.order_by(MilkAnalysis.analysis_date.desc()).all()


def get_ration_names_for_department(
    department: str = None,
    date_from: datetime.date = None,
    date_to: datetime.date = None,
) -> list[str]:
    """Возвращает уникальные имена рационов для подразделения/периода."""
    with get_db() as db:
        query = db.query(MilkAnalysis.ration_name).distinct()
        if department:
            query = query.filter(MilkAnalysis.department == department)
        if date_from:
            query = query.filter(MilkAnalysis.analysis_date >= datetime.datetime.combine(date_from, datetime.time.min))
        if date_to:
            query = query.filter(MilkAnalysis.analysis_date <= datetime.datetime.combine(date_to, datetime.time.max))
        
        # Фильтруем пустые значения
        query = query.filter(
            MilkAnalysis.ration_name.isnot(None),
            MilkAnalysis.ration_name != "",
            MilkAnalysis.ration_name != "nan"
        )
        return [row[0] for row in query.all()]


def get_analyses_for_ration_in_period(
    ration_name: str,
    department: str = None,
    date_from: datetime.date = None,
    date_to: datetime.date = None,
) -> list[MilkAnalysis]:
    """Возвращает анализы для конкретного рациона в заданном периоде."""
    with get_db() as db:
        query = db.query(MilkAnalysis).filter(MilkAnalysis.ration_name == ration_name)
        if department:
            query = query.filter(MilkAnalysis.department == department)
        if date_from:
            query = query.filter(MilkAnalysis.analysis_date >= datetime.datetime.combine(date_from, datetime.time.min))
        if date_to:
            query = query.filter(MilkAnalysis.analysis_date <= datetime.datetime.combine(date_to, datetime.time.max))
        return query.order_by(MilkAnalysis.analysis_date.asc()).all()
