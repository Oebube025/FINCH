"""
database.py - FINCH Supabase & Multi-Tenant Persistence Layer (Phase 3)
"""
import os
from typing import Optional
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self):
        # Securely loading from environment variables
        self.url = os.getenv("SUPABASE_URL", "https://qprcnyjbxtbkjjyalhpo.supabase.co")
        self.key = (
            os.getenv("SUPABASE_SECRET_KEY") or 
            os.getenv("SUPABASE_PUBLISHABLE_KEY") or 
            os.getenv("SUPABASE_ANON_KEY") or 
            ""
        )
        self._client: Optional[Client] = None

    def get_client(self) -> Optional[Client]:
        if not self.url or not self.key:
            return None
        if not self._client:
            try:
                self._client = create_client(self.url, self.key)
            except Exception as e:
                print(f"Supabase connection error: {e}")
                return None
        return self._client

db_manager = DatabaseManager()

def init_db():
    return db_manager.get_client() is not None

def save_scenario_db(user: str, scenario_name: str, data_key: str, res: dict):
    client = db_manager.get_client()
    if not client:
        return False
    try:
        data = {
            "user_id": user,
            "scenario_name": scenario_name,
            "data_key": data_key,
            "revenue": res.get("revenue"),
            "costs": res.get("costs"),
            "net_profit": res.get("net_profit"),
            "profit_margin": res.get("profit_margin")
        }
        client.table("scenarios").insert(data).execute()
        return True
    except Exception as e:
        print(f"Failed to save scenario: {e}")
        return False

def load_scenarios_db(user: str, data_key: str) -> list:
    client = db_manager.get_client()
    if not client:
        return []
    try:
        res = client.table("scenarios").select("*").eq("user_id", user).eq("data_key", data_key).execute()
        return res.data or []
    except Exception as e:
        print(f"Failed to load scenarios: {e}")
        return []

def delete_scenarios_db(user: str, data_key: str):
    client = db_manager.get_client()
    if not client:
        return
    try:
        client.table("scenarios").delete().eq("user_id", user).eq("data_key", data_key).execute()
    except Exception as e:
        print(f"Failed to delete scenarios: {e}")

def log_tenant_activity(email: str, activity: str, increment_upload: bool = False):
    client = db_manager.get_client()
    if not client:
        return
    try:
        data = {"email": email, "activity": activity}
        client.table("tenant_activity").insert(data).execute()
    except Exception as e:
        print(f"Failed to log activity: {e}")

def save_feedback_db(user: str, feedback: str):
    pass

def create_user(username: str, email: str, password_hash: str) -> bool:
    client = db_manager.get_client()
    if not client:
        return False
    try:
        client.table("tenants").insert({
            "username": username.strip().lower(),
            "email": email.strip().lower(),
            "password_hash": password_hash
        }).execute()
        return True
    except Exception as e:
        print(f"Create user error: {e}")
        return False

def verify_user(username_or_email: str, password_hash: str) -> Optional[str]:
    client = db_manager.get_client()
    if not client:
        return None
    try:
        q = client.table("tenants").select("username, email, password_hash").or_(
            f"username.eq.{username_or_email.strip().lower()},email.eq.{username_or_email.strip().lower()}"
        ).execute()
        if q.data and len(q.data) > 0:
            user_record = q.data[0]
            if user_record.get("password_hash") == password_hash:
                return user_record.get("username")
        return None
    except Exception as e:
        print(f"Verify user error: {e}")
        return None

def get_user_email(username: str) -> str:
    client = db_manager.get_client()
    if not client:
        return f"{username}@finch.local"
    try:
        q = client.table("tenants").select("email").eq("username", username.strip().lower()).execute()
        if q.data and len(q.data) > 0:
            return q.data[0].get("email", f"{username}@finch.local")
    except Exception:
        pass
    return f"{username}@finch.local"

def save_audit_history_db(email: str, report_type: str, file_name: str, totals: dict, advisory: str):
    client = db_manager.get_client()
    if not client:
        return
    try:
        data = {
            "email": email,
            "file_name": file_name,
            "total_revenue": totals.get("total_revenue", 0.0),
            "net_profit": totals.get("net_profit", 0.0),
            "profit_margin": totals.get("profit_margin", 0.0),
            "advisory": advisory
        }
        client.table("tenant_audits").insert(data).execute()
    except Exception as e:
        print(f"Failed to save audit history: {e}")

def load_user_history_db(email: str) -> list:
    client = db_manager.get_client()
    if not client:
        return []
    try:
        res = client.table("tenant_audits").select("*").eq("email", email).order("timestamp", desc=True).limit(20).execute()
        return res.data or []
    except Exception as e:
        print(f"Failed to load user history: {e}")
        return []