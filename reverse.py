class ReverseProxied(object):
            environ['REMOTE_ADDR'] = environ.pop('HTTP_X_FORWARDED_FOR')
        
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')