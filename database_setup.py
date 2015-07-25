from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base

__author__ = 'Zackarias Gustavsson'

base = declarative_base()


class Users(base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)


class Music(base):
    __tablename__ = 'music'

    id = Column(Integer, primary_key=True)
    song_name = Column(String(80), nullable=False)
    song_uri = Column(String)
    artist = Column(String, nullable=False)
    album_name = Column(String, nullable=False)
    album_cover = Column(String, nullable=False)


engine = create_engine('sqlite:///test.db')

base.metadata.create_all(engine)
