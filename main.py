import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from models import Base
from database import engine

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables safely
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown cleanup can go here if needed

# Initialize FastAPI application
app = FastAPI(
    title="AjoChain API",
    description="Digitizing traditional savings circles securely and transparently.",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import routers
from routers import circles, members, payments
app.include_router(circles.router)
app.include_router(members.router)
app.include_router(payments.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
