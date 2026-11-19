-- How many customers from each first-order cohort were still ordering in later months (retention)?
WITH cohort AS (
    SELECT f.customer_id,
           substr(d.date_key, 1, 7) AS cohort_month
    FROM fact_order_line AS f
    JOIN dim_order_date AS d ON d.date_key = f.date_key
    GROUP BY f.customer_id
),
activity AS (
    SELECT DISTINCT f.customer_id,
           substr(d.date_key, 1, 7) AS activity_month
    FROM fact_order_line AS f
    JOIN dim_order_date AS d ON d.date_key = f.date_key
),
timeline AS (
    SELECT c.cohort_month,
           a.activity_month,
           (CAST(substr(a.activity_month, 1, 4) AS INTEGER)
            - CAST(substr(c.cohort_month, 1, 4) AS INTEGER)) * 12
           + (CAST(substr(a.activity_month, 6, 2) AS INTEGER)
              - CAST(substr(c.cohort_month, 6, 2) AS INTEGER)) AS months_since_first_order
    FROM activity AS a
    JOIN cohort AS c ON c.customer_id = a.customer_id
)
SELECT cohort_month,
       months_since_first_order,
       COUNT(*) AS active_customers
FROM timeline
WHERE months_since_first_order BETWEEN 0 AND 6
GROUP BY cohort_month, months_since_first_order
ORDER BY cohort_month, months_since_first_order;
