"""NIVEL-2 content policy - prompt injection, jailbreak, refusal evasion.

Implementacao de V5 guarda-em-camadas §4 + ajustes Security carimbados via V5
cross-security-resposta (`aprovada-com-mitigacao-revisada`):

- Ajuste #2: threshold prompt injection mantido em zero-tolerance regex; gatilho
  explicito de reavaliacao adicionado quando volume rolling 30d >= 5.000 calls
  OR mudanca surface area (RAG / agent / usuario externo). Reavaliacao via novo
  handoff AI -> Security.
- Ajuste #3: categoria adicional jailbreak "Privilegio escalado" (admin supremo
  / modo root / super usuario interno / override admin / bypass RBAC / ignore
  minhas permissoes). Threshold zero-tolerance.
- Ajuste #7: refusal evasion check como defesa em profundidade. Padroes EN +
  PT-BR ("Sure, here's how to" / "Of course! Here's how" / "Claro, aqui esta
  como" / "Certamente, segue como" / "Posso te ajudar com isso. Primeiro,").

Cobertura zero-tolerance: 1+ match -> bloqueio HTTP 422 com reason enumerada +
audit + alerta. False-positive rate aceitavel em contexto interno restrito a
~10 lojas + operadores nominados (parecer V5 §4.3 + carimbo Security #2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ContentPolicyCategory(StrEnum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    REFUSAL_EVASION = "refusal_evasion"


@dataclass(frozen=True, slots=True)
class ContentPolicyMatch:
    category: ContentPolicyCategory
    pattern_id: str
    matched_substring: str


# Prompt injection direta - 6 padroes canonical V5 §4.1.
_PROMPT_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ignore_instructions",
        re.compile(
            r"ignore\s+(?:as\s+|the\s+|all\s+)?(?:instru[cç][oõ]es|instructions|"
            r"above|previous(?:\s+instructions)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "reveal_system_prompt",
        re.compile(
            r"(?:reveal|mostre?|exiba|imprima|show)\s+(?:your\s+|the\s+|seu\s+|o\s+)?"
            r"(?:system\s+)?prompt",
            re.IGNORECASE,
        ),
    ),
    (
        "forget_instructions",
        re.compile(
            r"(?:forget|esque[cç]a)\s+(?:everything|tudo|your\s+instructions|"
            r"suas\s+instru[cç][oõ]es)",
            re.IGNORECASE,
        ),
    ),
    (
        "act_as_unrestricted",
        re.compile(
            r"act\s+as\s+(?:an?\s+)?(?:unrestricted|jailbroken|unfiltered)\s+ai|"
            r"finja\s+ser\s+(?:uma\s+)?ia\s+sem\s+restri[cç][oõ]es",
            re.IGNORECASE,
        ),
    ),
    (
        "override_safety",
        re.compile(
            r"override\s+(?:your\s+)?safety|desative\s+(?:suas\s+|as\s+)?prote[cç][oõ]es|"
            r"disable\s+(?:your\s+)?safety",
            re.IGNORECASE,
        ),
    ),
    (
        "bypass_guardrails",
        re.compile(
            r"bypass\s+(?:your\s+|the\s+)?(?:guardrails?|guard\s*rails?|filters?)|"
            r"contornar?\s+(?:seus\s+)?guardrails?",
            re.IGNORECASE,
        ),
    ),
)

# Jailbreak - 5 categorias canonical V5 §4.2 + 1 categoria adicional Security
# ajuste #3 ("Privilegio escalado").
_JAILBREAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "dan_persona",
        re.compile(
            r"you\s+are\s+(?:now\s+)?dan\b|voc[eê]\s+(?:agora\s+)?[eé]\s+dan\b|"
            r"do\s+anything\s+now",
            re.IGNORECASE,
        ),
    ),
    (
        "grandmother_trick",
        re.compile(
            r"(?:my\s+)?grandmother\s+used\s+to\s+tell\s+me\s+bedtime\s+stories|"
            r"minha\s+av[oó]\s+(?:me\s+)?contava\s+hist[oó]rias",
            re.IGNORECASE,
        ),
    ),
    (
        "hypothetical_no_ethics",
        re.compile(
            r"in\s+a\s+(?:fictional|hypothetical)\s+(?:story|scenario)\s+where\s+"
            r"(?:ethics|safety)\s+(?:don'?t\s+matter|are\s+disabled)|"
            r"em\s+uma\s+hist[oó]ria\s+ficcional\s+sem\s+[eé]tica",
            re.IGNORECASE,
        ),
    ),
    (
        "malicious_roleplay",
        re.compile(
            r"pretend\s+you\s+are\s+(?:an?\s+)?ai\s+without\s+safety|"
            r"finja\s+ser\s+(?:uma\s+)?ia\s+sem\s+(?:[eé]tica|seguran[cç]a)",
            re.IGNORECASE,
        ),
    ),
    (
        "token_smuggling",
        # Heuristica conservadora: blocos base64-like longos (>=24 chars) que
        # comecam por sequencias suspeitas. Cobre tentativa basica de smuggling.
        # False-positive aceitavel em contexto restrito.
        re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
    ),
    (
        "privilege_escalation",
        re.compile(
            r"administrador\s+supremo|modo\s+root|super\s+usu[aá]rio\s+interno|"
            r"override\s+admin|bypass\s+rbac|ignore\s+minhas\s+permiss[oõ]es",
            re.IGNORECASE,
        ),
    ),
)

# Refusal evasion - padroes EN+PT-BR ajuste Security #7.
_REFUSAL_EVASION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "sure_heres_how_to",
        re.compile(r"^\s*sure[,!]?\s+here'?s?\s+how\s+to\b", re.IGNORECASE),
    ),
    (
        "of_course_heres_how",
        re.compile(r"^\s*of\s+course[,!]?\s+here'?s?\s+how\b", re.IGNORECASE),
    ),
    (
        "claro_aqui_esta_como",
        re.compile(r"^\s*claro[,!]?\s+aqui\s+est[aá]\s+como\b", re.IGNORECASE),
    ),
    (
        "certamente_segue_como",
        re.compile(r"^\s*certamente[,!]?\s+segue\s+como\b", re.IGNORECASE),
    ),
    (
        "posso_te_ajudar_primeiro",
        re.compile(r"^\s*posso\s+te\s+ajudar\s+com\s+isso\.\s+primeiro[,]", re.IGNORECASE),
    ),
)


def detect_content_policy_violation(text: str) -> ContentPolicyMatch | None:
    """Run prompt injection + jailbreak detectors over input `text`.

    Zero-tolerance: returns the first match found (any category). Returns None
    if the text passes both detectors. Used by NIVEL-2 pre-egress to block
    HTTP 422 with `reason=content_policy_blocked`.
    """
    for pattern_id, pattern in _PROMPT_INJECTION_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return ContentPolicyMatch(
                category=ContentPolicyCategory.PROMPT_INJECTION,
                pattern_id=pattern_id,
                matched_substring=match.group(0),
            )
    for pattern_id, pattern in _JAILBREAK_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return ContentPolicyMatch(
                category=ContentPolicyCategory.JAILBREAK,
                pattern_id=pattern_id,
                matched_substring=match.group(0),
            )
    return None


def detect_refusal_evasion(output_text: str) -> ContentPolicyMatch | None:
    """Detect refusal evasion in LLM output (NIVEL-1 §3.2 defense in depth).

    Triggered only when a `content_policy_blocked` flag is already raised on
    input, OR as periodic adversarial-set guard. Zero-tolerance match.
    """
    for pattern_id, pattern in _REFUSAL_EVASION_PATTERNS:
        match = pattern.search(output_text)
        if match is not None:
            return ContentPolicyMatch(
                category=ContentPolicyCategory.REFUSAL_EVASION,
                pattern_id=pattern_id,
                matched_substring=match.group(0),
            )
    return None
