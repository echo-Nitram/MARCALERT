from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.marcas import router as marcas_router
from app.api.alertas import router as alertas_router
from app.api.boletines import router as boletines_router
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas si no existen (en producción usar Alembic)
    Base.metadata.create_all(bind=engine)

    # Iniciar scheduler
    from app.services.ingest.scheduler import create_scheduler
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(
    title="MARCALERT",
    description="SaaS de vigilancia de marcas para Uruguay — DNPI/MIEM",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://app.marcalert.uy"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(marcas_router)
app.include_router(alertas_router)
app.include_router(boletines_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "marcalert"}
