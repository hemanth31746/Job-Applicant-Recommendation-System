from database import DatabaseConnection
from config import DB_CONFIG
from typing import Optional, List, Union
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
import uvicorn
import pandas as pd
import numpy as np
from model import JobMatchingModel
from dataaccess import (
    fetch_applicant_skills,
    fetch_applicant_experience,
    fetch_all_applicants,
    fetch_jobs
)

app = FastAPI(title="Job Recommendation API", version="1.0.0")

# --- CORS Configuration ---

origins = [
    
    "http://localhost:3000",
    "https://dev.humanwrk.com", 
    "https://musquaretech.humanwrk.com",
    "https://srcits.humanwrk.com",
    "https://scaleorange.humanwrk.com", 
    "https://humanwrk.com" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, 
    allow_methods=["*"],    
    allow_headers=["*"],    
)


# Initialize on startup
model = None
jobs_df = pd.DataFrame()

class RecommendationRequest(BaseModel):
    applicant_id: Optional[str] = None
    job_id: Optional[str] = None
    top_n: Optional[int] = 5

class JobRecommendation(BaseModel):
    job_id: str
    job_title: str
    match_percentage: float
    feedback: str

class ApplicantRecommendation(BaseModel):
    applicant_id: str
    match_percentage: float
    feedback: str

class JobsForApplicantResponse(BaseModel):
    applicant_id: str
    recommendations: List[JobRecommendation]

class ApplicantsForJobResponse(BaseModel):
    job_id: str
    job_title: str
    top_applicants: List[ApplicantRecommendation]

class EvaluationResponse(BaseModel):
    applicant_id: str
    job_id: str
    job_title: str
    match_percentage: float
    feedback: str

@app.on_event("startup")
def startup_event():
    global jobs_df, model
   
    jobs_df = fetch_jobs()
    model = JobMatchingModel()
    # On startup, load the model if it exists, otherwise build a new one.
    if not model.load():
        model._build_and_persist()

def generate_feedback(app_skills: List[str], job_skills: List[str],
                      total_app_exp_months: float,
                      job_min_exp_years: float, job_max_exp_years: float,
                      skill_score_percent: float, exp_score_percent: float) -> str:
    """
    Generates a detailed, multi-part feedback string.
    Expects skill_score and exp_score to be percentages (0-100) from the model.
    """
    feedback_parts = []

    # Part 1: Detailed Skill Analysis
    norm_app_skills = model.normalize_skills(app_skills)
    norm_job_skills = model.normalize_skills(job_skills)
    matched_skills = set(norm_app_skills) & set(norm_job_skills)
    missing_skills = set(norm_job_skills) - set(norm_app_skills)

    skills_summary = f"Skills: {len(matched_skills)}/{len(norm_job_skills)} matched."
    if missing_skills:
        # Show more missing skills as per the desired output format
        missing_summary = f" Missing: {', '.join(list(missing_skills)[:7])}...."
        skills_summary += missing_summary
    feedback_parts.append(skills_summary)

    # Part 2: Detailed Experience Comparison
    applicant_years = float(total_app_exp_months) / 12.0
    exp_summary = (f"Exp Match: {exp_score_percent:.1f}% "
                   f"(Applicant: {applicant_years:.1f} yrs | "
                   f"Job Req: {job_min_exp_years:.1f}-{job_max_exp_years:.1f} yrs).")
    feedback_parts.append(exp_summary)

    # Part 3: Skill Score Component
    skill_summary = f"Skills Score: {skill_score_percent:.1f}%."
    feedback_parts.append(skill_summary)

    return " | ".join(feedback_parts)


@app.post("/recommendations/", response_model=Optional[Union[JobsForApplicantResponse, ApplicantsForJobResponse, EvaluationResponse]])
def get_recommendations(req: RecommendationRequest):
    if not model or not model.job_ids:
        raise HTTPException(status_code=503, detail="Model not ready.")
    if not req.applicant_id and not req.job_id:
        raise HTTPException(status_code=400, detail="Provide applicant_id or job_id.")

    top_n = req.top_n or 5
    if req.applicant_id and not req.job_id:
        return _recommend_jobs_for_applicant(req.applicant_id, top_n)
    elif req.job_id and not req.applicant_id:
        return _recommend_applicants_for_job(req.job_id, top_n)
    elif req.applicant_id and req.job_id:
        return _evaluate_applicant_for_job(req.applicant_id, req.job_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid request")

def _recommend_jobs_for_applicant(applicant_id: str, top_n: int):
    skills = fetch_applicant_skills(applicant_id)
    exp_months = fetch_applicant_experience(applicant_id) or 0
    jobs = model.get_recommendations(skills, exp_months, top_n)

    recos = []
    for job_data in jobs:
        job_id, title, final_score, job_skills, min_exp, max_exp, skill_score, exp_score = job_data
        feedback = generate_feedback(skills, job_skills, exp_months, min_exp, max_exp, skill_score, exp_score)
        recos.append(JobRecommendation(
            job_id=str(job_id),
            job_title=str(title),
            match_percentage=final_score,
            feedback=feedback
        ))
    return JobsForApplicantResponse(applicant_id=applicant_id, recommendations=recos)

def _recommend_applicants_for_job(job_id: str, top_n: int):
    job_row = jobs_df[jobs_df['job_id'] == job_id]
    if job_row.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_row.iloc[0]
    job_skills = job['skills']
    job_title = job['job_title']
    min_exp = job['min_experience']
    max_exp = job['max_experience']
    applicants = fetch_all_applicants()
    recos = []
    for app in applicants.to_dict('records'):
        skills = app.get('skills', [])
        exp = app.get('totalWorkExp', 0)
        score, s_score, e_score = model.score(skills, exp, job_skills, min_exp, max_exp)
        feedback = generate_feedback(skills, job_skills, exp, min_exp, max_exp, s_score, e_score)
        recos.append(ApplicantRecommendation(
            applicant_id=app['applicantId'],
            match_percentage=score, 
            feedback=feedback
        ))
    recos.sort(key=lambda x: x.match_percentage, reverse=True)
    return ApplicantsForJobResponse(job_id=job_id, job_title=job_title, top_applicants=recos[:top_n])

def _evaluate_applicant_for_job(applicant_id: str, job_id: str):
    skills = fetch_applicant_skills(applicant_id)
    exp_months = fetch_applicant_experience(applicant_id) or 0
    job_row = jobs_df[jobs_df['job_id'] == job_id]
    if job_row.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    job = job_row.iloc[0]
    job_skills = job['skills']
    job_title = job['job_title']
    min_exp = job['min_experience']
    max_exp = job['max_experience']
    score, s_score, e_score = model.score(skills, exp_months, job_skills, min_exp, max_exp)
    feedback = generate_feedback(skills, job_skills, exp_months, min_exp, max_exp, s_score, e_score)
    return EvaluationResponse(
        applicant_id=applicant_id,
        job_id=job_id,
        job_title=job_title,
        match_percentage=score, 
        feedback=feedback
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "job-recommendation-api"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
