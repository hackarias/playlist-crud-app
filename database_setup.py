from sqlalchemy import Column, Integer, String

__author__ = 'Zackarias Gustavsson'


class Users():
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(250), nullable=False)

    def __init__(self):
        pass


class Music():
    __tablename__ = 'music'

    id = Column(Integer, primary_key=True)
    song_name = Column(String(80), nullable=False)
    song_uri = Column(String)
    artist = Column(String, nullable=False)
    album_name = Column(String, nullable=False)
    album_cover = Column(String, nullable=False)

    def __init__(self):
        pass
