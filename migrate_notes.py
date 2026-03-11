from app import app
from models import db, Eslatma

print("Creating table eslatmalar...")
with app.app_context():
    Eslatma.__table__.create(db.engine, checkfirst=True)
    print("Successfully created eslatmalar table")
