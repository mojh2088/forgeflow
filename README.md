# ForgeFlow

A manufacturing data platform on AWS, built to demonstrate how project-based fabrication
data — pressure vessel and structural steel jobs — becomes AI-ready across a Bronze →
Silver → Gold lakehouse, at zero infrastructure cost.

Built in public. Data is synthetic and anonymized; no client names, real project data,
or proprietary information appears anywhere in this repo (see [Anonymization](#anonymization)).

## The problem

Fabricators running pressure-vessel (PED) and structural-steel (SSD) work don't run
continuous production lines — they run discrete, contract-based jobs, each with its own
material procurement, stage-by-stage fabrication sequence, QC gates, and delivery
commitment. That data model doesn't fit off-the-shelf manufacturing analytics templates,
which mostly assume continuous-line production.

ForgeFlow models the job-based reality directly: every dataset is keyed on `job_id`,
from contract award through final site inspection, so the questions that actually matter —
which jobs are trending late, which delay reason codes recur, which inspection types
catch the most defects — are answerable with a join, not a workaround.

## Architecture

```
Python generator  →  S3 Bronze (JSON, partitioned by dt=award_date)
                          ↓
                    Glue Crawler → Glue Data Catalog
                          ↓
                    Athena (ad-hoc query, data-quality checks)
                          ↓
                    dbt (Silver: typed/validated/deduplicated)
                          ↓
                    dbt (Gold: on-time delivery rate, defect rate by
                         inspection type, material-delay-to-slip correlation)
                          ↓
                    Athena (BI-ready, dashboard queries)
```

Five datasets, all keyed on `job_id`:

| Dataset | Grain | Purpose |
|---|---|---|
| `projects` | 1 row / job | Job master: division, type, code standard, award/target delivery dates |
| `material_tracking` | 1 row / material event | PO issued → transit → received → issued-to-fab, planned vs actual |
| `fabrication_stages` | 1 row / stage | Division-specific stage sequence with planned/actual dates |
| `qc_inspections` | 1 row / inspection | Inspection events gated to specific stages, result, defect code |
| `delivery_variance` | 1 row / job | Planned vs actual ship date, variance, root-cause reason code |

## Key decisions

**No Kinesis, no Redshift.** The original design used Kinesis for streaming ingestion and
Redshift for the warehouse layer. Neither is available on AWS's free tier, and running
them continuously isn't justified for a synthetic dataset at this scale. Replaced with a
Python batch simulator writing directly to S3, and Athena as the query engine — a
genuinely zero-cost architecture that still exercises the same partitioning, crawling,
and analytical-query patterns a streaming setup would.

**Job-based, not continuous-line.** Most public manufacturing datasets model continuous
production. Real fabrication shops — especially PED/SSD divisions — run project-based
jobs. Modeling that correctly (variable stage sequences per division, subcontracted
ancillary items, job-level delivery variance) is the actual differentiator here.

**Synthetic data, not a demo toy.** The generator produces internally consistent,
realistic data: material delays that cascade into stage delays, QC failures that gate
downstream stages, delay reason codes that correlate with the actual cause. It's built
to survive real data-quality checks (see [Build log](#build-log)), not just to have
rows in a table.

## How to run

```bash
git clone https://github.com/mojh2088/forgeflow.git
cd forgeflow
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repo root:

```
BRONZE_BUCKET=<your-bronze-bucket-name>
AWS_REGION=us-east-1
```

Generate data (dry run first, to sanity-check locally before touching S3):

```bash
python3 data_generator/generate_fabrication.py --jobs 40 --dry-run \
  --out-dir datasets/forgeflow_fabrication/raw

python3 data_generator/generate_fabrication.py --jobs 40 \
  --out-dir datasets/forgeflow_fabrication/raw
```

Then run a Glue Crawler against `s3://<your-bronze-bucket>/forgeflow_fabrication/`
to populate the Data Catalog, and query via Athena.

## Results

- Bronze layer live: 40 jobs, ~190 material events, ~480 fabrication stage rows,
  ~220 QC inspections, 40 delivery-variance rows.
- Data-quality verified: uniqueness on all primary keys (`job_id`, `event_id`,
  `inspection_id`) and referential integrity across all 5 tables, confirmed via Athena.
- Silver/Gold dbt models: in progress.

## Build log

**Job ID collision bug (fixed).** An early Bronze generation run produced 44 project
rows instead of the expected 40. Root cause: `job_id` was built from a loop counter local
to a single script invocation, with no memory of prior runs — and the local write function
appended rather than overwrote, so an earlier `--dry-run` test's output silently sat
underneath a later real run's output in the same partition files. Two runs, same counter
range, colliding IDs on two jobs. Fixed by making `job_id` globally unique (uuid suffix)
and making writes overwrite-on-first-touch per run. Verified clean across all 5 tables
afterward — zero collisions, zero orphaned foreign keys.

## Anonymization

No client names, real project identifiers, or proprietary data appear in this repo.
All data is synthetically generated. Division names (PED/SSD), stage sequences, and
code standards (ASME, API, AISC) reflect general industry practice, not any specific
employer's internal processes.
