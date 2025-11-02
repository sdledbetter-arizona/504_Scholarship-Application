from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user

core = Blueprint('core', __name__)


@core.route('/')
def home():
    if current_user.is_authenticated:
        return render_template("home.html")
    return render_template("auth/landing-page.html")