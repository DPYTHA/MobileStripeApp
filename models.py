from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    pays = db.Column(db.String(100))
    password_hash = db.Column(db.Text, nullable=False)
    date_inscription = db.Column(db.DateTime, default=db.func.current_timestamp())
    abonnement_active = db.Column(db.Boolean, default=False)

class Bourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_limite = db.Column(db.DateTime, nullable=False)
