import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import uuid
import zmq
import zmq.asyncio
from backend.db.database import get_conn

logger = logging.getLogger("axiom.zmq")

ZMQ_ENDPOINT = os.getenv("ZMQ_AGENT_SUB_ENDPOINT", "tcp://axiom-agents:5556")

async def listen_for_agent_events(stop_event: asyncio.Event) -> None:
    """Subscribes to axiom-agents ZMQ PUB socket and logs detections to SQLite."""
    ctx = zmq.asyncio.Context.instance()
    sock = ctx.socket(zmq.SUB)
    sock.setsockopt_string(zmq.SUBSCRIBE, "")
    sock.setsockopt(zmq.RCVTIMEO, 1000)  # 1s poll so shutdown is clean

    try:
        sock.connect(ZMQ_ENDPOINT)
        logger.info("ZMQ listener connected to %s", ZMQ_ENDPOINT)
    except Exception as exc:
        logger.warning("ZMQ connect skipped (%s): %s", ZMQ_ENDPOINT, exc)
        sock.close()
        return

    try:
        while not stop_event.is_set():
            try:
                raw = await sock.recv_string()
                payload = json.loads(raw)
                _store_event(payload)
            except zmq.Again:
                continue
            except Exception as exc:
                logger.error("Failed to process ZMQ event: %s", exc)
    finally:
        sock.close()
        logger.info("ZMQ listener stopped.")

def _store_event(payload: dict) -> None:
    event_id = payload.get("id") or f"EVT-{uuid.uuid4().hex[:8].upper()}"
    ts = payload.get("timestamp_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = payload.get("summary", "Anomalous LEO track detected.")
    fits_path = payload.get("fits_path", f"data/events/{event_id}.fits")
    sig = payload.get("signature_sha256", "")
    valid = 1 if payload.get("attestation_valid") else 0

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO events
            (id, timestamp_utc, summary, fits_path, signature_sha256, attestation_valid)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, ts, summary, fits_path, sig, valid),
        )