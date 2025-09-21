# database_tools.py
import sqlite3
import os
import pandas as pd
from typing import List, Dict, Any
from langchain_core.tools import tool

# Database file path
DB_PATH = "hydroponics.db"

def init_database():
    """
    Initialize the database with tables from the provided Excel file with multiple sheets.
    """
    # Hapus file database yang ada untuk memastikan reset total
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✅ File database '{DB_PATH}' berhasil dihapus.")
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    excel_file = "hydro_data.xlsx"
    
    # List nama sheet yang akan menjadi nama tabel
    sheets_to_load = ["plants", "care_schedule", "knowledge_base", "user_memory"]
    
    if not os.path.exists(excel_file):
        print(f"❌ Error: File Excel '{excel_file}' tidak ditemukan.")
        conn.close()
        return

    for sheet_name in sheets_to_load:
        table_name = sheet_name
        try:
            # Gunakan pandas.read_excel untuk membaca sheet tertentu
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            df.columns = df.columns.str.lower().str.replace(' ', '_')
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"✅ Tabel '{table_name}' berhasil dibuat dari sheet '{sheet_name}'.")
        except Exception as e:
            print(f"❌ Error saat memuat sheet '{sheet_name}': {e}")
            
    conn.close()

def table_exists(conn, table_name):
    """
    Check if a table exists in the database.
    """
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def execute_sql_query(sql_query: str) -> List[Dict[str, Any]]:
    """
    Execute a SQL query and return the results as a list of dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(sql_query)
        columns = [col[0] for col in cursor.description]
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except Exception as e:
        conn.close()
        raise e

@tool
def text_to_sql(question: str) -> Dict[str, Any]:
    """
    A tool to convert a natural language question into a SQL query and execute it on the hydroponics database.
    Use this tool to get information about plants, care schedules, and hydroponic knowledge.
    
    Args:
        question: The natural language question to convert to SQL.
        
    Returns:
        Dictionary with SQL query and results.
    """
    if not os.path.exists(DB_PATH):
        init_database()
    
    sql_query = ""
    question_lower = question.lower()
    
    if "ec ideal" in question_lower:
        plant_name = "selada" if "selada" in question_lower else "tomat"
        sql_query = f"SELECT ec_min, ec_max FROM plants WHERE common_name = '{plant_name.capitalize()}'"
    elif "ph ideal" in question_lower:
        plant_name = "selada" if "selada" in question_lower else "tomat"
        sql_query = f"SELECT ph_min, ph_max FROM plants WHERE common_name = '{plant_name.capitalize()}'"
    elif "jadwal perawatan" in question_lower:
        plant_name = "selada" if "selada" in question_lower else "tomat"
        sql_query = f"SELECT task, frequency_days FROM care_schedule WHERE plant_common_name = '{plant_name.capitalize()}'"
    elif "tumbuhan apa" in question_lower or "jenis tanaman" in question_lower:
        sql_query = "SELECT common_name, type, notes FROM plants LIMIT 5"
    elif "pengetahuan umum" in question_lower:
        sql_query = "SELECT title, content FROM knowledge_base"
    else:
        return {
            "query": "No SQL query generated",
            "results": [{"message": "I'm sorry, I don't know how to answer that with my current tools."}]
        }

    try:
        results = execute_sql_query(sql_query)
        return {
            "query": sql_query,
            "results": results
        }
    except Exception as e:
        return {
            "query": sql_query,
            "results": [{"error": str(e)}]
        }

def get_database_info() -> Dict[str, Any]:
    """
    Get information about the database schema to help with query construction.
    """
    if not os.path.exists(DB_PATH):
        init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tables_info = {}
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [row[0] for row in cursor.fetchall()]

    for table_name in table_names:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]
        
        sample_data = execute_sql_query(f"SELECT * FROM {table_name} LIMIT 3")
        
        tables_info[table_name] = {
            "columns": columns,
            "sample_data": sample_data
        }
        
    conn.close()
    return tables_info