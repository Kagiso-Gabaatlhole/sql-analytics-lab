-- Which months produced the most revenue, and how many orders and units backed it?
SELECT d.year,
       d.month,
       printf('%d-%02d', d.year, d.month) AS year_month,
       COUNT(DISTINCT f.order_id)         AS orders,
       SUM(f.quantity)                    AS units_sold,
       ROUND(SUM(f.line_revenue), 2)      AS revenue
FROM fact_order_line AS f
JOIN dim_order_date AS d ON d.date_key = f.date_key
GROUP BY d.year, d.month
ORDER BY revenue DESC;
