-- Which ten products earned the most revenue over the whole period?
SELECT p.product_id,
       p.product_name,
       p.category,
       SUM(f.quantity)               AS units_sold,
       ROUND(SUM(f.line_revenue), 2) AS revenue
FROM fact_order_line AS f
JOIN dim_product AS p ON p.product_id = f.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;
