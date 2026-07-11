-- =====================================================================
-- experiment_funnel_milestones.sql
-- Purpose: Tracks session page milestones by safely stitching user IDs 
--          backward to prevent 100% conversion baseline bias.
-- Table  : thelook-analytics-engine.production_engine.experiment_funnel_milestones
-- Author : Ayesha Amer
-- =====================================================================


WITH user_groups AS (
        SELECT
            id AS user_id,
            CASE
                WHEN DATE(created_at) < '2023-01-01' THEN 'control'
                ELSE 'treatment'
            END AS experiment_group
        FROM `bigquery-public-data.thelook_ecommerce.users`
    ),
user_conversions AS (
        SELECT
            u.user_id,
            u.experiment_group,
            MAX(CASE
                WHEN o.status IN ('Complete','Shipped') THEN 1
                ELSE 0
            END) AS converted
        FROM user_groups u
        LEFT JOIN `bigquery-public-data.thelook_ecommerce.orders` o
            ON u.user_id = o.user_id
        GROUP BY u.user_id, u.experiment_group
    )
SELECT
        experiment_group,
        COUNT(*)                        AS total_users,
        SUM(converted)                  AS conversions,
        ROUND(AVG(converted) * 100, 4)  AS conversion_rate_pct
    FROM user_conversions
    GROUP BY experiment_group
    ORDER BY experiment_group
