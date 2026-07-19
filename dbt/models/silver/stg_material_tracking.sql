with source as (
    select * from {{ source('forgeflow_bronze', 'material_tracking') }}
),

typed as (
    select
        event_id,
        job_id,
        division,
        material_type,
        date(po_issued_date) as po_issued_date,
        date(planned_arrival_date) as planned_arrival_date,
        date(actual_arrival_date) as actual_arrival_date,
        date(issued_to_fabrication_date) as issued_to_fabrication_date,
        cast(delay_days as integer) as delay_days,
        (cast(delay_days as integer) > 0) as is_delayed,
        status,
        cast(from_iso8601_timestamp(timestamp) as timestamp) as event_timestamp
    from source
),

deduped as (
    select *,
        row_number() over (partition by event_id order by event_timestamp desc) as rn
    from typed
)

select
    event_id,
    job_id,
    division,
    material_type,
    po_issued_date,
    planned_arrival_date,
    actual_arrival_date,
    issued_to_fabrication_date,
    delay_days,
    is_delayed,
    status,
    event_timestamp
from deduped
where rn = 1
