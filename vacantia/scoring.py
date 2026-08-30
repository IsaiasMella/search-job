"""Scoring de ofertas 0-100 contra el CV.

Extraído de la lógica de scoring de autopilot-jobhunt/job_hunt/scanner.py, pero
separado del descubrimiento: acá entra una lista de `Job` (venga de la fuente
que venga) y sale la misma lista con score, stack, reason y worth_applying.
"""

import json
import time

from vacantia.llm import chat_with_llm, has_llm_credentials
from vacantia.log import get_logger
from vacantia.models import Job

logger = get_logger()

# Lotes de 6, no de 10: cada oferta ahora pide 5 campos extra para los filtros
# y con 10 la respuesta se pasaba de max_tokens y volvía cortada a la mitad.
SCORE_BATCH_SIZE = 6
# Techo de salida. Los modelos free de OpenRouter admiten mucho más (nemotron
# llega a 235k), el 4096 por defecto de llm.py era lo que truncaba.
SCORE_MAX_TOKENS = 8192
# Pausa entre lotes. Los planes gratis limitan por MINUTO (Gemini 5-15 req/min,
# OpenRouter 20), y con max_new_per_run alto o muchas empresas nuevas una
# corrida puede mandar varios lotes seguidos. Cinco segundos alcanzan para no
# rozar el techo y no se notan en una corrida que tarda minutos.
# Se puede ajustar con "llm": {"batch_delay": N} en el perfil.
SCORE_BATCH_DELAY = 5.0

SCORE_PROMPT = """You are evaluating job postings for a candidate. Output ONLY a JSON array, no other text.

CANDIDATE:
{candidate_profile}

RESUME SUMMARY:
{resume_summary}

JOBS TO SCORE:
{jobs_text}

For each job output:
{{
  "job_number": 1,
  "score": 0-100,
  "title": "extracted job title",
  "stack": "key tech from JD (comma-separated, max 6 items)",
  "location_remote": "location + remote policy",
  "reason": "one sentence why this fits or doesn't fit the candidate",
  "worth_applying": true/false,
  "country": "country of the job, in Spanish (e.g. Argentina, España, Italia)",
  "city": "city of the job",
  "work_mode": "remote | hybrid | onsite",
  "posting_language": "ISO 639-1 code of the language the posting is WRITTEN in (es, en, pt...)",
  "english_level": "CEFR level of English the job REQUIRES (A1, A2, B1, B2, C1, C2)",
  "requires_english": true/false
}}

CRITICAL — the last five fields are used to filter jobs out, so a wrong guess
silently discards a good job. Use "" (empty string) whenever the posting does
not clearly state it. Do NOT infer:
- country/city: "" if the posting doesn't name a location. The job Title, URL
  and Content ARE part of the posting, so a location named there is reliable
  ("Bologna Senior Python Developer" -> city Bologna, country Italia). What you
  must NOT do is infer a location from the company's headquarters or from the
  language the posting is written in.
- work_mode: "" unless the posting actually says remote/hybrid/onsite. A posting
  that never mentions the arrangement is "", not "onsite".
- english_level: "" if no English requirement is stated. Only give a level when
  the posting asks for English. Map wording to CEFR: "basic"=A2,
  "intermediate"/"upper intermediate"=B1, "advanced"=C1, "fluent"/"native"=C2.
  A posting merely WRITTEN in English is not an English requirement.
- posting_language: the language of the text itself, not the required language.
- requires_english: this one is a JUDGEMENT, not an extraction, so answer it even
  when the posting is vague. true if someone who speaks NO English at all would
  be rejected or unable to do the job day to day (explicit English requirement,
  international/English-speaking team, English-speaking clients). false if the
  job can plausibly be done entirely in the local language. Being written in
  English is itself weak evidence of true, but not proof.

Scoring: 80-100 near-perfect; 60-79 good fit; 40-59 partial; <40 poor.
Set worth_applying=true only if score >= {min_score}.
Include ALL jobs. Output ONLY the JSON array."""


def build_candidate_profile(profile: dict) -> str:
    cand = profile.get("candidate", {})
    lines = [f"- {cand.get('name', 'el candidato')}"]
    for key, label in (
        ("profile", None),
        ("seeking", "Seeking"),
        ("not_suitable", "NOT suitable"),
    ):
        val = cand.get(key)
        if val:
            lines.append(f"- {label + ': ' if label else ''}{val}")
    keywords = profile.get("keywords") or []
    if keywords:
        lines.append(f"- Keywords of interest: {', '.join(keywords)}")
    return "\n".join(lines)


_EMPTY_VALUES = {"", "n/a", "na", "none", "null", "unknown", "not specified",
                 "no especificado", "-", "?"}


def _clean(value) -> str:
    """Normaliza a "" los muchos modos en que un LLM dice 'no sé'."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in _EMPTY_VALUES else text


def _jobs_text(jobs: list[Job]) -> str:
    # OJO: no se le pasa `j.location` a proposito. Ese campo sale de
    # companies.json y describe la sede de la *empresa*, no el puesto:
    # Globant publica ofertas de Bologna y Pune bajo una entrada que dice
    # "Buenos Aires". Cuando estaba en el prompt el LLM lo copiaba tal cual
    # y extraia "Argentina" para todas. Pais y ciudad salen del aviso.
    return "\n\n".join(
        f"JOB {i + 1}:\nCompany: {j.company}\n"
        f"Title: {j.title}\nURL: {j.url}\n"
        f"Content:\n{j.description[:2500]}"
        for i, j in enumerate(jobs)
    )


def _parse_scored_array(raw: str) -> list[dict]:
    """Parsea el array JSON del LLM, tolerando respuestas cortadas.

    Si la respuesta se pasa de max_tokens vuelve sin el ']' final y un
    json.loads del bloque entero falla, tirando a la basura las ofertas que sí
    habían llegado completas. Acá, si el parseo limpio falla, rescatamos los
    objetos {...} que hayan quedado bien cerrados.
    """
    start = raw.find("[")
    if start == -1:
        raise ValueError("el LLM no devolvió un array JSON")

    end = raw.rfind("]")
    if end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass  # cortada o con basura al final -> rescatamos lo que se pueda

    salvaged, depth, obj_start, in_str, esc = [], 0, None, False, False
    for i, ch in enumerate(raw[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    salvaged.append(json.loads(raw[obj_start : i + 1]))
                except json.JSONDecodeError:
                    pass
                obj_start = None

    if not salvaged:
        raise ValueError("el LLM no devolvió ningún objeto JSON completo")
    logger.warning(
        f"  Respuesta del LLM incompleta — rescaté {len(salvaged)} oferta(s) puntuadas"
    )
    return salvaged


def _score_batch_with_llm(jobs: list[Job], resume: str, profile: dict, min_score: int) -> list[Job]:
    prompt = SCORE_PROMPT.format(
        candidate_profile=build_candidate_profile(profile),
        resume_summary=resume[:2500],
        jobs_text=_jobs_text(jobs),
        min_score=min_score,
    )

    logger.debug(f"  Puntuando {len(jobs)} oferta(s) con LLM (min_score={min_score})...")
    t0 = time.time()
    raw = chat_with_llm(
        profile.get("llm", {}),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=SCORE_MAX_TOKENS,
    )
    scored = _parse_scored_array(raw)
    logger.debug(f"  Scoring listo en {time.time() - t0:.1f}s — {len(scored)} resultados")

    for item in scored:
        idx = item.get("job_number", 0) - 1
        if not (0 <= idx < len(jobs)):
            continue
        job = jobs[idx]
        job.score = int(item.get("score", 0) or 0)
        job.scored_title = item.get("title", "") or job.title
        job.stack = item.get("stack", "")
        job.location_remote = item.get("location_remote", "") or job.location
        job.reason = item.get("reason", "")
        job.worth_applying = bool(item.get("worth_applying", job.score >= min_score))
        # Campos de filtrado. Se normalizan acá para que filters.py reciba
        # siempre "" cuando el aviso no dice nada (el LLM a veces manda null,
        # "N/A" o "unknown" en vez de la cadena vacía que le pedimos).
        # `or` y no asignación directa: si la fuente ya trajo el dato
        # estructurado (LinkedIn devuelve is_remote y location como campos
        # propios), ese vale más que lo que el LLM deduzca del texto.
        job.country = job.country or _clean(item.get("country"))
        job.city = job.city or _clean(item.get("city"))
        job.work_mode = job.work_mode or _clean(item.get("work_mode")).lower()
        job.posting_language = _clean(item.get("posting_language")).lower()[:2]
        job.english_level = _clean(item.get("english_level")).upper()[:2]
        req = item.get("requires_english")
        job.requires_english = bool(req) if isinstance(req, bool) else None
        logger.debug(f"    [{job.score:3d}] {job.display_title} — {job.reason[:80]}")

    return jobs


def _heuristic_score(job: Job, keywords: list[str], resume_words: set[str]) -> tuple[int, list[str]]:
    """Puntaje por solapamiento de keywords. Puro: no toca el Job.

    Se usa en dos lugares: como scoring de respaldo cuando no hay LLM, y como
    triaje gratuito para decidir a cuáles vale la pena gastarles una llamada.
    """
    haystack = f"{job.title} {job.description} {job.company}".lower()
    hits = [k for k in keywords if k in haystack]

    # Puntaje saturante, no proporcional: pedir que una oferta contenga *todas*
    # las keywords del perfil condenaría a cero a cualquiera que liste muchas.
    # Cada acierto suma y a partir del tercero satura.
    kw_score = 35.0 + min(len(hits), 3) * 15.0
    overlap = sum(1 for w in set(haystack.split()) if w in resume_words)
    resume_score = min(overlap / 25, 1.0) * 20
    return min(int(round(kw_score + resume_score)), 100), hits


def triage(jobs: list[Job], resume: str, profile: dict) -> tuple[list[Job], list[Job]]:
    """Reparte las ofertas nuevas entre "puntuar ahora" y "dejar para después".

    Existe para el pico de backfill: cuando cargás 20 empresas nuevas o cambiás
    los search_terms, entran cientos de ofertas de una y eso son decenas de
    llamadas al LLM en una sola corrida. El dedupe no ayuda porque son
    genuinamente nuevas.

    El triaje es gratis (keywords en Python, cero API) y ordena por lo que más
    pinta. Las diferidas NO se marcan como vistas, así que vuelven en la
    próxima corrida y el backlog se drena de a tandas.
    """
    limit = profile.get("max_new_per_run")
    if not limit or len(jobs) <= int(limit):
        return jobs, []

    limit = int(limit)
    keywords = [k.lower() for k in (profile.get("keywords") or []) if k]
    resume_words = {w for w in resume.lower().split() if len(w) > 3}

    ranked = sorted(
        jobs, key=lambda j: _heuristic_score(j, keywords, resume_words)[0], reverse=True
    )
    ahora, despues = ranked[:limit], ranked[limit:]
    logger.info(
        f"Triaje: {len(jobs)} nuevas supera el máximo de {limit} por corrida — "
        f"puntúo las {len(ahora)} más prometedoras, dejo {len(despues)} para la próxima"
    )
    return ahora, despues


def _score_batch_heuristic(jobs: list[Job], resume: str, profile: dict, min_score: int) -> list[Job]:
    """Scoring sin LLM: solapamiento de keywords entre el perfil/CV y la oferta.

    No pretende reemplazar al LLM — existe para que el pipeline corra completo
    sin credenciales (primera corrida, CI, debug de fuentes nuevas).
    """
    keywords = [k.lower() for k in (profile.get("keywords") or []) if k]
    resume_words = {w for w in resume.lower().split() if len(w) > 3}

    for job in jobs:
        job.score, hits = _heuristic_score(job, keywords, resume_words)
        job.scored_title = job.title
        job.stack = ", ".join(hits[:6])
        job.location_remote = job.location
        job.reason = (
            f"[heurística, sin LLM] {len(hits)}/{len(keywords) or '?'} keywords del perfil"
            f"{': ' + ', '.join(hits[:4]) if hits else ''}"
        )
        job.worth_applying = job.score >= min_score
        logger.debug(f"    [{job.score:3d}] {job.display_title} — {job.reason[:80]}")

    return jobs


def score_jobs(jobs: list[Job], resume: str, profile: dict) -> list[Job]:
    """Puntúa en lotes. Nunca levanta: si el LLM falla, cae a la heurística."""
    if not jobs:
        return []

    min_score = int(profile.get("min_score", 60))
    use_llm = has_llm_credentials(profile.get("llm", {}))
    if not use_llm:
        logger.warning(
            "Sin credenciales de LLM (OPENROUTER_API_KEY) — usando scoring heurístico por keywords."
        )

    demora = float((profile.get("llm") or {}).get("batch_delay", SCORE_BATCH_DELAY))
    out: list[Job] = []
    for i in range(0, len(jobs), SCORE_BATCH_SIZE):
        batch = jobs[i: i + SCORE_BATCH_SIZE]
        if use_llm:
            if i and demora > 0:
                logger.debug(f"  Espero {demora:.0f}s entre lotes (límite por minuto)")
                time.sleep(demora)
            try:
                out.extend(_score_batch_with_llm(batch, resume, profile, min_score))
                continue
            except Exception as e:
                logger.error(f"  Falló el scoring con LLM ({e}) — caigo a la heurística en este lote")
        out.extend(_score_batch_heuristic(batch, resume, profile, min_score))

    return sorted(out, key=lambda j: j.score or 0, reverse=True)


def filter_by_min_score(jobs: list[Job], min_score: int, top_n: int | None = None) -> list[Job]:
    passing = [j for j in jobs if (j.score or 0) >= min_score and j.worth_applying is not False]
    passing.sort(key=lambda j: j.score or 0, reverse=True)
    return passing[:top_n] if top_n else passing
