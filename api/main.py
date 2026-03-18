from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.elasticsearch import close_es_client
from api.routes import logs, stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_es_client()


app = FastAPI(
    title="Log Analytics Engine",
    description="Distributed log ingestion, search, and anomaly detection",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router)
app.include_router(stream.router)


@app.get("/health")
async def health():
    return {"status": "ok"}