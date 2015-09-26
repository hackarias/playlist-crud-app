from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

base = declarative_base()


class User(base):
    """ Model storing information about the user. Currently it stores the users
     id, username, name, email and picture """
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(25))
    name = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String)


class Playlist(base):
    """ Model storing information about the users playlist. Currently stores
    id, name, description, user_id. """
    __tablename__ = 'playlist'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(80))
    user_id = Column(Integer, ForeignKey('user.id'))
    user_relationship = relationship(User)

    @property
    def serialize(self):
        """ Returns data for each object in serializable format """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'user_relationship': self.user_relationship,
        }


class Song(base):
    """ Model storing the information about the users songs. Currently stores
    id, song name, artist, playlist id and user id. """
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True)
    song_name = Column(String(80), nullable=False)
    artist = Column(String, nullable=False)
    playlist_id = Column(Integer, ForeignKey('playlist.id'))
    playlist_relationship = relationship(Playlist)
    user_id = Column(Integer, ForeignKey('user.id'))
    user_relationship = relationship(User)

    @property
    def serialize(self):
        """ Returns data for each object in serializable format """
        return {
            'id': self.id,
            'song_name': self.song_name,
            'artist': self.artist,
            'playlist_id': self.playlist_id,
            'playlist_relationship': self.playlist_relationship,
            'user_id': self.user_id,
            'user_relationship': self.user_relationship,
        }

engine = create_engine('sqlite:///test.db')

base.metadata.create_all(engine)
