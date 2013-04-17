from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

pipelinereport_app = Blueprint('pipelinereport', __name__,template_folder='templates',static_folder='static')

@pipelinereport_app.route("/")
@beamline_or_vbl
def report():
    return render_template("pipelineReport.html")

