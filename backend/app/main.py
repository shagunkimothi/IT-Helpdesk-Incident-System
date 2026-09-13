from fastapi import FastAPI

from .database import init_db
from .routers import health, incidents, users

app = FastAPI(title="IT Helpdesk Incident Management API", version="1.0.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(health.router)
app.include_router(users.router)
app.include_router(incidents.router)
