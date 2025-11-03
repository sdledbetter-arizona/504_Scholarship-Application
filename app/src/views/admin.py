from flask import Blueprint, jsonify
from src.data.seed_data import seed_data
from flask_login import logout_user
from flask import Blueprint, flash, redirect, request, url_for



admin = Blueprint('admin', __name__)

@admin.route('/reset-db')
def reset_db():
    try:
        logout_user()
        seed_data() 
        flash("Your environment has now been reset!", category="info")
        return redirect(url_for('core.home'))
    except Exception as e:
        return jsonify({'message': f'Error: {e}'}), 500
