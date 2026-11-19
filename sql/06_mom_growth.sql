-- What was the month-on-month percentage change in revenue (LAG window function)?
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
       LAG(revenue) OVER (ORDER BY year, month)                          AS prev_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY year, month))
             / LAG(revenue) OVER (ORDER BY year, month), 2)              AS mom_growth_pct
FROM monthly
ORDER BY year, month;
