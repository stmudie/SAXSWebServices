from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

explorer_app = Blueprint('explorer', __name__,template_folder='templates',static_folder='static')

@explorer_app.route("/")
@beamline_or_vbl
def report():
    return render_template("explorer.html")
