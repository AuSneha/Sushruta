# Product Requirements Document — SUSHRUTA (The HealthBot)

**Problem Statement ID:** SIH25049
**Theme:** HealthTech | **Category:** Software
**Team:** Web House
**Version:** 1.0 · **Date:** 2026-08-03
**Author:** Web House (Team)

---

## 1. Purpose & Background

Rural and semi-urban India faces a persistent gap between government-verified health
information (vaccination schedules, disease outbreak alerts, preventive care guidance) and
citizens who need it. This gap is widened by:

- Low smartphone/app literacy, but high mobile phone penetration (including feature phones).
- Language and literacy barriers with English-first digital health tools.
- Rumor and misinformation filling the vacuum left by inaccessible official channels.
- Missed vaccination doses due to lack of timely, personal reminders.
- Delayed public awareness of local disease outbreaks.

**SUSHRUTA** is a multilingual AI chatbot, reachable over WhatsApp (smartphones) and SMS
(feature phones), that delivers verified government health information conversationally —
symptom guidance, vaccination reminders, outbreak alerts, and preventive health tips — without
requiring an app install or literacy in English.

## 2. Goals

| # | Goal | Metric |
|---|------|--------|
| G1 | Increase access to verified health info in underserved areas | # unique users reached per district |
| G2 | Reduce missed vaccination doses | % reduction in missed-dose rate vs. baseline (pilot district) |
| G3 | Speed up outbreak awareness | Median time from IDSP alert ingestion to user notification |
| G4 | Reduce reliance on misinformation | # misinformation-check queries resolved with verified answer |
| G5 | Be inclusive of feature-phone users | % of active users on SMS vs. WhatsApp |

### Non-goals (out of scope for v1)
- Replacing clinical diagnosis or emergency medical services (bot always directs to a
  facility/helpline for anything beyond general guidance).
- Processing or storing electronic health records (EHR) — no ABDM/health-ID integration in v1.
- Payments, teleconsultation booking, or prescription handling.

## 3. Target Users & Personas

1. **Rural/semi-urban citizen (primary)** — feature phone or basic smartphone, WhatsApp is
   often their only "app," moderate-to-low literacy, prefers a regional language.
2. **Parent/caregiver** — manages vaccination schedules for children and elderly dependents,
   needs reminders and simple yes/no confirmations.
3. **ASHA / frontline health worker (secondary)** — needs a lightweight view of query volume,
   flagged misinformation, and outbreak-alert delivery status in their coverage area, to
   prioritize household visits.
4. **Health department admin (secondary)** — needs to publish outbreak alerts and update the
   FAQ/knowledge base without redeploying the bot.

## 4. User Stories

- As a citizen, I can message the bot in my language and ask "when is my child's next
  vaccine due?" and get a clear date and location.
- As a citizen, I can describe symptoms and receive general guidance plus a nudge to visit a
  facility if red-flag symptoms are present — never a diagnosis.
- As a citizen with only SMS, I can reply with a number from a menu to navigate the same
  core flows as WhatsApp users.
- As a citizen, I automatically receive an alert if an outbreak is flagged in my
  district/pincode, without having to ask.
- As a citizen, I can forward a suspicious health "forward" message and get a verified/
  not-verified verdict against the knowledge base.
- As an ASHA worker, I can see anonymized query trends (top symptoms/topics) for my area this
  week.
- As an admin, I can add/update an FAQ entry or push an outbreak alert without a code deploy.

## 5. Functional Requirements

### FR1 — Conversational Core (NLU)
- FR1.1 Classify user intent: `symptom_check`, `vaccination_query`, `outbreak_alert_query`,
  `faq`, `misinformation_check`, `human_handoff`, `language_switch`.
- FR1.2 Extract entities: age, vaccine type, location (district/pincode), symptom keywords,
  language preference.
- FR1.3 Maintain short conversation context (last 1-2 turns) to support follow-ups
  ("what about the second dose?").
- FR1.4 If intent confidence is below threshold, escalate to human/helpline flow instead of
  guessing (see FR6).

### FR2 — Vaccination Reminders
- FR2.1 User (or dependent profile) can register name, DOB/age, and location.
- FR2.2 System computes due/upcoming vaccination dates against the national immunization
  schedule and sends a reminder N days before (configurable, default 3).
- FR2.3 Support multiple dependents per phone number (family profile).

### FR3 — Outbreak Alerts
- FR3.1 Ingest outbreak signals (mocked IDSP feed in v1) keyed by district/pincode.
- FR3.2 Push proactive alert to all opted-in users in the affected area.
- FR3.3 User can query current alert status for their area on demand.

### FR4 — Knowledge Base / FAQ
- FR4.1 Store FAQ + preventive-care content per topic, versioned per language.
- FR4.2 Admin can add/edit/retire an entry without redeploying the service.
- FR4.3 Bot answers FAQ intent by retrieving the best-matching entry in the user's language.

### FR5 — Misinformation Check
- FR5.1 User submits free text (a forwarded claim).
- FR5.2 System matches against knowledge base / known-rumor list and returns
  verified / false / unverified with a short explanation and source.

### FR6 — Human Handoff / Escalation
- FR6.1 Low-confidence NLU result, explicit request, or red-flag symptom keywords trigger a
  handoff message with nearest facility/helpline contact info.

### FR7 — Multi-channel Delivery
- FR7.1 WhatsApp rich flow (buttons/quick replies) for smartphone users.
- FR7.2 SMS numeric-menu flow for feature-phone users, functionally equivalent core paths.

### FR8 — Admin / ASHA Dashboard
- FR8.1 View aggregated, anonymized query volume and top intents by district/time range.
- FR8.2 View outbreak alerts published and delivery counts.
- FR8.3 Manage (create/edit/retire) knowledge-base entries.

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Availability | 99% uptime target for webhook service during pilot |
| Latency | Bot reply within 3s (WhatsApp), within 1 SMS round-trip |
| Scalability | Stateless webhook layer, horizontally scalable behind GCP App Engine/Cloud Run |
| Privacy | No storage of raw health conversation content beyond retention window (default 30 days); phone numbers hashed at rest; consent captured on first interaction |
| Security | TLS everywhere, signed webhook requests (Dialogflow/Twilio signature validation), least-privilege service accounts |
| Localization | Minimum launch languages: English, Hindi, +1 regional language (pilot-state dependent) |
| Accessibility | No app install; works on any WhatsApp-capable device and any SMS-capable feature phone |
| Auditability | All published outbreak alerts and KB edits are logged with admin identity + timestamp |

## 7. Success Metrics (Pilot)

- ≥ 70% intent-classification accuracy on real user traffic in target languages.
- ≥ 20% reduction in missed vaccination doses in pilot district vs. prior-quarter baseline.
- Outbreak alert delivered to ≥ 90% of opted-in users in the affected area within 1 hour of
  ingestion.
- ≥ 60% of misinformation-check queries resolved with a confident verdict (not "unverified").

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Multilingual NLU accuracy is low for regional languages | Start with 2-3 well-supported languages, fine-tune with real query logs, fall back to human handoff below confidence threshold |
| Data privacy concerns with health queries over WhatsApp/SMS | Minimal data retention, hashed identifiers, explicit consent flow, encryption in transit and at rest |
| Real-time sync with government data (CoWIN/IDSP) may lag or be unavailable | Cache last-known-good data with a visible "as of" timestamp; degrade gracefully |
| Low digital literacy limits self-service registration | Keep flows to yes/no and numbered choices; ASHA workers can register dependents on a citizen's behalf |
| Misinformation database becomes stale | Periodic admin review cadence; source citations shown to build trust |

## 9. Milestones (Hackathon → Pilot)

1. **Prototype (hackathon):** Rule-based/mock NLU, WhatsApp+SMS demo UI, mock CoWIN/IDSP data,
   core 4 intents working end-to-end.
2. **MVP:** Real Dialogflow agent, Twilio WhatsApp/SMS sandbox, live `data.gov.in` integration,
   admin dashboard for KB + alerts.
3. **Pilot:** 1-2 districts, real user traffic, feedback loop into NLU training data.
4. **Scale:** Additional languages, IVR/voice channel, national rollout.

## 10. Open Questions

- Which state/district to select for pilot (data availability + language coverage)?
- Exact vaccination-schedule source of truth to compute reminders against (CoWIN API vs.
  static national immunization schedule table)?
- Consent flow wording/legal review for health-data handling under DPDP Act.
