import os
from dotenv import load_dotenv
# Импорты необходимых библиотек
import locale
import sys
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, current_app, url_for
from models import db
from routes import routes_bp  # Make sure to import routes_bp
from prefix_middleware import PrefixMiddleware


load_dotenv()

# Check if running behind proxy - force to True for debugging
behind_proxy = os.getenv('BEHIND_PROXY', 'false').lower() == 'true'
print(f"BEHIND_PROXY environment variable: {behind_proxy}")

prefix = '/plan-fact' if behind_proxy else ''
print(f"Using URL prefix: '{prefix}'")

# Initialize Flask app with static files URL handling
app = Flask(__name__, 
    static_folder='static',
    static_url_path='/static')  # Always use /static regardless of prefix

# Configure app to work behind a proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Add a direct static file handler route to bypass Flask's router
@app.route('/plan-fact/static/<path:filename>')
def custom_static(filename):
    print(f"Custom static file request for: {filename}")
    return app.send_static_file(filename)

# Configuration without SERVER_NAME which can cause routing issues
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///ingd.db"),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-key-for-development-only"),
    APPLICATION_ROOT=prefix,
    MAX_CONTENT_LENGTH=100 * 1024 * 1024  # 100MB max upload size
)

db.init_app(app)  # Initialize SQLAlchemy with the app


# Register the blueprint
app.register_blueprint(routes_bp)

# Apply prefix middleware if running behind proxy
if behind_proxy:
    # Create middleware BEFORE setting static_url_path
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, app=app, prefix=prefix)
    # Now set the static URL path correctly
    app.static_url_path = prefix + '/static'
    print(f"Set static_url_path to: {app.static_url_path}")
    
    # Test URL generation
    with app.test_request_context():
        print(f"Test static URL generation: {url_for('static', filename='style.css')}")
        print(f"Test route URL generation: {url_for('routes.main')}")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=80, debug=False)