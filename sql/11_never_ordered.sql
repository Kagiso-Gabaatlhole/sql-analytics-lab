-- Which customers and products have never contributed a single rand of revenue (anti-join / NULL handling)?
SELECT 'customer' AS entity_type,
       c.customer_id AS entity_id,
       c.customer_name AS entity_name,
       c.province AS detail,
       COALESCE(ROUND(SUM(f.line_revenue), 2), 0.0) AS revenue
FROM dim_customer AS c
LEFT JOIN fact_order_line AS f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name, c.province
HAVING COALESCE(SUM(f.line_revenue), 0) = 0
UNION ALL
SELECT 'product' AS entity_type,
       p.product_id AS entity_id,
       p.product_name AS entity_name,
       p.category AS detail,
       COALESCE(ROUND(SUM(f.line_revenue), 2), 0.0) AS revenue
FROM dim_product AS p
LEFT JOIN fact_order_line AS f ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
HAVING COALESCE(SUM(f.line_revenue), 0) = 0
ORDER BY entity_type, entity_id;
