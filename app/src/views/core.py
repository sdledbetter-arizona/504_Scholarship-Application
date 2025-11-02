from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user

core = Blueprint('core', __name__)


@core.route('/')
@login_required
def home():
    return render_template("base.html")