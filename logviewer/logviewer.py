from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

logviewer_app = Blueprint('logviewer', __name__,template_folder='templates',static_folder='static')

@logviewer_app.route("/")
@beamline_or_vbl
def report():
    return render_template("logviewer.html")