from gevent import monkey; monkey.patch_all()
from socketio import socketio_manage
from socketio.server import SocketIOServer
from flask import Flask, request, session
from wellplates import wellPlate_app
from wellplates import WellPlateNamespace
from saxsprofiles import saxsprofiles_app
from saxsprofiles import SAXSProfilesNamespace
from pipelinereport import pipelinereport_app
from pipelinereport import PipelineReportNamespace
from genericscan import genericscan_app
from genericscan import GenericScanNamespace
from landingpage import landingpage_app
from reverse import ReverseProxied
from plugins import vbl, beamline
import config
from RedisSession import RedisSessionInterface

app = Flask(__name__)
app.config.from_object(config)

app.session_interface = RedisSessionInterface()
vbl.init_app(app)
beamline.init_app(app)
app.wsgi_app = ReverseProxied(app.wsgi_app)

app.register_blueprint(wellPlate_app, url_prefix='/wellplates')
app.register_blueprint(saxsprofiles_app, url_prefix='/saxsprofiles')
app.register_blueprint(pipelinereport_app, url_prefix='/pipelinereport')
app.register_blueprint(genericscan_app, url_prefix='/genericscan')
app.register_blueprint(landingpage_app, url_prefix='/')

#attributes = { 'epn': ['default_0001'], 'nicknames': [] }

@app.route("/socket.io/<path:path>")
def run_socketio(path):
    if vbl.current_user != None:
        user = vbl.current_user['email']
    else :
        user = 'Default_123'
    
    attributes = { 'epn' : [user]}
    print path
    socketio_manage(request.environ, {'/wellplates': WellPlateNamespace, '/saxsprofiles':SAXSProfilesNamespace, '/pipelinereport':PipelineReportNamespace, '/genericscan':GenericScanNamespace}, attributes)
    return ''

if __name__ == '__main__':
    print 'Listening on port 8081 and on port 843 (flash policy server)'
    SocketIOServer(('0.0.0.0', 8081), app,
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
