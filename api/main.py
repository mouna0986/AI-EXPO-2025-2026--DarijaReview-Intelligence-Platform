from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router.data import router as data_router

#keeping just in case: from router.data import router as data_router

app = FastAPI(
    title="DarijaReview Intelligence API",
    description="Backend API for the Ramy sentiment analysis dashboard",
    version="1.0.0"
)

# This allows the dashboard (running on a different port)
# to talk to the API without getting blocked
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routes under /api prefix
app.include_router(data_router, prefix="/api")


@app.get("/")
def root():
    return {"status": "running", "message": "DarijaReview API is live"}