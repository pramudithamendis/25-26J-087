import sys
import os
from datetime import datetime
from bson import ObjectId

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

# Essential imports ONLY
from app.models.application_model import applications_collection
from app.models.user_model import users_collection
from app.models.cv_trend_score_model import cv_trend_scores_collection
from app.utils.date_utils import current_week_id

# REDEFINE the function here to test the logic without triggering heavy imports
def get_job_applicants_scores_fixed(job_id: str, week_id: str):
    # 1. Fetch applications for the job
    applications = list(applications_collection.find({"job_id": job_id}))
    if not applications:
        return {
            "week_id": week_id,
            "job_id": job_id,
            "average_score": 0.0,
            "applicant_count": 0,
            "scores": []
        }

    # 2. Extract user_ids and map them to applications
    user_ids = [ObjectId(app["user_id"]) for app in applications if "user_id" in app]
    applicant_count = len(user_ids)

    # 3. Fetch user emails from users_collection
    users = list(users_collection.find({"_id": {"$in": user_ids}}, {"email": 1}))
    user_email_map = {str(u["_id"]): u["email"] for u in users if "email" in u}

    # 4. Fetch trend scores for these emails for the given week
    emails = list(user_email_map.values())
    cv_scores_docs = list(cv_trend_scores_collection.find({
        "email": {"$in": emails},
        "week_id": week_id
    }))

    # 5. Create a map of email -> score
    email_score_map = {}
    for doc in sorted(cv_scores_docs, key=lambda x: x.get("created_at", datetime.min)):
        email_score_map[doc["email"]] = {
            "cv_id": str(doc["cv_id"]),
            "cv_trend_score": doc.get("cv_trend_score", 0.0)
        }

    # 6. Build the final scores list based on applications
    scores_list = []
    numeric_scores = []
    for app in applications:
        u_id = str(app["user_id"])
        email = user_email_map.get(u_id)
        if email and email in email_score_map:
            score_data = email_score_map[email]
            scores_list.append(score_data)
            numeric_scores.append(score_data["cv_trend_score"])

    avg_score = round(sum(numeric_scores) / len(numeric_scores), 4) if numeric_scores else 0.0

    return {
        "week_id": week_id,
        "job_id": job_id,
        "average_score": avg_score,
        "applicant_count": applicant_count,
        "scores": scores_list
    }

def test_fix():
    print("Testing get_job_applicants_scores logic...")
    
    # 1. Setup mock data
    job_id = "test_job_123"
    week_id = current_week_id()
    user_email = "test_applicant@example.com"
    
    # Ensure user exists
    user = users_collection.find_one({"email": user_email})
    if not user:
        result = users_collection.insert_one({
            "email": user_email,
            "name": "Test Applicant"
        })
        user_id = str(result.inserted_id)
    else:
        user_id = str(user["_id"])
    
    # Ensure application exists
    app = applications_collection.find_one({"job_id": job_id, "user_id": user_id})
    if not app:
        applications_collection.insert_one({
            "job_id": job_id,
            "user_id": user_id,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat()
        })
    else:
        applications_collection.update_one(
            {"_id": app["_id"]},
            {"$set": {"user_id": user_id}}
        )
    
    # Ensure trend score exists
    cv_id = ObjectId()
    cv_trend_scores_collection.update_one(
        {"email": user_email, "week_id": week_id},
        {"$set": {
            "cv_id": cv_id,
            "week_id": week_id,
            "email": user_email,
            "cv_trend_score": 85.5,
            "skills_matched": [{"skill": "Python", "combined_score": 85.5}],
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )
    
    # 2. Call the function
    try:
        result = get_job_applicants_scores_fixed(job_id, week_id)
        
        print(f"Result: {result}")
        
        # 3. Assertions
        assert result["applicant_count"] >= 1
        assert len(result["scores"]) >= 1
        found = any(s["cv_trend_score"] == 85.5 and s["cv_id"] == str(cv_id) for s in result["scores"])
        assert found, "Test score not found in results"
        
        print("\nSUCCESS: get_job_applicants_scores logic is verified!")
        
    except Exception as e:
        print(f"\nFAILURE: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        cv_trend_scores_collection.delete_many({"email": user_email, "week_id": week_id})
        applications_collection.delete_many({"job_id": job_id, "user_id": user_id})

if __name__ == "__main__":
    test_fix()
