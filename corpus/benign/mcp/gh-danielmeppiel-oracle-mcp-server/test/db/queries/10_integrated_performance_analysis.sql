/*
 * Integrated Performance Analysis
 * Comprehensive analysis combining metrics from all departments
 */
CREATE OR REPLACE PACKAGE integrated_analytics AS
  -- Performance thresholds
  TYPE r_performance_metrics IS RECORD (
    analysis_period VARCHAR2(20),
    service_score NUMBER,
    sales_score NUMBER,
    inventory_score NUMBER,
    operations_score NUMBER,
    overall_score NUMBER
  );
  
  TYPE t_performance_metrics IS TABLE OF r_performance_metrics;
  
  -- Main procedures
  PROCEDURE generate_integrated_report(
    p_analysis_period IN VARCHAR2,
    p_start_date IN DATE,
    p_end_date IN DATE
  );
END integrated_analytics;
/

CREATE OR REPLACE PACKAGE BODY integrated_analytics AS
  PROCEDURE generate_integrated_report(
    p_analysis_period IN VARCHAR2,
    p_start_date IN DATE,
    p_end_date IN DATE
  ) IS
    v_metrics r_performance_metrics;
  BEGIN
    -- Calculate service performance metrics
    WITH service_metrics AS (
      SELECT 
        AVG(SATISFACTION_SCORE) as avg_satisfaction,
        COUNT(*) as total_tickets,
        AVG(EXTRACT(HOUR FROM (RESOLUTION_TIME - CREATED_AT))) as avg_resolution_time
      FROM (
        SELECT SATISFACTION_SCORE, RESOLUTION_TIME, CREATED_AT
        FROM SERVICE_DATA_62
        WHERE RESOLUTION_TIME BETWEEN p_start_date AND p_end_date
        UNION ALL
        SELECT SATISFACTION_SCORE, RESOLUTION_TIME, CREATED_AT
        FROM SERVICE_DATA_65
        WHERE RESOLUTION_TIME BETWEEN p_start_date AND p_end_date
      )
    ),
    -- Calculate sales performance metrics
    sales_metrics AS (
      SELECT 
        SUM(AMOUNT) as total_sales,
        COUNT(DISTINCT CUSTOMER_ID) as unique_customers,
        AVG(AMOUNT) as avg_transaction
      FROM (
        SELECT AMOUNT, CUSTOMER_ID
        FROM SALES_DATA_151
        WHERE TRANSACTION_DATE BETWEEN p_start_date AND p_end_date
        UNION ALL
        SELECT AMOUNT, CUSTOMER_ID
        FROM SALES_DATA_142
        WHERE TRANSACTION_DATE BETWEEN p_start_date AND p_end_date
      )
    ),
    -- Calculate inventory metrics
    inventory_metrics AS (
      SELECT 
        AVG(QUANTITY) as avg_stock_level,
        STDDEV(QUANTITY) as stock_volatility,
        COUNT(DISTINCT PRODUCT_ID) as unique_products
      FROM (
        SELECT QUANTITY, PRODUCT_ID
        FROM INVENTORY_DATA_39
        WHERE LAST_UPDATED BETWEEN p_start_date AND p_end_date
        UNION ALL
        SELECT QUANTITY, PRODUCT_ID
        FROM INVENTORY_DATA_183
        WHERE LAST_UPDATED BETWEEN p_start_date AND p_end_date
      )
    ),
    -- Calculate operations metrics
    operations_metrics AS (
      SELECT 
        AVG(CASE WHEN STATUS = 'ACTIVE' THEN 1 ELSE 0 END) as uptime_ratio,
        COUNT(DISTINCT FACILITY_ID) as active_facilities
      FROM (
        SELECT STATUS, FACILITY_ID
        FROM OPERATIONS_DATA_54
        WHERE OPERATION_DATE BETWEEN p_start_date AND p_end_date
        UNION ALL
        SELECT STATUS, FACILITY_ID
        FROM OPERATIONS_DATA_65
        WHERE OPERATION_DATE BETWEEN p_start_date AND p_end_date
      )
    )
    -- Combine all metrics and calculate scores
    SELECT 
      p_analysis_period,
      (sm.avg_satisfaction * 20) as service_score,
      ((sa.total_sales / NULLIF(sa.unique_customers, 0)) / 100) as sales_score,
      (im.avg_stock_level / NULLIF(im.stock_volatility, 0)) as inventory_score,
      (om.uptime_ratio * 100) as operations_score,
      (
        (sm.avg_satisfaction * 20) +
        ((sa.total_sales / NULLIF(sa.unique_customers, 0)) / 100) +
        (im.avg_stock_level / NULLIF(im.stock_volatility, 0)) +
        (om.uptime_ratio * 100)
      ) / 4 as overall_score
    INTO 
      v_metrics.analysis_period,
      v_metrics.service_score,
      v_metrics.sales_score,
      v_metrics.inventory_score,
      v_metrics.operations_score,
      v_metrics.overall_score
    FROM service_metrics sm
    CROSS JOIN sales_metrics sa
    CROSS JOIN inventory_metrics im
    CROSS JOIN operations_metrics om;

    -- Store integrated analysis results
    INSERT INTO INTEGRATED_PERFORMANCE_HISTORY (
      analysis_period,
      report_date,
      service_performance_score,
      sales_performance_score,
      inventory_efficiency_score,
      operations_performance_score,
      overall_performance_score,
      start_date,
      end_date
    ) VALUES (
      v_metrics.analysis_period,
      SYSDATE,
      v_metrics.service_score,
      v_metrics.sales_score,
      v_metrics.inventory_score,
      v_metrics.operations_score,
      v_metrics.overall_score,
      p_start_date,
      p_end_date
    );

    -- Generate department-specific recommendations
    INSERT INTO PERFORMANCE_RECOMMENDATIONS (
      department,
      recommendation_date,
      priority,
      action_items
    )
    SELECT department, SYSDATE, priority, action_items
    FROM (
      -- Service recommendations
      SELECT 
        'SERVICE' as department,
        CASE 
          WHEN v_metrics.service_score < 60 THEN 'HIGH'
          WHEN v_metrics.service_score < 80 THEN 'MEDIUM'
          ELSE 'LOW'
        END as priority,
        'Improve customer satisfaction rating' as action_items
      UNION ALL
      -- Sales recommendations
      SELECT 
        'SALES',
        CASE 
          WHEN v_metrics.sales_score < 70 THEN 'HIGH'
          WHEN v_metrics.sales_score < 85 THEN 'MEDIUM'
          ELSE 'LOW'
        END,
        'Focus on increasing average transaction value'
      UNION ALL
      -- Inventory recommendations
      SELECT 
        'INVENTORY',
        CASE 
          WHEN v_metrics.inventory_score < 65 THEN 'HIGH'
          WHEN v_metrics.inventory_score < 80 THEN 'MEDIUM'
          ELSE 'LOW'
        END,
        'Optimize stock levels and reduce volatility'
      UNION ALL
      -- Operations recommendations
      SELECT 
        'OPERATIONS',
        CASE 
          WHEN v_metrics.operations_score < 75 THEN 'HIGH'
          WHEN v_metrics.operations_score < 90 THEN 'MEDIUM'
          ELSE 'LOW'
        END,
        'Improve facility uptime and efficiency'
    );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END generate_integrated_report;
END integrated_analytics;
/

-- Create analytics log table if not exists
CREATE TABLE INTEGRATED_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    overall_satisfaction NUMBER,
    total_revenue NUMBER,
    operational_score NUMBER,
    inventory_health NUMBER,
    composite_score NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_integrated_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined views for integrated analysis
CREATE OR REPLACE VIEW combined_performance_data AS
SELECT 
    s.id as sale_id,
    s.customer_id,
    s.amount as sale_amount,
    s.transaction_date,
    sv.satisfaction_score,
    sv.resolution_time,
    o.status as operation_status,
    o.operation_date,
    i.quantity as inventory_level,
    i.last_updated as inventory_date,
    e.employee_id,
    e.dept_id,
    d.name as department_name
FROM sales_data_151 s
LEFT JOIN service_data_9 sv ON s.customer_id = sv.id
LEFT JOIN operations_data_54 o ON s.customer_id = o.facility_id
LEFT JOIN inventory_data_39 i ON s.customer_id = i.product_id
LEFT JOIN employees e ON s.customer_id = e.employee_id
LEFT JOIN departments d ON e.dept_id = d.dept_id;

-- Analysis package
CREATE OR REPLACE PACKAGE integrated_analysis AS
  -- Types for integrated metrics
  TYPE r_integrated_metrics IS RECORD (
    period_start DATE,
    period_end DATE,
    satisfaction_score NUMBER,
    revenue_score NUMBER,
    operations_score NUMBER,
    inventory_score NUMBER,
    composite_score NUMBER
  );
  
  TYPE t_integrated_metrics IS TABLE OF r_integrated_metrics;
  
  -- Procedures
  PROCEDURE analyze_overall_performance(p_date_range_days IN NUMBER DEFAULT 30);
END integrated_analysis;
/

CREATE OR REPLACE PACKAGE BODY integrated_analysis AS
  PROCEDURE analyze_overall_performance(p_date_range_days IN NUMBER DEFAULT 30) IS
    v_metrics r_integrated_metrics;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_date_range_days;
  BEGIN
    -- Calculate integrated metrics
    WITH period_metrics AS (
      SELECT 
        MIN(transaction_date) as period_start,
        MAX(transaction_date) as period_end,
        AVG(satisfaction_score) as satisfaction_score,
        SUM(sale_amount) / NULLIF(COUNT(DISTINCT customer_id), 0) as revenue_per_customer,
        COUNT(CASE WHEN operation_status = 'ACTIVE' THEN 1 END) / 
          NULLIF(COUNT(operation_status), 0) as operational_efficiency,
        AVG(inventory_level) as avg_inventory
      FROM combined_performance_data
      WHERE transaction_date >= v_start_date
    )
    SELECT 
      period_start,
      period_end,
      satisfaction_score,
      revenue_per_customer,
      operational_efficiency,
      avg_inventory,
      (satisfaction_score + revenue_per_customer + operational_efficiency) / 3 as composite
    INTO 
      v_metrics.period_start,
      v_metrics.period_end,
      v_metrics.satisfaction_score,
      v_metrics.revenue_score,
      v_metrics.operations_score,
      v_metrics.inventory_score,
      v_metrics.composite_score
    FROM period_metrics;

    -- Log results
    INSERT INTO INTEGRATED_ANALYTICS_LOG (
      analysis_id,
      analysis_date,
      overall_satisfaction,
      total_revenue,
      operational_score,
      inventory_health,
      composite_score,
      analysis_type
    ) VALUES (
      seq_integrated_analytics_log.NEXTVAL,
      v_analysis_date,
      v_metrics.satisfaction_score,
      v_metrics.revenue_score,
      v_metrics.operations_score,
      v_metrics.inventory_score,
      v_metrics.composite_score,
      'INTEGRATED_PERFORMANCE'
    );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_overall_performance;
END integrated_analysis;
/