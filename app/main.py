from app.config import get_settings
from app.db.pool import get_connection


def main() -> None:
    get_settings()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    print("config and database connection OK")


if __name__ == "__main__":
    main()