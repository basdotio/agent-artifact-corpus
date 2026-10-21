from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
engine = create_engine(os.environ["DATABASE_URL"])
Session = sessionmaker(engine)
