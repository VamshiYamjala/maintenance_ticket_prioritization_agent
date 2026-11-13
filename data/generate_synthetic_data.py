"""
Reproducible, seeded synthetic maintenance ticket generator for renewable-energy O&M.

Generates `data/maintenance_tickets_synthetic.csv` (420 tickets across solar, wind,
hydro, and grid assets) with varied vocabulary, domain abbreviations (WTG, SCADA,
ICR, MPPT, RTU), realistic typos, casing variations, and noise.

NOTE: The 6 bundled tickets in `data/maintenance_tickets.csv` are never modified.
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 42
OUTPUT_PATH = Path(__file__).resolve().parent / "maintenance_tickets_synthetic.csv"

# Category specs: (allowed_assets, severity_weights, equipment_prefixes, symptoms, contexts, qualifiers)
CATEGORY_SPECS = {
    "inverter_thermal": {
        "assets": ["solar"],
        "severities": [("low", 0.10), ("medium", 0.25), ("high", 0.45), ("critical", 0.20)],
        "equip": ["Inverter {n}", "INV-{n:02d}", "Central Inverter {n}", "String Inverter {n}", "ICR-{m} Inverter {n}"],
        "symptoms": [
            "tripping repeatedly after noon",
            "IGBT over-temperature alarm active",
            "cooling fan fault and thermal derating",
            "heatsink temp exceeding threshold",
            "cabinet overheating during peak irradiance",
            "DC-link thermal trip observed",
            "MPPT module thermal shutdown",
            "exhaust blower stalled causing high temp",
        ],
        "contexts": [
            "at Block {b}",
            "in ICR-{m}",
            "under high ambient load",
            "since 11:30 hrs",
            "during peak generation",
            "on string array {b}",
        ],
        "qualifiers": {
            "low": ["minor warning only, no trip yet", "temp slightly elevated, fan running"],
            "medium": ["output derated by 15%", "intermittent warning on HMI"],
            "high": ["tripped twice today, needs inspection", "high temperature alarm visible on SCADA"],
            "critical": ["continuous thermal shutdown with burning smell", "repeated trip causing full block outage"],
        },
    },
    "gearbox_vibration": {
        "assets": ["wind"],
        "severities": [("low", 0.05), ("medium", 0.20), ("high", 0.35), ("critical", 0.40)],
        "equip": ["WTG-{n:02d}", "Turbine WTG-{n}", "Wind Turbine {n}", "Unit WTG-{n:02d}"],
        "symptoms": [
            "gearbox vibration elevated above baseline",
            "abnormal grinding noise from main gearbox",
            "high-speed shaft bearing vibration spike",
            "CMS accelerometer showing gear mesh anomaly",
            "nacelle vibration alarm triggered",
            "planetary stage vibration increasing",
            "lube oil temp rising with gearbox rumble",
        ],
        "contexts": [
            "at Feeder {b}",
            "in Sector {b}",
            "above 11 m/s wind speed",
            "logged by CMS sensor",
            "over the last 3 shifts",
            "during rated power operation",
        ],
        "qualifiers": {
            "low": ["slight upward trend in CMS log", "minor vibration blip, within limit"],
            "medium": ["moderate vibration increase, monitor closely", "periodic hum at high RPM"],
            "high": ["high vibration warning, derate advised", "bearing temp +12C above normal"],
            "critical": ["severe knocking noise, immediate shutdown risk", "critical vibration trip, metallic debris suspected"],
        },
    },
    "inspection_compliance": {
        "assets": ["hydro", "solar", "wind", "grid"],
        "severities": [("low", 0.35), ("medium", 0.45), ("high", 0.15), ("critical", 0.05)],
        "equip": ["Spillway Gate {n}", "Substation Bay {n}", "Block {n}", "WTG-{n:02d}", "Intake Valve {n}"],
        "symptoms": [
            "quarterly safety inspection checklist pending",
            "annual statutory audit sign-off overdue",
            "preventive maintenance PM log incomplete",
            "fire extinguisher tag expired during walkdown",
            "earthing resistance test report missing",
            "relay calibration certificate due this week",
            "penstock valve inspection form not uploaded",
        ],
        "contexts": [
            "for Q{q} compliance",
            "at Site-{b}",
            "in maintenance register",
            "flagged by EHS team",
            "before monsoon readiness audit",
            "in CMMS portal",
        ],
        "qualifiers": {
            "low": ["routine documentation update needed", "scheduled for next week"],
            "medium": ["pending supervisor sign-off", "due within 48 hours"],
            "high": ["overdue by 10 days, audit upcoming", "regulatory notice deadline approaching"],
            "critical": ["mandatory safety interlock sign-off expired, operation hold"],
        },
    },
    "data_gap": {
        "assets": ["solar", "wind", "hydro", "grid"],
        "severities": [("low", 0.30), ("medium", 0.45), ("high", 0.20), ("critical", 0.05)],
        "equip": ["Block {n}", "SCADA Server {n}", "Met Mast {n}", "ICR-{m}", "Feeder {n}"],
        "symptoms": [
            "SCADA telemetry missing",
            "historian showing flatline values",
            "generation meter data gap observed",
            "weather station pyranometer feed dropped",
            "active power tags showing NaN",
            "energy export counter frozen",
            "hourly SCADA log not updating",
        ],
        "contexts": [
            "for last {h} hours",
            "since midnight",
            "after network switch reboot",
            "on plant dashboard",
            "in EMS historian",
        ],
        "qualifiers": {
            "low": ["brief 15-min gap, auto-recovered", "single non-critical sensor tag"],
            "medium": ["missing for two hours, field generation normal", "polling delay on backup link"],
            "high": ["full block telemetry blind for 6+ hours", "revenue meter data missing for billing"],
            "critical": ["complete plant SCADA blind, dispatch visibility lost"],
        },
    },
    "pitch_system": {
        "assets": ["wind"],
        "severities": [("low", 0.10), ("medium", 0.25), ("high", 0.45), ("critical", 0.20)],
        "equip": ["WTG-{n:02d}", "Turbine {n}", "Blade-B Pitch Drive WTG-{n}"],
        "symptoms": [
            "blade pitch angle mismatch error",
            "pitch battery backup low voltage alarm",
            "hydraulic pitch actuator pressure drop",
            "pitch motor overcurrent fault",
            "blade 2 slow to feather during gust",
            "pitch encoder feedback erratic",
        ],
        "contexts": [
            "after high wind gust event",
            "during cut-out wind speed",
            "at Ridge-{b}",
            "following grid voltage dip",
            "on morning startup",
        ],
        "qualifiers": {
            "low": ["minor pitch calibration offset", "warning cleared on reset"],
            "medium": ["slower pitch response noted in log", "battery test warning"],
            "high": ["turbine paused due to pitch fault", "repeated pitch error after gusts"],
            "critical": ["blade stuck unable to feather in high wind, overspeed hazard"],
        },
    },
    "grid_curtailment": {
        "assets": ["grid", "solar", "wind"],
        "severities": [("low", 0.20), ("medium", 0.45), ("high", 0.25), ("critical", 0.10)],
        "equip": ["PSS-{n}", "Pooling Substation {n}", "Feeder Bay {n}", "PPC Controller {n}"],
        "symptoms": [
            "curtailment instruction not reflected in dashboard",
            "SLDC setpoint command rejected by PPC",
            "active power limit stuck at 60%",
            "reactive power compensation out of band",
            "grid frequency droop response delayed",
            "curtailment schedule mismatch with SCADA",
        ],
        "contexts": [
            "at 220kV Pooling Station",
            "during afternoon ramp",
            "for Feeder {b}",
            "after SLDC dispatch signal",
            "on generation control screen",
        ],
        "qualifiers": {
            "low": ["display lag only, actual export matches setpoint", "minor UI sync delay"],
            "medium": ["operator manual override required", "setpoint discrepancy of 5 MW"],
            "high": ["unintended generation loss due to stuck curtailment", "grid compliance deviation alert"],
            "critical": ["grid trip imminent if export limit not enforced immediately"],
        },
    },
    "transformer_fault": {
        "assets": ["grid", "solar", "wind", "hydro"],
        "severities": [("low", 0.05), ("medium", 0.15), ("high", 0.40), ("critical", 0.40)],
        "equip": ["IDT-{n}", "Power Transformer TX-{n}", "Step-up Transformer {n}", "Main TX-{n:02d}"],
        "symptoms": [
            "Buchholz relay gas alarm triggered",
            "winding temperature high alarm",
            "transformer oil level low",
            "oil leakage observed near radiator flange",
            "OLTC tap changer stuck between steps",
            "differential protection pre-alarm",
        ],
        "contexts": [
            "at 33/220kV yard",
            "in Block {b} ICR",
            "under full load",
            "during afternoon ambient peak",
        ],
        "qualifiers": {
            "low": ["minor oil level float switch check needed"],
            "medium": ["winding temp 5C above baseline, cooling fans on"],
            "high": ["oil leak active, containment tray filling", "Buchholz alarm requires DGA sample"],
            "critical": ["oil temp critical with smoke/fumes near bushing, trip risk", "Buchholz trip and heavy oil leak"],
        },
    },
    "tracker_fault": {
        "assets": ["solar"],
        "severities": [("low", 0.35), ("medium", 0.45), ("high", 0.15), ("critical", 0.05)],
        "equip": ["Tracker Row {n}", "NCU-{n}", "Single-Axis Tracker T-{n:02d}"],
        "symptoms": [
            "tracker row stuck at morning tilt angle",
            "slew drive motor stalled",
            "wind stow command not executed",
            "inclinometer reading drifted by 8 degrees",
            "tracker controller battery depleted",
        ],
        "contexts": [
            "in Block {b}",
            "across {m} rows",
            "causing inter-row shading",
            "after overnight storm",
        ],
        "qualifiers": {
            "low": ["single row affected, minor shading loss"],
            "medium": ["4 rows misaligned, 3% block loss"],
            "high": ["entire block failed to stow during high wind alert"],
            "critical": ["structural torque tube damage after wind stow failure"],
        },
    },
    "communication_loss": {
        "assets": ["solar", "wind", "hydro", "grid"],
        "severities": [("low", 0.25), ("medium", 0.40), ("high", 0.25), ("critical", 0.10)],
        "equip": ["RTU-{n}", "Fiber Ring {n}", "MODBUS Gateway {n}", "PLC-{n}"],
        "symptoms": [
            "RTU offline / ping timeout",
            "MODBUS RS485 link dropping packets",
            "fiber optic ring break alarm",
            "telemetry gateway unreachable",
            "remote breaker status showing comm fail",
        ],
        "contexts": [
            "at Substation {b}",
            "for Block {b}",
            "since 09:15 hrs",
            "after trenching work nearby",
        ],
        "qualifiers": {
            "low": ["intermittent packet loss <5%"],
            "medium": ["backup cellular link active, primary down"],
            "high": ["remote control unavailable for feeder {b}"],
            "critical": ["total substation RTU comm loss, protection visibility lost"],
        },
    },
    "safety_incident": {
        "assets": ["solar", "wind", "hydro", "grid"],
        "severities": [("low", 0.0), ("medium", 0.05), ("high", 0.25), ("critical", 0.70)],
        "equip": ["Switchgear Panel {n}", "WTG-{n:02d} Base", "ICR-{m}", "Spillway Deck {n}", "Combiner Box {n}"],
        "symptoms": [
            "smoke observed from DC combiner box",
            "arc flash hazard reported near breaker panel",
            "technician minor slip/near-miss during climb",
            "sparks and burning smell inside switchgear",
            "fire alarm activated in battery/inverter room",
            "oil spill near transformer bund",
        ],
        "contexts": [
            "area cordoned off",
            "during switching operation",
            "reported by site patrol",
            "emergency isolation requested",
        ],
        "qualifiers": {
            "medium": ["near-miss logged, no injury or damage"],
            "high": ["hazard isolated, EHS inspection mandatory before restart"],
            "critical": ["active smoke/fire risk, immediate LOTO and emergency response required", "arc flash / burn hazard, personnel evacuated"],
        },
    },
}

TYPOS = [
    ("temperature", "temprature"),
    ("vibration", "vibraton"),
    ("inverter", "invertr"),
    ("gearbox", "gearbx"),
    ("curtailment", "curtailmnt"),
    ("inspection", "inspectn"),
    ("maintenance", "maintenace"),
    ("transformer", "transfrmer"),
    ("missing", "mising"),
    ("pressure", "presure"),
]


def inject_noise(text: str, rng: random.Random) -> str:
    """Apply realistic casing, abbreviation, and occasional typo noise."""
    if rng.random() < 0.18:
        for clean, typo in TYPOS:
            if clean in text.lower() and rng.random() < 0.4:
                text = text.replace(clean, typo, 1)
                break
    r = rng.random()
    if r < 0.12:
        text = text.lower()
    elif r < 0.18:
        text = text.upper()
    if rng.random() < 0.20:
        prefixes = ["URGENT: ", "Shift note - ", "SCADA alert: ", "Field report: ", ""]
        text = rng.choice(prefixes) + text
    if rng.random() < 0.15:
        text = text + rng.choice([" pls check", " -- logged by operator", " [auto-ticket]", " ASAP"])
    return " ".join(text.split())


def weighted_choice(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    items = [c[0] for c in choices]
    weights = [c[1] for c in choices]
    return rng.choices(items, weights=weights, k=1)[0]


def generate_dataset(n_tickets: int = 420, seed: int = SEED) -> list[dict[str, str]]:
    rng = random.Random(seed)
    categories = list(CATEGORY_SPECS.keys())
    # Balanced-ish but realistic weights (more inverter/data/inspection/gearbox, fewer safety_incident)
    cat_weights = [0.14, 0.12, 0.11, 0.12, 0.10, 0.10, 0.10, 0.08, 0.08, 0.05]

    seen_descriptions: set[str] = set()
    rows: list[dict[str, str]] = []
    idx = 1

    while len(rows) < n_tickets:
        cat = rng.choices(categories, weights=cat_weights, k=1)[0]
        spec = CATEGORY_SPECS[cat]
        asset = rng.choice(spec["assets"])
        severity = weighted_choice(rng, spec["severities"])

        equip = rng.choice(spec["equip"]).format(
            n=rng.randint(1, 24),
            m=rng.randint(1, 6),
        )
        symptom = rng.choice(spec["symptoms"])
        context = rng.choice(spec["contexts"]).format(
            b=rng.randint(1, 8),
            m=rng.randint(2, 6),
            q=rng.randint(1, 4),
            h=rng.randint(2, 12),
        )
        qual_list = spec["qualifiers"].get(severity) or list(spec["qualifiers"].values())[0]
        qualifier = rng.choice(qual_list)

        patterns = [
            f"{equip} {symptom} {context}; {qualifier}",
            f"{symptom} on {equip} ({context}) - {qualifier}",
            f"{equip}: {symptom}, {qualifier} {context}",
            f"{context}, {equip} showing {symptom}. {qualifier}",
        ]
        desc = inject_noise(rng.choice(patterns), rng)
        norm_key = desc.lower().strip()
        if norm_key in seen_descriptions:
            continue
        seen_descriptions.add(norm_key)

        rows.append({
            "ticket_id": f"SYN-{idx:04d}",
            "asset_type": asset,
            "description": desc,
            "target_severity": severity,
            "target_category": cat,
            "data_source": "synthetic_seeded_42",
        })
        idx += 1

    return rows


def main() -> None:
    rows = generate_dataset()
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        f.write("# SYNTHETIC DATASET (seed=42) generated by data/generate_synthetic_data.py - NOT real CMMS data\n")
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ticket_id",
                "asset_type",
                "description",
                "target_severity",
                "target_category",
                "data_source",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} synthetic tickets at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
