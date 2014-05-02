from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

catcher2_app = Blueprint('catcher2', __name__,template_folder='templates',static_folder='static')

@catcher2_app.route("/")
@beamline_or_vbl
def profile():
    return render_template("catcher2.html")