-- =============================================================
-- sessionization.sql
-- Purpose: Assign session sequence numbers to user events
--          using a 30-minute inactivity timeout threshold.
-- Dataset: bigquery-public-data.thelook_ecommerce.events
-- Author:  Ayesha Amer
-- =============================================================


-- calculating the time elapsed since each user's previous event
WITH event_gap AS (
    SELECT
        user_id,
        session_id,
        event_type,
        created_at,
        sequence_number,
        traffic_source,
        browser,
        uri,
        TIMESTAMP_DIFF(
            created_at,
            LAG(created_at) OVER (
                PARTITION BY user_id
                ORDER BY created_at ASC
            ),
            MINUTE
        ) AS mins_since_last_event
    FROM `bigquery-public-data.thelook_ecommerce.events`
    WHERE user_id IS NOT NULL
),

-- flagging the start of a ne session for each user(a new session begins when either the mins since last event is 0 
-- or gap exceeds the 30 minues inactivity threshold)
session_boundary AS (
    SELECT *,
        CASE
            WHEN mins_since_last_event IS NULL THEN 1
            WHEN mins_since_last_event > 30    THEN 1
            ELSE 0
        END AS is_new_session
    FROM event_gap
),

-- converting boundary flags into a session sequence number
assign_session_num AS (
    SELECT *,
        SUM(is_new_session) OVER (
            PARTITION BY user_id
            ORDER BY created_at ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS session_sequence
    FROM session_boundary
)

SELECT
    user_id,
    session_id AS raw_session_id,
    session_sequence,
    event_type,
    created_at,
    mins_since_last_event,
    is_new_session,
    traffic_source,
    browser,
    uri
FROM assign_session_num
ORDER BY user_id, created_at ASC;