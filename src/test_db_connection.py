from database import engine
from sqlalchemy import text

def test_connection():
    try:
        # Try to execute a simple SQL command
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


if __name__ == "__main__":
    test_connection()
