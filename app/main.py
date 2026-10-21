"""API HTTP do LegisUrb."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import APP_TITLE, APP_VERSION, DISCLAIMER, SEED_ON_STARTUP, STATIC_DIR
from app.db import SessionLocal, get_db, init_db
from app.engine.analyze import analyze
from app.models import City, Parameter, Project, Question, Rule, Source, Zone
from app.schemas import AnalyzeRequest, ProjectCreate
from app.seed.loader import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if SEED_ON_STARTUP:
        db = SessionLocal()
        try:
            seed_all(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=(
        "Consulta de parametros de ocupacao do solo (CA, TO, recuos, gabarito, permeabilidade) "
        "conforme a legislacao urbanistica do municipio, com indicacao do artigo aplicavel."
    ),
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _city_payload(city: City, db: Session, full: bool = False) -> dict[str, Any]:
    zones = db.query(Zone).filter(Zone.city_id == city.id).order_by(Zone.ord).all()
    questions = db.query(Question).filter(Question.city_id == city.id).order_by(Question.ord).all()
    sources = db.query(Source).filter(Source.city_id == city.id).all()

    payload: dict[str, Any] = {
        "slug": city.slug,
        "name": city.name,
        "uf": city.uf,
        "ibge": city.ibge,
        "description": city.description,
        "is_demo": city.is_demo,
        "zone_selection": {
            "method": city.zone_selection_method,
            "hint": city.zone_selection_hint,
            "helper_url": city.zone_selection_helper_url,
        },
        "zones": [
            {
                "code": z.code,
                "name": z.name,
                "group": z.group_name,
                "description": z.description,
            }
            for z in zones
        ],
        "questions": [
            {
                "key": q.key,
                "label": q.label,
                "type": q.type,
                "required": q.required,
                "options": q.options,
                "help": q.help_text,
                "unit": q.unit,
                "default": q.default_value if q.default_value is not None else q.default_text,
            }
            for q in questions
            if q.is_fact and q.type != "derived"
        ],
        "sources": [
            {
                "key": s.key,
                "kind": s.kind,
                "number": s.number,
                "year": s.year,
                "title": s.title,
                "url": s.url,
                "consolidated_as_of": s.consolidated_as_of,
                "retrieved_at": s.retrieved_at,
                "notes": s.notes,
            }
            for s in sources
        ],
        "disclaimer": DISCLAIMER,
    }

    if full:
        params = db.query(Parameter).filter(Parameter.city_id == city.id).all()
        by_zone: dict[int, list[Parameter]] = {}
        for p in params:
            by_zone.setdefault(p.zone_id, []).append(p)
        payload["zones"] = [
            {
                "code": z.code,
                "name": z.name,
                "group": z.group_name,
                "description": z.description,
                "parameters": [
                    {
                        "key": p.key,
                        "label": p.label,
                        "unit": p.unit,
                        "value": p.value_num if p.value_num is not None else p.value_text,
                        "basis": p.basis,
                        "notes": p.notes,
                        "check": p.check_spec,
                        "alternatives": p.alternatives,
                    }
                    for p in by_zone.get(z.id, [])
                ],
            }
            for z in zones
        ]
        rules = db.query(Rule).filter(Rule.city_id == city.id).order_by(Rule.ord).all()
        payload["rules"] = [
            {
                "code": r.code,
                "title": r.title,
                "message": r.message,
                "severity": r.severity,
                "when": r.when,
                "applies_to_zones": r.applies_to_zones,
                "exclude_zones": r.exclude_zones,
                "effects": r.effects,
                "basis": r.basis,
            }
            for r in rules
        ]
    return payload


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": APP_VERSION}


# Atalho de health check (padrao de orquestradores e probes)
@app.get("/health", include_in_schema=False)
@app.get("/healthz", include_in_schema=False)
def health_alias() -> dict[str, Any]:
    return health()


@app.get("/api/cities")
def list_cities(db: Session = Depends(get_db)) -> dict[str, Any]:
    cities = db.query(City).order_by(City.name).all()
    return {
        "items": [
            {
                "slug": c.slug,
                "name": c.name,
                "uf": c.uf,
                "description": c.description,
                "is_demo": c.is_demo,
                "zone_selection_method": c.zone_selection_method,
            }
            for c in cities
        ]
    }


@app.get("/api/cities/{slug}")
def get_city(slug: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    city = db.query(City).filter(City.slug == slug).one_or_none()
    if city is None:
        raise HTTPException(status_code=404, detail="Cidade nao encontrada")
    return _city_payload(city, db, full=True)


@app.post("/api/analyze")
def run_analysis(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    city = db.query(City).filter(City.slug == payload.city).one_or_none()
    if city is None:
        raise HTTPException(status_code=404, detail="Cidade nao encontrada")

    zones = db.query(Zone).filter(Zone.city_id == city.id).order_by(Zone.ord).all()
    questions = db.query(Question).filter(Question.city_id == city.id).order_by(Question.ord).all()
    rules = db.query(Rule).filter(Rule.city_id == city.id).order_by(Rule.ord).all()
    sources = db.query(Source).filter(Source.city_id == city.id).all()

    result = analyze(
        city=city,
        zones=zones,
        questions=questions,
        rules=rules,
        sources=sources,
        answers=payload.answers,
        explicit_zone=payload.zone,
    )
    return result


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)) -> dict[str, Any]:
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return {
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "city_id": p.city_id,
                "zone_id": p.zone_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]
    }


@app.post("/api/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    city = db.query(City).filter(City.slug == payload.city).one_or_none()
    if city is None:
        raise HTTPException(status_code=404, detail="Cidade nao encontrada")
    zones = db.query(Zone).filter(Zone.city_id == city.id).order_by(Zone.ord).all()
    questions = db.query(Question).filter(Question.city_id == city.id).order_by(Question.ord).all()
    rules = db.query(Rule).filter(Rule.city_id == city.id).order_by(Rule.ord).all()
    sources = db.query(Source).filter(Source.city_id == city.id).all()

    result = analyze(
        city=city,
        zones=zones,
        questions=questions,
        rules=rules,
        sources=sources,
        answers=payload.answers,
        explicit_zone=payload.zone,
    )
    zone_id = None
    if result["zone"]:
        zone = (
            db.query(Zone)
            .filter(Zone.city_id == city.id, Zone.code == result["zone"]["code"])
            .one_or_none()
        )
        zone_id = zone.id if zone else None

    project = Project(
        city_id=city.id,
        zone_id=zone_id,
        name=payload.name,
        input_payload=payload.answers,
        result_payload=result,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "name": project.name, "result": result}


@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Analise nao encontrada")
    return {
        "id": project.id,
        "name": project.name,
        "city_id": project.city_id,
        "zone_id": project.zone_id,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "input": project.input_payload,
        "result": project.result_payload,
    }


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Analise nao encontrada")
    db.delete(project)
    db.commit()
    return {"deleted": project_id}
