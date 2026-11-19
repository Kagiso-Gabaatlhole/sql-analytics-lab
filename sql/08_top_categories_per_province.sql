-- Which are the top two product categories in every province (top-N per group with DENSE_RANK)?
WITH province_category AS (
    SELECT c.province,
           p.category,
           ROUND(SUM(f.line_revenue), 2) AS revenue
    FROM fact_order_line AS f
    JOIN dim_customer AS c ON c.customer_id = f.customer_id
    JOIN dim_product AS p ON p.product_id = f.product_id
    GROUP BY c.province, p.category
)
SELECT province,
       category,
       revenue,
       ranked.province_rank
FROM (
    SELECT province,
           category,
           revenue,
           DENSE_RANK() OVER (PARTITION BY province ORDER BY revenue DESC)
               AS province_rank
    FROM province_category
) AS ranked
WHERE ranked.province_rank <= 2
ORDER BY province, province_rank;
