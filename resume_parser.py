import logging
import re
import sys
import os
import io
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import libraries for PDF processing, OCR, and NLP
import pdfplumber
import spacy
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import pytesseract
from PIL import Image

# Initialize spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("Spacy model not found. Downloading...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

from models import ResumeInfo, Education, Experience

def parse_resume(pdf_path):
    """
    Extract text from a PDF resume, using OCR if necessary.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text from the resume
    """
    try:
        logger.debug(f"Opening PDF: {pdf_path}")
        text = ""
        
        # Try to extract text with pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                
                # If no text is found, try OCR
                if not page_text.strip():
                    logger.debug(f"No text found in page {page.page_number}, trying OCR")
                    # Convert page to image
                    img = page.to_image(resolution=300)
                    img_bytes = img.original.tobytes()
                    pil_img = Image.open(io.BytesIO(img_bytes))
                    # Run OCR
                    page_text = pytesseract.image_to_string(pil_img)
                
                text += page_text + "\n"
        
        if not text.strip():
            logger.warning(f"Failed to extract any text from {pdf_path}")
            return None
            
        return text
        
    except Exception as e:
        logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
        return None

def extract_information(text):
    """
    Extract structured information from resume text.
    
    Args:
        text (str): Text extracted from a resume
        
    Returns:
        ResumeInfo: Structured information from the resume
    """
    if not text:
        return None
    
    try:
        info = ResumeInfo()
        info.raw_text = text
        
        # Parse with spaCy
        doc = nlp(text)
        
        # Extract name (assuming the name is at the beginning of the resume)
        info.name = extract_name(doc, text)
        
        # Extract contact information
        info.contact = extract_contact_info(text)
        
        # Extract skills
        info.skills = extract_skills(text)
        
        # Extract education
        info.education = extract_education(text, doc)
        
        # Extract experience and calculate total experience
        info.experience = extract_experience(text, doc)
        info.total_experience_years = calculate_total_experience(info.experience)
        
        return info
        
    except Exception as e:
        logger.error(f"Error extracting information: {str(e)}")
        return None

def extract_name(doc, text):
    """Extract the candidate's name from the resume"""
    # First, try to use a heuristic based on the first few lines
    lines = text.splitlines()
    for line in lines[:5]:
        # Ignore lines that contain an email, phone number, or are too long
        if "@" in line or re.search(r'\d', line):
            continue
        # Assume a candidate name is usually one or two words and in title case
        words = line.strip().split()
        if 1 <= len(words) <= 3 and all(word[0].isupper() for word in words if word):
            # Exclude common false positives
            if any(bad in line.lower() for bad in ["gmail", "email", "accra", "phone", "address", "resume", "cv"]):
                continue
            return line.strip()
    
    # Method 2: Use spaCy NER for PERSON entities
    for ent in doc.ents:
        if ent.label_ == "PERSON" and len(ent.text.split()) <= 4:
            # Check for common false positives
            if any(bad in ent.text.lower() for bad in ["gmail", "email", "accra", "phone", "address", "resume", "cv"]):
                continue
            return ent.text.strip()
    
    # Method 3: Fall back to first capital-case line not containing common header words
    for line in lines[:10]:
        line = line.strip()
        if len(line) > 0 and len(line.split()) <= 5:  # Assuming name has at most 5 words
            # Check if the line is in title case (each word capitalized)
            if all(word[0].isupper() for word in line.split() if word):
                if not any(title in line.lower() for title in ['resume', 'cv', 'curriculum vitae', 'gmail', 'email', 'phone']):
                    return line
    
    return "Unknown Name"

def extract_contact_info(text):
    """Extract contact information from resume text"""
    contact = {
        "email": "",
        "phone": "",
        "linkedin": "",
        "address": ""
    }
    
    # Extract email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, text)
    if email_matches:
        contact["email"] = email_matches[0]
    
    # Extract phone number
    phone_pattern = r'(?:\+\d{1,2}\s?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}'
    phone_matches = re.findall(phone_pattern, text)
    if phone_matches:
        contact["phone"] = phone_matches[0]
    
    # Extract LinkedIn
    linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/profile/view\?id=|linkedin\.com/pub/)[a-zA-Z0-9_-]+'
    linkedin_matches = re.findall(linkedin_pattern, text.lower())
    if linkedin_matches:
        contact["linkedin"] = linkedin_matches[0]
    
    return contact

def extract_skills(text):
    """Extract skills from resume text using regex for word boundaries."""
    # Common skill keywords to look for
    common_skills = [
        # Programming languages
        "python", "java", "javascript", "c++", "c#", "ruby", "php", "swift", "kotlin", "go", "rust",
        # Web development
        "html", "css", "react", "angular", "vue", "node.js", "express", "django", "flask", "spring",
        # Data science
        "machine learning", "deep learning", "data analysis", "natural language processing", "computer vision",
        "pandas", "numpy", "scipy", "scikit-learn", "tensorflow", "pytorch", "keras",
        # Databases
        "sql", "mysql", "postgresql", "mongodb", "oracle", "redis", "elasticsearch",
        # Cloud
        "aws", "azure", "google cloud", "docker", "kubernetes", "terraform",
        # Other tech skills
        "agile", "scrum", "git", "ci/cd", "rest api", "graphql", "microservices", "devops",
        # Soft skills
        "leadership", "communication", "teamwork", "problem solving", "time management", "project management",
        "critical thinking", "creativity", "attention to detail", "organization"
    ]
    
    # Additional keywords that might indicate skills but need validation
    potential_skill_words = [
        "bootstrap", "jquery", "sass", "typescript", "api", "mvc", "oop", "tableau", "power bi",
        "excel", "word", "powerpoint", "photoshop", "illustrator", "analytics", "presentation",
        "troubleshooting", "debugging", "testing", "qa", "ux", "ui", "design"
    ]
    
    skills = []
    text_lower = text.lower()
    
    # Use regex word-boundary to ensure an exact match.
    for skill in common_skills:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            skills.append(skill)
    
    for skill in potential_skill_words:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            skills.append(skill)
    
    # Look for skills sections with higher confidence
    skills_section_pattern = r'(?:skills|technical skills|technologies|competencies|expertise)(?::|\.|\n)([\s\S]*?)(?:\n\n|\n\w+:|\Z)'
    skills_section_matches = re.findall(skills_section_pattern, text_lower, re.IGNORECASE)
    
    if skills_section_matches:
        for section in skills_section_matches:
            for item in re.split(r'[,•\n]', section):
                item = item.strip()
                if is_valid_skill(item) and item not in skills:
                    skills.append(item)
    
    return list(set(skills))



def is_valid_skill(text):
    """Determine if a piece of text is likely to be a skill rather than a sentence or phrase."""
    if not text or len(text) < 2:
        return False
    
    # Ignore very long strings which are likely sentences not skills
    if len(text) > 30:
        return False
    
    # Ignore strings with certain stop phrases that suggest they're not skills
    stop_phrases = [
        "responsible for", "worked with", "managed", "collaborated", "helped", "assisted",
        "developed", "created", "designed", "implemented", "maintained", "contributed",
        "participated in", "involved in", "experience in", "experience with", "knowledge of",
        "proficient in", "familiar with", "expertise in"
    ]
    
    for phrase in stop_phrases:
        if phrase in text.lower():
            return False
    
    # Ignore if contains too many words (likely a phrase, not a skill)
    words = text.split()
    if len(words) > 4:
        return False
    
    return True

def extract_education(text, doc):
    """Extract education information"""
    education_list = []
    
    # Common education section headers
    edu_headers = ["education", "academic background", "academic qualification"]
    
    # Find education section
    text_lower = text.lower()
    education_section = None
    
    for header in edu_headers:
        if header in text_lower:
            pattern = rf'{header}(?::|\.|\n)([\s\S]*?)(?:\n\n|\n\w+:|\Z)'
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                education_section = matches[0]
                break
    
    if not education_section:
        return education_list
    
    # Extract degree information using patterns
    degree_patterns = [
        r'(?:Bachelor|BS|BA|B\.S\.|B\.A\.|Master|MS|MA|M\.S\.|M\.A\.|PhD|Ph\.D\.|MD|M\.D\.|MBA|M\.B\.A\.)[^\n,]*',
        r'(?:Bachelor\'s|Master\'s|Doctorate|Doctoral|Associate\'s|Associate)[^\n,]*'
    ]
    
    potential_degrees = []
    for pattern in degree_patterns:
        matches = re.findall(pattern, education_section, re.IGNORECASE)
        potential_degrees.extend(matches)
    
    # Extract dates from education section
    date_pattern = r'\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)?\s*\d{4}\s*(?:-|–|to)?\s*(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)?\s*\d{0,4}\b|\b\d{4}\s*(?:-|–|to)?\s*(?:present|current|now)\b|\b\d{4}\b'
    dates = re.findall(date_pattern, education_section, re.IGNORECASE)
    
    # Extract institutions using spaCy's named entity recognition
    edu_doc = nlp(education_section)
    institutions = [ent.text for ent in edu_doc.ents if ent.label_ in ["ORG", "GPE"]]
    
    # Create education entries
    for i, degree in enumerate(potential_degrees):
        edu = Education()
        edu.degree = degree.strip()
        
        # Try to assign an institution
        if i < len(institutions):
            edu.institution = institutions[i]
        elif institutions:
            edu.institution = institutions[0]
        
        # Try to assign dates
        if i < len(dates):
            date_text = dates[i]
            try:
                if "-" in date_text or "–" in date_text or "to" in date_text:
                    date_parts = re.split(r'-|–|to', date_text)
                    edu.start_date = date_parser.parse(date_parts[0].strip(), fuzzy=True)
                    
                    if len(date_parts) > 1 and date_parts[1].strip():
                        if any(current in date_parts[1].lower() for current in ["present", "current", "now"]):
                            edu.end_date = datetime.now()
                        else:
                            edu.end_date = date_parser.parse(date_parts[1].strip(), fuzzy=True)
                else:
                    # Just a single year, assume it's the completion date
                    edu.end_date = date_parser.parse(date_text.strip(), fuzzy=True)
            except Exception as e:
                logger.debug(f"Error parsing education date: {str(e)}")
        
        education_list.append(edu)
    
    return education_list

def extract_experience(text, doc):
    """Extract work experience information"""
    experience_list = []
    
    # Common work experience section headers
    exp_headers = ["experience", "work experience", "professional experience", "employment history", "work history"]
    
    # Find experience section
    text_lower = text.lower()
    experience_section = None
    
    for header in exp_headers:
        if header in text_lower:
            pattern = rf'{header}(?::|\.|\n)([\s\S]*?)(?:\n\n|\n\w+:|\Z)'
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                experience_section = matches[0]
                break
    
    if not experience_section:
        return experience_list
    
    # Split the experience section by job entries
    # Look for patterns like dates, company names, or job titles at the beginning of lines
    job_entries = re.split(r'\n(?=\d{4}|\w{3,}\s+\d{4}|[A-Z][a-z]+\s+\d{4}|\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)\b)', experience_section)
    
    for entry in job_entries:
        if not entry.strip():
            continue
            
        exp = Experience()
        
        # Extract job title
        title_pattern = r'^([A-Za-z\s,]+)(?:at|,|\n)'
        title_match = re.search(title_pattern, entry)
        if title_match:
            exp.title = title_match.group(1).strip()
        
        # Extract company name
        company_pattern = r'(?:at|@)\s+([A-Za-z0-9\s&.,]+)'
        company_match = re.search(company_pattern, entry)
        if company_match:
            exp.company = company_match.group(1).strip()
        else:
            # Try finding organizations with spaCy
            entry_doc = nlp(entry)
            orgs = [ent.text for ent in entry_doc.ents if ent.label_ == "ORG"]
            if orgs:
                exp.company = orgs[0]
        
        # Extract dates and calculate duration
        date_pattern = r'\b(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)?\s*\d{4}\s*(?:-|–|to)?\s*(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)?\s*\d{0,4}\b|\b\d{4}\s*(?:-|–|to)?\s*(?:present|current|now)\b|\b\d{4}\s*(?:-|–|to)?\s*\d{4}\b'
        date_matches = re.findall(date_pattern, entry, re.IGNORECASE)
        
        if date_matches:
            date_text = date_matches[0]
            try:
                if any(separator in date_text for separator in ["-", "–", "to"]):
                    # Split the date range
                    for separator in ["-", "–", "to"]:
                        if separator in date_text:
                            date_parts = date_text.split(separator)
                            break
                    
                    start_text = date_parts[0].strip()
                    end_text = date_parts[1].strip() if len(date_parts) > 1 else ""
                    
                    exp.start_date = date_parser.parse(start_text, fuzzy=True)
                    
                    if end_text:
                        if any(current in end_text.lower() for current in ["present", "current", "now"]):
                            exp.end_date = datetime.now()
                        else:
                            exp.end_date = date_parser.parse(end_text, fuzzy=True)
                else:
                    # Just a single date, assume it's the start date
                    exp.start_date = date_parser.parse(date_text, fuzzy=True)
                
                # Calculate duration
                if exp.start_date and exp.end_date:
                    delta = relativedelta(exp.end_date, exp.start_date)
                    exp.duration_years = delta.years + (delta.months / 12)
                elif exp.start_date:
                    # If only start date is available, assume it's recent experience
                    delta = relativedelta(datetime.now(), exp.start_date)
                    exp.duration_years = delta.years + (delta.months / 12)
                
            except Exception as e:
                logger.debug(f"Error parsing experience date: {str(e)}")
        
        # Extract job description
        exp.description = entry
        
        experience_list.append(exp)
    
    return experience_list

def calculate_total_experience(experience_list):
    """Calculate total years of professional experience"""
    if not experience_list:
        return 0.0
    
    return sum(exp.duration_years for exp in experience_list)
