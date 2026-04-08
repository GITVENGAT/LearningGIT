from flask import Flask
from routes import bp  # import your blueprint
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # secret key for sessions

# Register blueprint
app.register_blueprint(bp)

# Optional: Global config
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SESSION_COOKIE_SECURE'] = False  # True if using HTTPS

# Run server
if __name__ == "__main__":
    app.run(debug=True)  # debug=False in production