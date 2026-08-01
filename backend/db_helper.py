import sqlite3
from backend.config import DB_PATH

def execute_sql(query: str):
    """Executes a SQL query on the SQLite database and returns the columns and rows."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(query)
        
        # In case it is a SELECT query, cursor.description is not None
        if cursor.description:
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            conn.close()
            return {"success": True, "columns": columns, "rows": rows}
        else:
            conn.commit()
            conn.close()
            return {"success": True, "message": "Query executed successfully without returned rows."}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_schema_info() -> str:
    """Gets schema metadata context to teach the LLM the database structure."""
    return """
    Table: claims
    Columns:
        - claim_id (TEXT, PRIMARY KEY)
        - patient_id (TEXT)
        - patient_name (TEXT)
        - department (TEXT)
        - claim_type (TEXT)
        - diagnosis_code (TEXT)
        - insurer (TEXT)
        - claimed_amount (REAL)
        - approved_amount (REAL)
        - status (TEXT)
        - submitted_date (TEXT, format YYYY-MM-DD)
        - resolved_date (TEXT, format YYYY-MM-DD)

    Table: maintenance_tickets
    Columns:
        - ticket_id (TEXT, PRIMARY KEY)
        - equipment_name (TEXT)
        - equipment_id (TEXT)
        - category (TEXT)
        - campus (TEXT)
        - issue_type (TEXT)
        - fault_code (TEXT)
        - raised_by (TEXT)
        - raised_date (TEXT, format YYYY-MM-DD)
        - resolved_date (TEXT, format YYYY-MM-DD)
        - status (TEXT)
        - resolution_note (TEXT)
    """
