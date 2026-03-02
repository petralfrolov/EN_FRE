import streamlit as st
import extra_streamlit_components as esc
import logging
import time
import database as db
from modules.codebook import get_departments

logger = logging.getLogger(__name__)

def get_user_context():
    user = st.session_state.get('username', 'Anonymous')
    dept = st.session_state.get('department', 'NoDept')
    return f"[{user} | {dept}]"

def show_login_page():
    # CookieManager создается только на странице логина
    try:
        cookie_manager = esc.CookieManager(key="en_fae_cookie_manager")
    except Exception as e:
        logger.error(f"Ошибка инициализации CookieManager: {e}")
        cookie_manager = None

    # Автовход по cookie (только если ещё не аутентифицирован)
    if cookie_manager and not st.session_state.get("authenticated", False):
        username_from_cookie = cookie_manager.get(cookie="auth_username")
        if username_from_cookie:
            user = db.get_user(username_from_cookie)
            if user:
                st.session_state.authenticated = True
                st.session_state.username = user.username
                st.session_state.fio = user.fio
                st.session_state.department = user.department
                st.session_state.is_admin = getattr(user, 'is_admin', False)
                logger.info(f"Пользователь {user.username} вошел по куки.")
                st.rerun()
            else:
                cookie_manager.delete(cookie="auth_username")

    choice = st.radio(
        "Выберите действие:",
        ["Войти", "Зарегистрироваться"],
        horizontal=True,
        label_visibility="collapsed"
    )
    if choice == "Войти":
        with st.form("login_form"):
            username = st.text_input("Логин")
            password = st.text_input("Пароль", type="password")
            submitted = st.form_submit_button("Войти")

            if submitted:
                user = db.get_user(username)
                if user and db.check_password(password, user.hashed_password):
                    st.session_state.authenticated = True
                    st.session_state.username = user.username
                    st.session_state.fio = user.fio
                    st.session_state.department = user.department
                    st.session_state.is_admin = getattr(user, 'is_admin', False)

                    logger.info(f"Успешный вход пользователя: {username} ({user.department})")

                    if cookie_manager:
                        cookie_manager.set(
                            cookie="auth_username",
                            val=user.username,
                            max_age=30 * 24 * 60 * 60
                        )
                        time.sleep(0.5)
                    st.rerun()
                else:
                    logger.warning(f"Неудачная попытка входа для логина: {username}")
                    st.error("Неверный логин или пароль")
                    
        st.markdown("---")
        if st.button("Зайти как гость"):
            st.session_state.authenticated = True
            st.session_state.username = "Guest"
            st.session_state.fio = "Гость"
            st.session_state.department = "Без подразделения"
            st.session_state.is_admin = False
            logger.info("Вход под учетной записью гостя")
            st.rerun()

    elif choice == "Зарегистрироваться":
        with st.form("register_form"):
            st.subheader("Регистрация")
            fio = st.text_input("ФИО")
            username = st.text_input("Логин")
            department = st.selectbox("Подразделение", get_departments())
            password = st.text_input("Пароль", type="password")
            password_confirm = st.text_input("Повторите пароль", type="password")
            submitted = st.form_submit_button("Зарегистрироваться")

            if submitted:
                if not all([fio, username, department, password, password_confirm]):
                    st.error("Заполните все поля")
                elif password != password_confirm:
                    st.error("Пароли не совпадают")
                elif db.get_user(username):
                    st.error("Логин занят")
                else:
                    try:
                        new_user = db.create_user(fio, username, password, department)
                        if new_user:
                            logger.info(f"Зарегистрирован новый пользователь: {username} ({department})")
                            st.success(f"Пользователь {new_user.fio} создан.")
                        else:
                            logger.error(f"Не удалось создать пользователя: {username}")
                            st.error("Ошибка при регистрации.")
                    except Exception as e:
                        logger.error(f"Исключение при регистрации: {e}")
                        st.error(f"Ошибка: {e}")
