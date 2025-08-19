import joblib
import os
import numpy as np
import pandas as pd
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobMatchingModel:
    def __init__(self, model_file='job_matching_model.joblib'):
        logger.info("Initializing JobMatchingModel...")

        self.model_file = model_file
        self.job_ids = []
        self.job_titles = []
        self.job_skills = []
        self.job_embeddings = []
        self.min_experiences = []
        self.max_experiences = []

        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer model loaded")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

        try:
            if not self.load():
                logger.info("No existing model found, attempting to build from DB")
                self._build_and_persist()
            else:
                logger.info("Existing model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            raise

    def normalize_skills(self, skills):
        if not isinstance(skills, list):
            return []
        return [str(skill).strip().lower() for skill in skills if str(skill).strip()]

    def embed_skills(self, skill_list):
        cleaned = self.normalize_skills(skill_list)
        if not cleaned:
            return np.zeros(384)
        return self.embedding_model.encode([' '.join(cleaned)], convert_to_numpy=True)[0]

    def _exp_score(self, applicant_total_exp_months, job_min_exp, job_max_exp):
        try:
            applicant_years = float(applicant_total_exp_months) / 12.0
        except (TypeError, ValueError):
            applicant_years = 0.0

        try:
            job_min = float(job_min_exp)
        except:
            job_min = 0.0

        try:
            job_max = float(job_max_exp)
            if job_max < job_min:
                job_max = job_min
        except:
            job_max = job_min

        if job_min <= 0.0 and job_max <= 0.1:
            return 1.0

        if applicant_years <= 0.0:
            return 1.0 if job_min <= 0.0 else 0.0

        if job_min <= applicant_years <= job_max:
            return 1.0
        elif applicant_years < job_min:
            return max(0.0, 1.0 - (job_min - applicant_years) * 0.10)
        elif applicant_years > job_max:
            return max(0.0, 1.0 - (applicant_years - job_max) * 0.05)
        return 0.0

    def _build_and_persist(self):
        try:
            from dataaccess import fetch_jobs
            logger.info("Fetching jobs from database...")
            df = fetch_jobs()

            if df.empty:
                logger.warning("No jobs found in database")
                return True

            logger.info(f"Processing {len(df)} jobs...")
            self.job_ids = df['job_id'].tolist()
            self.job_titles = df['job_title'].tolist()
            self.job_skills = df['skills'].tolist()
            self.min_experiences = df['min_experience'].astype(float).tolist()
            self.max_experiences = df['max_experience'].astype(float).tolist()

            logger.info("Generating embeddings for job skills...")
            self.job_embeddings = [self.embed_skills(skills) for skills in self.job_skills]

            joblib.dump({
                'job_ids': self.job_ids,
                'job_titles': self.job_titles,
                'job_skills': self.job_skills,
                'job_embeddings': self.job_embeddings,
                'min_experiences': self.min_experiences,
                'max_experiences': self.max_experiences
            }, self.model_file)

            logger.info(f"Model built and saved with {len(self.job_ids)} jobs")
            return True

        except Exception as e:
            logger.error(f"Failed to build and persist model: {e}")
            raise

    def load(self):
        if not os.path.exists(self.model_file):
            logger.info("Model file does not exist")
            return False

        try:
            logger.info("Loading model from disk...")
            data = joblib.load(self.model_file)
            self.job_ids = data['job_ids']
            self.job_titles = data['job_titles']
            self.job_skills = data['job_skills']
            self.job_embeddings = data['job_embeddings']
            self.min_experiences = data['min_experiences']
            self.max_experiences = data['max_experiences']
            logger.info(f"Model loaded with {len(self.job_ids)} jobs")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def score(self, applicant_skills, applicant_total_exp_months, job_skills, job_min_exp, job_max_exp):
        try:
            app_embedding = self.embed_skills(applicant_skills)
            job_embedding = self.embed_skills(job_skills)
            skill_score = float(cosine_similarity([app_embedding], [job_embedding])[0][0])
            exp_score = self._exp_score(applicant_total_exp_months, job_min_exp, job_max_exp)
            final_score = 0.7 * skill_score + 0.3 * exp_score
            return round(final_score * 100, 2), round(skill_score * 100, 1), round(exp_score * 100, 1)
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return 0.0, 0.0, 0.0

    def get_recommendations(self, applicant_skills, applicant_total_exp_months, top_n=5, return_dataframe=True):
        if not self.job_embeddings:
            logger.warning("No job embeddings available")
            return []

        logger.info(f"Generating recommendations for applicant skills: {applicant_skills}")
        app_embedding = self.embed_skills(applicant_skills)

        results = []
        for i in range(len(self.job_embeddings)):
            try:
                job_emb = self.job_embeddings[i]
                skill_score = float(cosine_similarity([app_embedding], [job_emb])[0][0])
                exp_score = self._exp_score(applicant_total_exp_months, self.min_experiences[i], self.max_experiences[i])
                final_score = 0.7 * skill_score + 0.3 * exp_score

                results.append((
                    self.job_ids[i],
                    self.job_titles[i],
                    round(final_score * 100, 2),
                    self.job_skills[i],
                    self.min_experiences[i],
                    self.max_experiences[i],
                    round(skill_score * 100, 1),
                    round(exp_score * 100, 1)
                ))

            except Exception as e:
                logger.error(f"Error processing job {i}: {e}")
                continue

        results.sort(key=lambda x: x[2], reverse=True)
        logger.info(f"Generated {len(results)} recommendations, returning top {top_n}")
        return results[:top_n]
