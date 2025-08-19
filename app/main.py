from typing import List
from fastapi import HTTPException
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session, joinedload
from . import models, database, schema
from .schema import PlaySchema
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast, String, Integer, and_

app = FastAPI()

# before:
# create tables: python -m app.create_tables
# python etl.py (populate fields)
# run server: uvicorn app.main:app --reload 
# See Swagger at http://127.0.0.1:8000/docs


# Get DB
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# Endpoints

# Retrieve all genres
@app.get("/plays/genres")
def get_play_genres(db: Session = Depends(get_db)):
    q = db.query(models.Play)
    genres = [
        play.genre
        for play in q.all()
        ]
    return list(set(genres))

# Search lines by keyword, optional genre filter
@app.get("/search", response_model=list[schema.LineSchema])
def search_lines(query: str, genre: str = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(models.Line).options(joinedload(models.Line.annotations),
                                      joinedload(models.Line.scene).joinedload(models.Scene.play),
                                      joinedload(models.Line.character))
    if genre:
        q = q.join(models.Scene).join(models.Play).filter(models.Play.genre == genre)
    q = q.filter(models.Line.text.ilike(f"%{query}%"))
    
    q = q.limit(min(limit, 100))
    return q.all()

# Retrieve all play ids
@app.get("/plays/ids")
def get_play_ids(db: Session = Depends(get_db)):
    q = db.query(models.Play)
    return [
        ({"play_title": play.title, "play_id": play.id}) 
        for play in q.all()
        ]
    
# Retrieve all line ids
@app.get("/lines/ids")
def get_line_ids(limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(models.Line)
    q = q.limit(min(limit, 100))
    return [
        [{"play_title": line.scene.play.title, "scene_number": line.scene.scene_number, "line": line.text, "line_id": line.id}] 
        for line in q.all()
        ]

# Retrieve all scenes of a play
@app.get("/plays/{play_id}/scenes", response_model=list[schema.SceneSchema])
def get_scenes(play_id: int, db: Session = Depends(get_db)):
    return db.query(models.Scene).filter(models.Scene.play_id == play_id).all()

# 3Retrieve all characters of a play
@app.get("/plays/{play_id}/characters", response_model=list[schema.CharacterSchema])
def get_characters(play_id: int, db: Session = Depends(get_db)):
    return db.query(models.Character).filter(models.Character.play_id == play_id).all()

# Retrieve annotations for a line
@app.get("/lines/{line_id}/annotations", response_model=List[schema.AnnotationCreate])
def get_annotations(line_id: int, db: Session = Depends(get_db)):
    annotations = db.query(models.Annotation).filter(models.Annotation.line_id == line_id).all()
    if not annotations:
        raise HTTPException(status_code=404, detail="No annotations found")
    return annotations

# Add annotations for a line
@app.post("/lines/{line_id}/annotations", response_model=schema.AnnotationOut)
def add_annotation(line_id: int, annotation: schema.AnnotationCreate, db: Session = Depends(get_db)):
    db_annotation = models.Annotation(line_id=line_id, note=annotation.note, author=annotation.author)
    db.add(db_annotation)
    db.commit()
    db.refresh(db_annotation)
    return db_annotation


# Get metadata schema
@app.get("/metadata/schema")
def get_metadata_schema(db: Session = Depends(get_db)):
    return {
        "year_published": "int",
        "first_produced": "int",
        "period": "str",
        "source": "str",
}


# Search lines by play metadata key

@app.get("/search_metadata")
def search_lines_by_metadata(
    year_published_min: int = None,
    year_published_max: int = None,
    first_produced_min: int = None,
    first_produced_max: int = None,
    period: str = None,
    source: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Line).join(models.Scene).join(models.Play)
    conditions = []

    # Numeric filters
    if year_published_min is not None:
        conditions.append(cast(models.Play.play_metadata["year_published"], Integer) >= year_published_min)
    if year_published_max is not None:
        conditions.append(cast(models.Play.play_metadata["year_published"], Integer) <= year_published_max)
    if first_produced_min is not None:
        conditions.append(cast(models.Play.play_metadata["first_produced"], Integer) >= first_produced_min)
    if first_produced_max is not None:
        conditions.append(cast(models.Play.play_metadata["first_produced"], Integer) <= first_produced_max)

    # String filters (partial match)
    if period:
        conditions.append(cast(models.Play.play_metadata["period"], String).ilike(f"%{period}%"))
    if source:
        conditions.append(cast(models.Play.play_metadata["source"], String).ilike(f"%{source}%"))

    if conditions:
        query = query.filter(and_(*conditions))

    return query.options(joinedload(models.Line.annotations)).all()

# Add metadata
@app.post("/play/metadata/", response_model=PlaySchema)
def add_metadata(play_id: int, metadata: dict,  db: Session = Depends(get_db)):
    play = db.query(models.Play).filter(models.Play.id == play_id).first()
    if not play:
        raise HTTPException(status_code=404, detail="Play not found")
    
    if play.play_metadata:
        play.play_metadata.update(metadata)
    else:
        play.play_metadata = metadata
        
    db.commit()
    db.refresh(play)
    return play