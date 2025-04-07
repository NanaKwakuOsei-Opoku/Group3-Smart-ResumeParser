import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pandas as pd
import tempfile
import uuid

from resume_parser import parse_resume, extract_information
from recommendation_system import match_candidates, rank_candidates

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "resume-parser-secret-key")

# Configure upload folder
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# In-memory storage for parsed resumes
resumes_data = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        flash('No files selected', 'danger')
        return redirect(request.url)
    
    # Clear previous data if starting a new batch
    if request.form.get('clear_previous') == 'true':
        resumes_data.clear()
    
    parsed_count = 0
    failed_count = 0
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            resume_id = str(uuid.uuid4())
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{resume_id}_{filename}")
            
            try:
                file.save(file_path)
                logger.debug(f"Saved file to {file_path}")
                
                # Parse the resume
                resume_text = parse_resume(file_path)
                if not resume_text:
                    logger.warning(f"Could not extract text from {filename}")
                    failed_count += 1
                    continue
                
                # Extract information
                resume_info = extract_information(resume_text)
                if resume_info:
                    resumes_data[resume_id] = {
                        'filename': filename,
                        'info': resume_info
                    }
                    parsed_count += 1
                else:
                    failed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                failed_count += 1
            finally:
                # Clean up the file
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing temporary file {file_path}: {str(e)}")
    
    if parsed_count > 0:
        flash(f'Successfully parsed {parsed_count} resume(s)', 'success')
    if failed_count > 0:
        flash(f'Failed to parse {failed_count} resume(s)', 'warning')
    
    # Store resume data in session for persistence
    session['has_resumes'] = len(resumes_data) > 0
    
    return redirect(url_for('index'))

@app.route('/search', methods=['POST'])
def search():
    if not resumes_data:
        flash('No resumes have been uploaded yet', 'warning')
        return redirect(url_for('index'))
    
    # Get job requirements from form
    required_skills = request.form.get('required_skills', '').strip()
    required_skills = [skill.strip().lower() for skill in required_skills.split(',') if skill.strip()]
    
    min_experience = request.form.get('min_experience', '0')
    try:
        min_experience = float(min_experience)
    except ValueError:
        min_experience = 0
    
    # Find matching candidates
    matching_candidates = match_candidates(resumes_data, required_skills, min_experience)
    
    # Rank candidates
    top_candidates = rank_candidates(matching_candidates, required_skills)
    
    return render_template('results.html', 
                          candidates=top_candidates, 
                          required_skills=required_skills,
                          min_experience=min_experience,
                          total_candidates=len(resumes_data),
                          matching_count=len(top_candidates))

@app.route('/clear', methods=['POST'])
def clear_data():
    resumes_data.clear()
    session['has_resumes'] = False
    flash('All resume data has been cleared', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
