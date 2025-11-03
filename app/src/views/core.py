from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user

core = Blueprint('core', __name__)


@core.route('/')
def home():
    if current_user.is_authenticated:
        return render_template("core/home.html", user=current_user)
    return redirect(url_for('auth.landingpage'))

@core.route('/about')
def about():
    return render_template("core/about.html", user=current_user)