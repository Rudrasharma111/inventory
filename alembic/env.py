from alembic import context
from sqlalchemy import create_engine
from app import models
from app.core.config import DATABASE_URL
from app.database import Base

engine = create_engine(DATABASE_URL)

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()