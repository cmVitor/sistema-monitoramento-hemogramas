from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import create_tables, get_db
from app.routers import observations, subscriptions, alerts
from config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Sistema de Monitoramento de Hemogramas para detecção de surtos infecciosos"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(observations.router)
app.include_router(subscriptions.router)
app.include_router(alerts.router)

@app.on_event("startup")
async def startup_event():
    create_tables()

@app.get("/")
async def root():
    return {
        "message": "Sistema de Monitoramento de Hemogramas",
        "version": settings.version
    }

@app.get("/health")
async def health_check(db = Depends(get_db)):
    try:
        # Testar conexão com banco
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)