import logging
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def similarity_score(a, b):
    """
    Calculate string similarity between two strings.
    
    Args:
        a, b: Strings to compare
        
    Returns:
        float: Similarity score between 0 and 1
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def match_skills(candidate_skills, required_skills, threshold=0.8):
    """
    Match candidate skills to required skills.
    
    Args:
        candidate_skills (list): Candidate's skills.
        required_skills (list): Required skills.
        threshold (float): Similarity threshold.
        
    Returns:
        tuple: (List of matched skills, List of missing skills)
    """
    matched_skills = []
    missing_skills = required_skills.copy()
    
    for candidate_skill in candidate_skills:
        for req_skill in required_skills:
            if (req_skill.lower() in candidate_skill.lower() or 
                candidate_skill.lower() in req_skill.lower() or 
                similarity_score(candidate_skill, req_skill) >= threshold):
                if req_skill in missing_skills:
                    missing_skills.remove(req_skill)
                    matched_skills.append(req_skill)
                break
    
    return matched_skills, missing_skills

def match_candidates(resumes_data, required_skills, min_experience):
    """
    Find candidates matching job requirements while avoiding duplicate entries.
    
    Args:
        resumes_data (dict): Dictionary of parsed resumes.
        required_skills (list): Required skills.
        min_experience (float): Minimum years of experience.
        
    Returns:
        list: List of matching candidates with scores.
    """
    matching_candidates = []
    seen_keys = set()  # Using email if available, otherwise name
    
    for resume_id, resume_data in resumes_data.items():
        resume_info = resume_data['info']
        # Create a unique key based on email if present; else use candidate name.
        candidate_key = resume_info.contact.get("email", "").lower() or resume_info.name.lower()
        if candidate_key in seen_keys:
            logger.debug(f"Skipping duplicate candidate: {resume_info.name} ({candidate_key})")
            continue
        seen_keys.add(candidate_key)
        
        # Skip if insufficient experience.
        if resume_info.total_experience_years < min_experience:
            logger.debug(f"Candidate {resume_info.name} has insufficient experience: {resume_info.total_experience_years} < {min_experience}")
            continue
        
        # Match skills.
        matched_skills, missing_skills = match_skills(resume_info.skills, required_skills)
        skill_match_score = len(matched_skills) / len(required_skills) if required_skills else 1.0
        
        if len(matched_skills) == 0 and required_skills:
            logger.debug(f"Candidate {resume_info.name} has no matching skills")
            continue
        
        # Bonus for experience beyond minimum.
        experience_score = min(1.0, (resume_info.total_experience_years - min_experience) / 5.0) if min_experience > 0 else 0.5
        
        # Overall match score (weighted average).
        match_score = (skill_match_score * 0.7) + (experience_score * 0.3)
        
        candidate_match = {
            'resume_id': resume_id,
            'name': resume_info.name,
            'skills': resume_info.skills,
            'total_experience': resume_info.total_experience_years,
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'match_score': match_score
        }
        matching_candidates.append(candidate_match)
    
    return matching_candidates

def rank_candidates(candidates, required_skills):
    """
    Rank candidates by match score.
    
    Args:
        candidates (list): List of matching candidates.
        required_skills (list): Required skills.
        
    Returns:
        list: Sorted list of candidates by match score.
    """
    sorted_candidates = sorted(candidates, key=lambda x: x['match_score'], reverse=True)
    for i, candidate in enumerate(sorted_candidates):
        candidate['rank'] = i + 1
    return sorted_candidates
