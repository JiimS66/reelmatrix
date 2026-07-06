from sqlalchemy import text

from core.db.engine import create_db_engine, init_db


def test_create_engine_and_init_db_in_memory() -> None:
    engine = create_db_engine("sqlite://")
    # Should not raise even before any tables are declared.
    init_db(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
