
from sqlalchemy import text

from app.database.connection import engine


def test_postgres_connection():

    try:
        with engine.connect() as connection:

            result = connection.execute(
                text("SELECT current_database(), current_user")
            )

            database, user = result.fetchone()

            print("PostgreSQL Connected Successfully!")
            print("Database:", database)
            print("User:", user)

            tables = connection.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))

            print("\nAvailable Tables:")

            for row in tables:
                print("-", row[0])

    except Exception as error:
        print("PostgreSQL Connection Failed!")
        print(error)


if __name__ == "__main__":
    test_postgres_connection()
