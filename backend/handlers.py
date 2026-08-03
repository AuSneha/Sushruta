"""Intent handlers — the fulfillment logic shared by /chat, /webhook/dialogflow and
/webhook/sms (see docs/ARCHITECTURE.md section 6, "one handler, two entry points")."""
from store import store

STRINGS = {
    "greeting": {
        "en": "Namaste! I'm Sushruta, your health assistant. You can ask me about vaccinations, "
              "symptoms, disease outbreaks, or check if some health news is true. How can I help?",
        "hi": "नमस्ते! मैं सुश्रुत हूं, आपका स्वास्थ्य सहायक। आप मुझसे टीकाकरण, लक्षण, बीमारी के प्रकोप के "
              "बारे में पूछ सकते हैं, या किसी खबर की सच्चाई जांच सकते हैं। मैं कैसे मदद करूं?",
    },
    "no_dependents": {
        "en": "I don't have a child/family profile registered for you yet. Reply with "
              "'register <name> <DOB YYYY-MM-DD>' to add one, e.g. 'register Anaya 2026-06-15'.",
        "hi": "आपके लिए अभी कोई बच्चे/परिवार की प्रोफ़ाइल दर्ज नहीं है। जोड़ने के लिए "
              "'register <नाम> <जन्मतिथि YYYY-MM-DD>' भेजें, जैसे 'register Anaya 2026-06-15'।",
    },
    "all_done": {
        "en": "Great news — all scheduled vaccines for {name} are up to date!",
        "hi": "बढ़िया खबर — {name} के सभी निर्धारित टीके पूरे हो चुके हैं!",
    },
    "no_alerts": {
        "en": "No active outbreak alerts for your area right now. Stay safe and keep practicing "
              "preventive hygiene.",
        "hi": "फिलहाल आपके क्षेत्र के लिए कोई सक्रिय प्रकोप अलर्ट नहीं है। सुरक्षित रहें और स्वच्छता बनाए रखें।",
    },
    "kb_not_found": {
        "en": "I don't have verified information on that yet. Let me connect you to the helpline "
              "for a confident answer.",
        "hi": "मेरे पास इसकी सत्यापित जानकारी अभी नहीं है। सही जवाब के लिए आपको हेल्पलाइन से जोड़ता हूं।",
    },
    "misinfo_not_found": {
        "en": "I couldn't verify that claim against my knowledge base. Please don't forward it "
              "further until confirmed — you can also check with your nearest health facility.",
        "hi": "मैं इस दावे की पुष्टि नहीं कर सका। पुष्टि होने तक इसे आगे न भेजें — आप नज़दीकी स्वास्थ्य केंद्र से भी पुष्टि कर सकते हैं।",
    },
    "handoff": {
        "en": "Connecting you to human support. Nearest facility: {facility} ({phone}).",
        "hi": "आपको मानव सहायता से जोड़ रहा हूं। नज़दीकी केंद्र: {facility} ({phone})।",
    },
    "symptom_generic": {
        "en": "Thanks for sharing your symptoms. For general fever/cough/body pain: rest, stay "
              "hydrated, and monitor your temperature. If symptoms last more than 2 days or "
              "worsen, please visit {facility} ({phone}).",
        "hi": "अपने लक्षण बताने के लिए धन्यवाद। सामान्य बुखार/खांसी/शरीर दर्द के लिए: आराम करें, पानी पिएं, "
              "तापमान पर नज़र रखें। यदि लक्षण 2 दिन से अधिक रहें या बढ़ें, तो कृपया {facility} ({phone}) जाएं।",
    },
    "fallback": {
        "en": "I'm not fully sure I understood that. You can ask about vaccinations, symptoms, "
              "outbreak alerts, or reply 'helpline' to talk to a person.",
        "hi": "मुझे यह पूरी तरह समझ नहीं आया। आप टीकाकरण, लक्षण, प्रकोप अलर्ट के बारे में पूछ सकते हैं, "
              "या व्यक्ति से बात करने के लिए 'helpline' भेजें।",
    },
}


def _s(key, lang, **kwargs):
    text = STRINGS[key].get(lang, STRINGS[key]["en"])
    return text.format(**kwargs) if kwargs else text


def handle_greeting(user, entities, language, raw_text):
    return {"text": _s("greeting", language), "quick_replies": [
        "Vaccination status", "Check symptoms", "Outbreak alerts", "Health tips"
    ]}


def handle_vaccination_query(user, entities, language, raw_text):
    dependents = user.get("dependents", [])
    if not dependents:
        return {"text": _s("no_dependents", language), "quick_replies": []}

    target = dependents[0]
    if "relation" in entities:
        for d in dependents:
            if d.get("relation") == entities["relation"]:
                target = d
                break

    next_dose = store.next_due_vaccine(target)
    if not next_dose:
        return {"text": _s("all_done", language, name=target["name"]), "quick_replies": []}

    label = next_dose["label_hi"] if language == "hi" else next_dose["label_en"]
    facility = store.facility_for_district(user.get("district"))
    status = "overdue" if next_dose["overdue"] else "due"
    if language == "hi":
        text = (f"{target['name']} के लिए अगला टीका: {label}। नियत तिथि: {next_dose['due_date']}"
                f" ({'अतिदेय' if next_dose['overdue'] else 'नियत'})। स्थान: {facility['name']}।")
    else:
        text = (f"{target['name']}'s next vaccine: {label}. Due date: {next_dose['due_date']} "
                f"({status}). Location: {facility['name']}.")
    return {"text": text, "quick_replies": ["Set reminder", "Nearest facility"]}


def handle_outbreak_alert_query(user, entities, language, raw_text):
    district = entities.get("district") or user.get("district")
    alerts = store.list_alerts(district)
    if not alerts:
        return {"text": _s("no_alerts", language), "quick_replies": []}
    latest = alerts[-1]
    text = latest["message_hi"] if language == "hi" else latest["message_en"]
    return {"text": text, "quick_replies": ["Prevention tips", "Nearest facility"]}


def handle_faq(user, entities, language, raw_text):
    entry = store.find_kb_entry(raw_text, language)
    if not entry:
        return {"text": _s("kb_not_found", language), "quick_replies": ["Talk to helpline"]}
    return {"text": f"{entry['answer']}\n\n(Source: {entry['source']})", "quick_replies": []}


def handle_misinformation_check(user, entities, language, raw_text):
    entry = store.find_kb_entry(raw_text, language)
    if not entry:
        return {"text": _s("misinfo_not_found", language), "quick_replies": ["Talk to helpline"]}
    verdict = "FALSE" if entry["topic"].endswith("myth") else "VERIFIED"
    text = f"Verdict: {verdict}. {entry['answer']}\n\n(Source: {entry['source']})"
    return {"text": text, "quick_replies": []}


def handle_symptom_check(user, entities, language, raw_text):
    facility = store.facility_for_district(user.get("district"))
    return {"text": _s("symptom_generic", language, facility=facility["name"], phone=facility["phone"]),
            "quick_replies": ["Talk to helpline", "Nearest facility"]}


def handle_human_handoff(user, entities, language, raw_text):
    facility = store.facility_for_district(user.get("district"))
    prefix = ""
    if entities.get("red_flag"):
        prefix = ("⚠️ This sounds urgent. " if language == "en"
                  else "⚠️ यह गंभीर लग रहा है। ")
    return {"text": prefix + _s("handoff", language, facility=facility["name"], phone=facility["phone"]),
            "quick_replies": []}


def handle_fallback(user, entities, language, raw_text):
    return {"text": _s("fallback", language), "quick_replies": [
        "Vaccination status", "Check symptoms", "Outbreak alerts", "Talk to helpline"
    ]}


HANDLERS = {
    "greeting": handle_greeting,
    "vaccination_query": handle_vaccination_query,
    "outbreak_alert_query": handle_outbreak_alert_query,
    "faq": handle_faq,
    "misinformation_check": handle_misinformation_check,
    "symptom_check": handle_symptom_check,
    "human_handoff": handle_human_handoff,
    None: handle_fallback,
}


def route(intent, user, entities, language, raw_text):
    handler = HANDLERS.get(intent, handle_fallback)
    return handler(user, entities, language, raw_text)
