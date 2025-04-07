class ResumeInfo:
    def __init__(self):
        self.name = ""
        self.contact = {
            "email": "",
            "phone": "",
            "linkedin": "",
            "address": ""
        }
        self.skills = []
        self.education = []
        self.experience = []
        self.total_experience_years = 0.0
        self.raw_text = ""

class Education:
    def __init__(self):
        self.degree = ""
        self.institution = ""
        self.start_date = None
        self.end_date = None
        self.gpa = ""
        self.field_of_study = ""

class Experience:
    def __init__(self):
        self.title = ""
        self.company = ""
        self.start_date = None
        self.end_date = None
        self.description = ""
        self.duration_years = 0.0

class JobRequirement:
    def __init__(self):
        self.title = ""
        self.required_skills = []
        self.min_experience = 0.0
        self.preferred_skills = []
        self.education_level = ""

class CandidateMatch:
    def __init__(self, resume_id, resume_info, match_score=0.0):
        self.resume_id = resume_id
        self.name = resume_info.name
        self.skills = resume_info.skills
        self.total_experience = resume_info.total_experience_years
        self.matched_skills = []
        self.missing_skills = []
        self.match_score = match_score
