import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import nlu
import handlers
from store import store

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# ---------- static frontend ----------
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------- core message pipeline (shared by /chat and /webhook/sms) ----------
def process_message(phone: str, text: str):
    analysis = nlu.analyze(text)
    user = store.get_or_create_user(phone, language=analysis["language"])
    if analysis["entities"].get("district"):
        user["district"] = analysis["entities"]["district"]

    language = user.get("preferred_language") or analysis["language"]
    intent = analysis["intent"] if analysis["confidence"] >= 0.5 else None

    result = handlers.route(intent, user, analysis["entities"], language, text)
    store.log_query(intent, user.get("district"), language)
    return {
        "reply": result["text"],
        "quick_replies": result.get("quick_replies", []),
        "debug": {
            "intent": intent,
            "confidence": round(analysis["confidence"], 2),
            "entities": analysis["entities"],
            "language": language,
        },
    }


# ---------- demo chat endpoint (WhatsApp-equivalent, no Twilio/Dialogflow needed) ----------
@app.route("/api/v1/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True) or {}
    phone = body.get("phone", "+919990000001")
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    return jsonify(process_message(phone, text))


# ---------- SMS numeric-menu simulator (feature-phone equivalent flow) ----------
SMS_MENU_TEXT = {
    "en": (
        "SUSHRUTA Health Menu:\n"
        "1. Vaccination status\n"
        "2. Check symptoms\n"
        "3. Outbreak alerts\n"
        "4. Health tips\n"
        "5. Report a rumor\n"
        "0. Talk to helpline\n"
        "Reply with a number."
    ),
    "hi": (
        "सुश्रुत स्वास्थ्य मेनू:\n"
        "1. टीकाकरण स्थिति\n"
        "2. लक्षण जांच\n"
        "3. प्रकोप अलर्ट\n"
        "4. स्वास्थ्य सुझाव\n"
        "5. अफवाह की रिपोर्ट करें\n"
        "0. हेल्पलाइन से बात करें\n"
        "एक नंबर के साथ जवाब दें।"
    ),
}

SMS_MENU_TO_TEXT = {
    "1": "vaccination status",
    "2": "i have fever and cough",
    "3": "any outbreak alert in my area",
    "4": "how to prevent dengue",
    "5": "is it true that vaccines cause infertility",
    "0": "talk to human helpline",
}


@app.route("/api/v1/webhook/sms", methods=["POST"])
def webhook_sms():
    body = request.get_json(force=True) or {}
    phone = body.get("phone", "+919990000002")
    text = (body.get("text") or "").strip()

    if text.lower() in ("menu", "start", ""):
        user = store.get_or_create_user(phone)
        lang = user.get("preferred_language", "en")
        return jsonify({"reply": SMS_MENU_TEXT.get(lang, SMS_MENU_TEXT["en"]), "quick_replies": []})

    mapped_text = SMS_MENU_TO_TEXT.get(text, text)
    result = process_message(phone, mapped_text)
    result["reply"] += "\n\n(Reply 'menu' to see options again.)"
    return jsonify(result)


# ---------- Dialogflow-shaped fulfillment endpoint (production integration point) ----------
@app.route("/api/v1/webhook/dialogflow", methods=["POST"])
def webhook_dialogflow():
    """Mimics the request/response contract Dialogflow ES fulfillment expects, but is
    driven by our own nlu.analyze() instead of a live Dialogflow agent for this prototype."""
    body = request.get_json(force=True) or {}
    query_result = body.get("queryResult", {})
    text = query_result.get("queryText", "")
    session = body.get("session", "projects/demo/agent/sessions/unknown")
    phone = session.split("/")[-1]

    result = process_message(phone, text)
    return jsonify({
        "fulfillmentText": result["reply"],
        "fulfillmentMessages": [{"text": {"text": [result["reply"]]}}],
        "outputContexts": [],
    })


# ---------- knowledge base admin ----------
@app.route("/api/v1/kb", methods=["GET"])
def list_kb():
    return jsonify(store.list_kb())


@app.route("/api/v1/kb", methods=["POST"])
def create_kb():
    body = request.get_json(force=True) or {}
    required = {"topic", "language", "question_variants", "answer", "source"}
    if not required.issubset(body):
        return jsonify({"error": f"missing fields, need {sorted(required)}"}), 400
    body.setdefault("updated_by", "admin-dashboard")
    entry = store.add_kb_entry(body)
    return jsonify(entry), 201


@app.route("/api/v1/kb/<entry_id>", methods=["DELETE"])
def delete_kb(entry_id):
    ok = store.delete_kb_entry(entry_id)
    return jsonify({"deleted": ok}), (200 if ok else 404)


# ---------- outbreak alerts admin ----------
@app.route("/api/v1/alerts", methods=["GET"])
def list_alerts():
    district = request.args.get("district")
    return jsonify(store.list_alerts(district))


@app.route("/api/v1/alerts", methods=["POST"])
def create_alert():
    body = request.get_json(force=True) or {}
    required = {"district", "disease", "severity", "message_en"}
    if not required.issubset(body):
        return jsonify({"error": f"missing fields, need {sorted(required)}"}), 400
    body.setdefault("message_hi", body["message_en"])
    body.setdefault("pincode", "")
    body.setdefault("published_by", "admin-dashboard")
    alert = store.add_alert(body)
    return jsonify(alert), 201


# ---------- dashboard stats ----------
@app.route("/api/v1/stats", methods=["GET"])
def stats():
    return jsonify(store.stats())


@app.route("/api/v1/users/<user_id>/reminders", methods=["GET"])
def user_reminders(user_id):
    user = store.get_user(user_id)
    if not user:
        return jsonify({"error": "not found"}), 404
    upcoming = []
    for dep in user.get("dependents", []):
        due = store.next_due_vaccine(dep)
        if due:
            upcoming.append({"dependent": dep["name"], **due})
    return jsonify(upcoming)


@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
