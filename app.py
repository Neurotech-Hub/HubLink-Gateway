import threading
import time
import asyncio
from flask import Flask
from flask_migrate import Migrate
from models import db  # import the db instance from models.py
from config import DATABASE_FILE
from DBManager import fetch_and_store_settings
from LinkBLE import searchForLinks

app = Flask(__name__)

# Configure the database URI
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_FILE}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy and Flask-Migrate
db.init_app(app)
migrate = Migrate(app, db)

# Define the periodic tasks
def periodic_tasks():
    while True:
        fetch_and_store_settings()     # Run the sync task
        asyncio.run(searchForLinks())  # Run the async task
        time.sleep(60)                 # Wait

if __name__ == "__main__":
    # Start the Flask server in a background thread
    threading.Thread(target=periodic_tasks, daemon=True).start()

    # Start the Flask application
    app.run(debug=False)
