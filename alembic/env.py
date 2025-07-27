# alembic/env.py

from logging.config import fileConfig
import os # NEW: Import os for environment variables

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from dotenv import load_dotenv # NEW: Import load_dotenv

# NEW: Load environment variables from .env file
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# NEW: Import your Base and set target_metadata
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Add parent directory to path
from app.database import Base # Adjust this import if Base is located elsewhere
from app.models import * # NEW: Import all your models so Alembic can discover them
                         # OR import specific models like:
                         # from app.models import User, Goal, DailyLog, UserMessage

target_metadata = Base.metadata # NEW: Set target_metadata to Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Get the database URL from environment variable
    # This is more robust than relying on alembic.ini for the full URL
    alembic_url = os.environ.get("ALEMBIC_DATABASE_URL")
    if not alembic_url:
        # Fallback to alembic.ini if env var is not set
        alembic_url = config.get_main_option("sqlalchemy.url")
    
    if not alembic_url:
        raise ValueError("DATABASE_URL environment variable or sqlalchemy.url in alembic.ini must be set.")

    print(f"DEBUG: Alembic is attempting to connect with URL: {alembic_url}")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=alembic_url, # NEW: Pass the URL explicitly
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()