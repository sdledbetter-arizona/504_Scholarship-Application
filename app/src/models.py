from sqlalchemy import DECIMAL
from src import db
from flask_login import UserMixin
import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.dialects.sqlite import JSON



applicant_user_id_FK = 'user.id'

class SecurityQuestion(db.Model):
    __bind_key__ = 'applicant_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_text = db.Column(db.String(255), unique=True, nullable=False)

class User(db.Model, UserMixin):
    __bind_key__ = 'applicant_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    net_id = db.Column(db.String(100), unique=True, nullable=True)
    phone_num = db.Column(db.String(20), nullable=False)
    user_type = db.Column(db.String(50), nullable=False, default='Student')  
    reset_token = db.Column(db.String(6), nullable=True)
    reset_token_expiration = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='Enabled') 
    
    student_profile = db.relationship('StudentProfile', backref='user_account', uselist=False, lazy=True)
    security_questions = db.relationship('UserSecurityQuestion', backref='user', lazy=True, cascade='all, delete-orphan')
    approvals = db.relationship('TicketRequest', foreign_keys='TicketRequest.approved_by', backref='approver', lazy=True)
    notifications = db.relationship("Notification",backref="user", cascade="all, delete")

    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class UserSecurityQuestion(db.Model):
    __bind_key__ = 'applicant_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(applicant_user_id_FK), nullable=False)  # Links to User
    question_id = db.Column(db.Integer, db.ForeignKey('security_question.id'), nullable=False)  # Links to SecurityQuestion
    answer = db.Column(db.String(255), nullable=False)  # User's answer
    question_num = db.Column(db.Integer, nullable=False) 

    question = db.relationship('SecurityQuestion', backref='user_question_text')

class Scholarship(db.Model):
    __bind_key__ = 'scholarship_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String, nullable=False)
    amount = db.Column(DECIMAL(10, 2), nullable=False)
    donor_id = db.Column(db.Integer, nullable=False)
    donor_name = db.Column(db.String(255), nullable=False)
    donor_phone = db.Column(db.String(20), nullable=False)
    donor_email = db.Column(db.String(255), nullable=False)
    scholarships_available = db.Column(db.Integer, nullable=False)
    eligible_majors = db.Column(JSON(db.String), nullable=True)
    eligible_minors = db.Column(JSON(db.String), nullable=True)
    required_gpa = db.Column(DECIMAL(3, 2), nullable=True)
    required_year = db.Column(db.String(20), nullable=True)
    required_ethnicity = db.Column(db.String(25), nullable=True)
    application_deadline = db.Column(db.Date, nullable=False)
    other_requirements = db.Column(db.String, nullable=True)
    applications = db.relationship(
        'Application',
        backref='scholarship',
        lazy=True,
        cascade='all, delete-orphan',
        passive_deletes=True
    )

    scores = db.relationship(
        'ApplicationScore',
        back_populates='scholarship',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    
    @property
    def requirements(self):
        return {
            "gpa" : float(self.required_gpa),
            "major" : self.eligible_majors,
            "minor" : self.eligible_minors,
            "year" : self.required_year,
            "ethnicity" : self.required_ethnicity
        }

class Application(db.Model):
    __bind_key__ = 'scholarship_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    scholarship_id = db.Column(db.Integer, db.ForeignKey('scholarship.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(255), nullable=False, default="Pending Decision")
    preferred_pronoun = db.Column(db.String(50), nullable=True)
    student_id = db.Column(db.String(100), nullable=True)
    major = db.Column(db.String(255), nullable=True)
    minor = db.Column(db.String(255), nullable=True)
    cumulative_gpa = db.Column(db.Float, nullable=True)
    current_year = db.Column(db.Enum('Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate', name='year_levels'), nullable=True)
    ethnicity = db.Column(db.Enum('Caucasian', 'Hispanic', 'Black', 'European', 'Asian', 'Indian', 'American Indian', 'Arabic/Middle Eastern', 'Other', name='ethnicities'), nullable=True)
    personal_statement_essay = db.Column(db.Text, nullable=True)
    work_experience = db.Column(db.Text, nullable=True)
    date_submitted = db.Column(db.Date, nullable=False, default=datetime.datetime.now)

    scores = db.relationship(
            'ApplicationScore',
            back_populates='application',
            cascade='all, delete'
        )

    @property
    def user(self): 
        return User.query.filter_by(id=self.user_id).first()
    
    @property
    def results(self):
        return {
            "gpa" : self.cumulative_gpa,
            "major" : self.major,
            "minor" : self.minor,
            "year" : self.current_year,
            "ethnicity" : self.ethnicity
        }


class ApplicationScore(db.Model):
    __bind_key__ = 'scholarship_db'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey('application.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    scholarship_id = db.Column(
        db.Integer,
        db.ForeignKey('scholarship.id', ondelete='CASCADE'),
        nullable=False
    )
    score = db.Column(db.Integer, nullable=False)
    is_overridden = db.Column(db.Boolean, default=False, nullable=False)

    application = db.relationship('Application', back_populates='scores')
    scholarship = db.relationship('Scholarship', back_populates='scores')

    def __repr__(self):
        return str(self.score)
    

class StudentProfile(db.Model):
    __bind_key__ = 'applicant_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(applicant_user_id_FK), nullable=False, unique=True)
    preferred_pronoun = db.Column(db.String(50), nullable=True)
    student_id = db.Column(db.String(100), unique=True, nullable=True)
    major = db.Column(db.String(255), nullable=True)
    minor = db.Column(db.String(255), nullable=True)
    cumulative_gpa = db.Column(db.Float, nullable=True)
    current_year = db.Column(db.Enum('Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate', name='year_levels'), nullable=True)
    ethnicity = db.Column(db.Enum('Caucasian', 'Hispanic', 'Black', 'European', 'Asian', 'Indian', 'American Indian', 'Arabic/Middle Eastern', 'Other', name='ethnicities'), nullable=True)
    personal_statement_essay = db.Column(db.Text, nullable=True)
    work_experience = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
    
    @property
    def results(self):
        return {
            "gpa" : self.cumulative_gpa,
            "major" : self.major,
            "minor" : self.minor,
            "year" : self.current_year,
            "ethnicity" : self.ethnicity
        }


class TicketRequest(db.Model):
    __bind_key__ = 'applicant_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey(applicant_user_id_FK), nullable=True)
    request_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(10), default='Open')  # open, closed - complete, closed - cancelled
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(ZoneInfo("America/Phoenix")))
    approval_status = db.Column(db.String(20), default='Pending') # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey(applicant_user_id_FK), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    requester = db.relationship('User', foreign_keys=[user_id], backref='submitted_tickets')

class Notification(db.Model):
    __bind_key__ = 'applicant_db'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500))
    url = db.Column(db.String(300))  # link to scholarship or page

    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

class AuditLog(db.Model):
    __bind_key__ = 'applicant_db'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    action = db.Column(db.String(100), nullable=False)        # e.g. "scholarship_updated"
    entity_type = db.Column(db.String(50), nullable=False)    # e.g. "Scholarship"
    entity_id = db.Column(db.Integer, nullable=False)         # e.g. scholarship.id

    field_name = db.Column(db.String(100), nullable=True)     # e.g. "name"
    old_value = db.Column(db.Text, nullable=True)
    new_value = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.datetime.now, nullable=False)

    user = db.relationship("User", backref="audit_logs")
