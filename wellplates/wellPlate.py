import qrcode
from StringIO import StringIO
from flask import Blueprint, request, send_file, render_template

wellPlate_app = Blueprint('wellPlate', __name__,template_folder='templates',static_folder='static')

wellIDs = ['Well_' + str(num) for num in range(96)]

def serve_pil_image(pil_img):
    img_io = StringIO()
    pil_img.save(img_io)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@wellPlate_app.route("/")
def well():
    return render_template('wellplates.html',wells=wellIDs,epn='Norwood_5374A',plate='')

@wellPlate_app.route("/<epn>/<plate>")
def well1(epn,plate):
    return render_template('wellplates.html',wells=wellIDs,epn=epn,plate=plate,rel='../')

@wellPlate_app.route("/qrcode/<epn>/<plate>")
def serve_img(epn,plate):
    img = qrcode.make('http://10.6.0.65/' + epn + '/' + plate)
    return serve_pil_image(img)

@wellPlate_app.route("/qrcode")
def serve_img_empty():
    print 'qrcode'
    img = qrcode.make('This is not the code you are looking for.')
    return serve_pil_image(img)

