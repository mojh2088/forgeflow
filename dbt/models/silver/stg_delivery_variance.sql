with source as (
    select * from {{ source('forgeflow_bronze', 'delivery_variance') }}
),

typed as (
    select
        job_id,
        division,
        date(target_delivery_date) as target_delivery_date,
        date(actual_ship_date) as actual_ship_date,
        cast(variance_days as integer) as variance_days,
        cast(on_time as boolean) as on_time,
        reason_code,
        cast(from_iso8601_timestamp(timestamp) as timestamp) as event_timestamp
    from source
),

deduped as (
    select *,
        row_number() over (partition by job_id order by event_timestamp desc) as rn
    from typed
)

select
    job_id,
    division,
    target_delivery_date,
    actual_ship_date,
    variance_days,
    on_time,
    reason_code,
    event_timestamp
from deduped
where rn = 1
