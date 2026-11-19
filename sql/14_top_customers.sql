-- Who are the ten highest-spending customers, and how often and when did they order?
SELECT c.customer_id,
       c.customer_name,
       c.province,
       MIN(f.date_key)                AS first_order,
       MAX(f.date_key)                AS last_order,
       COUNT(DISTINCT f.order_id)     AS orders,
       ROUND(SUM(f.line_revenue), 2)  AS total_spend
FROM fact_order_line AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
GROUP BY c.customer_id, c.customer_name, c.province
ORDER BY total_spend DESC
LIMIT 10;
