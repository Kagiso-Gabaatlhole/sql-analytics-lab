-- Which product categories both earn plenty of revenue and attract a healthy number of distinct customers (HAVING filter)?
SELECT p.category,
       COUNT(DISTINCT f.customer_id) AS customers,
       COUNT(DISTINCT f.order_id)    AS orders,
       ROUND(SUM(f.line_revenue), 2) AS revenue
FROM fact_order_line AS f
JOIN dim_product AS p ON p.product_id = f.product_id
GROUP BY p.category
HAVING SUM(f.line_revenue) > 3000000
   AND COUNT(DISTINCT f.customer_id) > 720
ORDER BY revenue DESC;
