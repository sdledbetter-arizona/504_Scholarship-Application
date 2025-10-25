from flask import Blueprint, flash, redirect, render_template, request, url_for

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET','POST'])
def login():
    return render_template("auth/login.html")
