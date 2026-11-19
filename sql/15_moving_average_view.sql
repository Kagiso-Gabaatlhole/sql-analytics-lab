-- Using the v_monthly_revenue view, what does a three-month moving average of revenue look like?
SELECT year_month,
       orders,
       units_sold,
       revenue,
       ROUND(AVG(revenue) OVER (ORDER BY year, month
                                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
           AS moving_avg_3m_revenue
FROM v_monthly_revenue
ORDER BY year, month;
