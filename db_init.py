import os
from flask import Flask
from flask_migrate import Migrate, upgrade
from models import db  # import the db instance from models.py
from config import DATABASE_FILE  # Import DATABASE_FILE from config.py

app = Flask(__name__)

# Configure the database URI using the value from config.py
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_FILE}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy and Flask-Migrate
db.init_app(app)
migrate = Migrate(app, db)

# Function to initialize the database
def initialize_database():
    with app.app_context():
        # Check if the database file exists
        if not os.path.exists(DATABASE_FILE):
            # Run flask db upgrade to create the database schema
            print("Database not found. Creating a new database...")
            upgrade()
        else:
            print("Database already exists.")

# Run the initialization function if this script is executed directly
if __name__ == "__main__":
    initialize_database()
