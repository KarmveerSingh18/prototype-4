from sqlalchemy import create_engine, Column, Integer, Float, String, Text, Table, MetaData
from sqlalchemy.orm import sessionmaker
import os
from .utils import BASE_DIR, now_str

DB_PATH = os.path.join(BASE_DIR, "shol_events.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
metadata = MetaData()

events = Table('events', metadata,
    Column('id', Integer, primary_key=True),
    Column('ts', Float),
    Column('timestr', String),
    Column('pid', Integer),
    Column('proc_name', String),
    Column('issue', String),
    Column('detail', Text),
    Column('action', String)
)

metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def log_event(pid, proc_name, issue, detail="", action=""):
    ins = events.insert().values(ts=__import__('time').time(), timestr=now_str(), pid=pid, proc_name=proc_name, issue=issue, detail=detail, action=action)
    conn = engine.connect()
    conn.execute(ins)
    conn.close()
