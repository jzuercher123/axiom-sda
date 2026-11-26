import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.services.zmq_listener import listen_for_agent_events
from backend.routers import hardware, wizard, masking, events, updates


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(listen_for_agent_events(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await task

app = FastAPI(title="Axiom SDA", version="0.1.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.include_router(hardware.router)
app.include_router(wizard.router)
app.include_router(masking.router)
app.include_router(events.router)
app.include_router(updates.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}