from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

mdaplotter_app = Blueprint('mdaplotter', __name__,template_folder='templates',static_folder='static')

@mdaplotter_app.route("/")
@beamline_or_vbl
def profile():
    return render_template("mdaplotter.html")