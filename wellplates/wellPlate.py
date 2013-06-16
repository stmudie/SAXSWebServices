import qrcode
from StringIO import StringIO
from flask import Blueprint, request, send_file, render_template, redirect
from plugins import vbl, beamline, beamline_or_vbl

wellPlate_app = Blueprint('wellPlate', __name__,template_folder='templates',static_folder='static')

wellIDs = ['Well_' + str(num) for num in range(96)]

def serve_pil_image(pil_img):
    img_io = StringIO()
    pil_img.save(img_io)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@wellPlate_app.route("/")
@beamline_or_vbl
def well():
    return render_template('wellplates.html',wells=wellIDs,epn='',plate='',rel='./')

@wellPlate_app.route("/<epn>/<plate>/")
@beamline_or_vbl
def well1(epn,plate):
    return render_template('wellplates.html',wells=wellIDs,epn=epn,plate=plate,rel='../../')

@wellPlate_app.route("/<plate>/")
@beamline_or_vbl
def well2(plate):
    return render_template('wellplates.html',wells=wellIDs,epn='',plate=plate,rel='../')

@wellPlate_app.route("/qrcode/<epn>/<plate>/")
@beamline_or_vbl
def serve_img(epn,plate):
    img = qrcode.make('http://aswebsaxs/wellPlates/' + epn + '/' + plate)
    return serve_pil_image(img)

@wellPlate_app.route("/qrcode")
@beamline_or_vbl
def serve_img_empty():
    print 'qrcode'
    img = qrcode.make('This is not the code you are looking for.')
    return serve_pil_image(img)

