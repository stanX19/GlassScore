import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database import close_pools
import src.routes
from src import config  # Import config to load environment variables

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_pools()

app = FastAPI(
    title="GlassScore Core System API",
    version="v1",
    description="API for the GlassScore Core System",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    print("Root endpoint called")
    try:
        return {"message": "GlassScore API is running"}
    except Exception as e:
        print(f"Error in root: {e}")
        raise

@app.get("/healthz")
async def health_check():
    return {"status": "healthy", "service": "GlassScore API"}

app.include_router(src.routes.router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000))
    )