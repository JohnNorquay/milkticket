from flask import Flask
from db_init import db

# Initialize the Flask app
app = Flask(__name__)

# Set a secret key for CSRF protection
app.config['SECRET_KEY'] = 'a_long_random_secret_key'

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///milk_ticket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with the app
db.init_app(app)

# Import models and routes
from models import MilkTicket
from routes import *

# Ensure tables are created only once
@app.before_request
def create_tables():
    if not hasattr(create_tables, 'tables_created'):
        db.create_all()
        create_tables.tables_created = True

if __name__ == '__main__':
    app.run(debug=True)
