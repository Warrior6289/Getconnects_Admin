import os
from getconnects_admin import create_app

app = create_app(os.getenv("FLASK_CONFIG", "production"))
