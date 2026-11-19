-- How did cumulative revenue build up month by month (running total window function)?
WITH monthly AS (
    SELECT d.year,
           d.month,
           ROUND(SUM(f.line_revenue), 2) AS revenue
    FROM fact_order_line AS f
    JOIN dim_order_date AS d ON d.date_key = f.date_key
    GROUP BY d.year, d.month
)
SELECT printf('%d-%02d', year, month) AS year_month,
       revenue,
       ROUND(SUM(revenue) OVER (ORDER BY year, month
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)
           AS running_revenue
FROM monthly
ORDER BY year, month;
