-- Within each category, which products rank in the top three by revenue (ROW_NUMBER per group)?
WITH product_revenue AS (
    SELECT p.category,
           p.product_id,
           p.product_name,
           ROUND(SUM(f.line_revenue), 2) AS revenue
    FROM fact_order_line AS f
    JOIN dim_product AS p ON p.product_id = f.product_id
    GROUP BY p.category, p.product_id, p.product_name
)
SELECT category,
       product_id,
       product_name,
       revenue,
       ranked.revenue_rank
FROM (
    SELECT category,
           product_id,
           product_name,
           revenue,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC, product_id)
               AS revenue_rank
    FROM product_revenue
) AS ranked
WHERE ranked.revenue_rank <= 3
ORDER BY category, revenue_rank;
