from __future__ import annotations
import os
import uvicorn
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from .db import Base, engine, get_session, SessionLocal 
from .routes import router
from .seed import seed_pipelines
from .retry_worker import start_retry_worker

app = FastAPI(title="Orchestrator Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# def on_startup():
#     Base.metadata.create_all(bind=engine)
#     with get_session() as db:
#         seed_pipelines(db)
#     start_retry_worker()

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed_pipelines(db)
    finally:
        db.close()


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or os.urandom(8).hex()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"ready": True}

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8002)), reload=True)
