"""Fuente de ejemplo con ofertas hardcodeadas.

Sirve para probar el pipeline completo (quitar duplicados → scoring → notificación) sin
credenciales de TinyFish. El motor la usa como red de seguridad cuando ninguna
otra fuente está disponible.
"""

from vacantia.log import get_logger
from vacantia.models import Job
from vacantia.sources.base import Source

logger = get_logger()

SAMPLE_JOBS = [
    {
        "url": "https://example.com/jobs/senior-data-scientist-remote",
        "title": "Senior Data Scientist (Remote)",
        "company": "Ejemplo Analytics",
        "location": "Remoto (LATAM/EU)",
        "region": "Remote",
        "description": (
            "Buscamos un/a Senior Data Scientist para trabajar en modelos de "
            "recomendación y forecasting. Stack: Python, SQL, PyTorch, Airflow, "
            "AWS, dbt. Trabajo 100% remoto con reuniones en horario europeo. "
            "Requisitos: 5+ años de experiencia, sólido en estadística, "
            "experiencia poniendo modelos en producción y buen inglés escrito."
        ),
    },
    {
        "url": "https://example.com/jobs/machine-learning-engineer-llm",
        "title": "Machine Learning Engineer — LLM Platform",
        "company": "Ejemplo AI Labs",
        "location": "Barcelona, España / Híbrido",
        "region": "EU",
        "description": (
            "Sumate al equipo de plataforma de LLMs: pipelines de RAG, "
            "fine-tuning, evaluación y despliegue de modelos. Stack: Python, "
            "LangChain, vLLM, Kubernetes, GCP, Terraform. Ofrecemos visa "
            "sponsorship y ayuda de relocación. Se valora experiencia con MLOps "
            "y con sistemas de retrieval en producción."
        ),
    },
    {
        "url": "https://example.com/jobs/junior-frontend-developer",
        "title": "Junior Frontend Developer",
        "company": "Ejemplo Web Studio",
        "location": "Madrid, España / Presencial",
        "region": "EU",
        "description": (
            "Puesto junior para maquetar landings y mantener sitios en "
            "WordPress. Stack: HTML, CSS, jQuery, PHP. Presencial de lunes a "
            "viernes. Sin experiencia previa requerida. Incluido acá a propósito "
            "como caso de mal encaje: debería puntuar bajo."
        ),
    },
]


class DummySource(Source):
    name = "dummy"

    def fetch(self) -> list[Job]:
        jobs = [
            Job(
                url=d["url"],
                title=d["title"],
                company=d["company"],
                source=self.name,
                location=d["location"],
                region=d["region"],
                description=d["description"],
                raw={"fixture": True},
            )
            for d in SAMPLE_JOBS
        ]
        logger.info(f"[dummy] {len(jobs)} oferta(s) de ejemplo")
        return jobs
