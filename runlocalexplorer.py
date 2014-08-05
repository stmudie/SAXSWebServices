from gevent import monkey; monkey.patch_all()
from socketio import socketio_manage
from socketio.server import SocketIOServer
from flask import Flask, request, session
from explorer import explorerlocal_app
from explorer import ExplorerNamespace
from reverse import ReverseProxied
from RedisSession import RedisSessionInterface
import argparse
from os import getcwd


try:
    import localconfig as config
except Exception:
    import config

parser = argparse.ArgumentParser()
parser.add_argument('rootpath', nargs='?', default=getcwd(), type=str, help="root directory to search for experiments")
    
args = parser.parse_args()
root_path = args.rootpath

app = Flask(__name__)
app.config.from_object(config)
app.debug = True
app.session_interface = RedisSessionInterface()

app.wsgi_app = ReverseProxied(app.wsgi_app)

app.register_blueprint(explorerlocal_app, url_prefix='/explorer')

attributes = {'epn': ['local'], 'REDIS': app.config['REDIS'], 'GENERAL': app.config['GENERAL'], 'root_path': root_path}


@app.route("/socket.io/<path:path>")
def run_socketio(path):
        
    socketio_manage(request.environ, {'/explorer': ExplorerNamespace}, attributes)
    return ''

if __name__ == '__main__':
    
    print 'Listening on port 8081 and on port 843 (flash policy server)'
    SocketIOServer(('0.0.0.0', 8081), app,
        resource="socket.io", policy_server=True,
        policy_listener=('0.0.0.0', 10843)).serve_forever()
