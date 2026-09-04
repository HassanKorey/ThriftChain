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
    title="AjoLink API",
    description="Digitizing traditional savings circles securely and transparently.",
    version="1.0.0",
    lifespan=lifespan,
    debug=True
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import routers
from routers import circles, members, payments, auth
app.include_router(auth.router)
app.include_router(circles.router)
app.include_router(members.router)
app.include_router(payments.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
