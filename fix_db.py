import sqlite3
import os

# Connect to database with full path
db_path = 'Z:/sdg-assessment-tool/instance/sdg_assessment.db'
print(f"Attempting to connect to {db_path}")

try:
    conn = sqlite3.connect(db_path)
    print("Connected successfully")
    
    # Fix assessments table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(assessments);")
    columns = [col[1] for col in cursor.fetchall()]
    print("Current assessments columns:", columns)
    
    # Add all potentially missing columns to assessments
    missing_columns = {
        'user_id': 'INTEGER',
        'step1_completed': 'INTEGER DEFAULT 0',
        'step2_completed': 'INTEGER DEFAULT 0',
        'step3_completed': 'INTEGER DEFAULT 0',
        'step4_completed': 'INTEGER DEFAULT 0',
        'step5_completed': 'INTEGER DEFAULT 0',
        'overall_score': 'REAL',
        'completed_at': 'TIMESTAMP'
    }
    
    for col_name, col_type in missing_columns.items():
        if col_name not in columns:
            print(f"Adding {col_name} column...")
            conn.execute(f'ALTER TABLE assessments ADD COLUMN {col_name} {col_type}')
            conn.commit()
            print(f"{col_name} column added successfully")
    
    # Fix sdg_scores table
    cursor.execute("PRAGMA table_info(sdg_scores);")
    columns = [col[1] for col in cursor.fetchall()]
    print("Current sdg_scores columns:", columns)
    
    # Add potentially missing columns to sdg_scores
    missing_columns = {
        'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
        'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
    }
    
    for col_name, col_type in missing_columns.items():
        if col_name not in columns:
            print(f"Adding {col_name} column...")
            conn.execute(f'ALTER TABLE sdg_scores ADD COLUMN {col_name} {col_type}')
            conn.commit()
            print(f"{col_name} column added successfully")
    
    # Fix completed column
    conn.close()
    print("Database schema update completed")
    
    print("\nNow checking assessment_step2.html template...")
    print("Please manually update the template to include assessment_id in URL generation.")
    print("Change this line in assessment_step2.html:")
    print('{{ url_for(\'assessment_step2\', project_id=project.id) }}')
    print("to:")
    print('{{ url_for(\'assessment_step2\', project_id=project.id, assessment_id=assessment_id) }}')
    
except Exception as e:
    print(f"Error: {e}")