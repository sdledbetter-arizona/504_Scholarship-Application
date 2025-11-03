from functools import wraps
from flask_login import current_user
from flask import redirect, url_for, flash


def logout_required(route_function):
    @wraps(route_function)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated:
            flash("You must logout to view that page.", category="info")
            return redirect(url_for('core.home'))
        return route_function(*args, **kwargs)
    return decorated_view