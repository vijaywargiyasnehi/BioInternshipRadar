"""Generates draft outreach messages (networking email, LinkedIn message, referral
request) and an optional short cover letter. Drafts only — never sent automatically."""
from app.resume.resume_tailor import TailoringPlan


def generate_networking_message(student_name: str, company_name: str, job_title: str, network_contact: str, plan: TailoringPlan) -> str:
    skills_phrase = ", ".join(plan.matched_keywords[:3]) or "bioengineering and data analysis"
    greeting = f"Hi {network_contact.split(',')[0].strip()}," if network_contact else "Hi [Name],"
    return (
        f"{greeting}\n\n"
        f"I hope you're doing well. I saw an internship opening at {company_name} for {job_title}, "
        f"and it looks closely aligned with my background in {skills_phrase}. "
        f"I'm very interested in applying and wanted to ask if you had any advice about the role or the team.\n\n"
        f"Thank you,\n{student_name or '[Student Name]'}"
    )


def generate_linkedin_message(student_name: str, company_name: str, job_title: str) -> str:
    return (
        f"Hi! I'm {student_name or '[Student Name]'}, a bioengineering student interested in the "
        f"{job_title} role at {company_name}. I'd love to connect and learn more about your experience there."
    )


def generate_referral_request(student_name: str, company_name: str, job_title: str, network_contact: str) -> str:
    if not network_contact:
        return ""
    return (
        f"Hi {network_contact.split(',')[0].strip()},\n\n"
        f"I noticed {company_name} has an opening for {job_title} and I'm planning to apply. "
        f"Since you're connected to {company_name}, would you be open to referring me or sharing any tips "
        f"on standing out for this role? Happy to send my resume over.\n\n"
        f"Thanks so much,\n{student_name or '[Student Name]'}"
    )


def generate_short_cover_letter(student_name: str, company_name: str, job_title: str, plan: TailoringPlan) -> str:
    skills_phrase = ", ".join(plan.matched_keywords[:5]) or "relevant coursework and lab experience"
    return (
        f"Dear Hiring Team,\n\n"
        f"I am writing to express my interest in the {job_title} position at {company_name}. "
        f"My background includes {skills_phrase}, which I believe aligns well with this role. "
        f"I would welcome the opportunity to discuss how my experience could contribute to your team.\n\n"
        f"Thank you for your consideration.\n\n"
        f"Sincerely,\n{student_name or '[Student Name]'}\n\n"
        f"(Draft — review and personalize before sending.)"
    )
