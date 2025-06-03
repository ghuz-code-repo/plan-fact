class PrefixMiddleware:
    """
    Middleware for correctly handling static files and URL prefixes when behind a proxy.
    """
    def __init__(self, wsgi_app, app=None, prefix='/plan-fact'):
        self.wsgi_app = wsgi_app
        self.app = app
        self.prefix = prefix
        
        print(f"PrefixMiddleware initialized with prefix: '{self.prefix}'")
        
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        
        print(f"Request path: {path_info}")
        
        # If path doesn't start with prefix but should go to our app
        if not path_info.startswith(self.prefix):
            # This might be a static file request, so check if it's going to /static
            if path_info.startswith('/static'):
                environ['PATH_INFO'] = self.prefix + path_info
                print(f"Rewriting static path to: {environ['PATH_INFO']}")
        
        # Standard prefix handling for all other requests
        elif path_info.startswith(self.prefix):
            # Record original path for debugging
            original_path = path_info
            
            # Strip prefix from PATH_INFO
            new_path = path_info[len(self.prefix):]
            if not new_path:
                new_path = '/'
            environ['PATH_INFO'] = new_path
            
            # Update SCRIPT_NAME
            environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '') + self.prefix
            
            print(f"Modified path: {original_path} → {environ['PATH_INFO']}")
        
        return self.wsgi_app(environ, start_response)
