import sqlite3

conn = sqlite3.connect('instance/sdg_assessment.db')
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:", [table[0] for table in tables])

# Check assessment table structure
cursor.execute("PRAGMA table_info(assessments);")
columns = cursor.fetchall()
print("\nAssessment table columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

# Check actions table structure
cursor.execute("PRAGMA table_info(sdg_actions);")
columns = cursor.fetchall()
print("\nSDG Actions table columns:")
for col in columns:
    print(f"- {col[1]} ({col[2]})")

conn.close()