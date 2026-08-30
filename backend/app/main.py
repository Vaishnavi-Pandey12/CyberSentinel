from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.mongo import connect_to_mongo, close_mongo_connection, get_database
from app.api.auth import router as auth_router
from app.api.predictions import router as predictions_router
from app.api.locations import router as locations_router
from app.api.alerts import router as alerts_router
from app.api.dashboard import router as dashboard_router
from app.api.cases import router as cases_router
from app.api.complaints import router as complaints_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB Atlas
    await connect_to_mongo()
    app.mongodb = get_database()
    yield
    # Shutdown: Close MongoDB connection
    await close_mongo_connection()

app = FastAPI(
    title="CyberSentinel API",
    description="Backend API for SIH — Threat Risk Prediction & GIS Heatmap",
    version="1.0.0",
    lifespan=lifespan
)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(predictions_router, prefix=API_PREFIX)
app.include_router(locations_router, prefix=API_PREFIX)
app.include_router(alerts_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(cases_router, prefix=API_PREFIX)
app.include_router(complaints_router, prefix=API_PREFIX)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok"
    }

@app.get("/", tags=["Health"])
def root_health_check():
    return {
        "system": "CyberSentinel Backend",
        "status": "online",
        "message": "API with MongoDB Atlas connected"
    }

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    from app.config import settings
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.backend_port, reload=True)