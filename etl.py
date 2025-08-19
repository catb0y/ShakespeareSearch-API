import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "Kaggle_Shakespeare_data",
    "user": "postgres",
    "password": "psw"
}

CSV_PATH = "data/Kaggle_Shakespeare_data.csv"

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

df = pd.read_csv(CSV_PATH)

df = df.fillna("")

# Insert plays
plays = df[['Play']].drop_duplicates().reset_index(drop=True)
play_map = {} 

for _, row in plays.iterrows():
    title = row['Play']
    if title.lower() in ["hamlet", "macbeth", "othello", "king lear", "romeo and juliet"]:
        genre = "tragedy"
    elif title.lower() in ["a midsummer night’s dream", "twelfth night", "much ado about nothing"]:
        genre = "comedy"
    else:
        genre = "history"
    cur.execute("INSERT INTO plays (title, genre, play_metadata) VALUES (%s, %s, %s) RETURNING id",
                (title, genre, '{}'))
    play_id = cur.fetchone()[0]
    play_map[title] = play_id

conn.commit()

# Insert characters
characters = df[['Play', 'Player']].drop_duplicates()
char_map = {}

for _, row in characters.iterrows():
    play_id = play_map[row['Play']]
    name = row['Player'].strip()
    if name == "":
        continue
    cur.execute("INSERT INTO characters (name, play_id, description) VALUES (%s, %s, %s) RETURNING id",
                (name, play_id, ""))
    char_id = cur.fetchone()[0]
    char_map[(play_id, name)] = char_id

conn.commit()

# Insert scenes
scenes_map = {}
for _, row in df.iterrows():
    play_id = play_map[row['Play']]
    act_scene_line = str(row['ActSceneLine'])
    if act_scene_line == "":
        continue
    try:
        parts = act_scene_line.split(".")
        act = int(parts[0])
        scene_number = int(parts[1])
    except:
        continue
    key = (play_id, act, scene_number)
    if key not in scenes_map:
        cur.execute("INSERT INTO scenes (play_id, act, scene_number, description) VALUES (%s, %s, %s, %s) RETURNING id",
                    (play_id, act, scene_number, ""))
        scene_id = cur.fetchone()[0]
        scenes_map[key] = scene_id

conn.commit()

# Insert lines
lines_to_insert = []
for _, row in df.iterrows():
    play_id = play_map[row['Play']]
    char_name = row['Player'].strip()
    if char_name == "":
        continue
    char_id = char_map.get((play_id, char_name))
    act_scene_line = str(row['ActSceneLine'])
    if act_scene_line == "":
        continue
    try:
        parts = act_scene_line.split(".")
        act = int(parts[0])
        scene_number = int(parts[1])
    except:
        continue
    scene_id = scenes_map.get((play_id, act, scene_number))
    if scene_id is None or char_id is None:
        continue
    text = row['PlayerLine'].strip()
    if text == "":
        continue
    lines_to_insert.append((scene_id, char_id, text))

# Bulk insert lines
execute_values(cur,
               "INSERT INTO lines (scene_id, character_id, text) VALUES %s",
               lines_to_insert)

conn.commit()

# Create full-text search column and index
cur.execute("ALTER TABLE lines ADD COLUMN IF NOT EXISTS text_tsv tsvector")
cur.execute("UPDATE lines SET text_tsv = to_tsvector('english', text)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_lines_text_tsv ON lines USING GIN(text_tsv)")

conn.commit()
cur.close()
conn.close()

print("ETL complete")
