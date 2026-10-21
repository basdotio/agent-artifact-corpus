/*
 * Sales Trend Analysis
 * Analyzes sales patterns and customer behavior across multiple sales tables
 */
CREATE OR REPLACE PACKAGE sales_analytics AS
  -- Analysis thresholds
  high_value_threshold CONSTANT NUMBER := 10000;
  frequent_buyer_threshold CONSTANT NUMBER := 5;
  
  -- Custom types
  TYPE r_customer_segment IS RECORD (
    customer_id NUMBER,
    total_spent NUMBER,
    purchase_count NUMBER,
    avg_transaction NUMBER,
    last_purchase_date DATE,
    segment_name VARCHAR2(50)
  );
  
  TYPE t_customer_segments IS TABLE OF r_customer_segment;
  
  -- Main procedures
  PROCEDURE analyze_sales_trends(p_months_back IN NUMBER DEFAULT 12);
  FUNCTION calculate_customer_segment(
    p_total_spent IN NUMBER,
    p_purchase_count IN NUMBER
  ) RETURN VARCHAR2;
END sales_analytics;
/

CREATE OR REPLACE PACKAGE BODY sales_analytics AS
  FUNCTION calculate_customer_segment(
    p_total_spent IN NUMBER,
    p_purchase_count IN NUMBER
  ) RETURN VARCHAR2 IS
  BEGIN
    RETURN 
      CASE 
        WHEN p_total_spent >= high_value_threshold AND 
             p_purchase_count >= frequent_buyer_threshold 
          THEN 'PREMIUM'
        WHEN p_total_spent >= high_value_threshold 
          THEN 'HIGH_VALUE'
        WHEN p_purchase_count >= frequent_buyer_threshold 
          THEN 'FREQUENT'
        ELSE 'STANDARD'
      END;
  END calculate_customer_segment;

  PROCEDURE analyze_sales_trends(p_months_back IN NUMBER DEFAULT 12) IS
    v_customer_data t_customer_segments;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := ADD_MONTHS(v_analysis_date, -p_months_back);
  BEGIN
    -- Combine sales data from multiple tables
    WITH combined_sales AS (
      SELECT CUSTOMER_ID, AMOUNT, TRANSACTION_DATE
      FROM SALES_DATA_151
      WHERE TRANSACTION_DATE >= v_start_date
      UNION ALL
      SELECT CUSTOMER_ID, AMOUNT, TRANSACTION_DATE
      FROM SALES_DATA_142
      WHERE TRANSACTION_DATE >= v_start_date
      UNION ALL
      SELECT CUSTOMER_ID, AMOUNT, TRANSACTION_DATE
      FROM SALES_DATA_187
      WHERE TRANSACTION_DATE >= v_start_date
    ),
    customer_metrics AS (
      SELECT 
        CUSTOMER_ID,
        SUM(AMOUNT) as total_spent,
        COUNT(*) as purchase_count,
        AVG(AMOUNT) as avg_transaction,
        MAX(TRANSACTION_DATE) as last_purchase_date,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY AMOUNT) as median_purchase
      FROM combined_sales
      GROUP BY CUSTOMER_ID
    )
    SELECT 
      customer_id,
      total_spent,
      purchase_count,
      avg_transaction,
      last_purchase_date,
      calculate_customer_segment(total_spent, purchase_count) as segment_name
    BULK COLLECT INTO v_customer_data
    FROM customer_metrics;

    -- Process and store customer segments
    FORALL i IN 1..v_customer_data.COUNT
      INSERT INTO CUSTOMER_SEGMENT_HISTORY (
        customer_id,
        analysis_date,
        total_spent,
        purchase_count,
        average_transaction,
        last_purchase_date,
        segment_name,
        analysis_period_months
      ) VALUES (
        v_customer_data(i).customer_id,
        v_analysis_date,
        v_customer_data(i).total_spent,
        v_customer_data(i).purchase_count,
        v_customer_data(i).avg_transaction,
        v_customer_data(i).last_purchase_date,
        v_customer_data(i).segment_name,
        p_months_back
      );

    -- Generate segment summary
    INSERT INTO SEGMENT_SUMMARY (
      analysis_date,
      segment_name,
      customer_count,
      total_revenue,
      avg_customer_value
    )
    SELECT 
      v_analysis_date,
      segment_name,
      COUNT(*),
      SUM(total_spent),
      AVG(total_spent)
    FROM TABLE(v_customer_data)
    GROUP BY segment_name;

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_sales_trends;
END sales_analytics;
/

-- Create analytics log table if not exists
CREATE TABLE SALES_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    total_customers NUMBER,
    total_sales NUMBER,
    avg_transaction_amount NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_sales_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view of sales data
CREATE OR REPLACE VIEW combined_sales_data AS
SELECT 
    s.id,
    s.customer_id,
    s.amount,
    s.transaction_date,
    c.name as customer_name,
    c.email as customer_email
FROM sales_data_151 s
JOIN customers c ON s.customer_id = c.customer_id;

-- Analysis package
CREATE OR REPLACE PACKAGE sales_analysis AS
  -- Types for sales tracking
  TYPE r_sales_summary IS RECORD (
    customer_id NUMBER,
    total_sales NUMBER,
    order_count NUMBER,
    avg_order_value NUMBER,
    last_order_date DATE
  );
  
  TYPE t_sales_summary IS TABLE OF r_sales_summary;
  
  -- Procedures
  PROCEDURE analyze_sales_trends(p_date_range_days IN NUMBER DEFAULT 30);
END sales_analysis;
/

CREATE OR REPLACE PACKAGE BODY sales_analysis AS
  PROCEDURE analyze_sales_trends(p_date_range_days IN NUMBER DEFAULT 30) IS
    v_sales_stats t_sales_summary;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_date_range_days;
  BEGIN
    -- Calculate sales statistics
    WITH daily_sales AS (
      SELECT 
        customer_id,
        SUM(amount) as daily_total,
        COUNT(*) as daily_orders,
        transaction_date
      FROM combined_sales_data
      WHERE transaction_date >= v_start_date
      GROUP BY customer_id, transaction_date
    )
    SELECT 
      customer_id,
      SUM(daily_total) as total_sales,
      SUM(daily_orders) as order_count,
      AVG(daily_total) as avg_order_value,
      MAX(transaction_date) as last_order_date
    BULK COLLECT INTO v_sales_stats
    FROM daily_sales
    GROUP BY customer_id;

    -- Log results
    INSERT INTO SALES_ANALYTICS_LOG (
      analysis_id,
      analysis_date,
      total_customers,
      total_sales,
      avg_transaction_amount,
      analysis_type
    ) VALUES (
      seq_sales_analytics_log.NEXTVAL,
      v_analysis_date,
      v_sales_stats.COUNT,
      (SELECT SUM(total_sales) FROM TABLE(v_sales_stats)),
      (SELECT AVG(avg_order_value) FROM TABLE(v_sales_stats)),
      'SALES_TRENDS'
    );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_sales_trends;
END sales_analysis;
/