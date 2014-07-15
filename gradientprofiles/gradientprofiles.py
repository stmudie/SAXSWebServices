from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

gradientprofiles_app = Blueprint('gradientprofiles', __name__,template_folder='templates',static_folder='static')

@gradientprofiles_app.route("/")
@beamline_or_vbl
def profile():
    return render_template("gradientprofiles.html")