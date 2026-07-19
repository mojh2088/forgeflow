with source as (
    select * from {{ source('forgeflow_bronze', 'fabrication_stages') }}
),

typed as (
    select
        event_id,
        job_id,
        division,
        stage,
        item_scope,
        date(planned_start_date) as planned_start_date,
        date(planned_end_date) as planned_end_date,
        date(actual_start_date) as actual_start_date,
        date(actual_end_date) as actual_end_date,
        cast(duration_days_actual as integer) as duration_days_actual,
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
    stage,
    item_scope,
    planned_start_date,
    planned_end_date,
    actual_start_date,
    actual_end_date,
    duration_days_actual,
    -- slip in days, positive = ran long. Convenience field for Gold.
    date_diff('day', planned_end_date, actual_end_date) as stage_slip_days,
    status,
    event_timestamp
from deduped
where rn = 1
