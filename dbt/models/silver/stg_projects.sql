with source as (
    select * from {{ source('forgeflow_bronze', 'projects') }}
),

typed as (
    select
        job_id,
        division,
        client_type,
        job_type,
        code_standard,
        date(contract_award_date) as contract_award_date,
        date(target_delivery_date) as target_delivery_date,
        cast(planned_duration_weeks as integer) as planned_duration_weeks,
        cast(scope_qty as integer) as scope_qty,
        scope_unit,
        cast(has_subcontracted_ancillary as boolean) as has_subcontracted_ancillary,
        cast(from_iso8601_timestamp(created_at) as timestamp) as created_at
    from source
),

deduped as (
    select *,
        row_number() over (partition by job_id order by created_at desc) as rn
    from typed
)

select
    job_id,
    division,
    client_type,
    job_type,
    code_standard,
    contract_award_date,
    target_delivery_date,
    planned_duration_weeks,
    scope_qty,
    scope_unit,
    has_subcontracted_ancillary,
    created_at
from deduped
where rn = 1
