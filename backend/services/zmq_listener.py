import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import uuid
import zmq
import zmq.asyncio
from backend.db.database import get_conn
from backend.services.node_config import load_node_config
from pathlib import Path

logger = logging.getLogger("axiom.zmq")

ZMQ_ENDPOINT = os.getenv("ZMQ_AGENT_SUB_ENDPOINT", "tcp://axiom-agents:5556")

async def listen_for_agent_events(stop_event: asyncio.Event):
    last_mode: str | None = None
    last_replay: str | None = None

    while not stop_event.is_set():
        cfg = load_node_config()
        mode = cfg.get("data_source", "synthetic")
        replay_path = (cfg.get("replay_file_path") or "").strip()

        if mode == "replay" and (not replay_path or not Path(replay_path).is_file()):
            if last_mode != "replay_fallback":
                logger.warning(
                    "Replay file missing or invalid (%s); falling back to synthetic mode.",
                    replay_path or "<empty>",
                )
            mode = "synthetic"
            last_mode = "replay_fallback"
        elif mode != last_mode or replay_path != last_replay:
            logger.info("Active data source mode: %s (replay_path=%s)", mode, replay_path or "none")
            last_mode = mode
            last_replay = replay_path

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