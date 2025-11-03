from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, login_required, logout_user, current_user
from .utils import logout_required
from src.views import core
from src.data.models import User
from werkzeug.security import generate_password_hash, check_password_hash



auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET','POST'])
@logout_required
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('pwd')

        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password_hash, password):
                login_user(user, remember=True)
                flash('Logged in successfully!', category='success')
                return redirect(url_for('core.home'))
            else:
                flash('Incorrect username/password.', category='danger')
        else:
            flash('Account does not exist. Sign up to get started!', category='warning')
            return redirect(url_for('auth.sign_up'))
        
    return render_template("auth/login.html", user=current_user)

@auth.route('/landing-page')
@logout_required
def landingpage():
    return render_template("auth/landing-page.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('core.home'))

@auth.route('/reset-pwd')
@logout_required
def reset_pwd():
    return render_template("auth/reset-pwd.html", user=current_user)

@auth.route('/register')
@logout_required
def register():
    return render_template("auth/register.html", user=current_user)