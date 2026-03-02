# database/models.py

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from .base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    fio = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    department = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    settings = Column(String, nullable=True)  # JSON с настройками пользователя


class SavedRation(Base):
    __tablename__ = "saved_rations"
    id = Column(Integer, primary_key=True, index=True)
    user_username = Column(String, index=True, nullable=False)
    department = Column(String, index=True, nullable=False)
    ration_name = Column(String, nullable=False)
    ration_data = Column(String, nullable=False)  # JSON
    predictions_data = Column(String, nullable=True)  # JSON с прогнозами кислот
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    is_autosave = Column(Boolean, default=False, nullable=False, index=True)


class CompoundFeed(Base):
    __tablename__ = "compound_feeds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    department = Column(String, index=True, nullable=False)  # Видимость в пределах подразделения
    user_username = Column(String, nullable=False)  # Кто создал

    # Состав: {feed_id: weight, ...} для истории/редактирования
    composition_data = Column(String, nullable=False)

    # Итоговая питательность: {nutrient_name: value, ...}
    nutrients_data = Column(String, nullable=False)

    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class CustomFeed(Base):
    __tablename__ = "custom_feeds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    department = Column(String, index=True, nullable=False)
    user_username = Column(String, nullable=False)
    feed_type = Column(String, nullable=False, default="Другое")

    # Питательность: {nutrient_name: value, ...}
    nutrients_data = Column(String, nullable=False)

    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class MilkAnalysis(Base):
    __tablename__ = "milk_analyses"
    id = Column(Integer, primary_key=True, index=True)
    ration_name = Column(String, index=True, nullable=False)  # Сопоставляется с Источник из Excel
    analysis_date = Column(DateTime, nullable=False)  # Дата анализа
    
    # Жирные кислоты (значения %)
    # --- De novo кислоты (C4–C14) ---
    butyric = Column(Float, nullable=True)        # Масляная C4:0
    caproic = Column(Float, nullable=True)        # Капроновая C6:0
    caprylic = Column(Float, nullable=True)       # Каприловая C8:0
    capric = Column(Float, nullable=True)         # Каприновая C10:0
    decenoic = Column(Float, nullable=True)       # Деценовая C10:1
    lauric = Column(Float, nullable=True)         # Лауриновая C12:0
    myristic = Column(Float, nullable=True)       # Миристиновая C14:0
    myristoleic = Column(Float, nullable=True)    # Миристолеиновая C14:1
    
    # --- Основные кислоты ---
    palmitic = Column(Float, nullable=True)       # Пальмитиновая C16:0
    palmitoleic = Column(Float, nullable=True)    # Пальмитолеиновая C16:1
    stearic = Column(Float, nullable=True)        # Стеариновая C18:0
    oleic = Column(Float, nullable=True)          # Олеиновая C18:1
    linoleic = Column(Float, nullable=True)       # Линолевая C18:2
    linolenic = Column(Float, nullable=True)      # Линоленовая C18:3
    
    # --- Длинноцепочечные ---
    arachidic = Column(Float, nullable=True)      # Арахиновая C20:0
    behenic = Column(Float, nullable=True)        # Бегеновая C22:0
    
    department = Column(String, index=True, nullable=False)
    user_username = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
