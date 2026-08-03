# SUSHRUTA — The HealthBot (SIH25049 prototype)

AI-driven public health chatbot for disease awareness — multilingual (English/Hindi),
WhatsApp + SMS, vaccination reminders, outbreak alerts, symptom guidance, and a
misinformation-check flow. Built for Smart India Hackathon 2025.

## Contents

- [`docs/PRD.md`](docs/PRD.md) — full product requirements document
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system architecture, diagrams, API contract
- [`backend/`](backend) — Flask webhook service + rule-based NLU + knowledge base (the
  fulfillment logic a real Dialogflow/Twilio integration would call)
- [`frontend/`](frontend) — single-page demo: WhatsApp-style chat, SMS numeric-menu
  simulator, and an ASHA/admin dashboard, all served by the Flask app

The prototype swaps Dialogflow/Twilio for a local rule-based NLU and a direct `/chat`
endpoint so the whole thing runs with no external credentials — see
`docs/ARCHITECTURE.md` section 9 for exactly what changes to reach production.

## Run it

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python app.py
```

Then open **http://127.0.0.1:5050** — the Flask app serves the frontend directly, so
there's nothing else to start.

## Try it

- **WhatsApp Demo** tab — free-text chat in English or Hindi. Try: "when is my child's
  next vaccine due", "any outbreak alert in Rampur", "is it true that covid vaccine
  causes infertility", "I have chest pain and difficulty breathing" (escalation).
- **SMS Demo** tab — numeric menu flow for feature-phone users. Send `menu`, then a digit.
- **ASHA / Admin Dashboard** tab — query stats, publish outbreak alerts, manage the
  knowledge base. All writes are live against the running backend.

Data resets whenever the Flask process restarts (in-memory store, by design — see
architecture doc for the production storage plan).
