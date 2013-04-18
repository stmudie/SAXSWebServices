from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

landingpage_app = Blueprint('landingpage', __name__,template_folder='templates',static_folder='static')

@landingpage_app.route("/")
@beamline_or_vbl
def report():
    if vbl.current_user != None:
        user = vbl.current_user['email']
    else :
        user = ''
    return render_template("landingpage.html",user=user)