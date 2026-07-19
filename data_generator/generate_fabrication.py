#!/usr/bin/env python3
"""
Job-based fabrication data generator for ForgeFlow.

Models project-based (job-based) fabrication, not continuous production —
mirrors how PED (pressure vessels / process equipment) and SSD (structural
steel) divisions actually run: a contract is awarded as a job, material is
tracked against that job, fabrication moves through a division-specific
stage sequence, QC gates each stage, and the whole thing rolls up into a
planned-vs-actual delivery variance per job.

Four datasets, all keyed on job_id:
  - projects            : job master (one row per job)
  - material_tracking    : PO -> transit -> received -> issued events per job
  - fabrication_stages   : stage-by-stage planned/actual dates per job
  - qc_inspections        : inspection events gating each stage
  - delivery_variance    : one row per job, planned vs actual ship date

Local output lands in datasets/forgeflow_fabrication/raw/, partitioned by
dt=<job creation date>, mirroring the eventual S3 Bronze layout:
  s3://forgeflow-bronze-711266489387/forgeflow_fabrication/<dataset>/dt=YYYY-MM-DD/

Usage:
    python generate_fabrication.py --jobs 40
    python generate_fabrication.py --jobs 10 --dry-run
"""

import argparse
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("BRONZE_BUCKET", "forgeflow-bronze")
REGION = os.getenv("AWS_REGION", "us-east-1")
PREFIX = "forgeflow_fabrication"

# ---------------------------------------------------------------------------
# Reference data — anonymized, no real client names (NDA rule)
# ---------------------------------------------------------------------------

CLIENT_TYPES = [
    "EPC Contractor - Petrochemical",
    "EPC Contractor - Oil & Gas Refining",
    "EPC Contractor - Fertilizer Plant",
    "EPC Contractor - Power & Desalination",
    "EPC Contractor - High-Rise Building",
    "EPC Contractor - Cement Plant",
]

DIVISIONS = ["PED", "SSD"]

PED_JOB_TYPES = [
    ("Pressure Vessel", "ASME VIII Div.1"),
    ("Pressure Vessel", "ASME VIII Div.2"),
    ("Heat Exchanger", "ASME VIII Div.1"),
    ("Reactor", "ASME VIII Div.2"),
    ("Column / Tower", "ASME VIII Div.1"),
    ("Separator", "API 620"),
    ("Storage Tank", "API 650"),
]

SSD_JOB_TYPES = [
    ("Pipe Rack", "AISC"),
    ("Equipment Support Structure", "AISC"),
    ("Built-Up Girders & Columns", "AISC"),
    ("Structural Steel Building", "AISC"),
    ("High-Rise Building Steel", "AISC"),
]

MATERIAL_TYPES_PED = [
    "Carbon Steel Plate", "Stainless Steel Plate", "Alloy Steel Plate",
    "Cladded Plate", "Inconel Sheet", "Pipe / Nozzle Stock", "Fasteners & Gaskets",
]
MATERIAL_TYPES_SSD = [
    "Structural Steel Plate", "Wide Flange Sections", "Hollow Sections",
    "Handrail Stock", "Grating Material", "Bolts & Fasteners", "Galvanizing Zinc Stock",
]

# Division-specific fabrication stage sequences
PED_STAGES = [
    "cutting", "forming_rolling", "welding", "nitrogen_purging",
    "nde_inspection", "scaffolding", "blasting", "painting", "insulation",
    "final_inspection_workshop", "transportation_to_site", "final_inspection_site",
]

# SSD heavy structures fabricated in-house end-to-end
SSD_STAGES_HEAVY = [
    "cutting", "drilling", "welding", "in_house_inspection",
    "third_party_inspection", "galvanizing", "painting",
    "final_inspection_workshop", "transportation_to_site", "final_inspection_site",
]

# SSD small/ancillary items (handrails, monkey ladders) subcontracted out
SSD_STAGES_SUBCONTRACTED = [
    "cutting", "drilling", "welding", "in_house_inspection",
    "transport_to_subcontractor", "subcontractor_fabrication",
    "galvanizing", "painting", "return_from_subcontractor",
    "third_party_inspection", "final_inspection_workshop",
    "transportation_to_site", "final_inspection_site",
]

SSD_ANCILLARY_ITEM_TYPES = ["Handrails", "Monkey Ladders", "Stair Stringers", "Grating Panels"]

INSPECTION_TYPES = {
    "nde_inspection": ["Weld NDT - RT", "Weld NDT - UT", "Weld NDT - MT"],
    "nitrogen_purging": ["Purge Verification"],
    "in_house_inspection": ["Dimensional Check", "Weld Visual"],
    "third_party_inspection": ["Weld NDT - RT", "Dimensional Check", "Material Certification Review"],
    "final_inspection_workshop": ["Hydro Test", "Final Dimensional", "Final Visual"],
    "final_inspection_site": ["Site Fit-Up Check", "Site Dimensional", "Erection Verification"],
    "painting": ["Paint DFT Check"],
    "galvanizing": ["Galvanizing Thickness Check"],
}

DEFECT_CODES = [
    "Weld Porosity", "Undercut", "Dimensional Tolerance Exceeded",
    "Coating Thickness Below Spec", "Material Cert Mismatch",
    "Surface Contamination", "Bolt Torque Non-Conformance",
]

DELAY_REASON_CODES = [
    "material_delay", "fabrication_backlog", "qc_hold",
    "subcontractor_delay", "logistics_transport", "client_revision",
]


def iso_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def iso_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Job master generation
# ---------------------------------------------------------------------------

def gen_projects(num_jobs: int, start_date: datetime):
    jobs = []
    for i in range(num_jobs):
        division = random.choices(DIVISIONS, weights=[0.45, 0.55])[0]
        job_type, code_standard = random.choice(PED_JOB_TYPES if division == "PED" else SSD_JOB_TYPES)
        award_date = start_date + timedelta(days=random.randint(0, 180))
        # duration scales with complexity: PED vessels ~8-16 weeks, SSD ~10-20 weeks
        duration_weeks = random.randint(8, 16) if division == "PED" else random.randint(10, 20)
        target_delivery = award_date + timedelta(weeks=duration_weeks)

        job = {
            "job_id": f"{division}-{2025 + (i // 60)}-{1000 + i}-{uuid.uuid4().hex[:6]}",
            "division": division,
            "client_type": random.choice(CLIENT_TYPES),
            "job_type": job_type,
            "code_standard": code_standard,
            "contract_award_date": iso_date(award_date),
            "target_delivery_date": iso_date(target_delivery),
            "planned_duration_weeks": duration_weeks,
            "scope_qty": random.randint(1, 6) if division == "PED" else random.randint(50, 400),
            "scope_unit": "vessels" if division == "PED" else "tons",
            "has_subcontracted_ancillary": (division == "SSD" and random.random() < 0.6),
            "created_at": iso_ts(award_date),
        }
        jobs.append(job)
    return jobs


# ---------------------------------------------------------------------------
# Material tracking
# ---------------------------------------------------------------------------

def gen_material_tracking(job):
    events = []
    award = datetime.strptime(job["contract_award_date"], "%Y-%m-%d")
    materials = MATERIAL_TYPES_PED if job["division"] == "PED" else MATERIAL_TYPES_SSD
    num_materials = random.randint(3, 6)

    for mat in random.sample(materials, min(num_materials, len(materials))):
        po_issued = award + timedelta(days=random.randint(2, 14))
        lead_time_days = random.randint(14, 60)
        planned_arrival = po_issued + timedelta(days=lead_time_days)
        # 30% chance of delay
        is_delayed = random.random() < 0.30
        delay_days = random.randint(3, 25) if is_delayed else 0
        actual_arrival = planned_arrival + timedelta(days=delay_days)
        issued_to_fab = actual_arrival + timedelta(days=random.randint(1, 4))

        events.append({
            "event_id": str(uuid.uuid4()),
            "job_id": job["job_id"],
            "division": job["division"],
            "material_type": mat,
            "po_issued_date": iso_date(po_issued),
            "planned_arrival_date": iso_date(planned_arrival),
            "actual_arrival_date": iso_date(actual_arrival),
            "issued_to_fabrication_date": iso_date(issued_to_fab),
            "delay_days": delay_days,
            "status": "issued_to_fabrication",
            "timestamp": iso_ts(issued_to_fab),
        })
    return events


# ---------------------------------------------------------------------------
# Fabrication stages
# ---------------------------------------------------------------------------

def stage_sequence_for(job):
    if job["division"] == "PED":
        return PED_STAGES
    return SSD_STAGES_SUBCONTRACTED if job["has_subcontracted_ancillary"] else SSD_STAGES_HEAVY


def gen_fabrication_stages(job, material_events):
    stages = stage_sequence_for(job)
    # fabrication can't start until material is issued; use latest issued_to_fabrication date
    if material_events:
        fab_start = max(datetime.strptime(m["issued_to_fabrication_date"], "%Y-%m-%d") for m in material_events)
    else:
        fab_start = datetime.strptime(job["contract_award_date"], "%Y-%m-%d") + timedelta(days=14)

    rows = []
    cursor = fab_start
    for stage in stages:
        planned_days = random.randint(2, 10)
        # QC-related and subcontractor stages more prone to slippage
        slip_prone = stage in ("qc_hold", "third_party_inspection", "transport_to_subcontractor",
                                "subcontractor_fabrication", "nde_inspection")
        actual_days = planned_days + (random.randint(1, 6) if (slip_prone and random.random() < 0.35) else 0)

        planned_start = cursor
        planned_end = planned_start + timedelta(days=planned_days)
        actual_start = planned_start + timedelta(days=random.randint(0, 2))
        actual_end = actual_start + timedelta(days=actual_days)

        item_scope = None
        if stage in ("transport_to_subcontractor", "subcontractor_fabrication", "return_from_subcontractor"):
            item_scope = random.choice(SSD_ANCILLARY_ITEM_TYPES)

        rows.append({
            "event_id": str(uuid.uuid4()),
            "job_id": job["job_id"],
            "division": job["division"],
            "stage": stage,
            "item_scope": item_scope,
            "planned_start_date": iso_date(planned_start),
            "planned_end_date": iso_date(planned_end),
            "actual_start_date": iso_date(actual_start),
            "actual_end_date": iso_date(actual_end),
            "duration_days_actual": actual_days,
            "status": "complete",
            "timestamp": iso_ts(actual_end),
        })
        cursor = actual_end
    return rows


# ---------------------------------------------------------------------------
# QC inspections — gated off specific stages
# ---------------------------------------------------------------------------

def gen_qc_inspections(job, stage_rows):
    rows = []
    for stage_row in stage_rows:
        stage = stage_row["stage"]
        if stage not in INSPECTION_TYPES:
            continue

        inspection_type = random.choice(INSPECTION_TYPES[stage])
        third_party = stage == "third_party_inspection" or (
            stage == "final_inspection_workshop" and random.random() < 0.4
        )
        inspector_type = "third_party" if third_party else "in_house"
        inspector_level = random.choice(["II", "III"])

        passed = random.random() < 0.85
        result = "PASS" if passed else random.choice(["FAIL", "HOLD"])
        defect_code = None if passed else random.choice(DEFECT_CODES)
        disposition = None
        if not passed:
            disposition = random.choice(["repair_and_reinspect", "reject", "accept_with_concession"])

        rows.append({
            "inspection_id": str(uuid.uuid4()),
            "job_id": job["job_id"],
            "division": job["division"],
            "stage": stage,
            "inspection_type": inspection_type,
            "inspector_type": inspector_type,
            "inspector_level": inspector_level,
            "inspector_id": f"{'TPI' if third_party else 'QA'}-{random.randint(100, 299)}",
            "result": result,
            "defect_code": defect_code,
            "disposition": disposition,
            "inspection_date": stage_row["actual_end_date"],
            "timestamp": stage_row["timestamp"],
        })
    return rows


# ---------------------------------------------------------------------------
# Delivery variance — one row per job
# ---------------------------------------------------------------------------

def gen_delivery_variance(job, stage_rows, material_events):
    target = datetime.strptime(job["target_delivery_date"], "%Y-%m-%d")
    final_stage = next((s for s in stage_rows if s["stage"] == "transportation_to_site"), stage_rows[-1])
    actual_ship = datetime.strptime(final_stage["actual_end_date"], "%Y-%m-%d")

    variance_days = (actual_ship - target).days

    reason_code = None
    if variance_days > 0:
        max_material_delay = max((m["delay_days"] for m in material_events), default=0)
        if max_material_delay >= 10:
            reason_code = "material_delay"
        elif job["division"] == "SSD" and job["has_subcontracted_ancillary"]:
            reason_code = random.choice(["subcontractor_delay", "fabrication_backlog"])
        else:
            reason_code = random.choice(DELAY_REASON_CODES)

    return {
        "job_id": job["job_id"],
        "division": job["division"],
        "target_delivery_date": job["target_delivery_date"],
        "actual_ship_date": iso_date(actual_ship),
        "variance_days": variance_days,
        "on_time": variance_days <= 0,
        "reason_code": reason_code,
        "timestamp": iso_ts(actual_ship),
    }


# ---------------------------------------------------------------------------
# Write / upload
# ---------------------------------------------------------------------------

def write_local(dataset_name: str, rows: list, out_dir: Path, partition_date: str, seen_files: set):
    dir_path = out_dir / dataset_name / f"dt={partition_date}"
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{dataset_name}_{partition_date}.json"
    # First write THIS RUN makes to a given file -> overwrite, clearing out
    # any stale data left behind by a prior --dry-run or earlier partial run.
    # Subsequent writes in the same run to the same partition file (multiple
    # jobs sharing an award date) append as before.
    mode = "w" if str(file_path) not in seen_files else "a"
    seen_files.add(str(file_path))
    with open(file_path, mode) as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return file_path


def upload_to_s3(file_path: Path, dataset_name: str, partition_date: str):
    key = f"{PREFIX}/{dataset_name}/dt={partition_date}/{file_path.name}"
    s3 = boto3.client("s3", region_name=REGION)
    s3.upload_file(str(file_path), BUCKET, key)
    return f"s3://{BUCKET}/{key}"


def main():
    parser = argparse.ArgumentParser(description="Job-based fabrication data generator")
    parser.add_argument("--jobs", type=int, default=30, help="Number of jobs (projects) to generate")
    parser.add_argument("--start", type=str, default=None, help="Earliest contract award date YYYY-MM-DD (default: 1 year ago)")
    parser.add_argument("--dry-run", action="store_true", help="Write local JSON only, skip S3 upload")
    parser.add_argument("--out-dir", type=str, default="../datasets/forgeflow_fabrication/raw", help="Local output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=None)
    else:
        start_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)

    jobs = gen_projects(args.jobs, start_date)

    counts = {"projects": 0, "material_tracking": 0, "fabrication_stages": 0, "qc_inspections": 0, "delivery_variance": 0}
    uploaded_files = set()
    seen_files = set()

    for job in jobs:
        award_date_str = job["contract_award_date"]

        material_events = gen_material_tracking(job)
        stage_rows = gen_fabrication_stages(job, material_events)
        qc_rows = gen_qc_inspections(job, stage_rows)
        delivery_row = gen_delivery_variance(job, stage_rows, material_events)

        datasets = {
            "projects": [job],
            "material_tracking": material_events,
            "fabrication_stages": stage_rows,
            "qc_inspections": qc_rows,
            "delivery_variance": [delivery_row],
        }

        for name, rows in datasets.items():
            counts[name] += len(rows)
            file_path = write_local(name, rows, out_dir, award_date_str, seen_files)
            if not args.dry_run:
                s3_uri = upload_to_s3(file_path, name, award_date_str)
                uploaded_files.add(s3_uri.rsplit("/", 1)[0])

    print(f"Generated {counts['projects']} jobs across PED and SSD divisions (requested: {args.jobs}).\n")
    for name, count in counts.items():
        print(f"  {name}: {count} rows")
    print(f"\nLocal output: {out_dir.resolve()}")
    if args.dry_run:
        print("Dry run — nothing uploaded to S3.")
    else:
        print(f"Uploaded to s3://{BUCKET}/{PREFIX}/ ({len(uploaded_files)} partitions touched)")


if __name__ == "__main__":
    main()
