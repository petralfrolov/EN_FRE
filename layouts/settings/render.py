"""
Модуль настроек пользователя.
Позволяет изменять профиль, пути к файлам и целевые диапазоны.
"""

import streamlit as st
import logging
import database as db
import config
from modules.codebook import get_departments

logger = logging.getLogger(__name__)


def log_action(action: str, details: str = "", level: str = "INFO"):
    """Логирует действие пользователя с контекстом для process mining."""
    extra = {
        'session_id': st.session_state.get('session_id', '-'),
        'user': st.session_state.get('username', '-'),
        'action': action,
        'details': details
    }
    if level == "WARNING":
        logger.warning("", extra=extra)
    elif level == "ERROR":
        logger.error("", extra=extra)
    else:
        logger.info("", extra=extra)


def render_settings():
    """
    Отрисовывает содержимое страницы настроек.
    Вызывается внутри st.dialog в app.py.
    """
    log_action("SETTINGS_OPEN", "")
    
    username = st.session_state.get("username")
    if not username:
        st.error("Пользователь не авторизован")
        return

    # Загружаем текущие настройки
    current_settings = db.get_user_settings(username)
    
    # ==================== СЕКЦИЯ 1: ПРОФИЛЬ ====================
    if username != "Guest":
        st.subheader("Профиль")
        
        with st.form("profile_form"):
            new_fio = st.text_input(
                "ФИО",
                value=st.session_state.get("fio", ""),
                key="settings_fio"
            )
            
            new_department = st.selectbox(
                "Подразделение",
                options=get_departments(),
                index=get_departments().index(st.session_state.get("department", get_departments()[0])) 
                      if st.session_state.get("department") in get_departments() else 0,
                key="settings_department"
            )
            
            if st.form_submit_button("💾 Сохранить профиль", width='stretch'):
                if new_fio.strip():
                    success = db.update_user_profile(username, new_fio.strip(), new_department)
                    if success:
                        # Обновляем session_state
                        st.session_state.fio = new_fio.strip()
                        st.session_state.department = new_department
                        log_action("SETTINGS_SAVE_PROFILE", f"fio={new_fio.strip()}, department={new_department}")
                        st.success("Профиль обновлен!")
                    else:
                        log_action("SETTINGS_SAVE_PROFILE_ERROR", "", level="ERROR")
                        st.error("Ошибка при сохранении профиля")
                else:
                    st.error("ФИО не может быть пустым")
        
        st.divider()
    
    # ==================== СЕКЦИЯ 2: ПУТИ К ФАЙЛАМ ====================
    st.subheader("Пути к файлам")
    st.caption("Оставьте пустым для использования путей по умолчанию из config.py")
    
    with st.form("paths_form"):
        excel_path = st.text_input(
            "Путь к реестру кормов (Excel)",
            value=current_settings.get("excel_file_path") or "",
            placeholder=config.EXCEL_FILE_PATH,
            key="settings_excel_path"
        )
        
        reestr_norm_path = st.text_input(
            "Путь к файлу границ питательности (реестр)",
            value=current_settings.get("reestr_norm_file_path") or "",
            placeholder=config.REESTR_NORM_FILE_PATH,
            key="settings_reestr_norm_path"
        )
        
        reestr_codebook_path = st.text_input(
            "Путь к файлу кодировки (реестр)",
            value=current_settings.get("reestr_codebook_file_path") or "",
            placeholder=config.REESTR_CODEBOOK_FILE_PATH,
            key="settings_reestr_codebook_path"
        )
        
        if st.form_submit_button("💾 Сохранить пути", width='stretch'):
            current_settings["excel_file_path"] = excel_path.strip() if excel_path.strip() else None
            current_settings["reestr_norm_file_path"] = reestr_norm_path.strip() if reestr_norm_path.strip() else None
            current_settings["reestr_codebook_file_path"] = reestr_codebook_path.strip() if reestr_codebook_path.strip() else None
            
            success = db.update_user_settings(username, current_settings)
            if success:
                log_action("SETTINGS_SAVE_PATHS", "")
                st.success("Пути сохранены! Перезагрузите страницу для применения.")
                st.info("ℹ️ Нажмите F5 или перезапустите приложение")
            else:
                log_action("SETTINGS_SAVE_PATHS_ERROR", "", level="ERROR")
                st.error("Ошибка при сохранении путей")
    
    st.divider()
    
    # Target Ranges section removed as it's not relevant for reestr_app

    # ==================== СЕКЦИЯ 4: АВТОМАТИЗАЦИЯ РЕЕСТРА ====================
    st.subheader("Настройки автоматизации реестра")

    # --- Маппинг листов ---
    st.markdown("**Маппинг листов реестра**")
    sheet_mapping = current_settings.get("sheet_mapping")
    if sheet_mapping and isinstance(sheet_mapping, dict):
        from layouts.reestr_automation.constants import FEED_TYPE_LABELS
        rows = []
        for ft, sheet in sheet_mapping.items():
            label = FEED_TYPE_LABELS.get(ft, ft)
            rows.append({"Тип корма": label, "Лист реестра": sheet})
        if rows:
            st.dataframe(
                rows,
                hide_index=True,
                width='stretch',
            )
        if st.button("🗑️ Сбросить маппинг листов", key="reset_sheet_mapping"):
            current_settings["sheet_mapping"] = None
            db.update_user_settings(username, current_settings)
            log_action("SETTINGS_RESET_SHEET_MAPPING", "")
            st.success("Маппинг листов сброшен. При следующем заходе в реестр потребуется настроить заново.")
            st.rerun()
    else:
        st.info("Маппинг листов не настроен (используются значения по умолчанию).")

    st.markdown("---")

    # --- Маппинги столбцов ---
    st.markdown("**Сохранённые сопоставления столбцов**")
    column_mappings = current_settings.get("column_mappings", {})

    if column_mappings:
        from layouts.reestr_automation.constants import FEED_TYPE_LABELS as FTL
        for ft, mappings in column_mappings.items():
            if not mappings:
                continue
            label = FTL.get(ft, ft)
            with st.expander(f"📋 {label} ({len(mappings)} сопоставлений)"):
                rows = [{"Столбец файла": src, "Столбец реестра": tgt}
                        for src, tgt in mappings.items()]
                st.dataframe(rows, hide_index=True, width='stretch')

                if st.button(f"🗑️ Сбросить маппинги для «{label}»", key=f"reset_col_{ft}"):
                    current_settings["column_mappings"][ft] = {}
                    db.update_user_settings(username, current_settings)
                    log_action("SETTINGS_RESET_COL_MAPPING", f"type={ft}")
                    st.success(f"Маппинги столбцов для «{label}» сброшены.")
                    st.rerun()

        if st.button("🗑️ Сбросить все маппинги столбцов", key="reset_all_col"):
            current_settings["column_mappings"] = {}
            db.update_user_settings(username, current_settings)
            log_action("SETTINGS_RESET_ALL_COL_MAPPINGS", "")
            st.success("Все маппинги столбцов сброшены.")
            st.rerun()
    else:
        st.info("Сохранённых сопоставлений столбцов нет.")

