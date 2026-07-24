"""
Shared extension instances, created here (not in app.py) so that both
app.py and models.py can import them without circular-import issues.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Please log in to view that page."
login_manager.login_message_category = "info"
