from flask import Blueprint, request, send_file, render_template

pipelinereport_app = Blueprint('pipelinereport', __name__,template_folder='templates',static_folder='static')

@pipelinereport_app.route("/")
def report():
    return render_template("pipelineReport.html")

