with source as (
    select * from {{ source('forgeflow_bronze', 'qc_inspections') }}
),

typed as (
    select
        inspection_id,
        job_id,
        division,
        stage,
        inspection_type,
        inspector_type,
        inspector_level,
        inspector_id,
        result,
        defect_code,
        disposition,
        date(inspection_date) as inspection_date,
        cast(from_iso8601_timestamp(timestamp) as timestamp) as event_timestamp
    from source
),

deduped as (
    select *,
        row_number() over (partition by inspection_id order by event_timestamp desc) as rn
    from typed
)

select
    inspection_id,
    job_id,
    division,
    stage,
    inspection_type,
    inspector_type,
    inspector_level,
    inspector_id,
    result,
    defect_code,
    disposition,
    (result != 'PASS') as is_defect,
    inspection_date,
    event_timestamp
from deduped
where rn = 1
