from flask import Flask
from app.models import init_db
import os
from app.routes import views
from flask_login import LoginManager
from app.models import get_user_by_id, DB_PATH


app = Flask(__name__, template_folder='templates')  # <- this is important
app.secret_key = 'NDY4ZWViMmY1OGNhYWU2OTVhZjk1'
app.register_blueprint(views)

login_manager = LoginManager()
login_manager.login_view = 'views.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)

if __name__ == "__main__":
    os.makedirs('/data/printjobs', exist_ok=True)
    if not os.path.exists(DB_PATH):
        open(DB_PATH, 'w').close()
    init_db()
    app.run(host="0.0.0.0", port=8080)