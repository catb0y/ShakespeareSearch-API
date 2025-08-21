from typing import List
from fastapi import HTTPException
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func, text
from . import models, database, schema
from .schema import PlaySchema
from fastapi import Depends
from sqlalchemy.orm import Session

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

# Full-text search
@app.get("/search_tsv", response_model=list[schema.LineSchema])
def search_lines_tsv(query: str, db: Session = Depends(get_db)):
    q = db.query(models.Line).options(
        joinedload(models.Line.annotations),
        joinedload(models.Line.scene).joinedload(models.Scene.play),
        joinedload(models.Line.character)
    )
    
    # Full-text search w/ PostgreSQL @@ operator
    ts_query = func.to_tsquery(query)
    q = q.filter(models.Line.text_tsv.op('@@')(ts_query))
    
    return q.limit(50).all()

@app.get("/db/indexes")
def get_indexes(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public';
    """))
    
    # Use .mappings() to get dicts
    return [row for row in result.mappings()]

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
  "catalog_title": "str",
  "year_published": "str",
  "first_produced": "str",
  "historical_setting_year": "str",
  "historical_event": "str",
  "period_label": "str",
  "genre_subtype": "str",
  "principal_themes": ["str", "str", "str"],
  "principal_figures": ["str", "str", "str"],
  "primary_sources": ["str", "str"],
  "reference_source": "str",
  "editorial_notes": "str"
}



# Search lines by play metadata key
@app.get("/search_metadata")
def search_lines_by_metadata(
    year_published: str = None,
    first_produced: str = None,
    period: str = None,
    source: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Play)
    conditions = []

    if year_published:
        conditions.append(models.Play.play_metadata['year_published'].astext == year_published)
    if first_produced:
        conditions.append(models.Play.play_metadata['first_produced'].astext == first_produced)
    if period:
        conditions.append(models.Play.play_metadata['period'].astext == period)
    if source:
        conditions.append(models.Play.play_metadata['source'].astext.ilike(f"%{source}%"))

    if conditions:
        query = query.filter(and_(*conditions))

    return query.options(joinedload(models.Play.scenes).joinedload(models.Scene.lines)).all()


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