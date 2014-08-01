from flask import Blueprint, request, send_file, render_template

gradientprofileslocal_app = Blueprint('gradientprofiles', __name__,template_folder='templates',static_folder='static')

@gradientprofileslocal_app.route("/")
def profile():
    return render_template("gradientprofiles.html")