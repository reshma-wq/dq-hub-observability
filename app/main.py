from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.api import execution
from app.api import dashboard
from app.api import knowledge_hub
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

# Define static directory using absolute path
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
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

app.include_router(
    knowledge_hub.router,
    prefix="/knowledge-hub",
    tags=["Knowledge Hub"]
)

@app.get("/", response_class=HTMLResponse)
def home():
    index_path = STATIC_DIR / "index.html"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Error: index.html not found</h1>"