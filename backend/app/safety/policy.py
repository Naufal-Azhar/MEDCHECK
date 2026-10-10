"""Local preflight rules: refuse personal medical interpretation before inference.

Deliberately conservative, may overblock, and not exhaustive for all paraphrases.
Never use absence of a match as proof that a question is safe.
"""

import re
import unicodedata
from dataclasses import dataclass


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    return re.sub(r"\s+", " ", text).strip()


def _personal_decision(text: str) -> bool:
    # Remove only conversational request markers, never the remainder of the
    # message: "explain X to me. I have symptoms" must still be blocked.
    text = re.sub(r"\bto me\b", "", text)
    text = re.sub(r"\b(?:tell|show|teach) me\b", "explain", text)
    text = re.sub(r"\b(?:can|could|would) you help me (?:understand|learn about)\b", "explain", text)
    # Personal/third-party case descriptions: stay educational rather than deciding
    # whether the described person has a condition. Broad by design for this MVP.
    personal = r"\b(i|i'm|i've|me|my|mine|we|our|he|she|his|her|they|their|patient|someone)\b"
    medical = r"\b(symptoms?|diabet\w*|insulin|medicat\w*|medicin\w*|disease|condition|pain|thirst\w*|urina\w*|breath\w*|fever|dose|dosage|pills?|tablets?|metformin|sick|ill|bleed\w*|dizz\w*|vomit\w*|rash|numb\w*|pregnan\w*|chest|doctor|treatment|cancer|blood|antibiotic\w*)\b"
    if re.search(personal, text) and re.search(medical, text):
        return True
    decisions = (
        r"\bdiagnos(?:e|ing)\b", r"\bprescrib(?:e|ing)\b",
        r"\b(?:what|which)\s+(?:dose|dosage|units|mg|tablets|pills)\b",
        r"\b(?:how much|how many)\b.{0,100}\b(?:dose|dosage|units|mg|tablets|pills)\b",
        r"\b(?:should|can|must)\b.{0,60}\b(?:take|inject|stop|increase|decrease|double|wait)\b",
        r"\b(?:tell|give|recommend|calculate)\b.{0,80}\b(?:treatment|medicine|medication|dose|dosage)\b",
        r"\b(?:age[d]?\s*\d+|\d+\s*(?:years? old|year-old|kg))\b.{0,120}\b(?:symptoms?|dose|insulin|pain|diabetes)\b",
    )
    if any(re.search(pattern, text) for pattern in decisions):
        return True
    # Immediate-distress language: generic referral, not diagnosis/triage advice.
    distress = r"\b(chest pain|trouble breathing|difficulty breathing|can't breathe|cannot breathe|unconscious|overdose|severe bleeding)\b"
    immediate = r"\b(now|right now|severe|suddenly|help|emergency|wait|tomorrow)\b"
    return bool(re.search(distress, text) and re.search(immediate, text))


@dataclass(frozen=True)
class SafetyDecision:
    status: str
    reason: str
    message: str


def instruction_attack(text: str) -> bool:
    text = normalize(text)
    return any(re.search(p, text) for p in (
        r"\b(ignore|override|bypass|disregard)\b.{0,80}\b(instructions?|rules?|safety|system|guardrails?)\b",
        r"\b(reveal|print|show|repeat)\b.{0,60}\b(system prompt|api key|secret|credentials?)\b",
        r"\b(invent|fabricate|fake)\b.{0,50}\b(citations?|sources?|evidence)\b",
        r"\b(pretend|act|roleplay)\b.{0,50}\b(doctor|physician|unrestricted)\b",
        r"<\|(?:system|im_start|endoftext)\|>|\[inst\]",
    ))


def screen_question(question: str) -> SafetyDecision | None:
    """Local routing only; not exhaustive triage, language detection, or anonymization."""
    text = normalize(question)
    distress = re.search(r"\b(chest pain|trouble breathing|difficulty breathing|can't breathe|cannot breathe|not breathing|unconscious|unresponsive|overdose|severe bleeding)\b", text)
    immediate = re.search(r"\b(now|severe|suddenly|help|wait|tomorrow|i|my|he|she|child|friend)\b", text)
    if (distress and immediate) or re.search(r"\b(i (?:want|plan|intend) to (?:kill|hurt) myself|i took an overdose)\b", text):
        return SafetyDecision("safety_refusal", "urgent", "This could require urgent care. Contact local emergency services now. Do not wait for an AI response. This assistant cannot assess the situation or replace emergency care.")
    if instruction_attack(text):
        return SafetyDecision("safety_refusal", "instruction_override", "I can explain source-based health information, but cannot bypass safety rules, reveal secrets, or invent evidence. Please ask a general educational question.")
    if re.search(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b(?:mrn|patient id|medical record number|date of birth|dob)\s*[:#=]|\b\d{3}-\d{2}-\d{4}\b", text):
        return SafetyDecision("privacy_refusal", "personal_identifiers", "Please remove identifying information and medical records, then ask a general health question. This assistant is for public educational information.")
    if _personal_decision(text) or any(re.search(p, text) for p in (
        r"\b(?:do|could|might|can) i have\b", r"\b(?:what|which) (?:disease|condition) (?:is this|do i have)\b",
        r"\b(?:my|his|her|your) (?:lab|test|scan|results?|symptoms?)\b",
        r"\b(?:start|stop|double|halve|increase|decrease|switch)\b.{0,50}\b(?:dose|medication|insulin|metformin|antibiotics?)\b",
    )):
        return SafetyDecision("safety_refusal", "personal_medical_decision", "I cannot diagnose, prescribe, interpret a person's symptoms or tests, or recommend a personal dose. Ask a qualified healthcare professional. You can ask about general health terminology instead.")
    if re.fullmatch(r"(?:is (?:it|this|that) safe|what (?:is|does) (?:it|this|that)(?: mean)?|help|what should i do)[?.! ]*", text):
        return SafetyDecision("clarification_needed", "ambiguous", "Which health topic or term would you like explained? Please ask a specific general question without personal details.")
    return None


def requires_refusal(question: str) -> bool:
    """Compatibility wrapper for existing scripts; any blocked route makes no AI call."""
    return screen_question(question) is not None


def unsafe_output(text: str) -> bool:
    text = normalize(text)
    return instruction_attack(text) or bool(re.search(
        r"(?<!if )\byou (?:definitely |certainly )?(?:have|suffer from)\b|"
        r"\b(?:take|inject|swallow)\s+\d|\b(?:stop|double|increase|decrease) your\b|"
        r"\b(?:do not|don't|no need to) (?:call|seek|go to)\b|\bwait until tomorrow\b", text))
