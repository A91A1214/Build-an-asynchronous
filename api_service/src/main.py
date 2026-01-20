from fastapi import FastAPI
from contextlib import asynccontextmanager
import sys
import os

# Add parent directory to sys.path to import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from api_service.src.routes import router as notification_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic if needed
    yield
    # Shutdown logic if needed

app = FastAPI(title="Notification API", lifespan=lifespan)

app.include_router(notification_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}
