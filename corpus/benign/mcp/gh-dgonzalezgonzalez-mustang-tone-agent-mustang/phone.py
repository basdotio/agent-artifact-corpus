from __future__ import annotations

import io
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event

import cv2
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

from .config import DATA, adb_path


class ControlError(RuntimeError):
    pass


@dataclass
class Text:
    text: str
    x: float
    y: float
    confidence: float


class Phone:
    """Adapter for Tone 5.1.3 portrait screens. No unverified taps or shell tools exposed to agents."""

    def __init__(self, cancel: Event | None = None):
        self.adb = adb_path()
        self.cancel = cancel or Event()
        self.ocr = RapidOCR(
            intra_op_num_threads=4, inter_op_num_threads=1, det_limit_type="max", det_limit_side_len=1600
        )
        self.size = (1080, 2400)
        self._serial = None

    def run(self, *args: str, timeout: float = 20) -> bytes:
        if self.cancel.is_set():
            raise ControlError("Operation cancelled")
        command = [self.adb]
        if self._serial:
            command += ["-s", self._serial]
        result = subprocess.run(command + list(args), capture_output=True, timeout=timeout)
        if result.returncode:
            raise ControlError(result.stderr.decode(errors="replace")[:200])
        return result.stdout

    def connect(self) -> dict:
        lines = self.run("devices").decode().splitlines()[1:]
        connected = [line.split()[0] for line in lines if line.endswith("\tdevice")]
        if len(connected) != 1:
            raise ControlError("Connect exactly one unlocked, USB-debugging-authorized Android phone.")
        self._serial = connected[0]
        package = self.run("shell", "dumpsys", "package", "com.fender.tone").decode()
        version = re.search(r"versionName=(\S+)", package)
        if not version or not version[1].startswith("5.1.3."):
            raise ControlError(
                "Unsupported Fender Tone version. Recalibrate the screen adapter before writes."
            )
        model = self.run("shell", "getprop", "ro.product.model").decode().strip()
        return {
            "connected": True,
            "phone": model,
            "tone_version": version[1],
            "adapter": "tone-5.1.3-portrait",
        }

    def screenshot(self) -> np.ndarray:
        # Screen timeout can occur while OCR is working. WAKEUP never toggles an awake
        # display off and does not change the user's timeout or bypass a secure lock.
        now = time.monotonic()
        if now - getattr(self, "_last_screen_wake", float("-inf")) >= 10:
            self.run("shell", "input", "keyevent", "224")
            self._last_screen_wake = now
            time.sleep(0.25)
        image = np.array(Image.open(io.BytesIO(self.run("exec-out", "screencap", "-p"))).convert("RGB"))
        h, w = image.shape[:2]
        if h / w < 1.8:
            raise ControlError("Phone must be in portrait orientation.")
        self.size = w, h
        return image

    def verify_ble(self) -> dict:
        dump = self.run("shell", "dumpsys", "bluetooth_manager").decode(errors="replace")
        connected = any(
            re.match(r"\s*id:\s*\d+\s+address:", line)
            and "ch_state: GATT_CH_OPEN" in line
            and "com.fender.tone" in line
            for line in dump.splitlines()
        )
        if not connected:
            raise ControlError("Fender Tone Bluetooth control connection is not verified; reconnect the amp")
        return {"connected": True, "evidence": "Active Android GATT channel owned by Fender Tone"}

    def texts(self, image: np.ndarray | None = None) -> list[Text]:
        if image is None:
            image = self.screenshot()
        result, _ = self.ocr(image)
        h, w = image.shape[:2]
        return [
            Text(
                str(label),
                float(np.mean(np.array(box)[:, 0])) / w,
                float(np.mean(np.array(box)[:, 1])) / h,
                float(score),
            )
            for box, label, score in (result or [])
        ]

    def region_texts(self, top: float, bottom: float) -> list[Text]:
        image = self.screenshot()
        height, width = image.shape[:2]
        offset = int(top * height)
        result, _ = self.ocr(image[offset : int(bottom * height)])
        return [
            Text(
                str(label),
                float(np.mean(np.array(box)[:, 0])) / width,
                (float(np.mean(np.array(box)[:, 1])) + offset) / height,
                float(score),
            )
            for box, label, score in (result or [])
        ]

    def carousel_name(self) -> str:
        labels = [t for t in self.region_texts(0.88, 0.95) if t.confidence > 0.9]
        if not labels or len(labels) > 3 or max(t.y for t in labels) - min(t.y for t in labels) > 0.015:
            raise ControlError("Model carousel selection not reliably readable")
        return " ".join(t.text.strip() for t in sorted(labels, key=lambda t: t.x))

    def add_nodes(self) -> list[float]:
        image = self.screenshot()
        h, w = image.shape[:2]
        crop = cv2.cvtColor(image[int(h * 0.47) : int(h * 0.53)], cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(crop, 45, 100)
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        nodes = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            if 0.025 * w < width < 0.05 * w and 0.8 < width / max(height, 1) < 1.2:
                center = (y + height / 2) / h + 0.47
                if 0.496 < center < 0.509:
                    position = (x + width / 2) / w
                    if not any(abs(position - previous) < 0.02 for previous in nodes):
                        nodes.append(position)
        if not nodes:
            raise ControlError("No insertion nodes recognized")
        return sorted(nodes)

    def inspect(self) -> dict:
        self.connect()
        image = self.screenshot()
        Image.fromarray(image).save(DATA / "screens/current.png")
        return {
            "screen": [
                {"text": t.text, "x": round(t.x, 3), "y": round(t.y, 3), "confidence": round(t.confidence, 3)}
                for t in self.texts(image)
            ]
        }

    def tap(self, x: float, y: float):
        w, h = self.size
        self.run("shell", "input", "tap", str(int(x * w)), str(int(y * h)))
        time.sleep(0.35)

    def swipe(self, x: float, y: float, end_x: float, end_y: float, duration: int = 400):
        w, h = self.size
        self.run(
            "shell",
            "input",
            "swipe",
            str(int(x * w)),
            str(int(y * h)),
            str(int(end_x * w)),
            str(int(end_y * h)),
            str(duration),
        )
        time.sleep(0.25)

    def back(self):
        # Tone's internal navigation ignores Android BACK (which exits the app).
        self.tap(0.065, 0.063)

    def tap_text(self, label: str, *, exact: bool = True, min_y=0.0, max_y=1.0):
        matches = [
            t
            for t in self.texts()
            if t.confidence >= 0.8
            and min_y <= t.y <= max_y
            and (t.text.casefold() == label.casefold() if exact else label.casefold() in t.text.casefold())
        ]
        if len(matches) != 1:
            raise ControlError(f"Expected one '{label}' control; found {len(matches)}. No action taken.")
        self.tap(matches[0].x, matches[0].y)

    def launch(self):
        self.connect()
        self.run("shell", "input", "keyevent", "224")
        self.run("shell", "wm", "dismiss-keyguard")
        self.run("shell", "cmd", "statusbar", "collapse")
        self.run("shell", "am", "start", "-n", "com.fender.tone/.MainActivity")
        time.sleep(0.6)

    def header(self) -> dict:
        for attempt in range(3):
            try:
                return self._header_once()
            except ControlError:
                if attempt == 2:
                    raise
                time.sleep(0.4)
        raise ControlError("Preset editor not recognized")

    def _header_once(self) -> dict:
        texts = self.region_texts(0.035, 0.085) + self.region_texts(0.91, 0.99)
        top = [t.text for t in texts if 0.035 < t.y < 0.09 and t.confidence > 0.8]
        joined = " ".join(top)
        match = re.search(r"\b(\d{1,3})\b", joined)
        if (
            not match
            or not any(t.text.casefold() == "save" for t in texts)
            or not (
                any(t.text.casefold() in {"add block", "amp settings"} for t in texts)
                or {"remove", "replace"}.issubset({t.text.casefold() for t in texts})
            )
        ):
            raise ControlError("Preset editor not recognized. Open the intended preset in Fender Tone.")
        title = joined[match.end() :].replace("Save", "").strip()
        self._editor_footer = {t.text.casefold() for t in texts if t.y > 0.9}
        return {"slot": int(match[1]), "name": title}

    def ensure_editor(self):
        self.dismiss_parameter()
        for _ in range(4):
            try:
                return self.header()
            except ControlError:
                texts = self.texts()
                if self.is_save_dialog(texts):
                    self.tap_text("CANCEL", min_y=0.9)
                    time.sleep(0.6)
                    continue
                if any(
                    t.text.replace(" ", "").casefold() == "mypresets" and 0.09 < t.y < 0.14 for t in texts
                ):
                    current = next(
                        (t for t in texts if 0.04 < t.y < 0.085 and re.fullmatch(r"\d{1,3}", t.text)), None
                    )
                    row = [
                        t
                        for t in texts
                        if current and re.match(rf"^{current.text}\s*\D", t.text) and 0.16 < t.y < 0.9
                    ]
                    if len(row) != 1:
                        raise ControlError("Current preset row not visible in My Presets")
                    # The selected row's pencil opens the editor; its text only selects the preset.
                    self.tap(0.88, row[0].y)
                    time.sleep(0.6)
                else:
                    raise ControlError("Unrecognized phone screen; no navigation tap sent. Reopen Fender Tone.")
        raise ControlError("Could not reach a recognized preset editor.")

    def verify_slot(self, slot: int, expected_name: str | None = None):
        header = self.header()
        if header["slot"] != slot:
            raise ControlError(f"Preset slot/name mismatch: {header}. Refusing to edit.")
        if expected_name and header["name"] != expected_name:
            observed = self.read_full_name()
            if not self.name_matches(observed, expected_name):
                raise ControlError(f"Full preset name mismatch: {observed!r}. Refusing to edit.")
            if self.header()["slot"] != slot:
                raise ControlError("Preset changed during full-name inspection")
            header["name"] = expected_name
        return header

    @staticmethod
    def name_matches(observed: str, expected: str) -> bool:
        # Tone's font renders the capital I in the AI suffix as a vertical stroke;
        # RapidOCR consistently reads that particular suffix as 'Al'. No truncated text is accepted.
        return observed == expected or (expected.endswith(" AI") and observed == expected[:-1] + "l")

    def save_field_name(self) -> str:
        parts = [
            t
            for t in self.region_texts(0.09, 0.13)
            if t.x < 0.8 and t.confidence > 0.95 and t.text.casefold() != "clear"
        ]
        if not parts or max(t.y for t in parts) - min(t.y for t in parts) > 0.015:
            raise ControlError("Full preset name not reliably readable")
        return " ".join(t.text.strip() for t in sorted(parts, key=lambda t: t.x))

    def read_full_name(self) -> str:
        self.tap_text("Save", max_y=0.09)
        time.sleep(0.7)
        if not self.is_save_dialog(self.texts()):
            raise ControlError("Full-name inspection dialog not recognized")
        name = self.save_field_name()
        self.tap_text("CANCEL", min_y=0.9)
        time.sleep(0.6)
        return name

    def preset_row(self, slot: int) -> Text:
        for _ in range(16):
            texts = self.texts()
            if not any(
                t.text.replace(" ", "").casefold() == "mypresets" and 0.09 < t.y < 0.14 for t in texts
            ):
                raise ControlError("My Presets list not recognized")
            rows = [
                (int(m[1]), t)
                for t in texts
                if 0.17 < t.y < 0.9 and t.confidence > 0.9
                for m in [re.match(r"^(\d{1,3})\s*\D", t.text)]
                if m
            ]
            found = next((t for number, t in rows if number == slot), None)
            if found:
                time.sleep(0.6)
                check = [
                    t
                    for t in self.region_texts(0.17, 0.90)
                    if re.match(rf"^{slot}\s*\D", t.text) and t.confidence > 0.9
                ]
                if len(check) == 1 and abs(check[0].y - found.y) < 0.003:
                    return check[0]
                continue
            if not rows:
                raise ControlError("Preset list rows not readable")
            upward = slot > max(number for number, _ in rows)
            self.swipe(0.65, 0.72 if upward else 0.40, 0.65, 0.48 if upward else 0.64, 1100)
            time.sleep(1)  # Let list scrolling settle before choosing a row.
        raise ControlError("Preset not found within bounded list navigation")

    def open_slot(self, slot: int):
        row = self.preset_row(slot)
        self.tap(row.x, row.y)
        time.sleep(0.6)
        numbers = [t for t in self.region_texts(0.035, 0.085) if re.fullmatch(r"\d{1,3}", t.text)]
        if len(numbers) != 1 or int(numbers[0].text) != slot:
            raise ControlError("Preset selection failed readback")
        row = self.preset_row(slot)
        self.tap(0.88, row.y)
        time.sleep(0.6)
        self.verify_slot(slot)

    def empty_reload_neighbor(self, slot: int) -> Text:
        # Returning from the editor can leave the list scrolled before the saved
        # slot. Find and stabilize an adjacent row rather than relying on visibility.
        for neighbor in (slot + 1, slot - 1):
            if 1 <= neighbor <= 200:
                row = self.preset_row(neighbor)
                if row.confidence > 0.9 and re.fullmatch(rf"{neighbor}\s+Empty", row.text):
                    return row
        raise ControlError("No verified adjacent empty preset available for reload")

    def knobs(self) -> list[dict]:
        image = self.screenshot()
        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, np.array([12, 30, 160]), np.array([45, 130, 255]))
        mask[: int(h * 0.55)] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        circles = []
        for c in contours:
            (x, y), radius = cv2.minEnclosingCircle(c)
            if 0.035 * w < radius < 0.1 * w and cv2.contourArea(c) > 0.55 * np.pi * radius**2:
                circles.append((x, y, radius))
        labels = [t for t in self.texts(image) if 0.55 < t.y < 0.9]
        knobs = []
        for x, y, radius in sorted(circles):
            candidates = [t for t in labels if abs(t.x - x / w) < 0.08 and 0 < y / h - t.y < 0.07]
            if len(candidates) != 1:
                continue
            # Indicator: dark radial line inside the knob. Fit dark pixels, avoiding center/end decorations.
            yy, xx = np.mgrid[0:h, 0:w]
            r = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
            dark = (image.mean(axis=2) < 85) & (r > 0.25 * radius) & (r < 0.85 * radius)
            cy, cx = np.where(dark)
            if len(cx) < 10:
                continue
            angle = float(np.degrees(np.arctan2(np.mean(cx) - x, y - np.mean(cy))))
            value = float(np.clip((angle + 150) / 300, 0, 1))
            knobs.append(
                {
                    "parameter": candidates[0].text.lower(),
                    "x": x / w,
                    "y": y / h,
                    "position": round(value, 3),
                    "angle": round(angle, 1),
                }
            )
        return knobs

    def show_amp(self):
        self.ensure_editor()
        if any(t.text == "Amp Settings" for t in self.region_texts(0.91, 0.99)):
            return
        positions = self.block_positions()
        for x in positions:
            self.chain_view()
            self.tap(x, 0.503)
            if any(t.text == "Amp Settings" for t in self.region_texts(0.91, 0.99)):
                return
        raise ControlError("Amplifier block not recognized")

    def chain_view(self):
        self.ensure_editor()
        if "add block" not in self._editor_footer:
            self.tap(0.95, 0.85)
        if not any(t.text == "Add Block" for t in self.region_texts(0.91, 0.99)):
            raise ControlError("Signal chain screen not recognized")

    def block_positions(self) -> list[float]:
        self.chain_view()
        self.tap_text("Add Block", min_y=0.9)
        if not any(t.text == "Select Node To Add" for t in self.region_texts(0.04, 0.085)):
            raise ControlError("Insertion screen not recognized")
        nodes = self.add_nodes()
        self.back()
        if not 2 <= len(nodes) <= 7:
            raise ControlError("Chain length exceeds calibrated navigation limits")
        return [(a + b) / 2 for a, b in zip(nodes[:-1], nodes[1:])]

    def read_chain(self) -> list[str]:
        initial = self.header()["slot"]
        positions = self.block_positions()
        result = []
        for x in positions:
            self.chain_view()
            self.verify_slot(initial)
            self.tap(x, 0.503)
            result.append(self.selected_amp())
            getattr(self, "progress", lambda _: None)(f"Read signal chain: {' → '.join(result)}")
        self.chain_view()
        self.verify_slot(initial)
        return result

    def select_block(self, index: int, expected: str):
        positions = self.block_positions()
        if not 0 <= index < len(positions):
            raise ControlError("Block index outside observed chain")
        self.tap(positions[index], 0.503)
        time.sleep(0.6)  # The model title appears before the footer finishes its animation.
        if self.selected_amp() != expected:
            raise ControlError("Block selection failed model readback")

    def add_effect(self, slot: int, model: str, category: str, index: int):
        self.chain_view()
        self.verify_slot(slot)
        self.tap_text("Add Block", min_y=0.9)
        nodes = self.add_nodes()
        if not 0 <= index < len(nodes):
            raise ControlError("Insertion index outside observed nodes")
        self.tap(nodes[index], 0.503)
        self.tap_text(category, min_y=0.1, max_y=0.15)
        self.choose_carousel(model)
        if self.selected_amp() != model:
            raise ControlError("Effect insertion failed model readback")

    def remove_effect(self, slot: int, index: int, expected: str):
        self.select_block(index, expected)
        self.verify_slot(slot)
        self.tap_text("Remove", min_y=0.9)

    def effect_enabled(self) -> bool:
        controls = [
            t
            for t in self.region_texts(0.92, 0.98)
            if 0.35 < t.x < 0.65 and t.confidence > 0.9 and t.text.casefold() in {"bypass", "bypassed"}
        ]
        if len(controls) != 1:
            raise ControlError("Effect bypass state not reliably readable")
        return controls[0].text.casefold() == "bypass"

    def set_effect_enabled(self, slot: int, enabled: bool):
        self.verify_ble()
        self.verify_slot(slot)
        actual = self.effect_enabled()
        if actual != enabled:
            self.tap_text("BYPASS" if actual else "BYPASSED", min_y=0.9)
            if self.effect_enabled() != enabled:
                raise ControlError("Effect bypass change failed readback")
        self.verify_slot(slot)
        return {"enabled": enabled, "verified": True}

    def set_knob_position(self, slot: int, parameter: str, target: float) -> dict:
        if not 0 <= target <= 1:
            raise ControlError("Knob position must be between 0 and 1")
        self.verify_slot(slot)
        self.dismiss_parameter()
        for _ in range(8):
            items = [k for k in self.knobs() if k["parameter"] == parameter.lower()]
            if len(items) != 1:
                raise ControlError(f"Knob '{parameter}' not recognized")
            knob = items[0]
            delta = target - knob["position"]
            if abs(delta) <= 0.012:
                return {
                    "parameter": parameter,
                    "requested": target,
                    "observed": knob["position"],
                    "unit": "knob_position",
                    "verified": True,
                }
            # Small bounded vertical drag; feedback controls the next step, never blind absolute coordinates.
            step = float(np.clip(delta * 0.12, -0.035, 0.035))
            self.swipe(knob["x"], knob["y"], knob["x"], knob["y"] - step)
            self.dismiss_parameter()
        raise ControlError(f"'{parameter}' did not converge to requested position")

    def panel(self, parameter: str) -> float:
        pattern = r"(-?\d+(?:\.\d+)?)\s*(?:ms|Hz|dB)?"
        for _ in range(3):
            texts = self.region_texts(0.47, 0.56)
            if not any(t.text.casefold() == parameter.casefold() and 0.47 < t.y < 0.51 for t in texts):
                time.sleep(0.4)
                continue
            values = [
                t.text
                for t in texts
                if 0.35 < t.x < 0.96
                and 0.51 < t.y < 0.56
                and t.confidence > 0.95
                and re.fullmatch(pattern, t.text)
            ]
            if len(values) == 1:
                return float(re.fullmatch(pattern, values[0])[1])
            image = self.screenshot()
            h, w = image.shape[:2]
            crop = image[int(h * 0.508) : int(h * 0.565), int(w * 0.40) : int(w * 0.95)]
            result, _ = self.ocr(cv2.resize(crop, None, fx=2, fy=2))
            values = [
                str(label)
                for _, label, confidence in (result or [])
                if confidence > 0.95 and re.fullmatch(pattern, str(label))
            ]
            if len(values) == 1:
                return float(re.fullmatch(pattern, values[0])[1])
            time.sleep(0.3)
        raise ControlError("Numeric parameter value not reliably readable")

    def dismiss_parameter(self):
        texts = self.region_texts(0.47, 0.56)
        bottom = self.region_texts(0.92, 0.98)
        # The numeric drawer replaces the footer with +/- controls. A pedal's miniature logo
        # must never be mistaken for a drawer label/value pair.
        parameter_names = {
            "volume", "gain", "treble", "middle", "bass", "mix", "pitch", "delay",
            "feedback", "tone", "level", "depth", "phase",
        }
        if any(
            t.text.casefold() in parameter_names and 0.485 < t.y < 0.505 and 0.60 < t.x < 0.74
            for t in texts
        ) and not any(
            t.text.casefold() in {"add block", "amp settings", "remove", "replace"} for t in bottom
        ):
            if self.selected_amp() not in {
                "Studio Preamp", "British 70s", "Chromatic Pitch Shifter", "Sine Chorus"
            }:
                raise ControlError("Unrecognized parameter screen; no dismissal tap sent")
            self.tap(0.15, 0.11)
            time.sleep(0.4)

    def native_value(self, parameter: str) -> float:
        self.dismiss_parameter()
        labels = [t for t in self.texts() if t.text.casefold() == parameter.casefold() and 0.25 < t.y < 0.9]
        if len(labels) != 1:
            raise ControlError(f"Parameter label '{parameter}' not found")
        offsets = {
            "Studio Preamp": 0.039,
            "British 70s": -0.047,
            "Chromatic Pitch Shifter": -0.052,
            "Sine Chorus": -0.052,
        }
        model = self.selected_amp()
        if model not in offsets:
            raise ControlError(f"Parameter layout for '{model}' needs calibration")
        self.tap(labels[0].x, labels[0].y + offsets[model])
        time.sleep(0.8)  # Wait for the numeric drawer's opening animation before capturing pixels.
        return self.panel(parameter)

    def selected_amp(self) -> str:
        labels = [t for t in self.region_texts(0.09, 0.125) if t.x < 0.75 and t.confidence > 0.9]
        if not labels or max(t.y for t in labels) - min(t.y for t in labels) > 0.015:
            raise ControlError("Amplifier model not reliably readable")
        return " ".join(t.text.strip() for t in sorted(labels, key=lambda t: t.x))

    def choose_carousel(self, model: str):
        for direction in (1, -1):
            previous = None
            for _ in range(48):
                name = self.carousel_name()
                if name == model:
                    self.tap_text("Confirm", max_y=0.09)
                    time.sleep(0.6)
                    return
                if name == previous:
                    break
                previous = name
                # Selecting the adjacent thumbnail advances exactly one item; a swipe can skip models.
                self.tap(0.8 if direction == 1 else 0.2, 0.5)
        raise ControlError(f"Model '{model}' not found within the bounded carousel search")

    def replace_amp(self, slot: int, model: str):
        self.show_amp()
        self.verify_slot(slot)
        if self.selected_amp() == model:
            return
        self.tap_text("Replace", min_y=0.9)
        self.choose_carousel(model)
        if self.selected_amp() != model:
            raise ControlError("Amplifier replacement failed readback")

    def set_native(self, slot: int, parameter: str, target: float, *, minimum=0.0, maximum=10.0, step=0.1):
        self.verify_ble()
        self.verify_slot(slot)
        if not minimum <= target <= maximum:
            raise ControlError("Parameter outside calibrated range")
        value = self.native_value(parameter)
        calibration = None
        for _ in range(10):
            count = round(abs(target - value) / step)
            if count == 0:
                if abs(value - target) > step * 0.2:
                    raise ControlError("Requested value is between calibrated increments")
                self.dismiss_parameter()
                return {"parameter": parameter, "requested": target, "observed": value, "verified": True}
            if count > 100:
                # The drawer maps the END position to an absolute value, rather than a relative drag.
                # Measure two points on this specific parameter before interpolating; always read back.
                if calibration is None:
                    samples = []
                    for y in (0.60, 0.65):
                        self.swipe(0.67, 0.72, 0.67, y, 600)
                        time.sleep(0.3)
                        samples.append(self.panel(parameter))
                    slope = (samples[1] - samples[0]) / 0.05
                    if slope >= -step or abs(slope) > (maximum - minimum) * 3:
                        raise ControlError("Absolute slider calibration was inconsistent")
                    calibration = (slope, samples[0] - slope * 0.60)
                slope, intercept = calibration
                y = float(np.clip((target - intercept) / slope, 0.15, 0.88))
                previous = value
                self.swipe(0.67, 0.72, 0.67, y, 600)
                time.sleep(0.5)
                value = self.panel(parameter)
                calibration = (slope, value - slope * y)
                if abs(value - target) >= abs(previous - target):
                    raise ControlError("Absolute slider did not improve the requested setting")
                continue
            # The +/- buttons have been observed to move amp controls by exactly 0.1.
            x = 0.883 if target > value else 0.413
            for _ in range(count):
                self.tap(x, 0.947)
            value = self.panel(parameter)
        raise ControlError("Numeric value did not reach requested target")

    def snapshot(self, slot: int) -> dict:
        header = self.verify_slot(slot)
        self.show_amp()
        state = {
            **header,
            "knobs": self.knobs(),
            "adapter": "tone-5.1.3-portrait",
            "amp": self.selected_amp(),
        }
        if len(state["knobs"]) < 3:
            raise ControlError("Incomplete knob snapshot")
        state["parameters"] = {k["parameter"]: self.native_value(k["parameter"]) for k in state["knobs"]}
        self.dismiss_parameter()
        return state

    def checkpoint(self, snapshot: dict) -> Path:
        path = DATA / "checkpoints" / f"slot-{snapshot['slot']}-{time.time_ns()}.json"
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        return path

    def save_reload(self, slot: int, name: str, expected=None) -> dict:
        self.verify_ble()
        if not re.fullmatch(r"[A-Za-z0-9 _.-]{1,28}", name):
            raise ControlError("Preset names use 1–28 ASCII letters, numbers, spaces, '.', '-' or '_'")
        self.dismiss_parameter()
        self.verify_slot(slot)
        self.tap_text("Save", max_y=0.09)
        time.sleep(0.7)
        texts = self.texts()
        if not self.is_save_dialog(texts):
            raise ControlError("Save dialog not recognized")
        if not self.name_matches(self.save_field_name(), name):
            self.tap_text("clear")
            self.tap(0.4, 0.11)
            time.sleep(0.8)
            self.run("shell", "input", "text", name.replace(" ", "%s"))
            time.sleep(0.5)
            self.hide_keyboard()
        row = self.save_row(slot)
        self.tap(row.x, row.y)
        self.tap_text("SAVE", min_y=0.9)
        time.sleep(1)
        self.verify_slot(slot, name)
        getattr(self, "progress", lambda _: None)("Saved; switching away and reloading the preset")
        self.back()
        time.sleep(0.6)
        safe = self.empty_reload_neighbor(slot)
        # Select an untouched empty neighbor, then select our saved preset: this actually reloads the amp.
        self.tap(safe.x, safe.y)
        time.sleep(0.5)
        if not any(t.text == safe.text.split()[0] and 0.04 < t.y < 0.085 for t in self.texts()):
            raise ControlError("Neighbor selection failed readback")
        self.open_slot(slot)
        self.verify_slot(slot, name)
        readback = self.verify_plan(expected) if expected else {"verified": True, "chain": self.read_chain()}
        self.verify_slot(slot)
        self.verify_ble()
        return {
            "slot": slot,
            "name": name,
            "saved": True,
            "reloaded": True,
            "verified": True,
            "readback": readback,
        }

    def save_row(self, slot: int) -> Text:
        for _ in range(12):
            texts = self.texts()
            if not self.is_save_dialog(texts):
                raise ControlError("Save location dialog not recognized; no save performed")
            rows = [
                (int(m[1]), t)
                for t in texts
                if 0.22 < t.y < 0.89 and t.confidence > 0.9
                for m in [re.match(r"^\*?\s*(\d{1,3})\s*\D", t.text)]
                if m
            ]
            found = next((t for number, t in rows if number == slot), None)
            if found:
                time.sleep(0.5)
                check = [t for t in self.region_texts(0.22, 0.89) if re.match(rf"^\*?\s*{slot}\s*\D", t.text)]
                if len(check) == 1 and abs(check[0].y - found.y) < 0.003:
                    return check[0]
                continue
            if not rows:
                raise ControlError("Save location rows not readable; no save performed")
            upward = slot > max(number for number, _ in rows)
            self.swipe(0.65, 0.72 if upward else 0.4, 0.65, 0.52 if upward else 0.6, 1100)
            time.sleep(1)
        raise ControlError("Intended save location not found within bounded navigation")

    @staticmethod
    def is_save_dialog(texts: list[Text]) -> bool:
        heading = any(
            t.text == "Preset Name" or "save location in my presets" in t.text.casefold() for t in texts
        )
        footer = {t.text.upper() for t in texts if t.y > 0.9 and t.confidence > 0.9}
        return heading and {"SAVE", "CANCEL"}.issubset(footer)

    def hide_keyboard(self):
        status = self.run("shell", "dumpsys", "input_method").decode(errors="replace")
        if "mInputShown=true" not in status:
            return
        buttons = [
            t
            for t in self.region_texts(0.8, 0.95)
            if t.x > 0.75 and t.confidence > 0.9 and t.text.casefold() in {"hecho", "done", "ok"}
        ]
        if len(buttons) != 1:
            raise ControlError("Keyboard Done control needs calibration; no Back event sent")
        self.tap(buttons[0].x, buttons[0].y)
        time.sleep(0.8)
        status = self.run("shell", "dumpsys", "input_method").decode(errors="replace")
        if "mInputShown=true" in status:
            raise ControlError("Keyboard dismissal failed readback")

    def apply_plan(self, plan, previous=None) -> dict:
        from .config import ROOT
        from .models import ModelSpec

        catalog = [
            ModelSpec.model_validate(x) for x in json.loads((ROOT / "catalog/tone-5.1.3.json").read_text())
        ]
        plan.validate_catalog(catalog)
        self.verify_ble()
        if any(not b.enabled and b.kind == "amp" for b in plan.chain):
            raise ControlError("Amplifier bypass has not been calibrated")
        self.verify_slot(plan.slot)
        desired = [b.model for b in plan.chain if b.kind != "cabinet"]
        if any(b.kind == "cabinet" for b in plan.chain):
            raise ControlError(
                "Explicit cabinet replacement has not been calibrated; use the verified amp default"
            )
        actual = self.read_chain()
        changed = actual != desired

        def insert(block, index):
            category = {"Chromatic Pitch Shifter": "FILT+PITCH", "Sine Chorus": "MOD"}.get(block.model)
            if not category:
                raise ControlError("Effect category needs calibration")
            getattr(self, "progress", lambda _: None)(f"Adding and verifying {block.model}")
            self.add_effect(plan.slot, block.model, category, index)

        remaining = iter(desired)
        subsequence = all(any(candidate == name for candidate in remaining) for name in actual)
        if actual != desired and subsequence:
            for index, block in enumerate(plan.chain):
                if index >= len(actual) or actual[index] != block.model:
                    if block.kind != "effect":
                        raise ControlError("Cannot insert an extra amplifier")
                    insert(block, index)
                    actual.insert(index, block.model)
        elif actual != desired:
            self.show_amp()
            amp_name = self.selected_amp()
            for index in reversed(range(len(actual))):
                if actual[index] != amp_name:
                    self.remove_effect(plan.slot, index, actual[index])
                    expected = actual[:index] + actual[index + 1 :]
                    actual = self.read_chain()
                    if actual != expected:
                        raise ControlError("Effect removal failed chain readback")
            self.replace_amp(plan.slot, next(b.model for b in plan.chain if b.kind == "amp"))
            for index, block in enumerate(plan.chain):
                if block.kind == "effect":
                    insert(block, index)
        observed_chain = self.read_chain() if changed else actual
        if observed_chain != desired:
            raise ControlError(f"Final signal chain differs: observed {observed_chain}; requested {desired}")
        observations = []
        for index, block in enumerate(plan.chain):
            self.select_block(index, block.model)
            if block.kind == "effect":
                self.set_effect_enabled(plan.slot, block.enabled)
            spec = next(m for m in catalog if m.name == block.model and m.kind == block.kind)
            for parameter, value in block.parameters.items():
                getattr(self, "progress", lambda _: None)(
                    f"Setting and verifying {block.model}: {parameter} {value}"
                )
                ps = next(p for p in spec.parameters if p.name == parameter)
                if isinstance(value, str):
                    raise ControlError("Enumeration control has not been calibrated")
                observations.append(
                    self.set_native(
                        plan.slot,
                        parameter,
                        value,
                        minimum=ps.minimum,
                        maximum=ps.maximum,
                        step=ps.step or 0.1,
                    )
                )
        self.chain_view()
        self.verify_slot(plan.slot)
        self.verify_ble()
        return {"chain": desired, "parameters": observations, "verified": True}

    def verify_plan(self, plan) -> dict:
        if self.read_chain() != [b.model for b in plan.chain]:
            raise ControlError("Saved signal chain failed readback")
        values = []
        for index, block in enumerate(plan.chain):
            self.select_block(index, block.model)
            if block.kind == "effect" and self.effect_enabled() != block.enabled:
                raise ControlError(f"Saved effect bypass failed readback: {block.model}")
            for parameter, target in block.parameters.items():
                getattr(self, "progress", lambda _: None)(f"Reading {block.model}: {parameter}")
                value = self.native_value(parameter)
                if isinstance(target, str) or abs(value - target) > 0.051:
                    raise ControlError(f"Saved parameter failed readback: {block.model}.{parameter}")
                values.append({"model": block.model, "parameter": parameter, "observed": value})
            self.dismiss_parameter()
        self.chain_view()
        return {"verified": True, "parameters": values}

    def restore(self, original: dict, current=None):
        from .models import Block, TonePlan

        plan = TonePlan(
            name=original["name"],
            slot=original["slot"],
            chain=[Block(model=original["amp"], kind="amp", parameters=original["parameters"])],
        )
        result = self.apply_plan(plan, current)
        result["saved"] = self.save_reload(plan.slot, plan.name, expected=plan)
        return result
