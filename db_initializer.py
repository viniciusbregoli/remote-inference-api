import typer
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine, Base

app = typer.Typer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.command()
def init_db():
    """
    Initializes the database and creates tables.
    """
    typer.echo("Initializing database...")
    Base.metadata.create_all(bind=engine)
    typer.echo("Database initialized successfully.")


if __name__ == "__main__":
    app()
