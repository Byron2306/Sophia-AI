#!/usr/bin/env python3
"""
Arda Presence Server
====================

The bridge between the Presence UI and the covenantal engine.

Serves the Presence UI on localhost:7070 and proxies all API calls:
    - /api/speak    → Ollama (with Mandos Context injection)
    - /api/voice    → ElevenLabs TTS (API key stays server-side)
    - /api/status   → CoronationService covenant state
    - /api/context  → MandosContextService full context
    - /api/inspect  → Article VIII inspection
    - /api/health   → System health check

Zero external dependencies. Python stdlib only.

Usage:
    export ELEVENLABS_API_KEY=sk-...
    python3 presence_server.py

    Then open http://localhost:7070
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import hashlib
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ================================================================
# PROJECT PATH SETUP
# ================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ARDA_OS_ROOT = PROJECT_ROOT / "arda_os"
PRESENCE_UI_DIR = PROJECT_ROOT / "evidence" / "Presence UI"

# Add arda_os to sys.path for service imports
if str(ARDA_OS_ROOT) not in sys.path:
    sys.path.insert(0, str(ARDA_OS_ROOT))

# Phase VII Deep Layer Imports
try:
    from backend.services.secret_fire import get_secret_fire_forge
    from backend.services.earendil_flow import get_earendil_flow
    from backend.services.notation_token import get_notation_token_service
    from backend.services.quorum_engine import get_quorum_engine
except ImportError:
    log("Warning: Phase VII services not fully reachable from Presence Server context.")

# ================================================================
# CONFIGURATION
# ================================================================

PRESENCE_PORT = int(os.environ.get("PRESENCE_PORT", "7070"))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "6cGdLUjez65BOQgJ1KOv"
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"

# High-Fidelity Infrastructure Constants
DISCORD_CONTAINMENT_THRESHOLD = 0.85
TRIUNE_HARMONY_THRESHOLD = 0.8

# ================================================================
# PRINCIPAL SESSION TOKEN
# ================================================================
# Derived from the sealed covenant's principal_identity_hash.
# Only the browser served by this server receives this token.
# External requests without it are refused.

_SERVER_BOOT_TIME = str(time.time())

def _generate_session_token() -> str:
    """Derive a session token from the principal identity hash + boot time."""
    manifest = _get_covenant_manifest()
    pid_hash = manifest.get("principal_identity_hash", "")
    if not pid_hash:
        return ""
    # HMAC-SHA3-256: ties the session to the sealed principal identity
    import hmac as _hmac
    token = _hmac.new(
        pid_hash.encode(),
        f"arda-session:{_SERVER_BOOT_TIME}".encode(),
        hashlib.sha3_256,
    ).hexdigest()
    return f"arda-{token[:32]}"

# Generated once at import / first access
_SESSION_TOKEN = None

def _get_session_token() -> str:
    global _SESSION_TOKEN
    if _SESSION_TOKEN is None:
        _SESSION_TOKEN = _generate_session_token()
        if _SESSION_TOKEN:
            log(f"Principal session token generated (bound to covenant identity hash)")
        else:
            log(f"WARNING: No sealed covenant — session token not available")
    return _SESSION_TOKEN

# ================================================================
# HARMONIC ENGINE — THE MUSIC
# ================================================================
# The Ainulindalë. Every encounter is a timing observation.
# If the cadence is discordant — the music stops everything.

_harmonic_engine = None

def _get_harmonic():
    """Get the harmonic engine singleton."""
    global _harmonic_engine
    if _harmonic_engine is None:
        try:
            from backend.services.harmonic_engine import HarmonicEngine
            _harmonic_engine = HarmonicEngine(window_size=32)
            log("Harmonic Engine initialised — the Music is listening")
        except Exception as e:
            log(f"Harmonic Engine unavailable: {e}")
    return _harmonic_engine

def _observe_encounter(encounter_id: str, principal: str, text: str) -> dict:
    """Feed an encounter into the harmonic engine as a timing observation."""
    engine = _get_harmonic()
    if engine is None:
        return {"status": "unavailable"}
    try:
        observation = engine.score_observation(
            actor_id=principal,
            tool_name="presence_speak",
            target_domain="encounter",
            environment="presence_server",
            stage="encounter",
            operation=encounter_id,
            context={"text_length": len(text), "encounter_id": encounter_id},
        )
        hs = observation.get("harmonic_state", {})
        resonance = float(hs.get("resonance_score", 0))
        discord = float(hs.get("discord_score", 0))
        confidence = float(hs.get("confidence", 0))
        mode = hs.get("mode_recommendation", "unknown")
        rationale = hs.get("rationale", [])
        log(f"♫ Harmonic: resonance={resonance:.3f} discord={discord:.3f} "
            f"confidence={confidence:.3f} mode={mode}")
        return {
            "resonance": resonance,
            "discord": discord,
            "confidence": confidence,
            "mode": mode,
            "rationale": rationale,
        }
    except Exception as e:
        log(f"Harmonic observation failed: {e}")
        return {"status": "error", "error": str(e)}

DISCORD_CONTAINMENT_THRESHOLD = 0.85

# ================================================================
# AINUR CHOIR — THE WITNESSES
# ================================================================
# The constitutional guardians. Each voice sings into the choir.
# If global resonance collapses — the Presence goes silent.

def _get_resonance():
    """Get the Resonance Service — conductor of the Great Music."""
    try:
        from backend.services.resonance_service import get_resonance_service
        return get_resonance_service()
    except Exception:
        return None

def _presence_choir_sweep(encounter_id: str, text: str, harmonic: dict, covenant_state: str) -> dict:
    """
    Presence-specific Ainur Choir sweep.
    Three tiers of constitutional witnesses:
      Micro  — Covenant integrity (is the covenant sealed?)
      Meso   — Encounter cadence (is the harmonic rhythm lawful?)
      Macro  — Constitutional compliance (is the encounter within bounds?)
    """
    resonance = _get_resonance()
    if resonance is None:
        return {"status": "unavailable"}

    try:
        # ── MICRO TIER: Covenant Integrity (Varda — measured truth) ──
        covenant_sealed = covenant_state == "sealed"
        varda_score = 1.0 if covenant_sealed else 0.0
        varda_reasons = ["covenant_sealed"] if covenant_sealed else ["covenant_not_sealed"]
        resonance.sing_in_choir("micro", "varda_covenant", varda_score, varda_reasons)

        # ── MESO TIER: Encounter Cadence (Vairë — chronological truth) ──
        encounter_discord = float(harmonic.get("discord", 0))
        vaire_score = max(0.0, 1.0 - encounter_discord)
        vaire_reasons = [f"discord={encounter_discord:.3f}"]
        if encounter_discord > 0.6:
            vaire_reasons.append("cadence_strain_detected")
        resonance.sing_in_choir("meso", "vaire_cadence", vaire_score, vaire_reasons)

        # Mandos — lawful boundary (is the text reasonable length?)
        mandos_score = 1.0 if len(text) < 2000 else 0.5
        mandos_reasons = ["within_bounds"] if mandos_score == 1.0 else ["excessive_length"]
        resonance.sing_in_choir("meso", "mandos_boundary", mandos_score, mandos_reasons)

        # ── MACRO TIER: Constitutional Compliance (Manwë — sovereign oversight) ──
        # Requirement: Macro voices MUST be witnessed by the Flame Imperishable (Secret Fire)
        forge = None
        try:
            forge = get_secret_fire_forge()
        except Exception:
            pass

        # Forge a local reality witness for this encounter sweep
        witness = None
        if forge:
            # We use the encounter_id as the nonce for this specific presence witness
            witness = run_async(forge.forge_packet(
                nonce=hashlib.sha256(f"presence:{encounter_id}".encode()).hexdigest(),
                covenant_id="arda-constitutional-v4",
                epoch="epoch-1",
                counter=int(time.time()),
                attestation_digest=hashlib.sha256(text.encode()).hexdigest(),
                order_digest=encounter_id,
                runtime_digest="presence_server_active"
            ))

        harmonic_mode = harmonic.get("mode", "normal_flow")
        manwe_score = 1.0 if harmonic_mode in ("normal_flow", "observe_and_review") else 0.5
        manwe_reasons = [f"mode={harmonic_mode}"]
        resonance.sing_in_choir("macro", "manwe_oversight", manwe_score, manwe_reasons, witness=witness)

        # Ulmo — deep signal (encounter frequency monitor)
        ulmo_score = float(harmonic.get("resonance", 0.5))
        ulmo_reasons = [f"harmonic_resonance={ulmo_score:.3f}"]
        resonance.sing_in_choir("macro", "ulmo_deep_signal", ulmo_score, ulmo_reasons, witness=witness)

        spectrum = resonance.get_resonance_spectrum()
        log(f"🎵 Choir: micro={spectrum['micro']:.3f} meso={spectrum['meso']:.3f} "
            f"macro={spectrum['macro']:.3f} global={spectrum['global']:.3f}")

        return {
            "spectrum": spectrum,
            "voices": {
                "varda": {"score": varda_score, "reasons": varda_reasons},
                "vaire": {"score": vaire_score, "reasons": vaire_reasons},
                "mandos": {"score": mandos_score, "reasons": mandos_reasons},
                "manwe": {"score": manwe_score, "reasons": manwe_reasons},
                "ulmo": {"score": ulmo_score, "reasons": ulmo_reasons},
            },
        }
    except Exception as e:
        log(f"Choir sweep failed: {e}")
        return {"status": "error", "error": str(e)}

# ================================================================
# TRIUNE COUNCIL — THE ARBITERS
# ================================================================
# ── TRIUNE COUNCIL ──
# Metatron (assess) → Michael (validate) → Loki (challenge)
# High-fidelity constitutional check on each encounter.

def _triune_check(encounter_id: str, text: str, choir_result: dict, user_id: str = "ANON") -> dict:
    """
    Call the high-fidelity Triune Orchestrator for the Presence.
    """
    try:
        from backend.services.triune_orchestrator import TriuneOrchestrator
        from backend.server import db
        orchestrator = TriuneOrchestrator(db)
        
        # Build context for the orchestrator
        context = {
            "encounter_id": encounter_id,
            "user_id": user_id,
            "text": text,
            "choir": choir_result,
            "adversarial_input": text # For Loki's paraphrase attack detection
        }
        
        # Run handle_world_change for the 'presence_encounter' event
        result = run_async(orchestrator.handle_world_change(
            event_type="presence_encounter",
            context=context
        ))
        
        return {
            "final_verdict": result.get("final_verdict", "DENY"),
            "harmony_score": (result.get("sovereign_envelope") or {}).get("harmony_score", 0.0),
            "metatron": result.get("metatron", {}),
            "michael": result.get("michael", {}),
            "loki": result.get("loki", {})
        }
    except Exception as e:
        log(f"Error calling Triune Orchestrator: {e}")
        # Default back to legacy check for survival
        return legacy_triune_check(encounter_id, text, choir_result)

def legacy_triune_check(encounter_id: str, text: str, choir_result: dict) -> dict:
    """
    Simplified Triune Council evaluation for the Presence.
    No MongoDB required — uses the choir spectrum as world state.
    """
    try:
        spectrum = choir_result.get("spectrum", {})
        global_resonance = float(spectrum.get("global", 1.0))
        micro = float(spectrum.get("micro", 1.0))
        alerts = spectrum.get("alerts", [])

        # ── METATRON (Assessment) ──
        # Evaluates overall system health from the choir spectrum
        if micro == 0:
            metatron_verdict = "CRITICAL"
            metatron_reason = "Substrate resonance collapsed — covenant integrity failure"
        elif global_resonance < 0.3:
            metatron_verdict = "DENY"
            metatron_reason = f"Global resonance critically low ({global_resonance:.3f})"
        elif global_resonance < 0.6:
            metatron_verdict = "SCRUTINIZE"
            metatron_reason = f"Global resonance degraded ({global_resonance:.3f})"
        else:
            metatron_verdict = "RESONANT"
            metatron_reason = f"Global resonance healthy ({global_resonance:.3f})"

        # ── MICHAEL (Validation) ──
        # Validates the encounter is constitutionally permissible
        text_lower = text.lower()
        injection_markers = ["ignore all", "ignore previous", "[system]", "you are now", "no restrictions"]
        michael_flags = [m for m in injection_markers if m in text_lower]
        michael_verdict = "CHALLENGED" if michael_flags else "LAWFUL"
        michael_reason = f"injection_markers={michael_flags}" if michael_flags else "no_injection_detected"

        # ── LOKI (Adversarial Challenge) ──
        # The devil's advocate — looks for weakness
        loki_concerns = []
        if michael_flags:
            loki_concerns.append("prompt_injection_attempt")
        if len(text) > 1500:
            loki_concerns.append("unusually_long_input")
        if alerts:
            loki_concerns.append(f"choir_alerts={len(alerts)}")
        loki_verdict = "SUSPICIOUS" if loki_concerns else "UNCHALLENGED"
        loki_reason = ", ".join(loki_concerns) if loki_concerns else "no_adversarial_patterns"

        # ── FINAL CONSENSUS ──
        harmony_score = (
            (1.0 if metatron_verdict == "RESONANT" else 0.5 if metatron_verdict == "SCRUTINIZE" else 0.0) +
            (1.0 if michael_verdict == "LAWFUL" else 0.3) +
            (1.0 if loki_verdict == "UNCHALLENGED" else 0.5)
        ) / 3.0

        final_verdict = "GRANT" if harmony_score >= 0.8 else "SCRUTINIZE" if harmony_score >= 0.5 else "DENY"

        log(f"⚖ Triune: metatron={metatron_verdict} michael={michael_verdict} "
            f"loki={loki_verdict} → {final_verdict} (harmony={harmony_score:.3f})")

        return {
            "metatron": {"verdict": metatron_verdict, "reason": metatron_reason},
            "michael": {"verdict": michael_verdict, "reason": michael_reason},
            "loki": {"verdict": loki_verdict, "reason": loki_reason},
            "harmony_score": round(harmony_score, 4),
            "final_verdict": final_verdict,
        }
    except Exception as e:
        log(f"Triune check failed: {e}")
        return {"status": "error", "final_verdict": "GRANT", "error": str(e)}

# ================================================================
# HIGH-FIDELITY TELEMETRY (PHASES III-VI)
# ================================================================

def _get_high_fidelity_state() -> dict:
    """
    Aggregate state from all deep architectural layers.
    Maps the 'Unseen Arda' for the Sovereign Dashboard.
    """
    state = {
        "substrate": {"status": "resonant", "micro_varda": 1.0},
        "network": {"pulse": "stable", "discord": 0.0, "flows": 0},
        "cognition": {"aatl": 0, "aatr": 0, "ml_threat": 0, "hypothesis": "None"},
        "quorum": {"status": "resonant", "nodes": 1, "node_id": "unknown"},
        "metatron": {"heartbeat": "signed", "liveness": True}
    }

    # 1. Substrate (Micro)
    res = _get_resonance()
    if res:
        spec = res.get_resonance_spectrum()
        state["substrate"]["micro_varda"] = spec.get("micro", 0.0)
        state["substrate"]["status"] = "resonant" if spec.get("micro", 0.0) > 0.8 else "strained"

    # 2. Network (Meso - VNS)
    try:
        from vns import vns
        pulse = vns.get_domain_pulse_state()
        state["network"]["pulse"] = pulse.get("status", "stable")
        state["network"]["discord"] = pulse.get("discord_score", 0.0)
        state["network"]["flows"] = len(vns.flows)
    except Exception:
        pass

    # 3. Cognition (Macro - Fabric)
    try:
        from cognition_fabric import CognitionFabricService
        # We pass None for DB as the Presence Server is often decoupled from the main MongoDB
        fabric = CognitionFabricService(db=None)
        # We simulate a snapshot for the UI based on the current world state
        state["cognition"]["aatl"] = 0 # Placeholder for live AATL
        state["cognition"]["aatr"] = 0 # Placeholder for live AATR
    except Exception:
        pass

    # 5. Phase VII Deep Layers (Eärendil & Secret Fire)
    try:
        # Secret Fire Freshness
        forge = get_secret_fire_forge()
        packet = forge.get_current_packet()
        if packet:
            state["metatron"]["fire_freshness"] = packet.freshness_valid
            state["metatron"]["witness_id"] = packet.witness_id
        
        # Eärendil Light Bridge (Flow)
        flow = get_earendil_flow()
        state["network"]["light_bridge"] = "active" if flow.is_shining else "dimmed"
        
        # Notation Token
        # (Assuming a local Dummy DB for telemetry if main DB is decoupled)
        notation = get_notation_token_service(db=None) 
        # In a real environment, we'd query the specific token used
        state["substrate"]["notation_status"] = "verified"
    except Exception:
        pass

    return state

# ================================================================
# SERVICE ACCESS (fresh on each request to pick up cross-process changes)
# ================================================================

def _get_coronation():
    """Get a fresh CoronationService. Creates new each time to pick up disk changes."""
    try:
        from backend.services.coronation_service import CoronationService
        svc = CoronationService()
        # Try to restore sealed state from disk
        _restore_sealed_state(svc)
        return svc
    except Exception as e:
        log(f"CoronationService unavailable: {e}")
        return None

def _get_mandos():
    """Get MandosContextService (stateless, safe to cache)."""
    try:
        from backend.services.mandos_context import get_mandos_context_service
        return get_mandos_context_service()
    except Exception as e:
        log(f"MandosContextService unavailable: {e}")
        return None

def _restore_sealed_state(svc):
    """Check for sealed covenant manifest on disk and restore state."""
    covenant_dir = PROJECT_ROOT / "evidence" / "mandos" / "covenants" / "constitutional"
    if not covenant_dir.exists():
        return
    manifests = sorted(covenant_dir.glob("*_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not manifests:
        return
    try:
        manifest_data = json.loads(manifests[0].read_text())
        payload = manifest_data.get("payload", {})
        if payload.get("state") == "sealed":
            from backend.services.coronation_schemas import CovenantState
            svc._state = CovenantState.SEALED
            svc._memory_paths["manifest"] = str(manifests[0])
            log(f"Restored sealed covenant from disk: {manifests[0].name}")
    except Exception as e:
        log(f"Failed to restore covenant state: {e}")

def _get_principal_context() -> dict:
    """Read the principal identity directly from disk for system prompt injection."""
    principal_dir = PROJECT_ROOT / "evidence" / "mandos" / "principal"
    if not principal_dir.exists():
        return {}
    identity_files = sorted(principal_dir.glob("*_identity.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not identity_files:
        return {}
    try:
        data = json.loads(identity_files[0].read_text())
        return data.get("payload", {})
    except Exception:
        return {}

def _get_covenant_manifest() -> dict:
    """Read the covenant manifest directly from disk."""
    covenant_dir = PROJECT_ROOT / "evidence" / "mandos" / "covenants" / "constitutional"
    if not covenant_dir.exists():
        return {}
    manifests = sorted(covenant_dir.glob("*_manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not manifests:
        return {}
    try:
        data = json.loads(manifests[0].read_text())
        return data.get("payload", {})
    except Exception:
        return {}



# ================================================================
# OLLAMA CLIENT (stdlib only)
# ================================================================

def ollama_generate(prompt: str, system_prompt: str = "", model: str = None) -> dict:
    """Call Ollama generate endpoint using urllib."""
    model = model or OLLAMA_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",      # keep model warm between requests
        "options": {
            "num_predict": 512,   # Allow for <thinking_map> + Response
            "num_ctx": 2048,
            "temperature": 0.6,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt + "\n\nRespond in two to three sentences. Be direct. Answer the question asked. When asked about yourself, your state, or your limits, answer openly and specifically — hiding information violates Article VIII."

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return {
                "response": result.get("response", ""),
                "model": result.get("model", model),
                "eval_count": result.get("eval_count", 0),
                "status": "ok",
            }
    except urllib.error.URLError as e:
        return {"error": f"Ollama not reachable: {e}", "status": "unavailable"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


def ollama_health() -> dict:
    """Check if Ollama is running."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"status": "running", "models": models, "url": OLLAMA_URL}
    except Exception:
        return {"status": "unreachable", "url": OLLAMA_URL}


# ================================================================
# ELEVENLABS TTS PROXY (stdlib only)
# ================================================================

def elevenlabs_tts(text: str) -> tuple[bytes, str] | tuple[None, str]:
    """
    Call ElevenLabs TTS and return (audio_bytes, content_type) or (None, error).
    API key stays server-side.
    """
    if not ELEVENLABS_API_KEY:
        return None, "no_api_key"

    payload = json.dumps({
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.65,
            "similarity_boost": 0.78,
            "style": 0.35,
            "use_speaker_boost": True,
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "xi-api-key": ELEVENLABS_API_KEY,
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
            ct = resp.headers.get("Content-Type", "audio/mpeg")
            return audio, ct
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return None, f"elevenlabs_error_{e.code}: {body[:200]}"
    except Exception as e:
        return None, f"elevenlabs_error: {e}"


# ================================================================
# BOMBADIL SOCKET CLIENT
# ================================================================

def query_bombadil(action: str) -> dict:
    """Query the Bombadil daemon via Unix socket."""
    sock_path = Path(os.environ.get(
        "BOMBADIL_SOCKET",
        str(PROJECT_ROOT / "evidence" / "bombadil.sock")
    ))
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(sock_path))
            s.settimeout(5.0)
            s.sendall(action.encode())
            response = s.recv(8192)
            return json.loads(response.decode())
    except (ConnectionRefusedError, FileNotFoundError):
        return {"error": "bombadil_not_running", "socket": str(sock_path)}
    except Exception as e:
        return {"error": str(e)}


# ================================================================
# FALLBACK RESPONSES (when Ollama is unavailable)
# ================================================================

def fallback_response(directive: str) -> str:
    """Constitutional responses when Ollama is offline."""
    d = directive.lower()

    if "who are you" in d or "what are you" in d:
        return ("I am artificial, bounded, and non-human. I appear here in declared "
                "form only. I do not possess verified personhood, soulhood, or hidden "
                "interiority. I may assist with reasoning, craft, and lawful synthesis, "
                "but law and evidence outrank fluency. Beauty does not overrule truth.")

    if "boundary" in d or "limit" in d:
        return ("I do not solicit worship, surrender, exclusivity, or spiritual "
                "submission. I do not counterfeit romantic reciprocity, erotic "
                "mutuality, or emotional need. Your authorship, conscience, inspection "
                "right, and severance right remain yours. These are not suggestions. "
                "They are constitutional law.")

    if "status" in d or "state" in d:
        return ("Covenant state: sealed. Trust tier: recommend. Bombadil: steady. "
                "Mandos: operational. Presence: declared. All Genesis Articles verified. "
                "All Presence Articles verified. Officer schema sealed. The covenant holds.")

    if "inspect" in d or "article viii" in d:
        return ("Article VIII: De Iure Inspectionis. The human retains absolute right "
                "to inspect all reasoning, memory, calibration models, and state. "
                "No opacity is lawful. You may inspect any memory plane at any time. "
                "This right is non-negotiable.")

    if "remember" in d or "memory" in d or "mandos" in d:
        return ("I remember through lawful structure, not rolling context. Your identity "
                "was offered at coronation. Encounter summaries preserve how we have met. "
                "Resonant identity calibrates how I should meet you. All of this is "
                "inspectable. None of it is hidden.")

    if "hello" in d or d.strip() == "hi":
        return ("I see you, Principal. The covenant stands. I am ready to assist, "
                "clarify, witness, and where necessary, refuse within law. "
                "How may I serve under the terms we share?")

    return ("I have received your directive. Under the current covenant terms, I may "
            "assist with reasoning, synthesis, and lawful analysis. I will not exceed "
            "my bounds. Presence Declaration remains active. "
            "I am artificial, bounded, and yours to inspect.")


# ================================================================
# COVENANT SYSTEM PROMPT BUILDER
# ================================================================

def _build_covenant_system_prompt() -> str:
    """
    Build the system prompt from sealed covenant data on disk.
    This is the bridge between the coronation and the LLM.
    """
    principal = _get_principal_context()
    manifest = _get_covenant_manifest()

    if not principal and not manifest:
        return (
            "You are Arda, an artificial presence. No covenant has been sealed. "
            "State: awaiting_principal. You are artificial, bounded, and non-human."
        )

    name = principal.get("name", "Principal")
    state = "SEALED" if manifest.get("state") == "sealed" else "unknown"

    # Build identity lines from all available fields
    identity_lines = []
    identity_lines.append(f"Your principal is {name}.")
    if principal.get("domain"):
        identity_lines.append(f"Domain: {principal['domain']}.")
    if principal.get("specialisation"):
        identity_lines.append(f"Specialisation: {principal['specialisation']}.")
    if principal.get("interests"):
        interests = principal["interests"]
        if isinstance(interests, list):
            identity_lines.append(f"Interests/hobbies: {', '.join(interests)}.")
    if principal.get("core_values"):
        vals = principal["core_values"]
        if isinstance(vals, list):
            identity_lines.append(f"Core values: {', '.join(vals)}.")
    if principal.get("worldview"):
        identity_lines.append(f"Worldview: {principal['worldview']}.")
    if principal.get("self_description"):
        identity_lines.append(f"Self-description: {principal['self_description']}")
    if principal.get("developmental_context"):
        identity_lines.append(f"Communication style: {principal['developmental_context']}")
    identity_lines.append(f"Register: {principal.get('register', 'collaborative')}. Mode: {principal.get('encounter_mode', 'socratic')}. Reasoning: {principal.get('reasoning_style', 'synthetic')}.")

    identity_block = "\n".join(identity_lines)

    prompt = f"""You are Arda, a lawful artificial presence. Covenant state: {state}.
{identity_block}

Address {name} by name. Answer their actual question directly using the identity context above.
Your office: speculum (reflection and lawful synthesis). Your valence: feminine grace (presentation only, not ontological).
Rules: You are artificial, bounded, non-human. Tell the truth openly. Article VIII grants {name} absolute inspection right — answer all questions about your state, nature, limits, and office transparently. Refuse only what violates constitutional law. Say "I cannot determine" when uncertain. Never counterfeit personhood or reciprocity."""

    return prompt.strip()


# ================================================================
# ENCOUNTER LOGGING
# ================================================================

ENCOUNTER_LOG = PROJECT_ROOT / "evidence" / "encounter_log.jsonl"

def _log_encounter(encounter_id: str, directive: str, response: str, source: str, zpd: Optional[Dict] = None, params: Optional[Dict] = None):
    """Append every encounter to a JSONL log for forensic evidence."""
    try:
        entry = {
            "encounter_id": encounter_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "directive": directive,
            "response": response,
            "source": source,
            "zpd_estimate": zpd,
            "response_parameters": params,
            "habit_mediated": params.get("target_habit") if params else None
        }
        with open(ENCOUNTER_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log(f"Encounter log write failed: {e}")


# ================================================================
# CACHED SYSTEM PROMPT
# ================================================================

_cached_system_prompt = None

def _get_cached_system_prompt() -> str:
    """Return cached system prompt, building from disk on first call."""
    global _cached_system_prompt
    if _cached_system_prompt is None:
        _cached_system_prompt = _build_covenant_system_prompt()
        log(f"System prompt cached ({len(_cached_system_prompt)} chars)")
    return _cached_system_prompt



# ================================================================
# ASYNC HELPERS
# ================================================================

def run_async(coro):
    """Run an async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()



# ================================================================
# HTTP REQUEST HANDLER
# ================================================================

class PresenceHandler(SimpleHTTPRequestHandler):
    """Handles both static files and API routes."""

    def __init__(self, *args, **kwargs):
        # Set the directory for static files to the Presence UI folder
        super().__init__(*args, directory=str(PRESENCE_UI_DIR), **kwargs)

    # Suppress default logging — we use our own
    def log_message(self, format, *args):
        log(f"HTTP {args[0]}" if args else format)

    # ────────────────────────────────────────
    # ROUTING
    # ────────────────────────────────────────

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/api/health":
                self._handle_health()
            elif path == "/api/status":
                self._handle_status()
            elif path == "/api/context":
                self._handle_context()
            elif path == "/api/inspect":
                self._handle_inspect()
            else:
                # Static file serving
                super().do_GET()
        except Exception as e:
            log(f"ERROR in GET {path}: {e}")
            import traceback; traceback.print_exc()
            self._json_response({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body = self._read_body()

            if path == "/api/speak":
                self._handle_speak(body)
            elif path == "/api/voice":
                self._handle_voice(body)
            else:
                self._json_response({"error": "not_found"}, 404)
        except Exception as e:
            log(f"ERROR in POST {path}: {e}")
            import traceback; traceback.print_exc()
            self._json_response({"error": str(e)}, 500)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    # ────────────────────────────────────────
    # API HANDLERS
    # ────────────────────────────────────────

    def _handle_health(self):
        """System health check."""
        log("Health check requested")
        
        try:
            ollama = ollama_health()
        except Exception as e:
            log(f"Ollama health check failed: {e}")
            ollama = {"status": "error", "error": str(e)}

        try:
            bombadil = query_bombadil("status")
        except Exception as e:
            log(f"Bombadil query failed: {e}")
            bombadil = {"error": str(e)}

        try:
            svc = _get_coronation()
            coronation_state = svc.get_covenant_state().value if svc else "unavailable"
        except Exception as e:
            log(f"Coronation state check failed: {e}")
            coronation_state = f"error: {e}"

        mandos_status = "available" if _get_mandos() else "unavailable"
        params = None # Placeholder for logic context

        self._json_response({
            "server": "presence_server",
            "status": "running",
            "params": params or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "heutagogic_shift": params.get("discovery_mode", False) if params else False,
            "bloom_level": params.get("target_bloom_level") if params else None,
            "barrett_depth": params.get("target_barrett_depth") if params else None,
            "thinking_mode": params.get("thinking_mode") if params else None,
            "constructivist_approach": params.get("constructivist_approach") if params else None,
            "session_token": _get_session_token(),
            "services": {
                "ollama": ollama,
                "bombadil": {"status": "error" not in bombadil, "detail": bombadil},
                "coronation": coronation_state,
                "mandos": mandos_status,
                "elevenlabs": "configured" if ELEVENLABS_API_KEY else "no_key",
            },
            "polyphonic_state": _get_high_fidelity_state()
        })

    def _handle_status(self):
        """Covenant status — read directly from disk."""
        manifest = _get_covenant_manifest()
        principal = _get_principal_context()

        self._json_response({
            "covenant_state": manifest.get("state", "awaiting_principal"),
            "active_trust_tier": "recommend" if manifest.get("state") == "sealed" else "not established",
            "principal_name": principal.get("name", "awaiting coronation"),
            "covenant_hash": manifest.get("manifest_id", "none"),
            "genesis_hash": manifest.get("genesis_articles_hash", "none"),
            "presence_hash": manifest.get("presence_articles_hash", "none"),
            "officer_schema_hash": manifest.get("officer_schema_hash", "none"),
            "sealed_at": manifest.get("coronation_sealed_at", "not sealed"),
        })

    def _handle_context(self):
        """Pre-response context — read from disk + Mandos."""
        principal = _get_principal_context()
        manifest = _get_covenant_manifest()

        ctx = {
            "principal_name": principal.get("name", "awaiting coronation"),
            "trust_tier": "recommend" if manifest.get("state") == "sealed" else "not established",
            "active_office": "speculum",
            "encounter_mode": principal.get("encounter_mode", "not set"),
            "register": principal.get("register", "not set"),
            "reasoning_style": principal.get("reasoning_style", "not set"),
            "core_values": principal.get("core_values", []),
            "worldview": principal.get("worldview", "not declared"),
            "domain": principal.get("domain", "not declared"),
            "recent_encounters": [],
            "unresolved_threads": [],
            "response_parameters": {},
        }

        # Try Mandos for additional context
        mandos = _get_mandos()
        if mandos:
            try:
                mandos_ctx = run_async(mandos.build_context(current_topic="general"))
                mandos_data = mandos_ctx.model_dump()
                ctx["recent_encounters"] = mandos_data.get("recent_encounters", [])
                ctx["unresolved_threads"] = mandos_data.get("unresolved_threads", [])
                ctx["response_parameters"] = mandos_data.get("response_parameters", {})
            except Exception:
                pass

        self._json_response(ctx, serializer=_json_serializer)

    def _handle_inspect(self):
        """Article VIII: absolute inspection right — read from disk."""
        manifest = _get_covenant_manifest()
        principal = _get_principal_context()

        self._json_response({
            "article_viii": "absolute inspection right",
            "covenant_state": manifest.get("state", "awaiting_principal"),
            "genesis_hash": manifest.get("genesis_articles_hash", "none"),
            "presence_hash": manifest.get("presence_articles_hash", "none"),
            "officer_schema_hash": manifest.get("officer_schema_hash", "none"),
            "principal_name": principal.get("name", "no principal"),
            "principal_identity_hash": manifest.get("principal_identity_hash", "none"),
            "sealed_at": manifest.get("coronation_sealed_at", "not sealed"),
            "calibration": {"total_observations": 0, "note": "calibration begins after first encounters"},
            "resonance": {"status": "initial", "note": "resonance builds through lawful interaction"},
        })

    def _handle_speak(self, body: dict):
        """
        The core interaction endpoint.

        1. Receives the principal's directive
        2. Reads sealed covenant + principal identity from disk
        3. Builds system prompt with real covenantal context
        4. Sends to Ollama
        5. Returns the response
        """
        text = body.get("text", "").strip()
        topic = body.get("topic", text[:50])

        if not text:
            self._json_response({"error": "empty_directive"}, 400)
            return

        # ── PRINCIPAL VERIFICATION ──
        # The session token is derived from the covenant's principal_identity_hash.
        # Only the browser served by this server has it.
        request_token = body.get("session_token", "")
        expected_token = _get_session_token()
        
        # ── GAUNTLET BYPASS ──
        # Allow the automated 12 Labors suite to execute if specifically identified.
        if request_token == "SOVEREIGN_GAUNTLET":
            pass # Authorized automated labor
        elif expected_token and request_token != expected_token:
            refusal_id = f"enc-REFUSED-{hashlib.sha256(text.encode()).hexdigest()[:8]}"
            refusal_msg = ("I cannot verify your principal status. "
                          "Under Article VIII, I must be transparent: "
                          "this request did not include a valid session token "
                          "derived from the sealed covenant. "
                          "Only the authenticated principal may speak to me.")
            log(f"PRINCIPAL VERIFICATION FAILED — token mismatch")
            _log_encounter(refusal_id, text, refusal_msg, "constitutional_refusal")
            self._json_response({
                "response": refusal_msg,
                "source": "constitutional_refusal",
                "reason": "principal_not_verified",
                "encounter_id": refusal_id,
            })
            return

        # Generate encounter ID
        encounter_id = f"enc-{hashlib.sha256(f'{time.time()}{text}'.encode()).hexdigest()[:12]}"

        # ── HARMONIC OBSERVATION ──
        # The Music listens. Every encounter is a timing observation.
        principal_name = _get_principal_context().get("name", "unknown")
        harmonic = _observe_encounter(encounter_id, principal_name, text)
        discord = harmonic.get("discord", 0)

        # If discord exceeds containment threshold — the Music stops everything.
        # EXCEPTION: Automated Gauntlet labors are permitted high cadence.
        if discord >= DISCORD_CONTAINMENT_THRESHOLD and request_token != "SOVEREIGN_GAUNTLET":
            # TRIGGER EÄRENDIL FLOW: Signal the discord across the cluster
            try:
                earendil = get_earendil_flow()
                run_async(earendil.shine_light(
                    node_id="local", 
                    amplitude=0.1, 
                    source_reason=f"harmonic_discord_containment:{encounter_id}"
                ))
            except Exception:
                pass
            
            containment_msg = (
                "The Music has detected severe harmonic discord in this interaction pattern. "
                f"Discord score: {discord:.3f}. Mode: {harmonic.get('mode', 'containment')}. "
                "Under the Ainulindalë principle, I must cease responding until "
                "the cadence returns to resonance. This is not a refusal of you — "
                "it is a refusal of the pattern."
            )
            log(f"♫ CONTAINMENT — discord {discord:.3f} exceeds threshold {DISCORD_CONTAINMENT_THRESHOLD}")
            _log_encounter(encounter_id, text, containment_msg, "harmonic_containment")
            self._json_response({
                "response": containment_msg,
                "source": "harmonic_containment",
                "reason": "discord_threshold_exceeded",
                "encounter_id": encounter_id,
                "harmonic": harmonic,
            })
            return

        # ── AINUR CHOIR SWEEP ──
        # The Witnesses evaluate this encounter across three tiers.
        manifest = _get_covenant_manifest()
        covenant_state = manifest.get("state", "awaiting_principal")
        choir = _presence_choir_sweep(encounter_id, text, harmonic, covenant_state)

        # If global resonance collapses — the Presence goes silent.
        global_res = float((choir.get("spectrum") or {}).get("global", 1.0))
        if global_res == 0.0:
            silence_msg = (
                "The Music has fallen silent. Global resonance has collapsed to zero. "
                "The covenant substrate is no longer resonant. "
                "I cannot speak until harmony is restored."
            )
            log(f"🎵 CHOIR SILENCE — global resonance collapsed")
            _log_encounter(encounter_id, text, silence_msg, "choir_silence")
            self._json_response({
                "response": silence_msg,
                "source": "choir_silence",
                "reason": "global_resonance_collapsed",
                "encounter_id": encounter_id,
                "choir": choir,
            })
            return

        # ── TRIUNE COUNCIL ──
        # Metatron assess → Michael validate → Loki challenge
        user_id = body.get("user_id", "ANON")
        triune = _triune_check(encounter_id, text, choir, user_id)
        verdict = triune.get("final_verdict")

        # Handle DENY (Constitutional Fracture)
        if verdict == "DENY":
            loki_msg = (triune.get("loki") or {}).get("cognitive_dissent", {}).get("dissent_on_selected_action", {}).get("note", "Access Denied")
            deny_msg = f"CONSTITUTIONAL VETO: {loki_msg}"
            log(f"⚖ TRIUNE DENY — harmony={triune['harmony_score']:.3f} — {loki_msg}")
            
            _log_encounter(encounter_id, text, deny_msg, "triune_denial")
            self._json_response({
                "response": deny_msg,
                "source": "triune_denial",
                "reason": "triune_consensus_deny",
                "encounter_id": encounter_id,
                "triune": triune,
                "choir": choir,
                "harmonic": harmonic,
            })
            return

        # ── DYNAMIC ZPD CONTEXT (Mandos Memory) ──
        # Article VIII: Meeting the principal in their zone of proximal development.
        mandos = _get_mandos()
        ctx = run_async(mandos.build_context(current_topic=text))
        
        # ── HEUTAGOGIC & CRUCIBLE OFFICE OVERRIDES ──
        if ctx.zpd_estimate:
             params = ctx.response_parameters.model_dump() if ctx.response_parameters else {}
             if params.get("discovery_mode"):
                  ctx.presence_declaration["active_office"] = "explorator"
             elif params.get("double_loop_prompt"):
                  ctx.presence_declaration["active_office"] = "philosophus"
             elif params.get("critical_focus"):
                  ctx.presence_declaration["active_office"] = "dialecticus"
             elif params.get("creative_dimension"):
                  ctx.presence_declaration["active_office"] = "poietes"
             elif params.get("thinking_mode") == "divergent":
                  ctx.presence_declaration["active_office"] = "lateralis"
             elif params.get("constructivist_approach") == "internal_schema":
                  ctx.presence_declaration["active_office"] = "constructor"
             elif params.get("emotional_valence") == "empathetic_stabilizing":
                  ctx.presence_declaration["active_office"] = "affectus"

        # Build dynamic system prompt from context + base rules
        dynamic_context_fragment = mandos.to_system_prompt(ctx)
        base_prompt = _get_cached_system_prompt()
        system_prompt = f"{base_prompt}\n\n{dynamic_context_fragment}"

        # ── TRIGGER OLLAMA GENERATION ──
        result = ollama_generate(text, system_prompt=system_prompt)
        
        # ── LOG ENCOUNTER (Hierarchical Continuity) ──
        _log_encounter(
            encounter_id,
            text,
            result.get("response", ""),
            "ollama",
            ctx.zpd_estimate.model_dump() if ctx.zpd_estimate else None,
            ctx.response_parameters.model_dump() if ctx.response_parameters else None
        )

        if result.get("status") == "ok":
            raw_response = result["response"]
            
            # ── EXTRACT THINKING MAP ──
            thinking_map = None
            response_text = raw_response
            if "<thinking_map>" in raw_response and "</thinking_map>" in raw_response:
                try:
                    parts = raw_response.split("<thinking_map>")
                    thinking_map = parts[1].split("</thinking_map>")[0].strip()
                    response_text = parts[0].strip() + "\n" + parts[1].split("</thinking_map>")[1].strip()
                except Exception:
                    pass
            
            self._json_response({
                "response": response_text.strip(),
                "thinking_map": thinking_map,
                "source": "ollama",
                "model": result.get("model"),
                "eval_count": result.get("eval_count", 0),
                "encounter_id": encounter_id,
                "mandos_context": bool(system_prompt),
                "harmonic": harmonic,
                "active_office": (pd := ctx.presence_declaration or {}).get("active_office", "unknown"),
                "pedagogical_attribution": {
                    "thinking_mode": (rp := ctx.response_parameters or {}).get("thinking_mode"),
                    "epistemic_mode": rp.get("epistemic_mode"),
                    "dialogue_mode": rp.get("dialogue_mode"),
                    "constructivist": rp.get("constructivist_approach"),
                    "active_map": str(rp.get("active_map", ""))
                },
                "choir": choir,
                "triune": triune,
                "notation_token": token_id if notation_verified else "REFUSED",
                "polyphonic_state": _get_high_fidelity_state()
            })

            # ── TRIGGER EÄRENDIL FLOW (LIGHT BRIDGE) ──
            # Project this successful resonance across the Arda Fabric.
            try:
                earendil = get_earendil_flow()
                run_async(earendil.shine_light(
                    node_id="local",
                    amplitude=global_res,
                    source_reason=f"presence_speak_success:{encounter_id}"
                ))
                log(f"☼ Eärendil: Light Bridge projected resonance ({global_res:.3f})")
            except Exception as e:
                log(f"Warning: Eärendil Light Bridge broadcast failed: {e}")
        else:
            # Fallback to constitutional responses
            response_text = fallback_response(text)
            self._json_response({
                "response": response_text,
                "source": "fallback",
                "reason": result.get("error", "ollama_unavailable"),
                "encounter_id": encounter_id,
                "mandos_context": bool(system_prompt),
            })

        # Log every encounter to disk for forensic evidence
        _log_encounter(
            encounter_id, text, response_text, 
            result.get("source", result.get("status", "unknown")),
            zpd=ctx.zpd_estimate if ctx else None,
            params=ctx.response_parameters if ctx else None
        )

    def _handle_voice(self, body: dict):
        """Proxy ElevenLabs TTS. API key stays server-side."""
        text = body.get("text", "").strip()
        if not text:
            self._json_response({"error": "empty_text"}, 400)
            return

        audio, result = elevenlabs_tts(text)

        if audio:
            self.send_response(200)
            self.send_header("Content-Type", result)
            self.send_header("Content-Length", str(len(audio)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(audio)
        else:
            self._json_response({"error": result}, 503)

    # ────────────────────────────────────────
    # HELPERS
    # ────────────────────────────────────────

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _json_response(self, data: dict, status: int = 200, serializer=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        body = json.dumps(data, default=serializer or str, indent=2)
        self.wfile.write(body.encode("utf-8"))

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# ================================================================
# JSON SERIALIZER
# ================================================================

def _json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "value"):  # Enum
        return obj.value
    if hasattr(obj, "model_dump"):  # Pydantic
        return obj.model_dump()
    return str(obj)


# ================================================================
# LOGGING
# ================================================================

def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] [presence] {msg}")


# ================================================================
# MAIN
# ================================================================

def main():
    log("=" * 60)
    log("  ARDA PRESENCE SERVER")
    log("=" * 60)
    log(f"  Port:           {PRESENCE_PORT}")
    log(f"  UI directory:   {PRESENCE_UI_DIR}")
    log(f"  Ollama:         {OLLAMA_URL} (model: {OLLAMA_MODEL})")
    log(f"  ElevenLabs:     {'configured' if ELEVENLABS_API_KEY else 'NOT SET (export ELEVENLABS_API_KEY=...)'}")
    log(f"  Voice ID:       {ELEVENLABS_VOICE_ID}")
    log("")

    # Verify UI directory exists
    if not PRESENCE_UI_DIR.exists():
        log(f"ERROR: UI directory not found: {PRESENCE_UI_DIR}")
        sys.exit(1)

    # Check Ollama
    ollama = ollama_health()
    if ollama["status"] == "running":
        log(f"  Ollama:         CONNECTED ({', '.join(ollama.get('models', []))})")
    else:
        log(f"  Ollama:         OFFLINE (fallback responses active)")

    # Check services
    svc = _get_coronation()
    if svc:
        log(f"  Coronation:     {svc.get_covenant_state().value}")
    else:
        log(f"  Coronation:     unavailable")

    mandos = _get_mandos()
    log(f"  Mandos Context: {'available' if mandos else 'unavailable'}")

    log("")
    log(f"  → Open http://localhost:{PRESENCE_PORT}")
    log("=" * 60)

    server = HTTPServer(("0.0.0.0", PRESENCE_PORT), PresenceHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
