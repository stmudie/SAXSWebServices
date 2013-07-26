from flask import Blueprint, request, send_file, render_template

secprofileslocal_app = Blueprint('secprofiles', __name__,template_folder='templates',static_folder='static')

@secprofileslocal_app.route("/")
def profile():
    return render_template("secprofiles.html")