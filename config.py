SECRET_KEY = 'PAWR#$asd%EH'
DEBUG = True

BEAMLINE_NETWORKS = {
    "SAXS":"10.138.0.0/16",
    "LOCAL" :"127.0.0.1"
}

REDIS = {
    "LOG":"10.138.11.70:0",
    "REPORT":"10.138.11.70:1",
    "WEBSERVER":"10.138.11.69:0"
}
