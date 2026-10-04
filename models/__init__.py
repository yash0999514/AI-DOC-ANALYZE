import sys, os
if "/home/spark/pylib" not in sys.path:
    sys.path.insert(0, "/home/spark/pylib")

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.user import User
from models.document import Document

__all__ = ['db', 'User', 'Document']
