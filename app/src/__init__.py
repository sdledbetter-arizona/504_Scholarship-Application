import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os, secrets
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import joinedload


db = SQLAlchemy()
mail = Mail()

def create_app():

    
    from src.api import api_bp
    from .views import views
    from .auth import auth
    from .admin import admin
    from .donor import donor
    from .student import student
    from .models import User, Scholarship, StudentProfile, SecurityQuestion, Application



    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your email server
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'sdledbetter0616@gmail.com'
    app.config['MAIL_PASSWORD'] = 'qxak ahkp lnke uagl'
    app.config['MAIL_DEFAULT_SENDER'] = 'sdledbetter0616@gmail.com'
    
    mail.init_app(app)

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)  # Create 'data' folder if not exists

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Define database URIs inside the data folder
    app.config['SQLALCHEMY_BINDS'] = {
        'applicant_db': f"sqlite:///{os.path.join(DATA_DIR, 'applicant.db')}",
        'scholarship_db': f"sqlite:///{os.path.join(DATA_DIR, 'scholarship.db')}",
        'act_stud_db': f"sqlite:///{os.path.join(DATA_DIR, 'act_stud.db')}"
    }

    db.init_app(app)

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(donor, url_prefix='/donor')
    app.register_blueprint(student, url_prefix='/student')
    app.register_blueprint(api_bp, url_prefix="/api")


    with app.app_context():

        # Check if there are no security questions in the table
        db.create_all()

        if SecurityQuestion.query.count() == 0:
            # Populate the table with predefined questions
            questions = [
                "What is your pet’s name?",
                "What is your mother’s maiden name?",
                "What was the name of your first school?",
                "What is your favorite book?"
            ]
            
            for text in questions:
                question = SecurityQuestion(question_text=text)
                db.session.add(question)
            
            db.session.commit()

        if User.query.count() == 0:
            new_user = User(
                username="admin_account",
                email="sdledbetter@arizona.edu",
                password="pbkdf2:sha256:1000000$UXPzAbVov9gINxWQ$f0c822f3d8e1527d1e4d3b4afbfe84fc9611ed6f673684c576651963057b07c0",
                first_name="Admin",
                last_name="Account",
                net_id=None,
                phone_num="000-000-0000",
                user_type="Scholarship Admin",
                status="Enabled"
            )
            new_user1 = User(
                username="student_account",
                email="sdledbetter0616@yahoo.com",
                password="pbkdf2:sha256:1000000$UXPzAbVov9gINxWQ$f0c822f3d8e1527d1e4d3b4afbfe84fc9611ed6f673684c576651963057b07c0",
                first_name="Student",
                last_name="Account",
                net_id=None,
                phone_num="000-000-0000",
                user_type="Student",
                status="Enabled"
            )
            new_user2 = User(
                username="donor_account",
                email="sdledbetter0616@gmail.com",
                password="pbkdf2:sha256:1000000$UXPzAbVov9gINxWQ$f0c822f3d8e1527d1e4d3b4afbfe84fc9611ed6f673684c576651963057b07c0",
                first_name="Donor",
                last_name="Account",
                net_id=None,
                phone_num="000-000-0000",
                user_type="Scholarship Donor",
                status="Enabled"
            )
            db.session.add(new_user)
            db.session.add(new_user1)
            db.session.add(new_user2)
            db.session.commit()

        if StudentProfile.query.count() == 0:
            new_profile = StudentProfile(
                user_id = 1,
                preferred_pronoun = "he/him/his",
                student_id = "s520341",
                major = "Computer Science",
                minor = "American Sign Language",
                cumulative_gpa = 3.14,
                current_year = "Freshman",
                ethnicity = "Black",
                personal_statement_essay = "This is my personal statement essay.",
                work_experience = "I have none."
            )
            new_profile1 = StudentProfile(
                user_id = 2,
                preferred_pronoun = "he/him/his",
                student_id = "s520340",
                major = "Computer Science",
                minor = "American Sign Language",
                cumulative_gpa = 3.14,
                current_year = "Freshman",
                ethnicity = "Black",
                personal_statement_essay = "This is my personal statement essay.",
                work_experience = "I have none."
            )
            db.session.add(new_profile)
            new_profile2 = StudentProfile(
                user_id = 3,
                preferred_pronoun = "he/him/his",
                student_id = "s520342",
                major = "Computer Science",
                minor = "American Sign Language",
                cumulative_gpa = 3.14,
                current_year = "Freshman",
                ethnicity = "Black",
                personal_statement_essay = "This is my personal statement essay.",
                work_experience = "I have none."
            )
            db.session.add(new_profile)
            db.session.add(new_profile1)
            db.session.add(new_profile2)
            db.session.commit()

        if Scholarship.query.count() == 0:
            first_scholarship = Scholarship(
                name = "The Great Scholarship of 1812",
                description = "In honor of the resilience and determination displayed during the historic Battle of 1812, this scholarship aims to support students who embody the spirit of leadership and perseverance. Awarded to individuals pursuing studies in history, political science, or international relations, the scholarship provides $8,000 annually to assist with tuition and academic materials. Applicants must write a compelling essay on the significance of the Battle of 1812 in shaping modern diplomacy and submit two letters of recommendation from educators or community leaders.\n\nBeyond financial support, recipients will have the opportunity to engage in workshops and discussions focusing on the importance of historical events in today's global landscape. This scholarship is a tribute to the enduring legacy of those who fought for their nations and values.",
                amount = 2000.00,
                donor_id = 3,
                donor_name = "Donor Account",
                donor_phone = "000-000-0000",
                donor_email = "sdledbetter0616@gmail.com",
                scholarships_available = 5,
                eligible_majors = ["Computer Science"],
                eligible_minors = ["American Sign Language"],
                required_gpa = 3.0,
                application_deadline = datetime.datetime(2025, 4, 6, 21, 29, 12, 823427)
            )
            second_scholarship = Scholarship(
                name = "The Better Scholarship of 1813",
                description = "Building on the legacy of its predecessor, this scholarship commemorates the pivotal events of 1813 that reshaped strategies and strengthened alliances. Awarded to students who exhibit exceptional innovation and resilience, this scholarship supports individuals pursuing studies in strategic leadership, military history, or diplomacy. Offering $10,000 annually, it aims to empower future leaders who understand the importance of adaptability and strategic thinking.\n\nApplicants must submit an essay reflecting on the strategic lessons learned from the events of 1813 and their relevance today, alongside a letter of recommendation from a mentor or educator. Scholarship recipients will also gain exclusive access to seminars and workshops focusing on historical analysis and its application in modern problem-solving.",
                amount = 2000.00,
                donor_id = 3,
                donor_name = "Donor Account",
                donor_phone = "000-000-0000",
                donor_email = "sdledbetter0616@gmail.com",
                scholarships_available = 3,
                eligible_majors = ["Human Resources"],
                eligible_minors = ["American Sign Language"],
                required_gpa = 3.0,
                application_deadline = datetime.datetime(2025, 4, 6, 21, 29, 12, 823427)
            )
            db.session.add(first_scholarship)
            db.session.add(second_scholarship)
            
            db.session.commit()

        
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this application.'
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)


    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    return app