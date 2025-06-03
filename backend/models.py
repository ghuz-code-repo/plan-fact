from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    
    def __repr__(self):
        return f'<User {self.login}>'
    
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    max_discount_full = db.Column(db.Integer, nullable=False)
    do_kadastra = db.Column(db.Integer, nullable=False)
    fact_deals = db.Column(db.Integer, nullable=False)
    plan_deals = db.Column(db.Integer, nullable=False)
    deviation = db.Column(db.Integer, nullable=False)
    lowest_price_full = db.Column(db.Integer, nullable=False)
    lowest_price_full_dol = db.Column(db.Integer, nullable=False)
    average_price_full = db.Column(db.Integer, nullable=False)
    average_price_full_dol = db.Column(db.Integer, nullable=False)
    data_update = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<Project {self.name}>'