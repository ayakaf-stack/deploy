from models.extensions import db
from sqlalchemy import UniqueConstraint,ForeignKey

class Word(db.Model):
    __tablename__ = "words"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    word = db.Column(
        db.String(50),
        nullable=False
    )

    reading = db.Column(
        db.String(50),
        nullable=False
    )

    mean = db.Column(
        db.Text,
        nullable=False
    )

    __table_args__ = (UniqueConstraint('word','reading',name='unique_word'),)


    genres = db.relationship('Word_genre',back_populates='words')
    goods = db.relationship('Good_word')



class Genre(db.Model):
    __tablename__ = 'genres'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    genre = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

    word_genres = db.relationship('Word_genre',back_populates='genre')



class Word_genre(db.Model):
    __tablename__ = 'word_genres'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    word_id = db.Column(
        db.Integer,
        ForeignKey('words.id'),
        nullable=False
    )

    genre_id = db.Column(
        db.Integer,
        ForeignKey('genres.id'),
        nullable=False
    )

    genre = db.relationship('Genre',back_populates='word_genres')
    words = db.relationship('Word',back_populates='genres')



class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    user_name = db.Column(
        db.String(255),
        nullable=False
    )

    good_words = db.relationship("Good_word",cascade='all, delete-orphan')
    good_texts = db.relationship("Good_text",cascade='all,delete-orphan')
    texts = db.relationship('Text',cascade='all,delete-orphan')



class Text(db.Model):
    __tablename__ = 'texts'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.Integer,
        ForeignKey('users.id',ondelete="CASCADE"),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=False
    )

    main_text = db.Column(
        db.Text,
        nullable=False
    )

    text_status = db.Column(
        db.Integer,
        nullable=False
    )

    word = db.Column(
        db.Integer,
        ForeignKey('words.id'),
        nullable=False
    )

    goods = db.relationship('Good_text',cascade='all,delete-orphan')



class Good_word(db.Model):
    __tablename__ = 'good_words'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    word_id = db.Column(
        db.Integer,
        ForeignKey('words.id'),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        ForeignKey('users.id',ondelete='CASCADE'),
        nullable=False
    )

    __table_args__ = (UniqueConstraint('word_id','user_id',name='good_word_unique'),)



class Good_text(db.Model):
    __tablename__ = 'good_texts'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    text_id = db.Column(
        db.Integer,
        ForeignKey('texts.id',ondelete='CASCADE'),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        ForeignKey('users.id',ondelete='CASCADE'),
        nullable=False
    )

    __table_args__= (UniqueConstraint('text_id','user_id',name='good_text_unique'),)