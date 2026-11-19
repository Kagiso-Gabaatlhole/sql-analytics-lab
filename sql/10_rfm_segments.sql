-- How many customers fall into each RFM segment, and how do those segments spend (view-based report)?
SELECT segment,
       COUNT(*)                           AS customers,
       ROUND(AVG(recency_days), 1)        AS avg_recency_days,
       ROUND(AVG(frequency), 2)           AS avg_orders,
       ROUND(SUM(monetary), 2)            AS total_spend,
       ROUND(AVG(monetary), 2)            AS avg_spend_per_customer
FROM v_customer_rfm
GROUP BY segment
ORDER BY total_spend DESC;
