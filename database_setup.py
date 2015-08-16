from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

base = declarative_base()


class User(base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String)


class Playlist(base):
    __tablename__ = 'playlist'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(80))
    user_id = Column(Integer, ForeignKey('user.id'))
    user_relationship = relationship(User)


class Song(base):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True)
    song_name = Column(String(80), nullable=False)
    song_uri = Column(String)
    artist = Column(String, nullable=False)
    album_name = Column(String, nullable=False)
    album_cover = Column(String, nullable=False)
    playlist_id = Column(Integer, ForeignKey('playlist.id'))
    playlist_relationship = relationship(Playlist)
    user_id = Column(Integer, ForeignKey('user.id'))
    user_relationship = relationship(User)


engine = create_engine('sqlite:///test.db')

base.metadata.create_all(engine)
