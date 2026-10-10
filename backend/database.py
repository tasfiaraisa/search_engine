import psycopg


def get_connection():
    """Connect to the PostgreSQL search_engine database."""
    return psycopg.connect(
        dbname="search_engine"
    )


if __name__ == "__main__":
    try:
        with get_connection() as conn:
            print("Successfully connected to PostgreSQL!")
    except psycopg.Error as error:
        print("Database connection failed:", error)