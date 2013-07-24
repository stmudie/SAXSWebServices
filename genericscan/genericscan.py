import qrcode
from StringIO import StringIO
from flask import Blueprint, request, send_file, render_template
from plugins import vbl, beamline, beamline_or_vbl

genericscan_app = Blueprint('genericscan', __name__,template_folder='templates',static_folder='static')

def serve_pil_image(pil_img):
    img_io = StringIO()
    pil_img.save(img_io)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@genericscan_app.route("/")
@beamline_or_vbl
def well():
    return render_template('genericscan.html',epn='',scan='',rel='./')

@genericscan_app.route("/<epn>/<scan>/")
@beamline_or_vbl
def well1(epn,scan):
    return render_template('genericscan.html',epn=epn,scan=scan,rel='../../')

@genericscan_app.route("/<scan>/")
@beamline_or_vbl
def well2(scan):
    return render_template('genericscan.html',epn='',scan=scan,rel='../')

@genericscan_app.route("/qrcode/<epn>/<scan>/")
@beamline_or_vbl
def serve_img(epn,scan):
    img = qrcode.make('http://aswebsaxs/genericscan/' + epn + '/' + scan)
    return serve_pil_image(img)

@genericscan_app.route("/qrcode")
@beamline_or_vbl
def serve_img_empty():
    print 'qrcode'
    img = qrcode.make('This is not the code you are looking for.')
    return serve_pil_image(img)

