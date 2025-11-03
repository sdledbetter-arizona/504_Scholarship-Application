from flask import flash
from src import db
from src.data.models import User, Applicant, Donor, Scholarship, Application, Review, Award, Document
from werkzeug.security import generate_password_hash
import datetime

def seed_data():
    # Drop all tables and recreate
    db.drop_all()
    db.create_all()

    # --- USERS ---
    admin = User(
        name="Sheldon Ledbetter",
        email="sdledbetter@arizona.edu",
        password_hash=generate_password_hash("admin123"),
        role="admin"
    )

    admin2 = User(
        name="Angela Miller",
        email="angelakmiller@arizona.edu",
        password_hash=generate_password_hash("admin123"),
        role="admin"
    )

    admin3 = User(
        name="Rafael Estrada",
        email="restrada2@arizona.edu",
        password_hash=generate_password_hash("admin123"),
        role="admin"
    )

    reviewer = User(
        name="Dr. Robert Smith",
        email="robert.smith@arizona.edu",
        password_hash=generate_password_hash("reviewer123"),
        role="reviewer"
    )

    donor_user = User(
        name="Alice Thompson",
        email="alice.thompson@techdonors.org",
        password_hash=generate_password_hash("donor123"),
        role="donor"
    )

    applicant_user1 = User(
        name="Michael Brown",
        email="michael.brown@arizona.edu",
        password_hash=generate_password_hash("applicant123"),
        role="applicant"
    )

    applicant_user2 = User(
        name="Sarah Davis",
        email="sarah.davis@arizona.edu",
        password_hash=generate_password_hash("applicant123"),
        role="applicant"
    )

    db.session.add_all([admin,admin2, admin3, reviewer, donor_user, applicant_user1, applicant_user2])
    db.session.commit()

    # --- DONOR ---
    donor = Donor(
        user_id=donor_user.id,
        organization="TechDonors Foundation",
        contact_info="alice.thompson@techdonors.org | 555-867-5309"
    )
    db.session.add(donor)
    db.session.commit()

    # --- SCHOLARSHIPS ---
    scholarship1 = Scholarship(
        name="Women in Engineering Scholarship",
        description="Awarded to outstanding female students in the College of Engineering.",
        amount=2500.00,
        frequency="annual",
        requirements="Minimum GPA of 3.2, enrolled full-time in Engineering.",
        donor_id=donor.id,
        created_by=admin.id
    )

    scholarship2 = Scholarship(
        name="Tech Innovation Grant",
        description="Supports innovative student projects involving technology or sustainability.",
        amount=5000.00,
        frequency="semester",
        requirements="Submit project proposal and maintain GPA of 3.0 or higher.",
        donor_id=donor.id,
        created_by=admin.id
    )

    db.session.add_all([scholarship1, scholarship2])
    db.session.commit()

    # --- APPLICANTS ---
    applicant1 = Applicant(
        user_id=applicant_user1.id,
        student_id="S12345",
        netid="mbrown1",
        major="Computer Engineering",
        minor="Mathematics",
        gpa=3.8,
        financial_info="Family income below $50,000 annually."
    )

    applicant2 = Applicant(
        user_id=applicant_user2.id,
        student_id="S67890",
        netid="sdavis1",
        major="Mechanical Engineering",
        gpa=3.5,
        financial_info="Single parent household, Pell Grant recipient."
    )

    db.session.add_all([applicant1, applicant2])
    db.session.commit()

    # --- DOCUMENTS (now storing real binary data) ---
    transcript_pdf_bytes = b"%PDF-1.4\n% Fake transcript PDF data for Michael Brown"
    essay_docx_bytes = b"PK\x03\x04 Fake DOCX binary data for Sarah Davis essay"

    doc1 = Document(
        applicant_id=applicant1.id,
        file_name="transcript_mbrown.pdf",
        file_type="transcript",
        mime_type="application/pdf",
        file_data=transcript_pdf_bytes
    )

    doc2 = Document(
        applicant_id=applicant2.id,
        file_name="essay_sdavis.docx",
        file_type="essay",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_data=essay_docx_bytes
    )

    db.session.add_all([doc1, doc2])
    db.session.commit()

    # --- APPLICATIONS ---
    application1 = Application(
        applicant_id=applicant1.id,
        scholarship_id=scholarship1.id,
        essay="I aspire to innovate in embedded systems that support sustainable infrastructure.",
        status="under_review"
    )

    application2 = Application(
        applicant_id=applicant2.id,
        scholarship_id=scholarship2.id,
        essay="My project aims to design eco-friendly automotive components using 3D printing.",
        status="submitted"
    )

    db.session.add_all([application1, application2])
    db.session.commit()

    # --- REVIEWS ---
    review1 = Review(
        application_id=application1.id,
        reviewer_id=reviewer.id,
        score=95,
        comments="Exceptional academic record and strong essay.",
        created_at=datetime.datetime.now()
    )

    review2 = Review(
        application_id=application2.id,
        reviewer_id=reviewer.id,
        score=88,
        comments="Promising idea, but could use more detail in proposal.",
        created_at=datetime.datetime.now()
    )

    db.session.add_all([review1, review2])
    db.session.commit()

    # --- AWARD ---
    award1 = Award(
        scholarship_id=scholarship1.id,
        applicant_id=applicant1.id,
        amount_awarded=2500.00,
        award_date=datetime.datetime.now()
    )

    db.session.add(award1)
    db.session.commit()
