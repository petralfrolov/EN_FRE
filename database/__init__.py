# database/__init__.py

from .base import engine, SessionLocal, Base, init_db, get_db, DEPARTMENTS
from .models import User, SavedRation, CompoundFeed, CustomFeed, MilkAnalysis

from .crud.users import (
    create_user, get_user, hash_password, check_password,
    get_user_settings, update_user_settings, update_user_profile
)
from .crud.rations import (
    autosave_ration, create_manual_save, get_user_autosave,
    get_user_manual_saves, get_department_saves, get_colleague_saves,
    load_ration_data, delete_saved_ration, get_rations_with_predictions
)
from .crud.feeds import (
    create_compound_feed, get_department_compound_feeds, delete_compound_feed,
    create_custom_feed, get_department_custom_feeds, delete_custom_feed,
    find_feed_data_by_name, get_all_db_feed_names, get_feed_by_type_and_id,
    find_similar_feeds
)
from .crud.milk import (
    save_milk_analyses, get_analyses_for_ration,
    get_latest_analysis_for_ration, get_all_milk_analyses,
    get_analyses_by_department_period, get_ration_names_for_department,
    get_analyses_for_ration_in_period
)
