# Plays, characters, annotations, lines, scenes

from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from .database import Base


class Play(Base):
    __tablename__ = "plays"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    genre = Column(String)
    play_metadata = Column(JSON)

    # relationships
    scenes = relationship("Scene", back_populates="play")
    characters = relationship("Character", back_populates="play")


class Scene(Base):
    __tablename__ = "scenes"
    id = Column(Integer, primary_key=True)
    play_id = Column(Integer, ForeignKey("plays.id"))
    act = Column(Integer)
    scene_number = Column(Integer)
    description = Column(Text)

    play = relationship("Play", back_populates="scenes")
    lines = relationship("Line", back_populates="scene")

# todo: add act.scene.line?

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    play_id = Column(Integer, ForeignKey("plays.id"))
    description = Column(Text)

    play = relationship("Play", back_populates="characters")
    lines = relationship("Line", back_populates="character")


class Line(Base):
    __tablename__ = "lines"
    id = Column(Integer, primary_key=True, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"))
    character_id = Column(Integer, ForeignKey("characters.id"))
    text = Column(Text)
    text_tsv = Column(TSVECTOR)

    scene = relationship("Scene", back_populates="lines")
    character = relationship("Character", back_populates="lines")
    annotations = relationship("Annotation", back_populates="line")


class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    line_id = Column(Integer, ForeignKey("lines.id"), nullable=False)
    note = Column(Text, nullable=False)
    author = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    line = relationship("Line", back_populates="annotations")
