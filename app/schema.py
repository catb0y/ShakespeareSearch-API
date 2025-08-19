# Schema for Pydantic

from pydantic import BaseModel
from typing import List, Optional

class AnnotationSchema(BaseModel):
    id: int
    note: str
    class Config:
        orm_mode = True
        
class AnnotationCreate(BaseModel):
    note: str
    author: Optional[str] = None

class AnnotationOut(BaseModel):
    id: int
    note: str
    author: Optional[str] = None

    class Config:
        orm_mode = True

class LineSchema(BaseModel):
    id: int
    text: str
    annotations: List[AnnotationSchema] = []
    class Config:
        orm_mode = True

class CharacterSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    class Config:
        orm_mode = True

class SceneSchema(BaseModel):
    id: int
    act: int
    scene_number: int
    description: Optional[str]
    lines: List[LineSchema] = []
    class Config:
        orm_mode = True

class PlaySchema(BaseModel):
    id: int
    title: str
    genre: str
    play_metadata: dict
    scenes: List[SceneSchema] = []
    characters: List[CharacterSchema] = []

    class Config:
        orm_mode = True
        