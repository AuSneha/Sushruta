"""
In-memory data store for the prototype (see docs/ARCHITECTURE.md section 9 — production
swaps this module for Firestore/Cloud SQL without changing handler logic).
Resets on process restart; seeded with demo data so the dashboard has something to show.
"""
import hashlib
import json
import os
from datetime import datetime, date

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json(filename):
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()[:16]


class Store:
    def __init__(self):
        self.kb = _load_json("kb_seed.json")
        self.schedule = _load_json("immunization_schedule.json")
        self.alerts = _load_json("outbreak_alerts_seed.json")
        self.facilities = _load_json("facilities.json")

        self.users = {}
        self.reminders = []
        self.query_log = []  # anonymized: {intent, district, language, ts}
        self._next_kb_id = len(self.kb) + 1
        self._next_alert_id = len(self.alerts) + 1
        self._seed_demo_users()

    # ---------- users / dependents ----------
    def _seed_demo_users(self):
        demo_phone = "+919990000001"
        uid = hash_phone(demo_phone)
        self.users[uid] = {
            "id": uid,
            "phone_display": "+91 99900 00001 (demo)",
            "preferred_language": "hi",
            "district": "Rampur",
            "pincode": "244901",
            "consent_given": True,
            "consent_timestamp": "2026-07-01T10:00:00",
            "dependents": [
                {
                    "name": "Anaya",
                    "dob": "2026-06-15",
                    "relation": "child",
                    "vaccination_history": [
                        {"vaccine": "BCG", "date_given": "2026-06-15"},
                        {"vaccine": "OPV-0", "date_given": "2026-06-15"},
                        {"vaccine": "Hep B-1", "date_given": "2026-06-15"},
                    ],
                }
            ],
        }

    def get_or_create_user(self, phone: str, language="en", district=None, pincode=None):
        uid = hash_phone(phone)
        if uid not in self.users:
            self.users[uid] = {
                "id": uid,
                "phone_display": phone,
                "preferred_language": language,
                "district": district,
                "pincode": pincode,
                "consent_given": True,
                "consent_timestamp": datetime.utcnow().isoformat(),
                "dependents": [],
            }
        return self.users[uid]

    def get_user(self, uid: str):
        return self.users.get(uid)

    # ---------- knowledge base ----------
    def find_kb_entry(self, topic_hint: str, language: str):
        hint = topic_hint.lower()
        candidates = [e for e in self.kb if e["language"] == language]
        for entry in candidates:
            if any(hint in qv.lower() or qv.lower() in hint for qv in entry["question_variants"]):
                return entry
        # fall back to matching regardless of language, then regardless of hint
        for entry in self.kb:
            if any(hint in qv.lower() or qv.lower() in hint for qv in entry["question_variants"]):
                return entry
        return None

    def list_kb(self):
        return self.kb

    def add_kb_entry(self, entry: dict):
        entry["id"] = f"kb-{self._next_kb_id:03d}"
        self._next_kb_id += 1
        entry["updated_at"] = datetime.utcnow().isoformat()
        self.kb.append(entry)
        return entry

    def delete_kb_entry(self, entry_id: str):
        before = len(self.kb)
        self.kb = [e for e in self.kb if e["id"] != entry_id]
        return len(self.kb) < before

    # ---------- outbreak alerts ----------
    def list_alerts(self, district=None):
        if district:
            return [a for a in self.alerts if a["district"].lower() == district.lower()]
        return self.alerts

    def add_alert(self, alert: dict):
        alert["id"] = f"alert-{self._next_alert_id:03d}"
        self._next_alert_id += 1
        alert["published_at"] = datetime.utcnow().isoformat()
        self.alerts.append(alert)
        return alert

    # ---------- immunization schedule ----------
    def next_due_vaccine(self, dependent: dict):
        dob = date.fromisoformat(dependent["dob"])
        age_days = (date.today() - dob).days
        given = {h["vaccine"] for h in dependent.get("vaccination_history", [])}
        upcoming = sorted(self.schedule, key=lambda s: s["due_age_days"])
        for item in upcoming:
            if item["vaccine"] in given:
                continue
            due_date = dob.fromordinal(dob.toordinal() + item["due_age_days"])
            return {
                "vaccine": item["vaccine"],
                "label_en": item["label_en"],
                "label_hi": item["label_hi"],
                "due_date": due_date.isoformat(),
                "overdue": due_date < date.today(),
            }
        return None

    def facility_for_district(self, district: str):
        for f in self.facilities:
            if district and f["district"].lower() == district.lower():
                return f
        return next(f for f in self.facilities if f["district"] == "default")

    # ---------- analytics ----------
    def log_query(self, intent, district, language):
        self.query_log.append({
            "intent": intent or "unrecognized",
            "district": district or "unknown",
            "language": language,
            "ts": datetime.utcnow().isoformat(),
        })

    def stats(self):
        by_intent = {}
        by_district = {}
        for q in self.query_log:
            by_intent[q["intent"]] = by_intent.get(q["intent"], 0) + 1
            by_district[q["district"]] = by_district.get(q["district"], 0) + 1
        return {
            "total_queries": len(self.query_log),
            "by_intent": by_intent,
            "by_district": by_district,
            "recent": self.query_log[-20:][::-1],
        }


store = Store()
