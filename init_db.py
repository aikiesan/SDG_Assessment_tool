"""
Database initialization script for the SDG Assessment Tool.
"""
import os
import sys
from datetime import datetime
import sqlite3

def init_db():
    """Initialize the database with SDG data."""
    # Connect to SQLite database (will create if it doesn't exist)
    conn = sqlite3.connect('instance/sdg_assessment.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sdg_goals (
        id INTEGER PRIMARY KEY,
        number INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        color_code TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        organization TEXT,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if SDGs are already added
    cursor.execute("SELECT COUNT(*) FROM sdg_goals")
    sdg_count = cursor.fetchone()[0]
    
    if sdg_count == 0:
        print("Adding SDG goals...")
        sdgs = [
            (1, "No Poverty", "End poverty in all its forms everywhere", "#E5243B"),
            (2, "Zero Hunger", "End hunger, achieve food security and improved nutrition and promote sustainable agriculture", "#DDA63A"),
            (3, "Good Health and Well-being", "Ensure healthy lives and promote well-being for all at all ages", "#4C9F38"),
            (4, "Quality Education", "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all", "#C5192D"),
            (5, "Gender Equality", "Achieve gender equality and empower all women and girls", "#FF3A21"),
            (6, "Clean Water and Sanitation", "Ensure availability and sustainable management of water and sanitation for all", "#26BDE2"),
            (7, "Affordable and Clean Energy", "Ensure access to affordable, reliable, sustainable and modern energy for all", "#FCC30B"),
            (8, "Decent Work and Economic Growth", "Promote sustained, inclusive and sustainable economic growth, full and productive employment and decent work for all", "#A21942"),
            (9, "Industry, Innovation and Infrastructure", "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation", "#FD6925"),
            (10, "Reduced Inequality", "Reduce inequality within and among countries", "#DD1367"),
            (11, "Sustainable Cities and Communities", "Make cities and human settlements inclusive, safe, resilient and sustainable", "#FD9D24"),
            (12, "Responsible Consumption and Production", "Ensure sustainable consumption and production patterns", "#BF8B2E"),
            (13, "Climate Action", "Take urgent action to combat climate change and its impacts", "#3F7E44"),
            (14, "Life Below Water", "Conserve and sustainably use the oceans, seas and marine resources for sustainable development", "#0A97D9"),
            (15, "Life on Land", "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss", "#56C02B"),
            (16, "Peace, Justice and Strong Institutions", "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels", "#00689D"),
            (17, "Partnerships for the Goals", "Strengthen the means of implementation and revitalize the global partnership for sustainable development", "#19486A")
        ]
        
        cursor.executemany("INSERT INTO sdg_goals (number, name, description, color_code) VALUES (?, ?, ?, ?)", sdgs)
        conn.commit()
        print("SDG goals added successfully.")
    
    # Create an admin user if needed
    from werkzeug.security import generate_password_hash
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", ('admin@example.com',))
    admin_exists = cursor.fetchone()[0]
    
    if not admin_exists:
        print("Creating admin user...")
        admin_password_hash = generate_password_hash('admin123')
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, is_admin) VALUES (?, ?, ?, ?)",
            ('admin@example.com', admin_password_hash, 'Administrator', 1)
        )
        conn.commit()
        print("Admin user created.")
    
    # Drop existing tables to update schema (caution: will delete data)
    try:
        # Uncomment below lines if you want to drop tables and recreate them
        # Be careful, this will delete all existing data
        # cursor.execute("DROP TABLE IF EXISTS sdg_actions")
        # cursor.execute("DROP TABLE IF EXISTS sdg_criteria")
        # cursor.execute("DROP TABLE IF EXISTS sdg_scores")
        # cursor.execute("DROP TABLE IF EXISTS assessments")
        # cursor.execute("DROP TABLE IF EXISTS projects")
        # print("Dropped existing tables to update schema.")
        pass
    except:
        print("Error dropping tables, continuing...")
    
    # Create projects table with updated schema
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        project_type TEXT,
        location TEXT,
        size_sqm REAL,
        status TEXT DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create assessments table with enhanced fields
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY,
        project_id INTEGER NOT NULL,
        version INTEGER DEFAULT 1,
        status TEXT DEFAULT 'draft',
        completed_at TIMESTAMP,
        overall_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    ''')
    
    # Create SDG scores table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sdg_scores (
        id INTEGER PRIMARY KEY,
        assessment_id INTEGER NOT NULL,
        sdg_id INTEGER NOT NULL,
        score INTEGER,
        notes TEXT,
        FOREIGN KEY (assessment_id) REFERENCES assessments (id),
        FOREIGN KEY (sdg_id) REFERENCES sdg_goals (id)
    )
    ''')
    
    # Create SDG criteria table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sdg_criteria (
        id INTEGER PRIMARY KEY,
        sdg_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        weight REAL DEFAULT 1.0,
        FOREIGN KEY (sdg_id) REFERENCES sdg_goals (id)
    )
    ''')
    
    # Create actions table for specific measures related to SDGs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sdg_actions (
        id INTEGER PRIMARY KEY,
        assessment_id INTEGER NOT NULL,
        sdg_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'planned',
        target_date DATE,
        completion_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assessment_id) REFERENCES assessments (id),
        FOREIGN KEY (sdg_id) REFERENCES sdg_goals (id)
    )
    ''')
    
    # Create indexes for better performance
    print("Creating indexes...")
    
    # Projects indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects (user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status)")
    
    # Assessments indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assessments_project_id ON assessments (project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_assessments_status ON assessments (status)")
    
    # SDG scores indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sdg_scores_assessment_id ON sdg_scores (assessment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sdg_scores_sdg_id ON sdg_scores (sdg_id)")
    
    # SDG actions indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sdg_actions_assessment_id ON sdg_actions (assessment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sdg_actions_sdg_id ON sdg_actions (sdg_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sdg_actions_status ON sdg_actions (status)")
    
    conn.commit()
    conn.close()
    
    print("Database initialization complete.")

if __name__ == '__main__':
    # Make sure instance directory exists
    os.makedirs('instance', exist_ok=True)
    init_db()