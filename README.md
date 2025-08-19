# Job-Applicant-Recommendation-System


An AI-powered recommendation engine that matches applicants with suitable jobs using skill embeddings, cosine similarity, and experience-based scoring.

📌 Problem Statement

Recruiters spend excessive time manually screening resumes, which is time-consuming, inconsistent, and error-prone.
This leads to missed talent, delays in hiring, and poor candidate experience.
Our system solves this by automating job–applicant matching using NLP and machine learning.

🎯 Objectives

Automate job–applicant matching using embeddings.

Use SentenceTransformer (all-MiniLM-L6-v2) for skill vectorization.

Apply a weighted scoring system (70% skill similarity, 30% experience).

Incorporate a penalty system for missing skills or underqualified experience.

Provide explainable feedback (matched skills, missing skills, experience gaps).

Deploy as a FastAPI service for easy integration.

⚙️ Methodology
Match Score Calculation

Skill Similarity (70%)

Applicant & job skills → embeddings (384-dim vectors).

Similarity measured using cosine similarity.

Experience Score (30%)

Applicant’s experience compared with job’s min–max range.

Full score if within range, reduced if under/over.

Final Score Formula

Final Score = (0.7 × Skill Similarity) + (0.3 × Experience Score)

Penalty System

Missing required skills → reduce similarity score (10–20% penalty).

Underqualified experience → heavy penalty (score close to 0 if far below).

Overqualified experience → small penalty (to avoid poor fit).

Extra unrelated skills → ignored (no bonus).

🔄 System Flows

Flow 5: Model Building at Startup

Fetch jobs → embed skills → build job embedding matrix → save model (job_matching_model.joblib).

Flow 1: Jobs for an Applicant

Given applicant ID → embed skills → compare with job embeddings → sort by score → select top N jobs → return JSON with feedback.

Flow 2: Applicants for a Job

Given job ID → find applicants with closest skill embeddings and experience → return ranked applicant list.

Flow 3: Applicant vs Job

Given applicant & job → calculate detailed compatibility score → return explanation (skills matched, missing, experience gap).

📤 Example JSON Output
{
  "applicant_id": "A123",
  "recommendations": [
    {
      "job_id": "J456",
      "title": "Data Scientist",
      "match%": 87.5,
      "feedback": {
        "matched_skills": ["Python", "Machine Learning"],
        "missing_skills": ["Deep Learning"],
        "experience_match": "Within required range"
      }
    }
  ]
}

🚀 Setup & Run
1. Clone the repository
git clone https://github.com/YOUR-USERNAME/applicantRecommendation.git
cd applicantRecommendation

2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

3. Install dependencies
pip install -r requirements.txt

4. Configure database

Copy config_example.py → config.py and fill in your DB credentials.

Ensure PostgreSQL is running.

5. Run the FastAPI server
python main.py


Server runs at: http://0.0.0.0:8080

📬 API Endpoints

GET /applicant/{id}/jobs → Get recommended jobs for an applicant

GET /job/{id}/applicants → Get suitable applicants for a job

GET /match/{applicant_id}/{job_id} → Get match score between applicant & job

📊 Documentation

Flow diagrams available in docs/job_recommendation_flows_clean.pdf
