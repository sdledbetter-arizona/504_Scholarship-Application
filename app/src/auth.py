from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from .utils import logout_required, log_change
from .models import User, SecurityQuestion
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, mail
from flask_login import login_user, login_required, logout_user, current_user
import datetime
from zoneinfo import ZoneInfo
import requests
from .api.resources import current_user_id_or_none

auth = Blueprint('auth', __name__)

reset_request_view = 'auth.reset_request'
reset_view = 'auth.reset'
login_view = 'auth.login'
encrypt_method = 'pbkdf2:sha256'

@auth.route('/login', methods=['GET','POST'])
@logout_required
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('pwd')

        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember=True)
                flash('Logged in successfully!', category='success')
                log_change(
                    user_id=current_user_id_or_none(),
                    action="Login Successful",
                    entity=current_user,
                    field_name=None,
                    old_value=None,
                    new_value=None,
                )
                
                db.session.commit()

                return redirect(url_for('views.home'))
            else:
                flash('Incorrect username/password.', category='danger')
                log_change(
                    user_id=current_user_id_or_none(),
                    action="Login Failed",
                    entity=user,
                    field_name=None,
                    old_value=None,
                    new_value=None,
                )
                
                db.session.commit()
        else:
            flash('Account does not exist. Sign up to get started!', category='warning')
            return redirect(url_for('auth.sign_up'))
        
    return render_template("auth/login.html", user=current_user)

@auth.route('/reset', methods=['GET', 'POST'])
@logout_required
def reset():

    if not session.get('allow_reset'):
        flash("Please request a verification code.", category="danger")
        return redirect(url_for(reset_request_view))  # Redirect back
    

    if request.method == 'POST':

        session.pop('allow_reset', None)

        reset_token = request.form['verCode']
        password = request.form['pwd']
        password_conf = request.form['pwdConf']
        selected_user = session.get('selected_user')

        user = User.query.filter_by(email=selected_user).first()

        if password != password_conf:
            flash("Passwords do not match.", category='danger')
            session['allow_reset'] = True
            return redirect(url_for(reset_view))

        # IF NOT THE CORRECT TOKEN
        elif reset_token != user.reset_token:
            flash("Invalid verification code.", category='danger')
            session['allow_reset'] = True
            return redirect(url_for(reset_view))

        # ELSE IF NOW IS GREATER THAN TOKEN EXPIRATION
        elif user.reset_token_expiration.replace(tzinfo=ZoneInfo("America/Phoenix")) < datetime.datetime.now(ZoneInfo("America/Phoenix")):
            session.pop('selected_user', None)
            flash("Verification code has expired. Please submit a new request.", category='danger')
            return redirect(url_for(reset_request_view))

        # ELSE
        else:
            session.pop('selected_user', None)

            # Update the password
            user.password = generate_password_hash(password, method=encrypt_method)
            user.reset_token = None
            user.reset_token_expiration = None
            db.session.commit()

            flash("Your password has been successfully reset.", category='success')
            return redirect(url_for(login_view))

    
    return render_template("auth/reset-pwd.html", user=current_user)

@auth.route('/reset/request', methods=['GET', 'POST'])
@logout_required
def reset_request():

    import random
    import string
    from flask_mail import Message
    from werkzeug.security import generate_password_hash

    if request.method == 'POST':

        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        
        if user:

            session['allow_reset'] = True
            
            session['selected_user'] = email

            ver_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            expiration_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)  # 1 hour expiration
            
            user.reset_token = ver_code
            user.reset_token_expiration = expiration_time
            db.session.commit()

            msg = Message("SAS - Password Reset Request", recipients=[email])
            msg.body = f"Your password reset code is: {ver_code}"
            mail.send(msg)

            flash("Password reset code has been sent to your email. It may take a few minutes.", category='warning')
            return redirect(url_for(reset_view))
        else:
            flash("No account found with that email address.", category='danger')
            return redirect(url_for(reset_request_view))


    return render_template("auth/reset-pwd_request.html", user=current_user)



@auth.route('/logout')
@login_required
def logout():
    log_change(
        user_id=current_user_id_or_none(),
        action="Logout Successful",
        entity=current_user,
        field_name=None,
        old_value=None,
        new_value=None,
    )
    db.session.commit()
    logout_user()
    return redirect(url_for(login_view))

@auth.route('/sign-up', methods=['GET','POST'])
@logout_required
def sign_up():

    security_questions = SecurityQuestion.query.all()

    if(request.method == 'POST'):
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        last_name = request.form.get('lastName')
        password = request.form.get('pwd')
        username = request.form.get('username')
        net_id = request.form.get('netID')
        phonenum = request.form.get('phonenum')
        security_question_1 = request.form.get('security_question_1')
        security_question_2 = request.form.get('security_question_2')
        security_answer_1 = request.form.get('security_answer_1')
        security_answer_2 = request.form.get('security_answer_2')

        user = User.query.filter_by(email=email).first()

        if user:
            flash("Email address already in use.", category='danger')

        else:

            form_data = {
                "user_id":None,
                "request_type":"Create Account",
                "details":{
                    "username": username,
                    "email": email,
                    "password": generate_password_hash(password, method=encrypt_method),
                    "first_name": first_name,
                    "last_name": last_name,
                    "net_id": net_id if net_id else None,
                    "phone_num": phonenum,
                    "security_questions": [
                        {
                            "question_id": security_question_1,
                            "answer": generate_password_hash(security_answer_1, method=encrypt_method),
                            "question_num": 1
                        },
                        {
                            "question_id": security_question_2,
                            "answer": generate_password_hash(security_answer_2, method=encrypt_method),
                             "question_num": 2
                        }
                    ]
                }
            }
            
            api_url = "http://localhost:5000/api/requests"
            requests.post(api_url, json=form_data, cookies=request.cookies)
            
            flash("Account creation request has been submitted. You will receive an email once completed.", category="warning")
            return redirect(url_for(login_view))


    return render_template("auth/sign_up.html", user=current_user, security_questions=security_questions)