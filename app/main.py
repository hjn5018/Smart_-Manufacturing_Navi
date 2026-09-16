from fastapi import FastAPI
from app.api.routes import agent as agt
from app.core.application_config import settings
from app.domains.capability_management.presentation import container_conveyor_routes
from app.domains.capability_management.presentation import routes as capability_routes
from app.domains.control_contract.presentation import routes as device_routes
from app.domains.operation_event.presentation import routes as operation_event_routes
from app.domains.operation_profile.presentation import routes as operation_profile_routes
from app.domains.operation_profile.presentation import straight_conveyor_routes
from app.infra.db.session import init_db, seed_initial_data

app = FastAPI()

app.include_router(agt.router)
app.include_router(device_routes.router)
app.include_router(capability_routes.router)
app.include_router(operation_profile_routes.router)
app.include_router(operation_event_routes.router)
app.include_router(container_conveyor_routes.router)
app.include_router(straight_conveyor_routes.router)
app.include_router(container_conveyor_routes.ws_router)


@app.on_event("startup")
def startup():
    if settings.AUTO_CREATE_TABLES:
        init_db()
        seed_initial_data()
#python -m uvicorn app.main:app --reload
