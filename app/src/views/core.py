from flask import Blueprint, flash, redirect, render_template, request, url_for

core = Blueprint('core', __name__)


@core.route('/')
def home():
    return render_template("base.html")