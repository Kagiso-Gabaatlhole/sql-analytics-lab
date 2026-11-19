-- How heavy is discounting per category, and how does discounted revenue compare with full-price revenue?
SELECT p.category,
       ROUND(100.0 * SUM(CASE WHEN f.discount_pct > 0 THEN 1 ELSE 0 END) / COUNT(*), 2)
           AS discounted_line_pct,
       ROUND(AVG(f.discount_pct), 2) AS avg_discount_pct,
       ROUND(SUM(CASE WHEN f.discount_pct > 0 THEN f.line_revenue ELSE 0 END), 2)
           AS discounted_revenue,
       ROUND(SUM(CASE WHEN f.discount_pct = 0 THEN f.line_revenue ELSE 0 END), 2)
           AS full_price_revenue
FROM fact_order_line AS f
JOIN dim_product AS p ON p.product_id = f.product_id
GROUP BY p.category
ORDER BY discounted_revenue DESC;
