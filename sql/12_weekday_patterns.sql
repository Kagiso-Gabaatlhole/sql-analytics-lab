-- How do order volume and revenue differ by day of the week (date functions on dim_order_date)?
SELECT d.is_weekend,
       CASE d.is_weekend WHEN 1 THEN 'weekend' ELSE 'weekday' END AS day_type,
       CAST(strftime('%w', d.date_key) AS INTEGER) AS weekday_number,
       COUNT(DISTINCT f.order_id)    AS orders,
       ROUND(SUM(f.line_revenue), 2) AS revenue,
       ROUND(AVG(f.line_revenue), 2) AS avg_line_revenue
FROM fact_order_line AS f
JOIN dim_order_date AS d ON d.date_key = f.date_key
GROUP BY d.is_weekend, weekday_number
ORDER BY weekday_number;
