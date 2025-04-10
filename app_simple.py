from flask import Flask, render_template, redirect, url_for, request, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
from datetime import datetime

# Create Flask app
app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['DATABASE'] = os.path.join('instance', 'sdg_assessment.db')

# Template filters
@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d'):
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
    return value.strftime(format)

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def add_missing_columns():
    """Add any missing columns to the database"""
    conn = get_db_connection()
    
    # Check if overall_score column exists in assessments table
    columns = conn.execute("PRAGMA table_info(assessments)").fetchall()
    column_names = [col[1] for col in columns]
    
    # Add overall_score column if it doesn't exist
    if 'overall_score' not in column_names:
        conn.execute('ALTER TABLE assessments ADD COLUMN overall_score REAL')
        conn.commit()
        print("Added overall_score column to assessments table")
    
    # Add user_id column if it doesn't exist
    if 'user_id' not in column_names:
        conn.execute('ALTER TABLE assessments ADD COLUMN user_id INTEGER')
        conn.commit()
        print("Added user_id column to assessments table")
    
    conn.close()

# Basic routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['is_admin'] = user['is_admin']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        
        flash('Invalid email or password', 'danger')
    
    return render_template('auth/login_simple.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        # Implementation for password reset would go here
        flash('If that email is registered, a password reset link has been sent.', 'info')
        return redirect(url_for('login'))
    
    return render_template('auth/forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Placeholder route for password reset
    if request.method == 'POST':
        password = request.form.get('password')
        password2 = request.form.get('password2')
        
        if password != password2:
            flash('Passwords do not match', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Actual implementation would validate token and update password
        flash('Your password has been updated. You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/reset_password.html', token=token)

@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user_exists = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        
        if user_exists:
            flash('Email already registered', 'danger')
            conn.close()
            return render_template('auth/register.html')
        
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)',
                    (email, password_hash, name))
        conn.commit()
        conn.close()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/projects')
def projects():
    if not session.get('user_id'):
        flash('Please log in to view your projects', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects WHERE user_id = ?', 
                          (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('projects/index.html', projects=projects)

@app.route('/projects/new', methods=['GET', 'POST'])
def new_project():
    if not session.get('user_id'):
        flash('Please log in to create a project', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        project_type = request.form.get('project_type')
        location = request.form.get('location')
        size_sqm = request.form.get('size_sqm')
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO projects (name, description, project_type, location, size_sqm, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, project_type, location, size_sqm, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('projects'))
    
    return render_template('projects/new.html')

@app.route('/projects/<int:id>')
def show_project(id):
    if not session.get('user_id'):
        flash('Please log in to view project details', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (id, session['user_id'])).fetchone()
    
    # Fetch assessments for this project
    assessments = conn.execute('SELECT * FROM assessments WHERE project_id = ? ORDER BY created_at DESC', 
                            (id,)).fetchall()
    conn.close()
    
    if not project:
        flash('Project not found or you don\'t have permission to view it', 'danger')
        return redirect(url_for('projects'))
    
    return render_template('projects/show.html', project=project, assessments=assessments)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Process form data here
        # You can add email sending functionality later
        flash('Your message has been sent. We will contact you soon!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    if not session.get('user_id'):
        flash('Please log in to edit this project', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (id, session['user_id'])).fetchone()
    conn.close()
    
    if not project:
        flash('Project not found or you don\'t have permission to edit it', 'danger')
        return redirect(url_for('projects'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        project_type = request.form.get('project_type')
        location = request.form.get('location')
        size_sqm = request.form.get('size_sqm')
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE projects 
            SET name = ?, description = ?, project_type = ?, location = ?, size_sqm = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (name, description, project_type, location, size_sqm, id, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Project updated successfully!', 'success')
        return redirect(url_for('show_project', id=id))
    
    return render_template('projects/edit.html', project=project)

@app.route('/projects/<int:id>/delete', methods=['POST'])
def delete_project(id):
    if not session.get('user_id'):
        flash('Please log in to delete this project', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (id, session['user_id'])).fetchone()
    
    if not project:
        conn.close()
        flash('Project not found or you don\'t have permission to delete it', 'danger')
        return redirect(url_for('projects'))
    
    # First delete all related assessments and their scores/actions
    conn.execute('DELETE FROM sdg_actions WHERE assessment_id IN (SELECT id FROM assessments WHERE project_id = ?)', (id,))
    conn.execute('DELETE FROM sdg_scores WHERE assessment_id IN (SELECT id FROM assessments WHERE project_id = ?)', (id,))
    conn.execute('DELETE FROM assessments WHERE project_id = ?', (id,))
    
    # Then delete the project
    conn.execute('DELETE FROM projects WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Project and all related assessments have been deleted', 'success')
    return redirect(url_for('projects'))

# Assessment routes for app_simple.py
@app.route('/projects/<int:project_id>/assessments/step1', methods=['GET', 'POST'])
def assessment_step1(project_id):
    # Authentication and project checks
    if not session.get('user_id'):
        flash('Please log in to access this page.', 'danger')
        return redirect(url_for('login'))
    
    # Get database connection
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (project_id, session['user_id'])).fetchone()
    
    if not project:
        flash('Project not found or you don\'t have permission to access it.', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Check if there's an existing assessment
    assessment = conn.execute('SELECT * FROM assessments WHERE project_id = ?', 
                            (project_id,)).fetchone()
    assessment_id = assessment['id'] if assessment else None
    
    # Prepare context manually for Step 1
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    scores = {}

    if assessment_id:
        assessment_scores = conn.execute(
            'SELECT * FROM sdg_scores WHERE assessment_id = ?',
            (assessment_id,)
        ).fetchall()
        scores = {score['sdg_id']: score for score in assessment_scores}
      
    # SDG context variables for the template
    sdg_colors = {
        1: '#e5243b',  # Red
        2: '#dda63a',  # Orange
        3: '#4c9f38',  # Green
        6: '#26bde2',   # Blue
        13: '#3F7E44',  # Green
        14: '#0A97D9',  # Blue
        15: '#56C02B'   # Light Green
    }
    
    sdg_titles = {
        1: 'No Poverty',
        2: 'Zero Hunger',
        3: 'Good Health and Well-being',
        6: 'Clean Water and Sanitation',
        13: 'Climate Action',
        14: 'Life Below Water',
        15: 'Life on Land'        
    }
    
    sdg_subtitles = {
        1: 'End poverty in all its forms everywhere',
        2: 'End hunger, achieve food security and improved nutrition',
        3: 'Ensure healthy lives and promote well-being for all',
        6: 'Ensure availability and sustainable management of water',
        13: 'Take urgent action to combat climate change and its impacts',
        14: 'Conserve and sustainably use the oceans, seas and marine resources',
        15: 'Protect, restore and promote sustainable use of terrestrial ecosystems'
    }
    
    sdg_targets = {
        1: [
            {'code': '1.4', 'text': 'By 2030, ensure that all people have equal rights to economic resources, basic services, ownership and control over land and property'},
            {'code': '1.5', 'text': 'Build the resilience of the poor to reduce their exposure to climate-related extreme events and disasters'}
        ],
        2: [
            {'code': '2.1', 'text': 'By 2030, end hunger and ensure access to safe, nutritious food'},
            {'code': '2.4', 'text': 'By 2030, ensure sustainable food production systems and resilient agricultural practices'}
        ],
        3: [
            {'code': '3.4', 'text': 'Reduce premature mortality from non-communicable diseases and promote mental health and well-being'},
            {'code': '3.9', 'text': 'Reduce deaths and illnesses from hazardous chemicals and air, water and soil pollution'}
        ],
        6: [
            {'code': '6.1', 'text': 'By 2030, achieve universal and equitable access to safe and affordable drinking water'},
            {'code': '6.2', 'text': 'By 2030, achieve access to adequate and equitable sanitation and hygiene'},
            {'code': '6.3', 'text': 'By 2030, improve water quality by reducing pollution and increasing recycling and safe reuse'},
            {'code': '6.4', 'text': 'By 2030, substantially increase water-use efficiency across all sectors'}
        ],
        13: [
            {'code': '13.1', 'text': 'Strengthen resilience and adaptive capacity to climate-related hazards'},
            {'code': '13.2', 'text': 'Integrate climate change measures into policies and planning'},
            {'code': '13.3', 'text': 'Improve education and capacity on climate change mitigation and adaptation'}
        ],
        14: [
            {'code': '14.1', 'text': 'Prevent and reduce marine pollution of all kinds'},
            {'code': '14.2', 'text': 'Sustainably manage and protect marine and coastal ecosystems'}
        ],
        15: [
            {'code': '15.1', 'text': 'Ensure conservation of terrestrial and inland freshwater ecosystems'},
            {'code': '15.2', 'text': 'Promote sustainable management of forests'},
            {'code': '15.5', 'text': 'Take action to reduce degradation of natural habitats and halt biodiversity loss'}
        ]
    }
    
    sdg_applications = {
        1: [
            'Energy poverty reduction through efficient building design',
            'Affordable housing solutions using sustainable materials',
            'Disaster resilience in vulnerable communities',
            'Inclusive design for all socioeconomic backgrounds'
        ],
        2: [
            'Urban agriculture integration in building designs',
            'Food storage solutions to reduce waste',
            'Community food spaces and markets',
            'Water-efficient design for food production'
        ],
        3: [
            'Healthy buildings with adequate ventilation and natural light',
            'Biophilic design to reduce stress and improve mental health',
            'Active design that encourages physical activity',
            'Healthcare facilities and wellness centers',
            'Air quality management systems'
        ],
        6: [
            'Water-efficient fixtures and appliances',
            'Rainwater harvesting and greywater recycling',
            'Sustainable drainage solutions',
            'On-site wastewater treatment',
            'Water-sensitive urban design'
        ],
        13: [
            'Low-carbon or carbon-neutral design strategies',
            'Climate-resilient building techniques',
            'Design for extreme weather events',
            'Urban heat island mitigation',
            'Carbon sequestration in building materials and landscapes'
        ],
        14: [
            'Responsible waterfront development',
            'Stormwater management to prevent water pollution',
            'Wastewater treatment and recycling',
            'Prevention of harmful runoff into water bodies',
            'Marine-friendly construction practices'
        ],
        15: [
            'Biodiversity-friendly site planning',
            'Native plant species selection',
            'Preservation of habitats and ecological corridors',
            'Sustainable forestry practices in material sourcing',
            'Green roofs and walls for biodiversity'
        ]
    }
    
    sdg_resources = {
        1: [
            {'title': 'UN SDG 1 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/poverty/', 'icon': 'link-45deg'},
            {'title': 'York University Teaching Resources', 'url': 'https://www.yorku.ca/unsdgs/toolkit/teaching-the-17-un-sdgs/goal-1/', 'icon': 'book'},
            {'title': 'Engaging Lesson Plans on No Poverty', 'url': 'https://www.bookwidgets.com/blog/2024/08/8-engaging-lesson-plans-to-teach-sdg-1-no-poverty-to-your-students', 'icon': 'file-earmark-text'}
        ],
        2: [
            {'title': 'UN SDG 2 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/hunger/', 'icon': 'link-45deg'},
            {'title': 'OER Commons: Zero Hunger Lesson Plans', 'url': 'https://oercommons.org/courseware/lesson/117761/overview', 'icon': 'book'},
            {'title': 'FAO Resources on Zero Hunger', 'url': 'https://www.fao.org/sustainable-development-goals/goals/goal-2', 'icon': 'globe'}
        ],
        3: [
            {'title': 'UN SDG 3 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/health/', 'icon': 'link-45deg'},
            {'title': 'Generation Global: SDG 3 Resources', 'url': 'https://generation.global/assets/resources/sdgblocks/sdg3', 'icon': 'people'},
            {'title': 'Free Lesson Plans for SDG 3', 'url': 'https://www.bookwidgets.com/blog/2024/10/8-free-lesson-plans-to-teach-sdg-3-good-health-and-well-being', 'icon': 'file-earmark-text'},
            {'title': 'Gaia Education: SDG 3 Explained', 'url': 'https://www.gaiaeducation.org/blog/103256-sdg-3-good-health-and-wellbeing', 'icon': 'book'}
        ],
        6: [
            {'title': 'UN SDG 6 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/water-and-sanitation/', 'icon': 'link-45deg'},
            {'title': 'Free Digital Lessons for SDG 6', 'url': 'https://www.bookwidgets.com/blog/2025/02/8-free-digital-lessons-for-teaching-sdg-6-clean-water-and-sanitation', 'icon': 'file-earmark-text'},
            {'title': 'Classroom Strategies for SDG 6', 'url': 'https://additioapp.com/en/do-you-know-how-to-address-sdg-6-clean-water-and-sanitation-in-the-classroom/', 'icon': 'book'},
            {'title': 'World Water Day Resources', 'url': 'https://www.worldwaterday.org/learn', 'icon': 'droplet'}
        ],
        13: [
            {'title': 'UN SDG 13 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/climate-change/', 'icon': 'link-45deg'},
            {'title': 'Architecture 2030', 'url': 'https://architecture2030.org/', 'icon': 'building'},
            {'title': 'Climate Positive Design', 'url': 'https://climatepositivedesign.com/', 'icon': 'globe'}
        ],
        14: [
            {'title': 'UN SDG 14 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/oceans/', 'icon': 'link-45deg'},
            {'title': 'Blue Architecture', 'url': 'https://www.bluearchitecture.org/', 'icon': 'water'},
            {'title': 'Coastal Resilience Design Guide', 'url': 'https://www.coastalresilience.org/', 'icon': 'file-earmark-text'}
        ],
        15: [
            {'title': 'UN SDG 15 Official Resources', 'url': 'https://www.un.org/sustainabledevelopment/biodiversity/', 'icon': 'link-45deg'},
            {'title': 'Biodiversity in Architecture', 'url': 'https://www.biodiversityinarchitecture.com/', 'icon': 'tree'},
            {'title': 'Green Roof Guide', 'url': 'https://greenroofguide.org/', 'icon': 'house'}
        ]
    }
    
    sdg_connections = [
        {'sdg': 'SDG 1: No Poverty', 'links': [
            {'sdg': 'SDG 10', 'title': 'Reduced Inequalities'},
            {'sdg': 'SDG 13', 'title': 'Climate Action'}
        ]},
        {'sdg': 'SDG 2: Zero Hunger', 'links': [
            {'sdg': 'SDG 12', 'title': 'Responsible Consumption'},
            {'sdg': 'SDG 15', 'title': 'Life on Land'}
        ]},
        {'sdg': 'SDG 3: Good Health', 'links': [
            {'sdg': 'SDG 7', 'title': 'Clean Energy'},
            {'sdg': 'SDG 11', 'title': 'Sustainable Cities'}
        ]},
        {'sdg': 'SDG 6: Clean Water', 'links': [
            {'sdg': 'SDG 14', 'title': 'Life Below Water'},
            {'sdg': 'SDG 15', 'title': 'Life on Land'}
        ]}
    ]
    
    if request.method == 'POST':
        # Process form submission
        scores = {}
        notes = {}
        
        for sdg in [1, 2, 3, 6]:
            score_key = f'score_{sdg}'
            notes_key = f'notes_{sdg}'
            
            if score_key in request.form:
                scores[sdg] = int(request.form[score_key])
            if notes_key in request.form:
                notes[sdg] = request.form[notes_key]
        
        # Create or update assessment
        if not assessment:
            conn.execute('''
                INSERT INTO assessments 
                (project_id, user_id, created_at, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (project_id, session['user_id']))
            conn.commit()
            
            # Get the new assessment ID
            assessment = conn.execute('SELECT * FROM assessments WHERE project_id = ?', 
                                   (project_id,)).fetchone()
            assessment_id = assessment['id']
        
        # Update scores and notes
        for sdg, score in scores.items():
            existing_score = conn.execute('''
                SELECT id FROM sdg_scores 
                WHERE assessment_id = ? AND sdg_id = ?
            ''', (assessment_id, sdg)).fetchone()
            
            if existing_score:
                conn.execute('''
                    UPDATE sdg_scores 
                    SET score = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE assessment_id = ? AND sdg_id = ?
                ''', (score, notes.get(sdg, ''), assessment_id, sdg))
            else:
                conn.execute('''
                    INSERT INTO sdg_scores 
                    (assessment_id, sdg_id, score, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (assessment_id, sdg, score, notes.get(sdg, '')))
        
        # Mark step 1 as completed
        conn.execute('''
            UPDATE assessments 
            SET step1_completed = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (assessment_id,))
        
        conn.commit()
        flash('Assessment step 1 saved successfully!', 'success')
        return redirect(url_for('assessment_step2', project_id=project_id, assessment_id=assessment_id))
    
    # Pre-fill form with existing data if available
    form_data = {}
    if assessment:
        scores = conn.execute('''
            SELECT sdg_id, score, notes 
            FROM sdg_scores 
            WHERE assessment_id = ?
        ''', (assessment_id,)).fetchall()
        
        for score in scores:
            sdg_id = score['sdg_id']
            form_data[f'score_{sdg_id}'] = score['score']
            if score['notes']:
                form_data[f'notes_{sdg_id}'] = score['notes']
    
    conn.close()
    
    return render_template('assessments/assessment_step1.html',
                          project=project,
                          assessment_id=assessment_id,
                          sdgs=sdgs,
                          form_data=form_data,
                          sdg_colors=sdg_colors,
                          sdg_titles=sdg_titles,
                          sdg_subtitles=sdg_subtitles,
                          sdg_targets=sdg_targets,
                          sdg_applications=sdg_applications,
                          sdg_resources=sdg_resources,
                          sdg_connections=sdg_connections)

@app.route('/projects/<int:project_id>/assessments/<int:assessment_id>/step2', methods=['GET', 'POST'])
def assessment_step2(project_id, assessment_id):
    """Second step of assessment: Enablers and Opportunities (SDGs 4, 5, 8, 10)"""
    # Check login status
    if not session.get('user_id'):
        flash('Please log in to continue the assessment', 'warning')
        return redirect(url_for('login'))
      
    # Get database connection
    conn = get_db_connection()
    
    # Get project and assessment data
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (project_id, session['user_id'])).fetchone()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ? AND project_id = ?', 
                            (assessment_id, project_id)).fetchone()

    # Check authorization
    if not project or not assessment:
        flash('Project or assessment not found or you don\'t have permission', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Get all SDGs
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    
    # Handle form submission
    if request.method == 'POST':
        # Process SDG scores for step 2 (SDGs 4, 5, 8, 10)
        step2_sdgs = [4, 5, 8, 10]
        for sdg_number in step2_sdgs:
            sdg = next((s for s in sdgs if s['number'] == sdg_number), None)
            if sdg:
                score_key = f'score_{sdg_number}'
                notes_key = f'notes_{sdg_number}'

                score_value = request.form.get(score_key)
                notes = request.form.get(notes_key)
                
                if score_value:
                    # Update or insert score
                    existing = conn.execute(
                        'SELECT id FROM sdg_scores WHERE assessment_id = ? AND sdg_id = ?',
                        (assessment_id, sdg['id'])
                    ).fetchone()
                
                    if existing:
                        conn.execute(
                            'UPDATE sdg_scores SET score = ?, notes = ? WHERE assessment_id = ? AND sdg_id = ?',
                            (score_value, notes, assessment_id, sdg['id'])
                        )
                    else:
                        conn.execute(
                            'INSERT INTO sdg_scores (assessment_id, sdg_id, score, notes) VALUES (?, ?, ?, ?)',
                            (assessment_id, sdg['id'], score_value, notes)
                        )
        
        # Mark step 2 as completed
        conn.execute(
            'UPDATE assessments SET step2_completed = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (assessment_id,)
        )
        
        conn.commit()
        conn.close()
        
        flash('Assessment step 2 saved successfully!', 'success')
        return redirect(url_for('assessment_step3', project_id=project_id, assessment_id=assessment_id))
    
    # For GET request, prepare form data
    assessment_scores = conn.execute(
        'SELECT * FROM sdg_scores WHERE assessment_id = ?',
        (assessment_id,)
    ).fetchall()

    # Transform scores into a dict for easier template access
    scores = {score['sdg_id']: score for score in assessment_scores}
    
    # Add resources for SDGs 4, 5, 8, 10
    sdg_resources = {
        4: [
            {'title': 'UN SDG 4 Resources', 'url': 'https://sdgs.un.org/goals/goal4', 'icon': 'globe'},
            {'title': 'Education & Architecture', 'url': 'https://www.archdaily.com/tag/educational-architecture', 'icon': 'book'},
            {'title': 'Universal Design Guidelines', 'url': 'https://universaldesign.ie/what-is-universal-design/', 'icon': 'people-fill'}
        ],
        5: [
            {'title': 'UN SDG 5 Resources', 'url': 'https://sdgs.un.org/goals/goal5', 'icon': 'globe'},
            {'title': 'Gender Responsive Design', 'url': 'https://www.unwomen.org/en/digital-library', 'icon': 'gender-female'},
            {'title': 'Safety in Public Spaces', 'url': 'https://unhabitat.org/topic/safety', 'icon': 'shield-check'}
        ],
        8: [
            {'title': 'UN SDG 8 Resources', 'url': 'https://sdgs.un.org/goals/goal8', 'icon': 'globe'},
            {'title': 'Decent Work Guidelines', 'url': 'https://www.ilo.org/global/topics/sdg-2030/goal-8/lang--en/index.htm', 'icon': 'briefcase'},
            {'title': 'Sustainable Construction', 'url': 'https://www.unep.org/explore-topics/resource-efficiency/what-we-do/cities/sustainable-buildings', 'icon': 'building'}
        ],
        10: [
            {'title': 'UN SDG 10 Resources', 'url': 'https://sdgs.un.org/goals/goal10', 'icon': 'globe'},
            {'title': 'Inclusive Design Resources', 'url': 'https://www.designcouncil.org.uk/resources/guide/principles-inclusive-design', 'icon': 'people-fill'},
            {'title': 'Social Inclusion Standards', 'url': 'https://www.un.org/development/desa/dspd/2030agenda-sdgs.html', 'icon': 'diagram-3'}
        ]
    }

    conn.close()
    
    # Return the template with all necessary context
    return render_template(
        'assessments/assessment_step2.html',
        project=project,
        assessment=assessment,
        assessment_id=assessment_id,
        sdgs=sdgs,
        scores=scores,
        sdg_resources=sdg_resources
    )

@app.route('/projects/<int:project_id>/assessments/<int:assessment_id>/step3', methods=['GET', 'POST'])
def assessment_step3(project_id, assessment_id):
    """Third step of assessment: Sustainable Infrastructure (SDGs 7, 9, 11, 12)"""
    if not session.get('user_id'):
        flash('Please log in to continue the assessment', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (project_id, session['user_id'])).fetchone()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ? AND project_id = ?', 
                            (assessment_id, project_id)).fetchone()
    
    if not project or not assessment:
        flash('Project or assessment not found or you don\'t have permission', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Get all SDGs
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    
    if request.method == 'POST':
        # Process SDG scores for step 3 (SDGs 7, 9, 11, 12)
        step3_sdgs = [7, 9, 11, 12]
        for sdg_number in step3_sdgs:
            sdg = next((s for s in sdgs if s['number'] == sdg_number), None)
            if sdg:
                score_value = request.form.get(f'score_{sdg_number}')
                notes = request.form.get(f'notes_{sdg_number}')
                
                existing_score = conn.execute(
                    'SELECT id FROM sdg_scores WHERE assessment_id = ? AND sdg_id = ?',
                    (assessment_id, sdg['id'])
                ).fetchone()
                
                if existing_score:
                    conn.execute(
                        'UPDATE sdg_scores SET score = ?, notes = ? WHERE assessment_id = ? AND sdg_id = ?',
                        (score_value, notes, assessment_id, sdg['id'])
                    )
                else:
                    conn.execute(
                        'INSERT INTO sdg_scores (assessment_id, sdg_id, score, notes) VALUES (?, ?, ?, ?)',
                        (assessment_id, sdg['id'], score_value, notes)
                    )
        
        # Mark step 3 as completed
        conn.execute(
            'UPDATE assessments SET step3_completed = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (assessment_id,)
        )
        
        conn.commit()
        flash('Step 3 saved successfully!', 'success')
        return redirect(url_for('assessment_step4', project_id=project_id, assessment_id=assessment_id))
    
    # Get existing scores
    assessment_scores = conn.execute(
        'SELECT * FROM sdg_scores WHERE assessment_id = ?',
        (assessment_id,)
    ).fetchall()
    scores = {score['sdg_id']: score for score in assessment_scores}
    
    # Add resources for SDGs 7, 9, 11, 12
    sdg_resources = {
        7: [
            {'title': 'UN SDG 7 Resources', 'url': 'https://sdgs.un.org/goals/goal7', 'icon': 'globe'},
            {'title': 'Clean Energy Solutions', 'url': 'https://www.irena.org/', 'icon': 'lightning-charge'},
            {'title': 'Energy Efficient Design', 'url': 'https://www.energy.gov/eere/buildings/building-design-and-energy-codes', 'icon': 'building'}
        ],
        9: [
            {'title': 'UN SDG 9 Resources', 'url': 'https://sdgs.un.org/goals/goal9', 'icon': 'globe'},
            {'title': 'Innovation in Architecture', 'url': 'https://www.archdaily.com/tag/innovation', 'icon': 'lightbulb'},
            {'title': 'Sustainable Infrastructure', 'url': 'https://www.unep.org/explore-topics/resource-efficiency/what-we-do/cities/sustainable-infrastructure', 'icon': 'building-gear'}
        ],
        11: [
            {'title': 'UN SDG 11 Resources', 'url': 'https://sdgs.un.org/goals/goal11', 'icon': 'globe'},
            {'title': 'Sustainable Cities Network', 'url': 'https://www.c40.org/', 'icon': 'building-fill'},
            {'title': 'Urban Planning Guidelines', 'url': 'https://unhabitat.org/planning-and-design', 'icon': 'map'}
        ],
        12: [
            {'title': 'UN SDG 12 Resources', 'url': 'https://sdgs.un.org/goals/goal12', 'icon': 'globe'},
            {'title': 'Circular Economy Principles', 'url': 'https://ellenmacarthurfoundation.org/topics/circular-economy-introduction/overview', 'icon': 'arrow-repeat'},
            {'title': 'Sustainable Materials', 'url': 'https://www.usgbc.org/leed/materials', 'icon': 'boxes'}
        ]
    }
    
    conn.close()
    
    return render_template('assessments/assessment_step3.html',
                        project=project,
                        assessment=assessment,
                        assessment_id=assessment_id,
                        sdgs=sdgs,
                        scores=scores,
                        sdg_resources=sdg_resources)

@app.route('/projects/<int:project_id>/assessments/<int:assessment_id>/step4', methods=['GET', 'POST'])
def assessment_step4(project_id, assessment_id):
    """Fourth step of assessment: Environmental Stewardship (SDGs 13, 14, 15)"""
    if not session.get('user_id'):
        flash('Please log in to continue the assessment', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                         (project_id, session['user_id'])).fetchone()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ? AND project_id = ?', 
                            (assessment_id, project_id)).fetchone()

    if not project or not assessment:
        flash('Project or assessment not found or you don\'t have permission', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Get all SDGs
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    
    if request.method == 'POST':
        # Process SDG scores for step 4 (SDGs 13, 14, 15)
        step4_sdgs = [13, 14, 15]
        for sdg_number in step4_sdgs:
            sdg = next((s for s in sdgs if s['number'] == sdg_number), None)
            if sdg:
                score_value = request.form.get(f'score_{sdg_number}')
                notes = request.form.get(f'notes_{sdg_number}')
                
                existing_score = conn.execute(
                    'SELECT id FROM sdg_scores WHERE assessment_id = ? AND sdg_id = ?',
                    (assessment_id, sdg['id'])
                ).fetchone()
                
                if existing_score:
                    conn.execute(
                        'UPDATE sdg_scores SET score = ?, notes = ? WHERE assessment_id = ? AND sdg_id = ?',
                        (score_value, notes, assessment_id, sdg['id'])
                    )
                else:
                    conn.execute(
                        'INSERT INTO sdg_scores (assessment_id, sdg_id, score, notes) VALUES (?, ?, ?, ?)',
                        (assessment_id, sdg['id'], score_value, notes)
                    )
        
        # Mark step 4 as completed
        conn.execute(
            'UPDATE assessments SET step4_completed = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (assessment_id,)
        )
        
        conn.commit()
        flash('Step 4 saved successfully!', 'success')
        return redirect(url_for('assessment_step5', project_id=project_id, assessment_id=assessment_id))
    
    # Get existing scores
    assessment_scores = conn.execute(
        'SELECT * FROM sdg_scores WHERE assessment_id = ?',
        (assessment_id,)
    ).fetchall()
    scores = {score['sdg_id']: score for score in assessment_scores}
    
    # Define necessary context variables
    sdg_colors = {
        13: '#3F7E44',  # Green
        14: '#0A97D9',  # Blue
        15: '#56C02B'   # Light Green
    }
    
    sdg_titles = {
        13: 'Climate Action',
        14: 'Life Below Water',
        15: 'Life on Land'        
    }
    
    sdg_subtitles = {
        13: 'Take urgent action to combat climate change and its impacts',
        14: 'Conserve and sustainably use the oceans, seas and marine resources',
        15: 'Protect, restore and promote sustainable use of terrestrial ecosystems'
    }
    
    sdg_targets = {
        13: [
            {'code': '13.1', 'text': 'Strengthen resilience and adaptive capacity to climate-related hazards'},
            {'code': '13.2', 'text': 'Integrate climate change measures into policies and planning'},
            {'code': '13.3', 'text': 'Improve education and capacity on climate change mitigation and adaptation'}
        ],
        14: [
            {'code': '14.1', 'text': 'Prevent and reduce marine pollution of all kinds'},
            {'code': '14.2', 'text': 'Sustainably manage and protect marine and coastal ecosystems'}
        ],
        15: [
            {'code': '15.1', 'text': 'Ensure conservation of terrestrial and inland freshwater ecosystems'},
            {'code': '15.2', 'text': 'Promote sustainable management of forests'},
            {'code': '15.5', 'text': 'Take action to reduce degradation of natural habitats and halt biodiversity loss'}
        ]
    }
    
    sdg_applications = {
        13: [
            'Low-carbon or carbon-neutral design strategies',
            'Climate-resilient building techniques',
            'Design for extreme weather events',
            'Urban heat island mitigation',
            'Carbon sequestration in building materials and landscapes'
        ],
        14: [
            'Responsible waterfront development',
            'Stormwater management to prevent water pollution',
            'Wastewater treatment and recycling',
            'Prevention of harmful runoff into water bodies',
            'Marine-friendly construction practices'
        ],
        15: [
            'Biodiversity-friendly site planning',
            'Native plant species selection',
            'Preservation of habitats and ecological corridors',
            'Sustainable forestry practices in material sourcing',
            'Green roofs and walls for biodiversity'
        ]
    }
    
    sdg_resources = {
        13: [
            {'title': 'UN SDG 13 Resources', 'url': 'https://sdgs.un.org/goals/goal13', 'icon': 'globe'},
            {'title': 'Climate Action in Architecture', 'url': 'https://architecture2030.org/', 'icon': 'thermometer-half'},
            {'title': 'Carbon Neutral Design', 'url': 'https://www.carbonbrief.org/', 'icon': 'cloud-minus'}
        ],
        14: [
            {'title': 'UN SDG 14 Resources', 'url': 'https://sdgs.un.org/goals/goal14', 'icon': 'globe'},
            {'title': 'Ocean Friendly Design', 'url': 'https://oceanconservancy.org/', 'icon': 'water'},
            {'title': 'Protecting Water Resources', 'url': 'https://www.wateraid.org/', 'icon': 'droplet-fill'}
        ],
        15: [
            {'title': 'UN SDG 15 Resources', 'url': 'https://sdgs.un.org/goals/goal15', 'icon': 'globe'},
            {'title': 'Biodiversity in Architecture', 'url': 'https://www.worldwildlife.org/', 'icon': 'tree-fill'},
            {'title': 'Land Conservation', 'url': 'https://www.nature.org/', 'icon': 'geo-alt'}
        ]
    }
    
    conn.close()
    
    return render_template('assessments/assessment_step4.html',
                          project=project,
                          assessment=assessment,
                          assessment_id=assessment_id,
                          sdgs=sdgs,
                          scores=scores,
                          sdg_colors=sdg_colors,
                          sdg_titles=sdg_titles,
                          sdg_subtitles=sdg_subtitles,
                          sdg_targets=sdg_targets,
                          sdg_applications=sdg_applications,
                          sdg_resources=sdg_resources)

@app.route('/projects/<int:project_id>/assessments/step5', methods=['GET', 'POST'])
@app.route('/projects/<int:project_id>/assessments/<int:assessment_id>/step5', methods=['GET', 'POST'])
def assessment_step5(project_id, assessment_id=None):

    # Geet the assessment_id from the URL or from the database if not provided
    if assessment_id is None:
        conn = get_db_connection()
        assessment = conn.execute('SELECT * FROM assessments WHERE project_id = ?', 
                            (project_id,)).fetchone()
        conn.close()
        
        if assessment:
            assessment_id = assessment['id']
        else:
            flash('Assessment not found', 'danger')
            return redirect(url_for('show_project', id=project_id))

    ## # Authentication check
    if not session.get('user_id'):
        flash('Please log in to continue the assessment', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    project = conn.execute('SELECT * FROM projects WHERE id = ? AND user_id = ?', 
                     (project_id, session['user_id'])).fetchone()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ? AND project_id = ?', 
                        (assessment_id, project_id)).fetchone()

    if not project or not assessment:
        flash('Project or assessment not found or you don\'t have permission', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Get all SDGs
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    
    if request.method == 'POST':
        # Process SDG scores for step 5 (SDGs 16, 17)
        step5_sdgs = [16, 17]
        for sdg_number in step5_sdgs:
            sdg = next((s for s in sdgs if s['number'] == sdg_number), None)
            if sdg:
                score_value = request.form.get(f'score_{sdg_number}')
                notes = request.form.get(f'notes_{sdg_number}')
                
                existing_score = conn.execute(
                    'SELECT id FROM sdg_scores WHERE assessment_id = ? AND sdg_id = ?',
                    (assessment_id, sdg['id'])
                ).fetchone()
                
                if existing_score:
                    conn.execute(
                        'UPDATE sdg_scores SET score = ?, notes = ? WHERE assessment_id = ? AND sdg_id = ?',
                        (score_value, notes, assessment_id, sdg['id'])
                    )
                else:
                    conn.execute(
                        'INSERT INTO sdg_scores (assessment_id, sdg_id, score, notes) VALUES (?, ?, ?, ?)',
                        (assessment_id, sdg['id'], score_value, notes)
                    )
        
        # Mark step 5 as completed
        conn.execute(
            'UPDATE assessments SET step5_completed = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (assessment_id,)
        )
        
        conn.commit()
        flash('Step 5 saved successfully!', 'success')
        return redirect(url_for('show_assessment', id=assessment_id))
    
    # Get existing scores
    assessment_scores = conn.execute(
        'SELECT * FROM sdg_scores WHERE assessment_id = ?',
        (assessment_id,)
    ).fetchall()
    scores = {score['sdg_id']: score for score in assessment_scores}
    
    # Define resources for SDGs 16-17
    sdg_resources = {
        16: [
            {'title': 'UN SDG 16 Resources', 'url': 'https://sdgs.un.org/goals/goal16', 'icon': 'globe'},
            {'title': 'Peace & Justice in Design', 'url': 'https://www.un.org/ruleoflaw/', 'icon': 'building'},
            {'title': 'Ethical Practice Resources', 'url': 'https://www.transparency.org/en/what-is-corruption', 'icon': 'shield-check'}
        ],
        17: [
            {'title': 'UN SDG 17 Resources', 'url': 'https://sdgs.un.org/goals/goal17', 'icon': 'globe'},
            {'title': 'Partnerships for Sustainability', 'url': 'https://www.undp.org/sustainable-development-goals/partnerships-goals', 'icon': 'people'},
            {'title': 'Global Collaboration', 'url': 'https://sdgcompass.org/', 'icon': 'globe-americas'}
        ]
    }
    
    conn.close()
    
    return render_template('assessments/assessment_step5.html',
                          project=project,
                          assessment=assessment,
                          assessment_id=assessment_id,
                          sdgs=sdgs,
                          scores=scores,
                          sdg_resources=sdg_resources)

@app.route('/assessments/<int:id>')
def show_assessment(id):
    """Display assessment results"""
    if not session.get('user_id'):
        flash('Please log in to view assessment results', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ?', (id,)).fetchone()
    
    if not assessment:
        flash('Assessment not found', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (assessment['project_id'],)).fetchone()
    
    if project['user_id'] != session['user_id']:
        flash('You do not have permission to view this assessment', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Get all SDGs
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    
    # Get assessment scores
    scores_data = conn.execute('SELECT * FROM sdg_scores WHERE assessment_id = ?', (id,)).fetchall()
    scores = {score['sdg_id']: score for score in scores_data}
    
    conn.close()
    
    return render_template('assessments/show.html',
                          assessment=assessment,
                          project=project,
                          project_name=project['name'],
                          project_id=project['id'],
                          sdgs=sdgs,
                          scores=scores)

@app.route('/assessments/<int:id>/edit', methods=['GET', 'POST'])
def edit_assessment(id):
    """Edit an assessment"""
    if not session.get('user_id'):
        flash('Please log in to edit an assessment', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ?', (id,)).fetchone()
    
    if not assessment:
        flash('Assessment not found', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (assessment['project_id'],)).fetchone()
    
    if project['user_id'] != session['user_id']:
        flash('You do not have permission to edit this assessment', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Get all SDGs
    sdgs = conn.execute('SELECT * FROM sdg_goals ORDER BY number').fetchall()
    
    if request.method == 'POST':
        # Process all SDG scores
        for sdg in sdgs:
            score_value = request.form.get(f'score_{sdg["id"]}')
            notes = request.form.get(f'notes_{sdg["id"]}')
            
            if score_value:
                existing_score = conn.execute(
                    'SELECT id FROM sdg_scores WHERE assessment_id = ? AND sdg_id = ?',
                    (id, sdg['id'])
                ).fetchone()
                
                if existing_score:
                    conn.execute(
                        'UPDATE sdg_scores SET score = ?, notes = ? WHERE assessment_id = ? AND sdg_id = ?',
                        (score_value, notes, id, sdg['id'])
                    )
                else:
                    conn.execute(
                        'INSERT INTO sdg_scores (assessment_id, sdg_id, score, notes) VALUES (?, ?, ?, ?)',
                        (id, sdg['id'], score_value, notes)
                    )
        
        conn.execute(
            'UPDATE assessments SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (id,)
        )
        
        conn.commit()
        flash('Assessment updated successfully!', 'success')
        return redirect(url_for('show_assessment', id=id))
    
    # Get existing scores
    scores_data = conn.execute('SELECT * FROM sdg_scores WHERE assessment_id = ?', (id,)).fetchall()
    scores = {score['sdg_id']: score for score in scores_data}
    
    conn.close()
    
    return render_template('assessments/edit.html',
                          assessment=assessment,
                          project_id=project['id'],
                          project_name=project['name'],
                          sdgs=sdgs,
                          scores=scores)

@app.route('/assessments/<int:assessment_id>/finalize', methods=['POST'])
def finalize_assessment(assessment_id):
    """Finalize an assessment"""
    if not session.get('user_id'):
        flash('Please log in to finalize an assessment', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    assessment = conn.execute('SELECT * FROM assessments WHERE id = ?', (assessment_id,)).fetchone()
    
    if not assessment:
        flash('Assessment not found', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (assessment['project_id'],)).fetchone()
    
    if project['user_id'] != session['user_id']:
        flash('You do not have permission to finalize this assessment', 'danger')
        conn.close()
        return redirect(url_for('projects'))
    
    # Calculate overall score
    scores = conn.execute(
        'SELECT score FROM sdg_scores WHERE assessment_id = ?',
        (assessment_id,)
    ).fetchall()
    
    total_score = sum(score['score'] for score in scores if score['score'] is not None)
    num_scores = len([score for score in scores if score['score'] is not None])
    overall_score = total_score / num_scores if num_scores > 0 else 0
    
    # Update assessment
    conn.execute(
        'UPDATE assessments SET status = ?, completed_at = ?, overall_score = ?, updated_at = ? WHERE id = ?',
        ('completed', datetime.now(), overall_score, datetime.now(), assessment_id)
    )
    conn.commit()
    conn.close()
    
    flash('Assessment has been finalized successfully!', 'success')
    return redirect(url_for('show_assessment', id=assessment_id))

@app.route('/assessments/<int:id>/export_pdf')
def export_assessment_pdf(id):
    """Export assessment as PDF"""
    if not session.get('user_id'):
        flash('Please log in to export assessments', 'warning')
        return redirect(url_for('login'))
    
    # This would be implemented with a PDF generation library
    flash('PDF export functionality is not implemented yet', 'info')
    return redirect(url_for('show_assessment', id=id))

# Context processor to add data to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Helper function to make templates work with both blueprint and non-blueprint routes
@app.context_processor
def utility_processor():
    def url_for_project_routes(endpoint, **kwargs):
        """Handle both blueprint and non-blueprint routes for projects"""
        if endpoint.startswith('projects.'):
            # Convert blueprint route to simple route
            simple_endpoint = endpoint.replace('projects.', '')
            if simple_endpoint == 'index':
                return url_for('projects', **kwargs)
            elif simple_endpoint == 'new':
                return url_for('new_project', **kwargs)
            elif simple_endpoint == 'show':
                return url_for('show_project', **kwargs)
            elif simple_endpoint == 'edit':
                return url_for('edit_project', **kwargs)
            elif simple_endpoint == 'delete':
                return url_for('delete_project', **kwargs)
        elif endpoint.startswith('assessments.'):
            # Convert blueprint route to simple route
            simple_endpoint = endpoint.replace('assessments.', '')
            if simple_endpoint == 'new':
                return url_for('new_assessment', **kwargs)
            elif simple_endpoint == 'show':
                return url_for('show_assessment', **kwargs)
        
        # Fall back to standard url_for
        return url_for(endpoint, **kwargs)
    
    return dict(url_for_project_routes=url_for_project_routes)

if __name__ == '__main__':
    # Add any missing columns to the database
    add_missing_columns()
    app.run(debug=True)