from app.common.contexts import UserContext
from init.settings import DEFAULT_USER


def get_user_info() -> str:
    return UserContext.user_id or DEFAULT_USER
