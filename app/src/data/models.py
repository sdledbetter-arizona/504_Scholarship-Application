from flask_sqlalchemy import SQLAlchemy
import datetime
from src import db


# ---------- USER & ROLES ---------- #
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # applicant, reviewer, admin, donor
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    # Relationships
    applicant = db.relationship("Applicant", back_populates="user", uselist=False)
    donor = db.relationship("Donor", back_populates="user", uselist=False)
    reviews = db.relationship("Review", back_populates="reviewer", cascade="all, delete")
    scholarships = db.relationship("Scholarship", back_populates="created_by_user", cascade="all, delete")

# ---------- APPLICANT ---------- #
class Applicant(db.Model):
    __tablename__ = "applicant"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    student_id = db.Column(db.String(20))
    netid = db.Column(db.String(20))
    major = db.Column(db.String(100))
    minor = db.Column(db.String(100))
    gpa = db.Column(db.Float)
    financial_info = db.Column(db.Text)

    user = db.relationship("User", back_populates="applicant")
    applications = db.relationship("Application", back_populates="applicant", cascade="all, delete")
    documents = db.relationship("Document", back_populates="applicant", cascade="all, delete")

# ---------- DONOR ---------- #
class Donor(db.Model):
    __tablename__ = "donors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    organization = db.Column(db.String(120))
    contact_info = db.Column(db.String(200))

    user = db.relationship("User", back_populates="donor")
    scholarships = db.relationship("Scholarship", back_populates="donor", cascade="all, delete")

# ---------- SCHOLARSHIP ---------- #
class Scholarship(db.Model):
    __tablename__ = "scholarship"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float)
    frequency = db.Column(db.String(50))  # e.g., annual, semester
    requirements = db.Column(db.Text)
    donor_id = db.Column(db.Integer, db.ForeignKey("donors.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    donor = db.relationship("Donor", back_populates="scholarships")
    created_by_user = db.relationship("User", back_populates="scholarships")
    applications = db.relationship("Application", back_populates="scholarship", cascade="all, delete")
    awards = db.relationship("Award", back_populates="scholarship", cascade="all, delete")

# ---------- APPLICATION ---------- #
class Application(db.Model):
    __tablename__ = 'application'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    scholarship_id = db.Column(db.Integer, db.ForeignKey('scholarship.id'), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.datetime.now())
    status = db.Column(db.String(50), default='submitted')
    essay = db.Column(db.Text)

    applicant = db.relationship('Applicant', back_populates='applications')
    scholarship = db.relationship('Scholarship', back_populates='applications')
    reviews = db.relationship('Review', back_populates='application', cascade='all, delete')
    documents = db.relationship('Document', back_populates='application', cascade='all, delete')

# ---------- REVIEW ---------- #
class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    score = db.Column(db.Integer)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now())

    application = db.relationship("Application", back_populates="reviews")
    reviewer = db.relationship("User", back_populates="reviews")

# ---------- AWARD ---------- #
class Award(db.Model):
    __tablename__ = "awards"
    id = db.Column(db.Integer, primary_key=True)
    scholarship_id = db.Column(db.Integer, db.ForeignKey("scholarships.id"), nullable=False)
    applicant_id = db.Column(db.Integer, db.ForeignKey("applicants.id"), nullable=False)
    amount_awarded = db.Column(db.Float)
    award_date = db.Column(db.DateTime, default=datetime.datetime.now())

    scholarship = db.relationship("Scholarship", back_populates="awards")
    applicant = db.relationship("Applicant")

# ---------- DOCUMENTS ---------- #
class Document(db.Model):
    __tablename__ = 'document'

    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.datetime.now())

    # Relationships
    applicant = db.relationship('Applicant', back_populates='documents')
    application = db.relationship('Application', back_populates='documents')

