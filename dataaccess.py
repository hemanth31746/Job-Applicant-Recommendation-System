# # dataaccess.py
# import os
# import re
# import pandas as pd
# from database import DatabaseConnection
# import logging
# import json

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Build a master skill set from the CSV
# SKILL_SET = set()
# skills_csv_path = os.path.join(os.path.dirname(__file__), "skills.csv")
# try:
#     with open(skills_csv_path, "r", encoding="utf-8") as f:
#         for line in f:
#             skill = line.strip()
#             if skill:
#                 SKILL_SET.add(skill.lower())
#     logger.info(f"Loaded SKILL_SET with {len(SKILL_SET)} skills")
# except Exception as e:
#     logger.error(f"Error loading skills.csv: {e}")
#     # Create empty skill set if file doesn't exist
#     SKILL_SET = set()

# def parse_skills(sk):
#     """Parse skills from various formats: string, list, or JSON."""
#     if not sk:
#         return []
    
#     # If it's already a list, return it processed
#     if isinstance(sk, list):
#         return [s.strip().lower() for s in sk if s and s.strip()]
    
#     # If it's a string, try to parse it
#     if isinstance(sk, str):
#         # Try to parse as JSON first (for PostgreSQL array format)
#         if sk.startswith('[') and sk.endswith(']'):
#             try:
#                 parsed = json.loads(sk)
#                 if isinstance(parsed, list):
#                     return [s.strip().lower() for s in parsed if s and s.strip()]
#             except json.JSONDecodeError:
#                 pass
        
#         # Parse as comma-separated string
#         return [s.strip().lower() for s in sk.split(",") if s.strip()]
    
#     # For any other type, try to convert to string first
#     try:
#         return parse_skills(str(sk))
#     except:
#         logger.warning(f"Could not parse skills: {sk} (type: {type(sk)})")
#         return []

# def extract_skills_from_description(description):
#     if not isinstance(description, str):
#         return []
#     tokens = re.findall(
#         r"\b[a-zA-Z0-9\+\#\.]+(?:\s+[a-zA-Z0-9\+\#\.]+)?\b",
#         description.lower()
#     )
#     return [w for w in set(tokens) if w in SKILL_SET]

# def fetch_jobs():
#     """Fetch jobs with improved error handling."""
#     db = None
#     try:
#         db = DatabaseConnection()
#         db.connect()
#         query = """
#             SELECT "jobId", "jobTitle", "skills", "description", "minExp", "maxExp"
#             FROM jobs
#             WHERE "skills" IS NOT NULL OR "description" IS NOT NULL;
#         """
#         rows, cols = db.execute_query(query)
        
#         if not rows:
#             logger.warning("No jobs found in database")
#             return pd.DataFrame(columns=[
#                 "job_id", "job_title", "skills", "description", "min_experience", "max_experience"
#             ])

#         df = pd.DataFrame(rows, columns=cols)
#         df = df.rename(columns={
#             "jobId": "job_id",
#             "jobTitle": "job_title",
#             "minExp": "min_experience",
#             "maxExp": "max_experience"
#         })

#         logger.info("Sample skills data from database:")
#         for i, skill_data in enumerate(df["skills"].head(3)):
#             logger.info(f"  Row {i}: {skill_data} (type: {type(skill_data)})")

#         df["skills"] = df["skills"].apply(parse_skills)
#         df["desc_skills"] = df["description"].apply(extract_skills_from_description)
#         df["skills"] = df.apply(
#             lambda r: list(set(r["skills"] + r["desc_skills"])),
#             axis=1
#         )
#         df.drop(columns=["desc_skills"], inplace=True)

#         df["min_experience"] = pd.to_numeric(df["min_experience"], errors="coerce").fillna(0.0)
#         df["max_experience"] = pd.to_numeric(df["max_experience"], errors="coerce")

#         def fix_max_experience(row):
#             if pd.isna(row["max_experience"]):
#                 return row["min_experience"] + 5.0
#             else:
#                 return row["max_experience"]

#         df["max_experience"] = df.apply(fix_max_experience, axis=1)
#         df[["min_experience", "max_experience"]] = df[["min_experience", "max_experience"]].clip(0.0, 30.0)

#         def ensure_max_ge_min(row):
#             return max(row["max_experience"], row["min_experience"])

#         df["max_experience"] = df.apply(ensure_max_ge_min, axis=1)

#         # Filter out jobs with empty skill list
#         df = df[df["skills"].apply(lambda s: bool(s))]

#         logger.info(f"Successfully fetched {len(df)} jobs")
#         return df[[
#             "job_id", "job_title", "skills", "description",
#             "min_experience", "max_experience"
#         ]]
        
#     except Exception as e:
#         logger.error(f"Error fetching jobs: {e}")
#         raise
#     finally:
#         if db:
#             db.close()

# def fetch_applicant_skills(applicant_id: str):
#     """Fetch applicant skills with improved error handling."""
#     db = None
#     try:
#         db = DatabaseConnection()
#         db.connect()
#         query = """SELECT "skills" FROM employment WHERE "applicantId" = %s;"""
#         rows, _ = db.execute_query(query, (applicant_id,))
        
#         if not rows or not rows[0][0]:
#             logger.info(f"No skills found for applicant {applicant_id}")
#             return []
            
#         skills_data = rows[0][0]
#         logger.info(f"Raw skills data for applicant {applicant_id}: {skills_data} (type: {type(skills_data)})")
        
#         result = parse_skills(skills_data)
#         logger.info(f"Fetched {len(result)} skills for applicant {applicant_id}: {result}")
#         return result
#     except Exception as e:
#         logger.error(f"Error fetching skills for applicant {applicant_id}: {e}")
#         raise
#     finally:
#         if db:
#             db.close()

# def fetch_applicant_experience(applicant_id: str):
#     """Fetch applicant experience with improved error handling."""
#     db = None
#     try:
#         db = DatabaseConnection()
#         db.connect()
#         query = """SELECT "totalWorkExp" FROM employment WHERE "applicantId" = %s;"""
#         rows, _ = db.execute_query(query, (applicant_id,))
        
#         try:
#             result = float(rows[0][0]) if rows and rows[0][0] is not None else 0.0
#             logger.info(f"Fetched experience {result} for applicant {applicant_id}")
#             return result
#         except (ValueError, TypeError):
#             logger.warning(f"Invalid experience value for applicant {applicant_id}, defaulting to 0.0")
#             return 0.0
#     except Exception as e:
#         logger.error(f"Error fetching experience for applicant {applicant_id}: {e}")
#         raise
#     finally:
#         if db:
#             db.close()

# def fetch_all_applicants():
#     """Fetch all applicants with improved error handling."""
#     db = None
#     try:
#         db = DatabaseConnection()
#         db.connect()
#         query = """SELECT "applicantId", "skills", "totalWorkExp" FROM employment;"""
#         rows, cols = db.execute_query(query)

#         if not rows:
#             logger.warning("No applicants found in database")
#             return pd.DataFrame(columns=["applicantId","skills","totalWorkExp"])

#         df = pd.DataFrame(rows, columns=cols)
        
#         # Debug: Log the first few skills entries
#         logger.info("Sample applicant skills data from database:")
#         for i, skill_data in enumerate(df["skills"].head(3)):
#             logger.info(f"  Row {i}: {skill_data} (type: {type(skill_data)})")
        
#         df["skills"] = df["skills"].apply(parse_skills)
#         df["totalWorkExp"] = pd.to_numeric(df["totalWorkExp"], errors="coerce").fillna(0.0)
        
#         logger.info(f"Successfully fetched {len(df)} applicants")
#         return df
        
#     except Exception as e:
#         logger.error(f"Error fetching all applicants: {e}")
#         raise
#     finally:
#         if db:
#             db.close()

# dataaccess.py
import os
import re
import pandas as pd
import logging
import json

from database import DatabaseConnection
from config import DB_CONFIG   # ✅ Import DB_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Build a master skill set from the CSV
SKILL_SET = set()
skills_csv_path = os.path.join(os.path.dirname(__file__), "skills.csv")
try:
    with open(skills_csv_path, "r", encoding="utf-8") as f:
        for line in f:
            skill = line.strip()
            if skill:
                SKILL_SET.add(skill.lower())
    logger.info(f"Loaded SKILL_SET with {len(SKILL_SET)} skills")
except Exception as e:
    logger.error(f"Error loading skills.csv: {e}")
    # Create empty skill set if file doesn't exist
    SKILL_SET = set()

def parse_skills(sk):
    """Parse skills from various formats: string, list, or JSON."""
    if not sk:
        return []
    
    if isinstance(sk, list):
        return [s.strip().lower() for s in sk if s and s.strip()]
    
    if isinstance(sk, str):
        if sk.startswith('[') and sk.endswith(']'):
            try:
                parsed = json.loads(sk)
                if isinstance(parsed, list):
                    return [s.strip().lower() for s in parsed if s and s.strip()]
            except json.JSONDecodeError:
                pass
        return [s.strip().lower() for s in sk.split(",") if s.strip()]
    
    try:
        return parse_skills(str(sk))
    except:
        logger.warning(f"Could not parse skills: {sk} (type: {type(sk)})")
        return []

def extract_skills_from_description(description):
    if not isinstance(description, str):
        return []
    tokens = re.findall(
        r"\b[a-zA-Z0-9\+\#\.]+(?:\s+[a-zA-Z0-9\+\#\.]+)?\b",
        description.lower()
    )
    return [w for w in set(tokens) if w in SKILL_SET]

def fetch_jobs():
    """Fetch jobs with improved error handling."""
    db = None
    try:
        db = DatabaseConnection(**DB_CONFIG)   # ✅ Pass DB_CONFIG
        db.connect()
        query = """
            SELECT "jobId", "jobTitle", "skills", "description", "minExp", "maxExp"
            FROM jobs
            WHERE "skills" IS NOT NULL OR "description" IS NOT NULL;
        """
        rows, cols = db.execute_query(query)
        
        if not rows:
            logger.warning("No jobs found in database")
            return pd.DataFrame(columns=[
                "job_id", "job_title", "skills", "description", "min_experience", "max_experience"
            ])

        df = pd.DataFrame(rows, columns=cols)
        df = df.rename(columns={
            "jobId": "job_id",
            "jobTitle": "job_title",
            "minExp": "min_experience",
            "maxExp": "max_experience"
        })

        logger.info("Sample skills data from database:")
        for i, skill_data in enumerate(df["skills"].head(3)):
            logger.info(f"  Row {i}: {skill_data} (type: {type(skill_data)})")

        df["skills"] = df["skills"].apply(parse_skills)
        df["desc_skills"] = df["description"].apply(extract_skills_from_description)
        df["skills"] = df.apply(
            lambda r: list(set(r["skills"] + r["desc_skills"])),
            axis=1
        )
        df.drop(columns=["desc_skills"], inplace=True)

        df["min_experience"] = pd.to_numeric(df["min_experience"], errors="coerce").fillna(0.0)
        df["max_experience"] = pd.to_numeric(df["max_experience"], errors="coerce")

        def fix_max_experience(row):
            if pd.isna(row["max_experience"]):
                return row["min_experience"] + 5.0
            else:
                return row["max_experience"]

        df["max_experience"] = df.apply(fix_max_experience, axis=1)
        df[["min_experience", "max_experience"]] = df[["min_experience", "max_experience"]].clip(0.0, 30.0)

        def ensure_max_ge_min(row):
            return max(row["max_experience"], row["min_experience"])

        df["max_experience"] = df.apply(ensure_max_ge_min, axis=1)

        df = df[df["skills"].apply(lambda s: bool(s))]

        logger.info(f"Successfully fetched {len(df)} jobs")
        return df[[
            "job_id", "job_title", "skills", "description",
            "min_experience", "max_experience"
        ]]
        
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        raise
    finally:
        if db:
            db.close()

def fetch_applicant_skills(applicant_id: str):
    """Fetch applicant skills with improved error handling."""
    db = None
    try:
        db = DatabaseConnection(**DB_CONFIG)   # ✅
        db.connect()
        query = """SELECT "skills" FROM employment WHERE "applicantId" = %s;"""
        rows, _ = db.execute_query(query, (applicant_id,))
        
        if not rows or not rows[0][0]:
            logger.info(f"No skills found for applicant {applicant_id}")
            return []
            
        skills_data = rows[0][0]
        logger.info(f"Raw skills data for applicant {applicant_id}: {skills_data} (type: {type(skills_data)})")
        
        result = parse_skills(skills_data)
        logger.info(f"Fetched {len(result)} skills for applicant {applicant_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error fetching skills for applicant {applicant_id}: {e}")
        raise
    finally:
        if db:
            db.close()

def fetch_applicant_experience(applicant_id: str):
    """Fetch applicant experience with improved error handling."""
    db = None
    try:
        db = DatabaseConnection(**DB_CONFIG)   # ✅
        db.connect()
        query = """SELECT "totalWorkExp" FROM employment WHERE "applicantId" = %s;"""
        rows, _ = db.execute_query(query, (applicant_id,))
        
        try:
            result = float(rows[0][0]) if rows and rows[0][0] is not None else 0.0
            logger.info(f"Fetched experience {result} for applicant {applicant_id}")
            return result
        except (ValueError, TypeError):
            logger.warning(f"Invalid experience value for applicant {applicant_id}, defaulting to 0.0")
            return 0.0
    except Exception as e:
        logger.error(f"Error fetching experience for applicant {applicant_id}: {e}")
        raise
    finally:
        if db:
            db.close()

def fetch_all_applicants():
    """Fetch all applicants with improved error handling."""
    db = None
    try:
        db = DatabaseConnection(**DB_CONFIG)   # ✅
        db.connect()
        query = """SELECT "applicantId", "skills", "totalWorkExp" FROM employment;"""
        rows, cols = db.execute_query(query)

        if not rows:
            logger.warning("No applicants found in database")
            return pd.DataFrame(columns=["applicantId","skills","totalWorkExp"])

        df = pd.DataFrame(rows, columns=cols)
        
        logger.info("Sample applicant skills data from database:")
        for i, skill_data in enumerate(df["skills"].head(3)):
            logger.info(f"  Row {i}: {skill_data} (type: {type(skill_data)})")
        
        df["skills"] = df["skills"].apply(parse_skills)
        df["totalWorkExp"] = pd.to_numeric(df["totalWorkExp"], errors="coerce").fillna(0.0)
        
        logger.info(f"Successfully fetched {len(df)} applicants")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching all applicants: {e}")
        raise
    finally:
        if db:
            db.close()
