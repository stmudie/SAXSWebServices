from flask import Blueprint, request, send_file, render_template

saxsprofiles_app = Blueprint('saxsprofiles', __name__,template_folder='templates',static_folder='static')

@saxsprofiles_app.route("/")
def profile():
    return render_template("saxsprofiles.html")