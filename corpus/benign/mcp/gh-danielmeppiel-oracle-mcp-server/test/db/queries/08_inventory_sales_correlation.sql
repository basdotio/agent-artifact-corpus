/*
 * Inventory-Sales Correlation Analysis
 * Analyzes relationship between inventory levels and sales performance
 */
CREATE OR REPLACE PACKAGE inventory_sales_analysis AS
  -- Threshold constants
  stock_out_threshold CONSTANT NUMBER := 5;
  high_stock_threshold CONSTANT NUMBER := 1000;
  
  -- Type definitions
  TYPE r_product_performance IS RECORD (
    product_id NUMBER,
    avg_stock_level NUMBER,
    stock_turnover_rate NUMBER,
    sales_velocity NUMBER,
    correlation_score NUMBER
  );
  
  TYPE t_product_performance IS TABLE OF r_product_performance;
  
  -- Main procedures
  PROCEDURE analyze_inventory_sales_correlation(p_days_back IN NUMBER DEFAULT 30);
  FUNCTION calculate_turnover_rate(
    p_sales_quantity IN NUMBER,
    p_avg_inventory IN NUMBER
  ) RETURN NUMBER;
END inventory_sales_analysis;
/

CREATE OR REPLACE PACKAGE BODY inventory_sales_analysis AS
  FUNCTION calculate_turnover_rate(
    p_sales_quantity IN NUMBER,
    p_avg_inventory IN NUMBER
  ) RETURN NUMBER IS
  BEGIN
    RETURN CASE 
      WHEN p_avg_inventory = 0 THEN 0
      ELSE ROUND(p_sales_quantity / NULLIF(p_avg_inventory, 0), 2)
    END;
  END calculate_turnover_rate;

  PROCEDURE analyze_inventory_sales_correlation(p_days_back IN NUMBER DEFAULT 30) IS
    v_metrics t_product_performance;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_days_back;
  BEGIN
    -- Combine inventory and sales data
    WITH daily_inventory AS (
      SELECT 
        PRODUCT_ID,
        TRUNC(LAST_UPDATED) as stock_date,
        AVG(QUANTITY) as daily_stock_level
      FROM (
        SELECT PRODUCT_ID, LAST_UPDATED, QUANTITY
        FROM INVENTORY_DATA_39
        WHERE LAST_UPDATED >= v_start_date
        UNION ALL
        SELECT PRODUCT_ID, LAST_UPDATED, QUANTITY
        FROM INVENTORY_DATA_183
        WHERE LAST_UPDATED >= v_start_date
      )
      GROUP BY PRODUCT_ID, TRUNC(LAST_UPDATED)
    ),
    daily_sales AS (
      SELECT 
        i.PRODUCT_ID,
        TRUNC(s.TRANSACTION_DATE) as sale_date,
        COUNT(*) as daily_sales_count,
        SUM(s.AMOUNT) as daily_sales_amount
      FROM SALES_DATA_151 s
      JOIN INVENTORY_DATA_39 i ON s.CUSTOMER_ID = i.PRODUCT_ID -- Simplified join for example
      WHERE s.TRANSACTION_DATE >= v_start_date
      GROUP BY i.PRODUCT_ID, TRUNC(s.TRANSACTION_DATE)
    ),
    product_metrics AS (
      SELECT 
        i.PRODUCT_ID,
        AVG(i.daily_stock_level) as avg_stock_level,
        STDDEV(i.daily_stock_level) as stock_volatility,
        AVG(s.daily_sales_count) as avg_daily_sales,
        CORR(i.daily_stock_level, NVL(s.daily_sales_count, 0)) as stock_sales_correlation
      FROM daily_inventory i
      LEFT JOIN daily_sales s ON i.PRODUCT_ID = s.PRODUCT_ID 
        AND i.stock_date = s.sale_date
      GROUP BY i.PRODUCT_ID
    )
    SELECT 
      PRODUCT_ID,
      avg_stock_level,
      calculate_turnover_rate(
        SUM(avg_daily_sales) OVER (PARTITION BY PRODUCT_ID),
        avg_stock_level
      ),
      avg_daily_sales,
      stock_sales_correlation
    BULK COLLECT INTO v_metrics
    FROM product_metrics;

    -- Store analysis results
    FORALL i IN 1..v_metrics.COUNT
      INSERT INTO INVENTORY_SALES_CORRELATION (
        analysis_date,
        product_id,
        avg_stock_level,
        turnover_rate,
        sales_velocity,
        correlation_score,
        analysis_period_days
      ) VALUES (
        v_analysis_date,
        v_metrics(i).product_id,
        v_metrics(i).avg_stock_level,
        v_metrics(i).stock_turnover_rate,
        v_metrics(i).sales_velocity,
        v_metrics(i).correlation_score,
        p_days_back
      );

    -- Generate inventory optimization recommendations
    INSERT INTO INVENTORY_RECOMMENDATIONS (
      product_id,
      recommendation_date,
      recommendation_type,
      priority,
      description
    )
    SELECT 
      product_id,
      v_analysis_date,
      CASE 
        WHEN avg_stock_level <= stock_out_threshold THEN 'RESTOCK'
        WHEN avg_stock_level >= high_stock_threshold AND 
             stock_turnover_rate < 0.5 THEN 'REDUCE_STOCK'
        WHEN correlation_score < 0 THEN 'REVIEW_STRATEGY'
        ELSE 'MAINTAIN'
      END,
      CASE 
        WHEN avg_stock_level <= stock_out_threshold THEN 'HIGH'
        WHEN correlation_score < 0 THEN 'MEDIUM'
        ELSE 'LOW'
      END,
      'Based on ' || p_days_back || ' days analysis'
    FROM TABLE(v_metrics);

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_inventory_sales_correlation;
END inventory_sales_analysis;
/

-- Create analytics log table if not exists
CREATE TABLE INVENTORY_SALES_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    product_id NUMBER,
    sales_volume NUMBER,
    inventory_level NUMBER,
    correlation_score NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_inventory_sales_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view for inventory-sales analysis
CREATE OR REPLACE VIEW combined_inventory_sales AS
SELECT 
    i.id as inventory_id,
    i.product_id,
    i.quantity as inventory_level,
    i.last_updated as inventory_date,
    s.id as sale_id,
    s.amount as sale_amount,
    s.transaction_date as sale_date,
    p.name as product_name,
    p.price as product_price
FROM inventory_data_39 i
JOIN products p ON i.product_id = p.product_id
LEFT JOIN sales_data_151 s ON i.product_id = s.customer_id;

-- Analysis package
CREATE OR REPLACE PACKAGE inventory_sales_analysis AS
  -- Types for correlation analysis
  TYPE r_product_correlation IS RECORD (
    product_id NUMBER,
    inventory_avg NUMBER,
    sales_avg NUMBER,
    correlation_coefficient NUMBER
  );
  
  TYPE t_product_correlations IS TABLE OF r_product_correlation;
  
  -- Procedures
  PROCEDURE analyze_inventory_sales_correlation(p_date_range_days IN NUMBER DEFAULT 30);
END inventory_sales_analysis;
/

CREATE OR REPLACE PACKAGE BODY inventory_sales_analysis AS
  PROCEDURE analyze_inventory_sales_correlation(p_date_range_days IN NUMBER DEFAULT 30) IS
    v_product_stats t_product_correlations;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_date_range_days;
  BEGIN
    -- Calculate correlations
    WITH daily_metrics AS (
      SELECT 
        product_id,
        AVG(inventory_level) as daily_inventory,
        SUM(sale_amount) as daily_sales,
        TRUNC(inventory_date) as metric_date
      FROM combined_inventory_sales
      WHERE inventory_date >= v_start_date
      GROUP BY product_id, TRUNC(inventory_date)
    )
    SELECT 
      product_id,
      AVG(daily_inventory) as inventory_avg,
      AVG(daily_sales) as sales_avg,
      CORR(daily_inventory, daily_sales) as correlation_coefficient
    BULK COLLECT INTO v_product_stats
    FROM daily_metrics
    GROUP BY product_id;

    -- Log results for each product
    FORALL i IN 1..v_product_stats.COUNT
      INSERT INTO INVENTORY_SALES_ANALYTICS_LOG (
        analysis_id,
        analysis_date,
        product_id,
        sales_volume,
        inventory_level,
        correlation_score,
        analysis_type
      ) VALUES (
        seq_inventory_sales_analytics_log.NEXTVAL,
        v_analysis_date,
        v_product_stats(i).product_id,
        v_product_stats(i).sales_avg,
        v_product_stats(i).inventory_avg,
        v_product_stats(i).correlation_coefficient,
        'INVENTORY_SALES_CORRELATION'
      );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_inventory_sales_correlation;
END inventory_sales_analysis;
/