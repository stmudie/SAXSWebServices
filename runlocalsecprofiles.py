from gevent import monkey; monkey.patch_all()
from socketio import socketio_manage
from socketio.server import SocketIOServer
from flask import Flask, request, session
from secprofiles import secprofileslocal_app
from secprofiles import SECProfilesNamespace
from reverse import ReverseProxied
from RedisSession import RedisSessionInterface
try:
    import localconfig as config
except Exception:
    import config
    
app = Flask(__name__)
app.config.from_object(config)

# app.session_interface = RedisSessionInterface()

app.wsgi_app = ReverseProxied(app.wsgi_app)

app.register_blueprint(secprofileslocal_app, url_prefix='/secprofiles')

attributes = { 'epn' : ['local'],'REDIS' : app.config['REDIS'],'GENERAL' : app.config['GENERAL']}

@app.route("/socket.io/<path:path>")
def run_socketio(path):
        
    socketio_manage(request.environ, {'/secprofiles':SECProfilesNamespace}, attributes)
    return ''

if __name__ == '__main__':
    print 'Listening on port 8081 and on port 843 (flash policy server)'
    SocketIOServer(('0.0.0.0', 8081), app,
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
