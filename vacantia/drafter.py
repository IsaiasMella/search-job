"""Genera CV y carta de presentación a medida de una oferta.

Adaptado de autopilot-jobhunt/job_hunt/drafter.py, reescrito contra el perfil
multi-persona y el estado por perfil de vacantia.

    python -m vacantia.drafter --profile isaias --job 1
    python -m vacantia.drafter --profile isaias --job https://...

La descarga de la descripción usa TinyFish si hay API key; si no, usa el texto
que ya quedó guardado en state/<perfil>/last_run.json durante la corrida.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from vacantia.config import load_profile, load_resume, resolve_secret
from vacantia.llm import chat_with_llm, has_llm_credentials
from vacantia.log import get_logger
from vacantia.state import State

logger = get_logger()

OUTPUT_DIR = Path("output")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "empresa"


def _load_last_run(profile_name: str) -> list[dict]:
    path = State(profile_name).last_run_file
    if not path.exists():
        raise FileNotFoundError(
            f"No hay resultados en {path}. Corré primero: python -m vacantia.run --profile {profile_name}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_job(profile_name: str, job_ref: str) -> dict:
    if job_ref.startswith("http"):
        return {"url": job_ref, "company": "empresa", "description": ""}

    jobs = _load_last_run(profile_name)
    idx = int(re.sub(r"\D", "", job_ref) or 0) - 1
    if not (0 <= idx < len(jobs)):
        raise ValueError(f"La oferta #{idx + 1} no está en la última corrida ({len(jobs)} ofertas)")
    job = jobs[idx]
    logger.debug(f"Oferta #{idx + 1}: '{job.get('title')}' @ {job.get('company')} — {job.get('url')}")
    return job


def _fetch_description(profile: dict, job: dict) -> str:
    """Descarga la JD con TinyFish; si no se puede, usa la que ya tenemos."""
    cached = job.get("description") or ""
    tinyfish_cfg = next(
        (s for s in profile.get("sources", []) if s.get("type") == "careers"), {}
    )
    api_key = resolve_secret(
        tinyfish_cfg.get("api_key"), tinyfish_cfg.get("api_key_env", "TINYFISH_API_KEY")
    )
    if not api_key:
        logger.warning("Sin TINYFISH_API_KEY — uso la descripción guardada en el estado.")
        return cached

    try:
        from tinyfish import TinyFish

        resp = TinyFish(api_key=api_key).fetch.get_contents([job["url"]], format="markdown")
        if resp.results and resp.results[0].text:
            text = resp.results[0].text
            logger.info(f"JD descargada: {len(text)} chars")
            return text
        logger.warning("TinyFish no devolvió texto — uso la descripción guardada.")
    except ImportError:
        logger.warning("Falta el paquete 'tinyfish' — uso la descripción guardada.")
    except Exception as e:
        logger.warning(f"No pude descargar la JD ({e}) — uso la descripción guardada.")
    return cached


def draft(profile: dict, job_ref: str) -> Path:
    profile_name = profile.get("name", "?")
    if not has_llm_credentials(profile.get("llm", {})):
        raise RuntimeError(
            "El drafter necesita un LLM. Cargá OPENROUTER_API_KEY en el .env "
            "(o poné llm.provider = 'claude_cli' en el perfil)."
        )

    resume = load_resume(profile)
    if not resume:
        raise RuntimeError(f"No encontré el CV en {profile.get('cv_path')}")

    job = _resolve_job(profile_name, job_ref)
    jd = _fetch_description(profile, job)[:4000]
    if not jd:
        raise RuntimeError("No hay descripción de la oferta para trabajar.")

    cand = profile.get("candidate", {})
    candidate_name = cand.get("name", "el candidato")
    relocation_note = cand.get("relocation_note", "")
    company_slug = _slug(job.get("company", "empresa"))

    out_dir = OUTPUT_DIR / profile_name / f"{company_slug}-{datetime.now():%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    llm = profile["llm"]

    logger.info("Adaptando el CV...")
    resume_md = chat_with_llm(
        llm,
        messages=[{"role": "user", "content": f"""Rewrite the resume below to mirror the language and emphasized skills in this job description.

Rules:
- Keep every fact truthful — do NOT invent experience
- Mirror JD terminology where the candidate genuinely has that experience
- Reorder projects/bullets to surface most relevant experience first
- Keep the same section structure
- Write in the same language as the job description
- Output full resume in Markdown

JOB DESCRIPTION:
{jd}

ORIGINAL RESUME:
{resume}

Output ONLY the tailored resume in Markdown. No preamble."""}],
        temperature=0.2,
    )
    (out_dir / f"cv_{company_slug}.md").write_text(resume_md, encoding="utf-8")
    logger.info(f"  Guardado: {out_dir / f'cv_{company_slug}.md'} ({len(resume_md)} chars)")

    logger.info("Escribiendo la carta...")
    relocation_line = f"- {relocation_note}" if relocation_note else ""
    cover_md = chat_with_llm(
        llm,
        messages=[{"role": "user", "content": f"""Write a one-page cover letter for {candidate_name} applying to this role.

Rules:
- Open with one specific reason this role fits {candidate_name} (reference something concrete in the JD)
- Paragraph 1: most relevant experience (2-3 sentences)
- Paragraph 2: why this company specifically (not generic)
- Close: clear ask for an interview
- Tone: direct and confident, not obsequious
- Write in the same language as the job description
{relocation_line}
- Do NOT use: "I am excited to apply", "I am a team player", "I am passionate about"

JOB DESCRIPTION:
{jd}

CANDIDATE RESUME:
{resume[:2500]}

Output ONLY the cover letter. No preamble."""}],
        temperature=0.3,
    )
    (out_dir / f"carta_{company_slug}.md").write_text(cover_md, encoding="utf-8")
    logger.info(f"  Guardado: {out_dir / f'carta_{company_slug}.md'} ({len(cover_md)} chars)")

    logger.info("Extrayendo datos de postulación...")
    info_txt = chat_with_llm(
        llm,
        messages=[{"role": "user", "content": f"""Extract from this job posting (plain text output, clear labels):

1. Application URL or email
2. Hiring manager / recruiter name (if mentioned)
3. Contact for questions (if mentioned)
4. Application deadline (if mentioned)
5. Key requirements (bullet list, max 8 items)
6. Nice-to-have skills (bullet list, max 5 items)

JOB DESCRIPTION:
{jd}"""}],
        temperature=0.1,
    )
    (out_dir / "datos_postulacion.txt").write_text(
        f"Fuente: {job['url']}\n\n{info_txt}", encoding="utf-8"
    )

    logger.info(f"\nTodo en: {out_dir.resolve()}")
    logger.info("Revisá, editá y mandá a mano.")
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m vacantia.drafter",
        description="Genera CV y carta a medida de una oferta de la última corrida.",
    )
    parser.add_argument("--profile", "-p", required=True, help="Perfil en profiles/")
    parser.add_argument(
        "--job", "-j", required=True, help="Número de la última corrida (ej: 1) o una URL"
    )
    args = parser.parse_args(argv)

    try:
        draft(load_profile(args.profile), args.job)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        logger.error(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
