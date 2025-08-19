import psycopg2
from config import DB_CONFIG
class DatabaseConnection:
    def __init__(self, **kwargs):
        self.conn_params = kwargs
        self.conn = None
        self.cursor = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor()
        except psycopg2.OperationalError as e:
            print(f"❌ Database connection failed!\nError: {e}")
            self.conn = None
            self.cursor = None

    def execute_query(self, query, params=None):
        if not self.conn or not self.cursor:
            raise ConnectionError("❌ Cannot execute query: database is not connected.")
        try:
            self.cursor.execute(query, params)
            # Only fetch if SELECT query
            if query.strip().lower().startswith("select"):
                rows = self.cursor.fetchall()
                cols = [desc[0] for desc in self.cursor.description]
                return rows, cols
            else:
                self.conn.commit()
                return [], []
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            print(f"❌ Error executing query: {e}")
            return [], []

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
