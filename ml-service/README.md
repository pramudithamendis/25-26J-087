# Deployment process

## 1. Container 1
```txt
NER Service (Container 1) ✅
skill-ner-bert-service/
    ├── model/
    ├── Dockerfile
    ├── requirements.txt
    ├── hybrid_extractor.py
    ├── loader.py
    └── main.py
```
```bash
# Build 
docker build -t ner-service . # Also use this to modify the container

# Run
docker run -it --rm -p 8000:8000 ner-service

# Test
 Invoke-RestMethod -Uri "http://localhost:8000/extract" -Method POST -ContentType "application/json" -Body '{"text": "Python, SQL, Docker"}'
```
## 2. Container 2 
```txt
Attrition Service (Container 2) ✅
prehire-attrition-service/
    ├── model/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    └── loader.py
```

 ```bash
 # Build
 docker build -t attrition-service . # Also use this to modify the container

 # Run
 docker run -it --rm -p 8001:8001 attrition-service

 # Test
 $body = @'
{
  "features": {
    "skill_match_score": 0.65,
    "title_match_score": 0.55,
    "exp_match_score": 0.70,
    "edu_match_score": 1.0,
    "location_match_score": 0.80,
    "overall_match_score": 0.68,
    "is_overqualified": 0,
    "is_underqualified": 0,
    "total_jobs": 4.0,
    "total_exp_years": 5.5,
    "avg_tenure_months": 18.0,
    "current_job_tenure": 14.0,
    "short_stints_count": 1.0,
    "job_hopping_rate": 0.25,
    "tenure_slope": 0.5,
    "industry_switches": 1.0,
    "has_progression": 1.0,
    "progression_jumps": 1.0,
    "has_masters": 0.0,
    "n_education": 1.0,
    "n_skills": 12.0,
    "n_certifications": 2.0,
    "is_remote_cv": 0.0,
    "is_remote_jd": 0.0,
    "work_mode_mismatch": 0.0,
    "region": 0.0,
    "university_tier": 1.0,
    "has_career_gap": 0.0,
    "career_gap_months": 0.0,
    "is_remote_preference": 0.0
  }
}
'@

Invoke-RestMethod -Uri "http://localhost:8001/predict" -Method POST -Body $body -ContentType "application/json"
 ```

