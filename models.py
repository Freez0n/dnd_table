from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    characters = db.relationship('Character', backref='owner', lazy=True)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    dm_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), default="Новый герой")
    race = db.Column(db.String(50), default="Человек")
    char_class = db.Column(db.String(50), default="Воин")
    level = db.Column(db.Integer, default=1)

    strength = db.Column(db.Integer, default=10)
    dexterity = db.Column(db.Integer, default=10)
    constitution = db.Column(db.Integer, default=10)
    intelligence = db.Column(db.Integer, default=10)
    wisdom = db.Column(db.Integer, default=10)
    charisma = db.Column(db.Integer, default=10)

    hp_max = db.Column(db.Integer, default=10)
    hp_current = db.Column(db.Integer, default=10)
    ac = db.Column(db.Integer, default=10)
    initiative_bonus = db.Column(db.Integer, default=0)

    inventory = db.Column(db.Text, default="")
    spells = db.Column(db.Text, default="")