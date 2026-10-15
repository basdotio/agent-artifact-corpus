from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import audio, decisions, references
from .config import DATA, ROOT
from .models import CaptureRequest, Feedback, ModelSpec, ReferenceRequest, SessionRequest, TonePlan
from .phone import ControlError, Phone
from .store import Store


class Service:
    def __init__(self, store=None, phone_factory=Phone):
        self.store = store or Store()
        self.phone_factory = phone_factory
        self.cancel = threading.Event()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mustang")
        self.lock = threading.Lock()
        self.active_job = None
        self._state_lock = threading.RLock()
        for job in self.store.list("job"):
            if job["status"] in {"running", "queued"}:
                self.store.put("job", {**job, "status": "interrupted", "message": "Application restarted"})

    def catalog(self):
        path = ROOT / "catalog/tone-5.1.3.json"
        return [ModelSpec.model_validate(x) for x in json.loads(path.read_text())] if path.exists() else []

    def capabilities(self):
        hardware_path = DATA / "hardware.json"
        hardware = json.loads(hardware_path.read_text(encoding="utf-8")) if hardware_path.exists() else {}
        return {
            "models": [m.model_dump() for m in self.catalog()],
            "max_trials_default": 6,
            "max_replacements": 2,
            "adapter": "tone-5.1.3-portrait",
            "amp": "Mustang GT40",
            "pedal": "MGT-4",
            "match_target": "USB",
            "decision_model": decisions.status(),
            "firmware": hardware.get("firmware"),
            "firmware_source": hardware.get("firmware_source"),
            "adapter_target_firmware": "3.0.43",
            "calibrated_chain_limit": 6,
            "unsupported": ["USB reamping", "arbitrary footswitch assignment", "automatic master volume"],
            "plan_schema": TonePlan.model_json_schema(),
        }

    def connections(self):
        result = {"phone": {"connected": False}, "audio": {"connected": False}, "busy": self.active_job}
        try:
            phone = self.phone_factory()
            result["phone"] = phone.connect()
            try:
                result["amp_control"] = phone.verify_ble()
            except Exception as exc:
                result["amp_control"] = {"connected": False, "error": str(exc)}
        except Exception as exc:
            result["phone"]["error"] = str(exc)
        try:
            result["audio"] = {"connected": True, **audio.fender_device()}
        except Exception as exc:
            result["audio"]["error"] = str(exc)
        return result

    def create_session(self, request: SessionRequest):
        if self.active_job:
            raise ValueError("Wait for the current operation to finish")
        session = {
            **request.model_dump(),
            "status": "awaiting_plan",
            "section": "Main riff",
            "trials": 0,
            "replacements": 0,
            "plateau": 0,
            "takes": [],
            "baseline_ids": [],
            "best_take": None,
            "best_plan": None,
            "reference_id": None,
            "reference_quality": None,
            "current_plan": None,
            "checkpoint": None,
            "owned": False,
            "setup_recommendation": "Bridge pickup, standard tuning, guitar volume/tone at 10.",
            "evidence": [],
            "limitations": [],
        }
        if request.song.casefold() == "atom city queen" and request.artist.casefold() == "failure":
            session["evidence"] = [
                {"url": "https://www.youtube.com/watch?v=GbDRNvLlMuU", "role": "Studio listening reference"},
                {
                    "url": "https://www.premierguitar.com/artists/failures-monster-comeback?page=2",
                    "role": "Band identifies Rainbow Machine on this song",
                },
            ]
            session["limitations"] = [
                "Rainbow Machine approximation depends on available GT40 effects",
                "No isolated original guitar stem verified",
            ]
        return self.store.put("session", session)

    def session(self, key):
        return self.store.get(key, "session")

    def update(self, session, **changes):
        with self._state_lock:
            latest = self.session(session["id"])
            return self.store.put("session", {**latest, **changes})

    def duplicate(self, session_id, action, request_id, fingerprint=None):
        if not request_id:
            return None
        with self._state_lock:
            for existing in self.store.list("job"):
                if existing.get("request_id") == request_id:
                    if existing["session_id"] != session_id or existing["action"] != action:
                        raise ValueError("Idempotency key already used for another action")
                    if existing.get("fingerprint") != fingerprint:
                        raise ValueError("Idempotency key payload differs from the original request")
                    return existing
        return None

    def submit(self, session_id, action, function, request_id=None, fingerprint=None):
        self.session(session_id)
        with self._state_lock:
            existing = self.duplicate(session_id, action, request_id, fingerprint)
            if existing:
                return existing
            if not self.lock.acquire(blocking=False):
                raise ValueError("Another operation is running; wait or cancel it")
            self.cancel.clear()
            job = self.store.put(
                "job",
                {
                    "session_id": session_id,
                    "action": action,
                    "request_id": request_id,
                    "fingerprint": fingerprint,
                    "status": "queued",
                    "message": "Queued",
                },
            )
            self.active_job = job["id"]

        def progress(message):
            self.store.put("job", {**self.store.get(job["id"]), "message": message, "status": "running"})

        def work():
            try:
                progress("Starting")
                result = function(self.session(session_id), progress)
                if self.cancel.is_set():
                    raise ControlError("Cancelled")
                self.store.put(
                    "job",
                    {
                        **self.store.get(job["id"]),
                        "status": "complete",
                        "message": "Complete",
                        "result": result,
                    },
                )
            except Exception as exc:
                status = "cancelled" if self.cancel.is_set() else "failed"
                logging.getLogger(__name__).exception("Operation %s failed", action)
                self.store.put(
                    "job", {**self.store.get(job["id"]), "status": status, "message": str(exc)[:1800]}
                )
                self.update(self.session(session_id), status="needs_attention")
            finally:
                self.active_job = None
                self.lock.release()

        self.pool.submit(work)
        return job

    def phone(self):
        phone = self.phone_factory(self.cancel)
        phone.launch()
        return phone

    def apply(self, session_id, plan: TonePlan, request_id=None):
        plan.validate_catalog(self.catalog())
        fingerprint = hashlib.sha256(plan.model_dump_json().encode()).hexdigest()
        existing = self.duplicate(session_id, "apply", request_id, fingerprint)
        if existing:
            return existing
        session = self.session(session_id)
        if plan.slot != session["slot"]:
            raise ValueError("Plan slot must match session slot")
        if session["status"] == "complete" or session["trials"] >= session["max_trials"]:
            raise ValueError("Session complete or trial limit reached; create a new session for more trials")
        changing_tone = (
            session["current_plan"] and plan.model_dump()["chain"] != session["current_plan"]["chain"]
        )
        if changing_tone and not session.get("pending_plan"):
            if len(session["baseline_ids"]) < 2:
                raise ValueError("Record two baseline takes before adjusting the verified tone")
            if session["status"] != "awaiting_adjustment":
                raise ValueError("Record a fresh take of the current candidate before another adjustment")

        def work(s, progress):
            if any(
                other["id"] != s["id"] and other["slot"] == s["slot"] and other["owned"]
                for other in self.store.list("session")
            ):
                raise ControlError(
                    "Another session owns this slot; continue that session or restore it first"
                )
            phone = self.phone()
            phone.ensure_editor()
            header = phone.verify_slot(s["slot"])
            if not s["owned"] and header["name"] != "Empty":
                raise ControlError(
                    "New sessions only edit a preset named Empty; existing presets are preserved"
                )
            allowed_names = {"Empty"}
            if s["current_plan"]:
                allowed_names.add(s["current_plan"]["name"])
            if s.get("pending_plan"):
                allowed_names.add(s["pending_plan"]["name"])
            if s["owned"] and header["name"] not in allowed_names:
                full_name = phone.read_full_name()
                if not any(phone.name_matches(full_name, name) for name in allowed_names):
                    raise ControlError("The session's preset was changed externally")
            if not s["checkpoint"]:
                if phone.read_chain() != ["Studio Preamp"]:
                    raise ControlError(
                        "Empty slot contains an unexpected chain; restore or inspect before editing"
                    )
                snapshot = phone.snapshot(s["slot"])
                checkpoint = phone.checkpoint(snapshot)
                s = self.update(s, checkpoint=str(checkpoint), original=snapshot)
            s = self.update(s, owned=True, pending_plan=plan.model_dump())
            progress("Applying and verifying signal chain")
            phone.progress = progress
            observations = phone.apply_plan(plan, s.get("current_plan"))
            self.update(
                s,
                current_plan=plan.model_dump(),
                owned=True,
                status="awaiting_take",
                setup_recommendation=plan.setup_recommendation,
                pending_plan=None,
                limitations=plan.limitations,
            )
            return {"verified": True, "observations": observations, "saved": False}

        fingerprint = hashlib.sha256(plan.model_dump_json().encode()).hexdigest()
        return self.submit(session_id, "apply", work, request_id, fingerprint)

    def save(self, session_id, request_id=None):
        def work(s, progress):
            if not s["owned"] or not s["current_plan"]:
                raise ValueError("No verified preset to save")
            phone = self.phone()
            phone.progress = progress
            phone.ensure_editor()
            if s.get("pending_plan"):
                raise ValueError("Apply and verify the preset again before saving")
            if s["status"] == "needs_attention":
                progress("Rechecking the complete preset before retrying save")
                if phone.header()["slot"] != s["slot"]:
                    progress("Reopening the session's owned preset for save recovery")
                    phone.back()
                    phone.open_slot(s["slot"])
                phone.verify_slot(s["slot"], s["current_plan"]["name"])
                phone.verify_plan(TonePlan.model_validate(s["current_plan"]))
                phone.verify_slot(s["slot"])
            progress("Saving and reloading preset")
            result = phone.save_reload(
                s["slot"], s["current_plan"]["name"], expected=TonePlan.model_validate(s["current_plan"])
            )
            previous = next((p for p in self.store.list("preset") if p["session_id"] == s["id"]), None)
            self.store.put(
                "preset",
                {
                    "session_id": s["id"],
                    "plan": s["current_plan"],
                    "profile": s["profile"],
                    "verified": True,
                    "validation": result,
                    "limitations": s["limitations"],
                },
                key=previous["id"] if previous else None,
            )
            if s["status"] == "needs_attention":
                self.update(s, status="complete" if s.get("accepted") else "awaiting_take")
            return result

        return self.submit(session_id, "save", work, request_id)

    def restore(self, session_id, request_id=None, best=False):
        def work(s, progress):
            phone = self.phone()
            phone.ensure_editor()
            progress("Restoring verified checkpoint")
            if best:
                if not s["best_plan"]:
                    raise ValueError("No measured best preset yet")
                result = phone.apply_plan(TonePlan.model_validate(s["best_plan"]), s["current_plan"])
                self.update(s, current_plan=s["best_plan"])
            else:
                if not s["checkpoint"]:
                    raise ValueError("No original checkpoint")
                result = phone.restore(s["original"], s.get("current_plan"))
                self.update(s, current_plan=None, owned=False, status="restored")
            return {"verified": True, "restored": "best" if best else "original", "observations": result}

        return self.submit(session_id, "restore_best" if best else "restore", work, request_id)

    def stop(self):
        self.cancel.set()
        return {
            "cancellation_requested": True,
            "job_id": self.active_job,
            "message": "Stopping at the next safe boundary. Restore remains a separate action.",
        }

    def attach_reference(self, session_id, path: Path, source: str, quality="mixed"):
        if quality not in {"mixed", "separated", "isolated"}:
            raise ValueError("Unknown reference quality")
        result = audio.file_features(path)
        if not result["valid"]:
            raise ValueError(f"Reference quality check failed: {result['issues']}")
        item = self.store.put(
            "audio",
            {
                "session_id": session_id,
                "role": "reference",
                "path": str(path),
                "source": source,
                "quality": quality,
                "features": result,
            },
        )
        session = self.session(session_id)
        best = None
        for key in session["takes"]:
            take = self.store.get(key, "audio")
            if take["features"]["valid"]:
                comparison = {**audio.distance(result, take["features"]), "reference_id": item["id"]}
                take = self.store.put("audio", {**take, "comparison": comparison})
                if best is None or comparison["distance"] < best["comparison"]["distance"]:
                    best = take
        self.update(
            session,
            reference_id=item["id"],
            reference_quality=quality,
            plateau=0,
            best_take=best["id"] if best else None,
            best_plan=best["plan"] if best else None,
        )
        return {"audio_id": item["id"], "quality": quality, "features": result}

    def acquire(self, session_id, request: ReferenceRequest, request_id=None):
        def work(s, progress):
            progress("Acquiring reference excerpt")
            path = DATA / "audio" / f"{uuid.uuid4()}.wav"
            references.acquire(request, path, self.cancel)
            return self.attach_reference(session_id, path, request.source)

        return self.submit(
            session_id,
            "reference",
            work,
            request_id,
            hashlib.sha256(request.model_dump_json().encode()).hexdigest(),
        )

    def separate(self, session_id, request_id=None):
        def work(s, progress):
            if not s["reference_id"]:
                raise ValueError("Attach a reference first")
            item = self.store.get(s["reference_id"], "audio")
            cache = self.store.list("separation")
            previous = next((c for c in cache if c["input_id"] == item["id"]), None)
            if previous:
                return self.attach_reference(session_id, Path(previous["path"]), item["source"], "separated")
            destination = DATA / "audio" / f"{uuid.uuid4()}.wav"
            progress("Separating guitar locally — this may take several minutes")
            references.separate(Path(item["path"]), destination, self.cancel)
            self.store.put("separation", {"input_id": item["id"], "path": str(destination)})
            return self.attach_reference(session_id, destination, item["source"], "separated")

        return self.submit(session_id, "separate", work, request_id)

    def capture(self, session_id, request: CaptureRequest, request_id=None):
        fingerprint = hashlib.sha256(request.model_dump_json().encode()).hexdigest()
        existing = self.duplicate(session_id, "capture", request_id, fingerprint)
        if existing:
            return existing
        if not request.ready:
            raise ValueError("Press Ready when prepared to play or capture playback")
        if request.role == "reference" and not request.permitted:
            raise ValueError("Confirm permission to process the reference playback")
        s = self.session(session_id)
        if request.role != "reference":
            if (
                not s["current_plan"]
                or s["status"] in {"complete", "needs_attention"}
                or s.get("pending_plan")
            ):
                raise ValueError("Apply a preset before recording")
            if request.role == "trial" and (len(s["baseline_ids"]) < 2 or s["trials"] >= s["max_trials"]):
                raise ValueError("Two baseline takes required, or trial limit reached")
            if request.role == "baseline" and len(s["baseline_ids"]) >= 2:
                raise ValueError("Two baselines already recorded; record a trial")

        def work(s, progress):
            path = DATA / "audio" / f"{uuid.uuid4()}.wav"
            phone = None
            if request.role != "reference":
                phone = self.phone()
                phone.ensure_editor()
                phone.verify_slot(s["slot"])
                phone.verify_ble()
            result = audio.record(path, request.seconds, self.cancel, progress, request.role == "reference")
            if phone:
                phone.verify_slot(s["slot"])
                phone.verify_ble()
            if request.role == "reference":
                return self.attach_reference(session_id, path, "User-started Windows playback capture")
            if s["reference_id"]:
                reference_item = self.store.get(s["reference_id"], "audio")
                if audio.contamination(path, Path(reference_item["path"])):
                    result["valid"] = False
                    result["issues"].append("reference_playback_contamination")
            if request.role != "reference" and s["baseline_ids"]:
                baseline = self.store.get(s["baseline_ids"][0], "audio")["features"]
                if not audio.comparable(baseline, result):
                    result["valid"] = False
                    result["issues"].append("different_phrase_or_tuning")
            item = self.store.put(
                "audio",
                {
                    "session_id": session_id,
                    "role": request.role,
                    "path": str(path),
                    "features": result,
                    "plan": s["current_plan"],
                },
            )
            takes = s["takes"] + [item["id"]]
            if not result["valid"]:
                replacements = s["replacements"] + 1
                self.update(
                    s,
                    takes=takes,
                    replacements=replacements,
                    status="complete" if replacements >= 2 else "awaiting_take",
                )
                if replacements >= 2 and s["best_plan"] and s["best_plan"] != s["current_plan"]:
                    progress("Restoring the best verified candidate after invalid-take limit")
                    phone.apply_plan(TonePlan.model_validate(s["best_plan"]), s["current_plan"])
                    self.update(s, current_plan=s["best_plan"])
                return {
                    "audio_id": item["id"],
                    "valid": False,
                    "issues": result["issues"],
                    "replacements_remaining": max(0, 2 - replacements),
                }
            changes = {"takes": takes}
            if request.role == "baseline":
                baselines = s["baseline_ids"] + [item["id"]]
                changes["baseline_ids"] = baselines
                if len(baselines) == 2:
                    first = self.store.get(baselines[0], "audio")["features"]
                    changes["variability"] = audio.distance(first, result)["distance"]
            else:
                changes["trials"] = s["trials"] + 1
            comparison = None
            if s["reference_id"]:
                reference = self.store.get(s["reference_id"], "audio")["features"]
                comparison = {**audio.distance(reference, result), "reference_id": s["reference_id"]}
                item = self.store.put("audio", {**item, "comparison": comparison})
                best = self.store.get(s["best_take"], "audio") if s["best_take"] else None
                improvement = (
                    best["comparison"]["distance"] - comparison["distance"] if best else float("inf")
                )
                if not best or improvement > 0:
                    changes.update(best_take=item["id"], best_plan=s["current_plan"])
                if request.role == "trial":
                    changes["plateau"] = s["plateau"] + 1 if improvement <= s.get("variability", 0) else 0
            complete = changes.get("trials", s["trials"]) >= s["max_trials"] or changes.get("plateau", 0) >= 2
            changes["status"] = "complete" if complete else "awaiting_adjustment"
            self.update(s, **changes)
            best_plan = changes.get("best_plan", s["best_plan"])
            if complete and best_plan and best_plan != s["current_plan"]:
                progress("Restoring the best verified candidate at the refinement limit")
                phone.apply_plan(TonePlan.model_validate(best_plan), s["current_plan"])
                self.update(s, current_plan=best_plan)
            return {
                "audio_id": item["id"],
                "valid": True,
                "comparison": comparison,
                "stopped": complete,
                "reason": "limit_or_plateau" if complete else None,
            }

        return self.submit(session_id, "capture", work, request_id, fingerprint)

    def feedback(self, session_id, feedback: Feedback):
        s = self.session(session_id)
        if feedback.accepted:
            return self.update(
                s,
                status=s["status"] if s["status"] in {"needs_attention", "restored"} else "complete",
                accepted=True,
            )
        result = {"description": feedback.description, "decision": None}
        if decisions.status().get("enabled"):
            try:
                result["decision"] = decisions.decide(feedback.description)
            except Exception as exc:
                result["decision_error"] = str(exc)
        self.update(s, feedback=result)
        return result

    def comparisons(self, session_id):
        s = self.session(session_id)
        return {
            "reference_id": s["reference_id"],
            "reference_quality": s["reference_quality"],
            "variability": s.get("variability"),
            "best_take": s["best_take"],
            "trials": s["trials"],
            "limit": s["max_trials"],
            "status": s["status"],
            "takes": [
                {
                    "audio_id": key,
                    "valid": item["features"]["valid"],
                    "issues": item["features"]["issues"],
                    "comparison": item.get("comparison"),
                }
                for key in s["takes"]
                for item in [self.store.get(key, "audio")]
            ],
        }

    def candidate(self, session_id, direction=None):
        s = self.session(session_id)
        if not s["current_plan"] or len(s["baseline_ids"]) < 2:
            raise ValueError("Apply a plan and record two baseline takes first")
        if s["trials"] >= s["max_trials"] or s["status"] == "complete":
            raise ValueError("Refinement has stopped")
        plan = TonePlan.model_validate(s.get("best_plan") or s["current_plan"])
        amp = next(b for b in plan.chain if b.kind == "amp")
        selected = amp
        # Select a bounded EQ/gain candidate. Spatial/pitch changes require expert selection of supported parameters.
        parameters = [p for p in ("gain", "treble", "middle", "bass") if p in amp.parameters]
        if not parameters:
            raise ValueError("No calibrated adjustable amp parameters in this plan")
        mapping = {
            "brighter": ("treble", 0.5),
            "darker": ("treble", -0.5),
            "gain_up": ("gain", 0.5),
            "gain_down": ("gain", -0.5),
        }
        if direction in {"modulation_up", "modulation_down"}:
            selected = next((b for b in plan.chain if b.kind == "effect" and "depth" in b.parameters), None)
            if selected is None:
                raise ValueError("No calibrated modulation depth in this plan")
            name, step = "depth", 0.5 if direction == "modulation_up" else -0.5
        elif direction in {"delay_up", "delay_down"}:
            selected = next((b for b in plan.chain if b.kind == "effect" and "delay" in b.parameters), None)
            if selected is None:
                raise ValueError("No calibrated delay time in this plan")
            name, step = "delay", 10 if direction == "delay_up" else -10
        elif direction in mapping:
            name, step = mapping[direction]
        else:
            name = parameters[s["trials"] % len(parameters)]
            step = 0.5 if (s["trials"] // len(parameters)) % 2 == 0 else -0.5
        if name not in selected.parameters:
            raise ValueError("Requested parameter is not calibrated")
        spec = next(m for m in self.catalog() if m.name == selected.model)
        limits = next(p for p in spec.parameters if p.name == name)
        selected.parameters[name] = round(
            float(np_clip(float(selected.parameters[name]) + step, limits.minimum, limits.maximum)), 1
        )
        if (
            selected.parameters[name]
            == (s.get("best_plan") or s["current_plan"])["chain"][plan.chain.index(selected)]["parameters"][
                name
            ]
        ):
            raise ValueError("Parameter already at the requested bound; choose another adjustment")
        plan.validate_catalog(self.catalog())
        plan.rationale = f"Bounded local candidate: {name} changed by {step}; record a new take to evaluate."
        return {"plan": plan.model_dump(), "automatic_application": False}


def np_clip(value, minimum, maximum):
    return min(maximum, max(minimum, value))
