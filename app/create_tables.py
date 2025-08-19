from .models import *
from .database import Base, engine

if __name__ == "__main__":
    # Todo:
    # This drops all tables and re-create every time. Good in dev, not great later
    # Remove the below line once everything is stable with your models + schemas
    Base.metadata.drop_all(bind=engine)
    ###
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")