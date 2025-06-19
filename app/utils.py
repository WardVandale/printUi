from functools import wraps
from flask import redirect, request
from flask_login import current_user
from app.models import has_users

def onboard_or_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not has_users():
            return redirect('/onboard/user')
        if not current_user.is_authenticated:
            return redirect('/login?next=' + request.path)
        return view_func(*args, **kwargs)
    return wrapper