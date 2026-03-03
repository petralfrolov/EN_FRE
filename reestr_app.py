"""
EN_FRE — самостоятельное Streamlit-приложение для управления реестром кормов.

Включает:
  - Автоматизация реестра (загрузка лабораторных файлов, добавление в реестр)
  - Визуализация реестра (фильтры, графики, статистика)

Запуск:
  streamlit run reestr_app.py
"""

import streamlit as st
import os
import uuid
import logging
import time

import database as db
from config import EXCEL_FILE_PATH, PAGE_TITLE, FONT, DB_PATH
from modules.auth import show_login_page
from modules.visuals import style_css
from layouts.reestr_automation import render_reestr_automation
from layouts.reestr_visualisation import render_reestr_visualisation
from layouts.settings.render import render_settings

# ─── Настройка логирования ────────────────────────────────────────────────────
LOG_FORMAT = '%(asctime)s | %(levelname)s | %(session_id)s | %(user)s | %(action)s | %(details)s'


class ProcessMiningFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'session_id'):
            record.session_id = '-'
        if not hasattr(record, 'user'):
            record.user = '-'
        if not hasattr(record, 'action'):
            record.action = '-'
        if not hasattr(record, 'details'):
            record.details = record.getMessage()
            record.msg = ''
            record.args = ()
        return super().format(record)


root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("reestr_app.log", encoding='utf-8')
file_handler.setFormatter(ProcessMiningFormatter(LOG_FORMAT))
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(ProcessMiningFormatter(LOG_FORMAT))
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# ─── Инициализация БД ─────────────────────────────────────────────────────────
if os.path.exists(DB_PATH):
    db.init_db()


def log_action(action: str, details: str = "", level: str = "INFO"):
    """Логирует действие пользователя с контекстом."""
    extra = {
        'session_id': st.session_state.get('session_id', '-'),
        'user': st.session_state.get('username', '-'),
        'action': action,
        'details': details,
    }
    if level == "WARNING":
        logger.warning("", extra=extra)
    elif level == "ERROR":
        logger.error("", extra=extra)
    else:
        logger.info("", extra=extra)


# ─── Основное приложение ─────────────────────────────────────────────────────
def main_app():
    st.set_page_config(layout="wide", page_title=PAGE_TITLE)
    st.markdown(style_css(FONT), unsafe_allow_html=True)

    # Инициализация session_id
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
        log_action("SESSION_START", "New session started in EN_FRE")

    # ── Инициализация пути к реестру из настроек пользователя ──
    # (нужно для render_reestr_visualisation, которая берёт current_excel_path из session_state)
    if 'current_excel_path' not in st.session_state:
        user_settings = db.get_user_settings(st.session_state.username)
        user_excel_path = user_settings.get("excel_file_path")
        if user_excel_path and os.path.exists(user_excel_path):
            st.session_state.current_excel_path = user_excel_path
        else:
            st.session_state.current_excel_path = EXCEL_FILE_PATH

    # ── Сайдбар ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"**{PAGE_TITLE}**")
        st.markdown("---")
        st.markdown(f"Пользователь: **{st.session_state.get('fio', 'N/A')}**")
        st.markdown(f"Подразделение: **{st.session_state.get('department', 'N/A')}**")
        st.markdown("---")

        @st.dialog("Настройки")
        def show_settings_dialog():
            render_settings()

        if st.button("Настройки", width='stretch'):
            show_settings_dialog()

        if st.button("Выход", width='stretch'):
            log_action("LOGOUT", "User logged out from EN_FRE")
            st.session_state.authenticated = False
            try:
                import extra_streamlit_components as esc
                logout_cookie_manager = esc.CookieManager(key="en_fre_cookie_manager_logout")
                logout_cookie_manager.delete(cookie="auth_username")
            except Exception:
                pass
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            time.sleep(1)
            st.rerun()

    # ── Вкладки ───────────────────────────────────────────────────────────────
    tab1, tab2 = st.tabs(["Визуализация реестра", "Автоматизация реестра"])

    with tab1:
        render_reestr_visualisation()

    with tab2:
        render_reestr_automation()


# ─── Точка входа ─────────────────────────────────────────────────────────────
if not os.path.exists(DB_PATH):
    st.session_state.authenticated = True
    st.session_state.username = "Guest"
    st.session_state.fio = "Гость"
    st.session_state.department = "Без подразделения"
    st.session_state.db_unavailable = True

if not st.session_state.get("authenticated", False):
    st.set_page_config(layout="centered", page_title=PAGE_TITLE)
    show_login_page()
else:
    main_app()
