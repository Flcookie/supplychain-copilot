import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "supplychain_kpi.db")


def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Supplier table
    cur.execute(
        """
        CREATE TABLE suppliers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            country TEXT,
            is_strategic INTEGER
        );
        """
    )

    # Purchase order table (simplified version)
    cur.execute(
        """
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY,
            supplier_id INTEGER,
            material TEXT,
            qty INTEGER,
            due_date TEXT,
            delivery_date TEXT,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
        """
    )

    # Insert sample suppliers
    suppliers = [
        (1, "Alpha Electronics", "CN", 1),
        (2, "Beta Plastics", "VN", 0),
        (3, "Gamma Metals", "DE", 1),
        (4, "Delta Packaging", "VN", 0),
    ]
    cur.executemany(
        "INSERT INTO suppliers (id, name, country, is_strategic) VALUES (?, ?, ?, ?);",
        suppliers,
    )

    # Insert sample purchase orders (some on-time, some delayed)
    pos = [
        # Alpha Electronics (mostly on time)
        (1, 1, "IC Chip", 1000, "2025-01-10", "2025-01-09"),
        (2, 1, "IC Chip", 500, "2025-01-20", "2025-01-20"),
        (3, 1, "Sensor", 300, "2025-02-01", "2025-02-03"),  # delayed
        # Beta Plastics (frequent delays)
        (4, 2, "Plastic Case", 800, "2025-01-15", "2025-01-18"),
        (5, 2, "Plastic Case", 600, "2025-01-25", "2025-01-30"),
        # Gamma Metals (good performance)
        (6, 3, "Metal Frame", 400, "2025-01-12", "2025-01-11"),
        (7, 3, "Metal Frame", 400, "2025-01-30", "2025-01-30"),
        # Delta Packaging (mixed performance)
        (8, 4, "Box", 1000, "2025-01-18", "2025-01-18"),
        (9, 4, "Box", 1200, "2025-01-28", "2025-02-02"),  # delayed
    ]
    cur.executemany(
        """
        INSERT INTO purchase_orders
        (id, supplier_id, material, qty, due_date, delivery_date)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        pos,
    )

    conn.commit()
    conn.close()
    print(f"Demo KPI DB initialized at {DB_PATH}")


if __name__ == "__main__":
    init_db()
