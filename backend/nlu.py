"""
Lightweight rule-based NLU used for the hackathon prototype.

Stands in for a Google Cloud Dialogflow agent (see docs/ARCHITECTURE.md, section 9 —
"Prototype scope vs production scope"). It exposes the same shape of output an actual
Dialogflow webhook fulfillment call would receive: an intent name, a confidence score,
and extracted entities. Swapping this module for a real Dialogflow client later does not
require changing any handler code in handlers.py.
"""
import re

INTENT_KEYWORDS = {
    "greeting": {
        "en": ["hi", "hello", "hey", "start", "namaste"],
        "hi": ["नमस्ते", "हैलो", "शुरू"],
    },
    "vaccination_query": {
        "en": ["vaccine", "vaccination", "dose", "immunization", "immunisation", "jab", "shot", "tika", "vaccinated"],
        "hi": ["टीका", "वैक्सीन", "टीकाकरण", "खुराक"],
    },
    "outbreak_alert_query": {
        "en": ["outbreak", "epidemic", "alert", "cases in", "spreading", "dengue cases", "cholera cases"],
        "hi": ["प्रकोप", "अलर्ट", "फैल रहा", "मामले बढ़"],
    },
    "misinformation_check": {
        "en": ["is it true", "rumor", "rumour", "someone forwarded", "fake news", "myth", "forward said"],
        "hi": ["सच है क्या", "अफवाह", "झूठ है क्या"],
    },
    "human_handoff": {
        "en": ["talk to human", "helpline", "emergency", "real doctor", "speak to agent", "call someone"],
        "hi": ["सहायता चाहिए", "इमरजेंसी", "डॉक्टर से बात"],
    },
    "faq": {
        "en": ["how to prevent", "prevention", "what is", "tell me about", "information on", "how do i avoid"],
        "hi": ["कैसे बचें", "बचाव", "क्या है", "जानकारी दो"],
    },
    "symptom_check": {
        "en": ["fever", "cough", "pain", "sick", "ill", "vomit", "diarrhea", "diarrhoea", "headache", "rash", "symptom"],
        "hi": ["बुखार", "खांसी", "दर्द", "बीमार", "उल्टी", "दस्त", "सिरदर्द"],
    },
}

# Keyword order above matters as a tie-break: more specific intents (misinformation,
# outbreak, vaccination, faq) are checked before the generic symptom_check bucket so a
# message like "is it true fever means dengue" resolves to misinformation_check first.
INTENT_PRIORITY = [
    "greeting",
    "human_handoff",
    "misinformation_check",
    "outbreak_alert_query",
    "vaccination_query",
    "faq",
    "symptom_check",
]

RED_FLAG_SYMPTOMS = [
    "chest pain", "difficulty breathing", "can't breathe", "cannot breathe",
    "unconscious", "seizure", "fits", "severe bleeding", "blue lips",
    "convulsion", "बेहोश", "सांस लेने में दिक्कत", "दौरा",
]

VACCINE_NAMES = [
    "bcg", "opv", "penta", "pentavalent", "rvv", "rotavirus", "mr", "measles",
    "dpt", "hepatitis", "hep b", "covid", "covishield", "covaxin",
]

RELATION_KEYWORDS = {
    "child": ["child", "son", "daughter", "baby", "बेटा", "बेटी", "बच्चे", "बच्चा"],
    "self": ["myself", "me", "मुझे", "मेरा"],
    "elder": ["father", "mother", "elderly", "grandfather", "grandmother", "पिता", "माता", "दादा", "दादी"],
}

DISTRICT_NAMES = ["rampur", "sitapur", "barabanki"]

AGE_RE = re.compile(r"(\d{1,3})\s*(?:years?|yrs?|साल|month|months|महीने|week|weeks|सप्ताह)", re.IGNORECASE)
PINCODE_RE = re.compile(r"\b(\d{6})\b")


def detect_language(text: str) -> str:
    return "hi" if re.search(r"[ऀ-ॿ]", text) else "en"


def _contains_keyword(haystack: str, keyword: str) -> bool:
    """Substring containment with word boundaries, so short keywords like 'hi' don't
    match inside unrelated words like 'child' (a real bug found via manual testing)."""
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return re.search(pattern, haystack, re.IGNORECASE | re.UNICODE) is not None


def classify_intent(text: str):
    lowered = text.lower()
    matched_scores = {}
    for intent in INTENT_PRIORITY:
        kws = INTENT_KEYWORDS[intent]
        hits = sum(1 for kw in kws["en"] if _contains_keyword(lowered, kw))
        hits += sum(1 for kw in kws["hi"] if _contains_keyword(text, kw))
        if hits > 0:
            matched_scores[intent] = hits

    if not matched_scores:
        return None, 0.25  # low confidence -> caller should escalate/fallback

    best_intent = max(matched_scores, key=lambda k: (matched_scores[k], -INTENT_PRIORITY.index(k)))
    confidence = min(0.95, 0.6 + 0.15 * matched_scores[best_intent])
    return best_intent, confidence


def has_red_flag(text: str) -> bool:
    lowered = text.lower()
    return any(_contains_keyword(lowered, flag) or _contains_keyword(text, flag) for flag in RED_FLAG_SYMPTOMS)


def extract_entities(text: str):
    lowered = text.lower()
    entities = {}

    age_match = AGE_RE.search(text)
    if age_match:
        entities["age"] = int(age_match.group(1))

    pin_match = PINCODE_RE.search(text)
    if pin_match:
        entities["pincode"] = pin_match.group(1)

    for district in DISTRICT_NAMES:
        if _contains_keyword(lowered, district):
            entities["district"] = district.capitalize()
            break

    for vaccine in VACCINE_NAMES:
        if _contains_keyword(lowered, vaccine):
            entities["vaccine"] = vaccine
            break

    for relation, kws in RELATION_KEYWORDS.items():
        if any(_contains_keyword(lowered, kw) or _contains_keyword(text, kw) for kw in kws):
            entities["relation"] = relation
            break

    return entities


def analyze(text: str):
    """Single entry point handlers.py uses: returns intent, confidence, entities, language."""
    language = detect_language(text)
    intent, confidence = classify_intent(text)
    entities = extract_entities(text)
    if has_red_flag(text):
        intent = "human_handoff"
        confidence = 0.99
        entities["red_flag"] = True
    return {
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "language": language,
    }
