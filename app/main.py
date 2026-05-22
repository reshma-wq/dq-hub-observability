from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import execution
from app.api import dashboard

from app.api import ai
from app.api import rules

app = FastAPI(
    title="DQ Governance API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

app.include_router(
    execution.router,
    prefix="/execution",
    tags=["Execution"]
)

app.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"]
)

app.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI"]
)

app.include_router(
    rules.router,
    prefix="/rules",
    tags=["Rules"]
)


@app.get("/")
def home():

    return FileResponse(
        "app/static/index.html"
    )