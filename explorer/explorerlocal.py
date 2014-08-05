from flask import Blueprint, request, send_file, render_template

explorerlocal_app = Blueprint('explorer', __name__,template_folder='templates',static_folder='static')

@explorerlocal_app.route("/")
def profile():
    return render_template("explorer.html")