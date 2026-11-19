-- Which South African provinces generate the most revenue, and what is each one's share of the total?
SELECT c.province,
       COUNT(DISTINCT f.order_id)    AS orders,
       ROUND(SUM(f.line_revenue), 2) AS revenue,
       ROUND(100.0 * SUM(f.line_revenue)
             / SUM(SUM(f.line_revenue)) OVER (), 2) AS revenue_share_pct
FROM fact_order_line AS f
JOIN dim_customer AS c ON c.customer_id = f.customer_id
GROUP BY c.province
ORDER BY revenue DESC;
