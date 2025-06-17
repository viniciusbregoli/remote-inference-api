import typer
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine, Base, User, APIKey
from src.auth import generate_api_key
from datetime import datetime, timedelta

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


@app.command()
def create_user(
    username: str = typer.Option(..., prompt=True),
    email: str = typer.Option(..., prompt=True),
    is_admin: bool = typer.Option(False, "--admin"),
):
    """
    Creates a new user.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.username == username).first()
    if user:
        typer.echo(f"User with username '{username}' already exists.")
        raise typer.Exit()

    new_user = User(username=username, email=email, is_admin=is_admin)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    typer.echo(f"User '{username}' created successfully with ID {new_user.id}.")


@app.command()
def create_apikey(
    username: str = typer.Option(..., prompt=True),
    key_name: str = typer.Option(..., prompt="Enter a name for the key"),
    expires_in_days: int = typer.Option(
        None,
        help="Number of days until the key expires. Leave empty for no expiration.",
    ),
):
    """
    Generates an API key for a user.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.username == username).first()
    if not user:
        typer.echo(f"User '{username}' not found.")
        raise typer.Exit()

    api_key_str = generate_api_key()
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    new_api_key = APIKey(
        key=api_key_str,
        name=key_name,
        user_id=user.id,
        expires_at=expires_at,
    )
    db.add(new_api_key)
    db.commit()
    db.refresh(new_api_key)

    typer.echo(f"API key generated for user '{username}':")
    typer.echo(f"Key: {api_key_str}")
    typer.echo(f"Name: {key_name}")
    if expires_at:
        typer.echo(f"Expires at: {expires_at.isoformat()}")


if __name__ == "__main__":
    app()
