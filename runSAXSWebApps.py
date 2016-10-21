from gevent import monkey; monkey.patch_all()
from socketio import socketio_manage
from socketio.server import SocketIOServer
from flask import Flask, request, session
from wellplates import wellPlate_app
from wellplates import WellPlateNamespace
from saxsprofiles import saxsprofiles_app
from saxsprofiles import SAXSProfilesNamespace
from secprofiles import secprofiles_app
from secprofiles import SECProfilesNamespace
#from gradientprofiles import gradientprofiles_app
#from gradientprofiles import GradientProfilesNamespace
from pipelinereport import pipelinereport_app
from pipelinereport import PipelineReportNamespace
from genericscan import genericscan_app
from genericscan import GenericScanNamespace
from logviewer import logviewer_app
from logviewer import LogViewerNamespace
#from mdaplotter import mdaplotter_app
#from mdaplotter import MDAPlotterNamespace
#from catcher import catcher_app
#from catcher import CatcherNamespace
#from catcher2 import catcher2_app
#from catcher2 import Catcher2Namespace
from landingpage import landingpage_app
from reverse import ReverseProxied
from plugins import vbl, beamline
try:
    import localconfig as config
except Exception:
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
app.register_blueprint(secprofiles_app, url_prefix='/secprofiles')
#app.register_blueprint(gradientprofiles_app, url_prefix='/gradientprofiles')
app.register_blueprint(pipelinereport_app, url_prefix='/pipelinereport')
app.register_blueprint(genericscan_app, url_prefix='/genericscan')
app.register_blueprint(logviewer_app, url_prefix='/logviewer')
#app.register_blueprint(mdaplotter_app, url_prefix='/mdaplotter')
#app.register_blueprint(catcher_app, url_prefix='/catcher')
#app.register_blueprint(catcher2_app, url_prefix='/catcher2')
app.register_blueprint(landingpage_app, url_prefix='/')
app.register_blueprint(landingpage_app, url_prefix='/static')
#attributes = { 'epn': ['default_0001'], 'nicknames': [] }

@app.route("/socket.io/<path:path>")
def run_socketio(path):
    
    if vbl.current_user != None:
        user = vbl.current_user['email']
    else:
        user = 'Beamline'
    
    print beamline.current
    
    attributes = { 'epn': [user], 'REDIS': app.config['REDIS'], 'GENERAL': app.config['GENERAL'], 'beamline': beamline.current}
    #socketio_manage(request.environ, {'/wellplates': WellPlateNamespace, '/saxsprofiles':SAXSProfilesNamespace, '/secprofiles':SECProfilesNamespace, '/pipelinereport':PipelineReportNamespace, '/genericscan':GenericScanNamespace, '/mdaplotter':MDAPlotterNamespace}, attributes)
    #socketio_manage(request.environ, {'/wellplates': WellPlateNamespace, '/saxsprofiles':SAXSProfilesNamespace, '/secprofiles':SECProfilesNamespace, '/pipelinereport':PipelineReportNamespace, '/genericscan':GenericScanNamespace, '/logviewer':LogViewerNamespace}, attributes)
    #socketio_manage(request.environ, {'/wellplates': WellPlateNamespace, '/saxsprofiles':SAXSProfilesNamespace, '/secprofiles':SECProfilesNamespace, '/pipelinereport':PipelineReportNamespace, '/genericscan':GenericScanNamespace, '/logviewer':LogViewerNamespace, '/catcher':CatcherNamespace}, attributes)
    socketio_manage(request.environ, {'/wellplates': WellPlateNamespace, '/saxsprofiles':SAXSProfilesNamespace, '/secprofiles':SECProfilesNamespace,
                                      #'/gradientprofiles':GradientProfilesNamespace,
                                      '/pipelinereport':PipelineReportNamespace, '/genericscan':GenericScanNamespace, '/logviewer':LogViewerNamespace, '/catcher2':Catcher2Namespace}, attributes)
    return ''

if __name__ == '__main__':
    print 'Listening on port 8081 and on port 843 (flash policy server)'
    SocketIOServer(('0.0.0.0', 8081), app,
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
