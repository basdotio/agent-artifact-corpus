/*
 * Cross-Department Performance Analysis
 * Analyzes correlations between service quality, sales performance, and operational efficiency
 */
CREATE OR REPLACE PACKAGE department_analytics AS
  -- Performance thresholds
  performance_threshold CONSTANT NUMBER := 0.75;
  correlation_threshold CONSTANT NUMBER := 0.5;
  
  -- Custom types
  TYPE r_department_metrics IS RECORD (
    analysis_date DATE,
    service_score NUMBER,
    sales_performance NUMBER,
    operational_efficiency NUMBER,
    correlation_factor NUMBER
  );
  
  -- Main procedures
  PROCEDURE analyze_department_correlations(p_days_back IN NUMBER DEFAULT 90);
  FUNCTION calculate_correlation(
    p_metric1 IN NUMBER,
    p_metric2 IN NUMBER
  ) RETURN NUMBER;
END department_analytics;
/

CREATE OR REPLACE PACKAGE BODY department_analytics AS
  FUNCTION calculate_correlation(
    p_metric1 IN NUMBER,
    p_metric2 IN NUMBER
  ) RETURN NUMBER IS
    v_correlation NUMBER;
  BEGIN
    -- Simplified correlation calculation
    v_correlation := (p_metric1 * p_metric2) / 
                    NULLIF(SQRT(POWER(p_metric1, 2) * POWER(p_metric2, 2)), 0);
    RETURN ROUND(v_correlation, 4);
  END calculate_correlation;

  PROCEDURE analyze_department_correlations(p_days_back IN NUMBER DEFAULT 90) IS
    v_metrics r_department_metrics;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_days_back;
  BEGIN
    -- Calculate service performance
    WITH service_metrics AS (
      SELECT 
        TRUNC(RESOLUTION_TIME) as metric_date,
        AVG(SATISFACTION_SCORE) as avg_satisfaction
      FROM (
        SELECT RESOLUTION_TIME, SATISFACTION_SCORE
        FROM SERVICE_DATA_62
        WHERE RESOLUTION_TIME >= v_start_date
        UNION ALL
        SELECT RESOLUTION_TIME, SATISFACTION_SCORE
        FROM SERVICE_DATA_65
        WHERE RESOLUTION_TIME >= v_start_date
      )
      GROUP BY TRUNC(RESOLUTION_TIME)
    ),
    -- Calculate sales performance
    sales_metrics AS (
      SELECT 
        TRUNC(TRANSACTION_DATE) as metric_date,
        SUM(AMOUNT) / MAX(daily_avg) as performance_ratio
      FROM (
        SELECT 
          TRANSACTION_DATE, 
          AMOUNT,
          AVG(AMOUNT) OVER () as daily_avg
        FROM (
          SELECT TRANSACTION_DATE, AMOUNT
          FROM SALES_DATA_151
          WHERE TRANSACTION_DATE >= v_start_date
          UNION ALL
          SELECT TRANSACTION_DATE, AMOUNT
          FROM SALES_DATA_142
          WHERE TRANSACTION_DATE >= v_start_date
        )
      )
      GROUP BY TRUNC(TRANSACTION_DATE)
    ),
    -- Calculate operational efficiency
    operations_metrics AS (
      SELECT 
        TRUNC(OPERATION_DATE) as metric_date,
        COUNT(CASE WHEN STATUS = 'ACTIVE' THEN 1 END) / 
        NULLIF(COUNT(*), 0) as efficiency_ratio
      FROM (
        SELECT OPERATION_DATE, STATUS
        FROM OPERATIONS_DATA_54
        WHERE OPERATION_DATE >= v_start_date
        UNION ALL
        SELECT OPERATION_DATE, STATUS
        FROM OPERATIONS_DATA_65
        WHERE OPERATION_DATE >= v_start_date
      )
      GROUP BY TRUNC(OPERATION_DATE)
    )
    -- Combine and correlate metrics
    SELECT 
      v_analysis_date,
      AVG(sm.avg_satisfaction),
      AVG(sa.performance_ratio),
      AVG(om.efficiency_ratio),
      (
        calculate_correlation(sm.avg_satisfaction, sa.performance_ratio) +
        calculate_correlation(sa.performance_ratio, om.efficiency_ratio) +
        calculate_correlation(om.efficiency_ratio, sm.avg_satisfaction)
      ) / 3
    INTO 
      v_metrics.analysis_date,
      v_metrics.service_score,
      v_metrics.sales_performance,
      v_metrics.operational_efficiency,
      v_metrics.correlation_factor
    FROM service_metrics sm
    FULL OUTER JOIN sales_metrics sa ON sm.metric_date = sa.metric_date
    FULL OUTER JOIN operations_metrics om ON sa.metric_date = om.metric_date;

    -- Store analysis results
    INSERT INTO DEPARTMENT_CORRELATION_HISTORY (
      analysis_date,
      service_performance_score,
      sales_performance_score,
      operational_efficiency_score,
      interdepartmental_correlation,
      analysis_period_days
    ) VALUES (
      v_metrics.analysis_date,
      v_metrics.service_score,
      v_metrics.sales_performance,
      v_metrics.operational_efficiency,
      v_metrics.correlation_factor,
      p_days_back
    );

    -- Generate performance alerts
    IF v_metrics.correlation_factor < correlation_threshold THEN
      INSERT INTO DEPARTMENT_ALERTS (
        alert_date,
        alert_type,
        severity,
        description
      ) VALUES (
        v_analysis_date,
        'LOW_CORRELATION',
        CASE 
          WHEN v_metrics.correlation_factor < correlation_threshold/2 THEN 'HIGH'
          ELSE 'MEDIUM'
        END,
        'Departments showing weak performance correlation. Review coordination.'
      );
    END IF;

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_department_correlations;
END department_analytics;
/

-- Create analytics log table if not exists
CREATE TABLE CROSS_DEPT_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    department_id NUMBER,
    employee_count NUMBER,
    total_sales NUMBER,
    customer_satisfaction NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_cross_dept_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined views for cross-department analysis
CREATE OR REPLACE VIEW combined_department_sales AS
SELECT 
    d.dept_id,
    d.name as department_name,
    e.employee_id,
    s.amount as sale_amount,
    s.transaction_date
FROM departments d
JOIN employees e ON d.dept_id = e.dept_id
JOIN sales_data_151 s ON e.employee_id = s.customer_id;

CREATE OR REPLACE VIEW combined_department_satisfaction AS
SELECT 
    d.dept_id,
    d.name as department_name,
    e.employee_id,
    sv.satisfaction_score,
    sv.resolution_time
FROM departments d
JOIN employees e ON d.dept_id = e.dept_id
JOIN service_data_9 sv ON e.employee_id = sv.id;

-- Analysis package
CREATE OR REPLACE PACKAGE cross_department_analysis AS
  -- Types for department metrics
  TYPE r_department_metrics IS RECORD (
    dept_id NUMBER,
    employee_count NUMBER,
    total_sales NUMBER,
    avg_satisfaction NUMBER
  );
  
  TYPE t_department_metrics IS TABLE OF r_department_metrics;
  
  -- Procedures
  PROCEDURE analyze_department_performance(p_date_range_days IN NUMBER DEFAULT 30);
END cross_department_analysis;
/

CREATE OR REPLACE PACKAGE BODY cross_department_analysis AS
  PROCEDURE analyze_department_performance(p_date_range_days IN NUMBER DEFAULT 30) IS
    v_dept_metrics t_department_metrics;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_date_range_days;
  BEGIN
    -- Calculate department metrics
    WITH dept_metrics AS (
      SELECT 
        d.dept_id,
        COUNT(DISTINCT e.employee_id) as employee_count,
        SUM(s.sale_amount) as total_sales,
        AVG(sv.satisfaction_score) as avg_satisfaction
      FROM departments d
      LEFT JOIN employees e ON d.dept_id = e.dept_id
      LEFT JOIN combined_department_sales s ON e.employee_id = s.employee_id
      LEFT JOIN combined_department_satisfaction sv ON e.employee_id = sv.employee_id
      WHERE s.transaction_date >= v_start_date
      GROUP BY d.dept_id
    )
    SELECT 
      dept_id,
      employee_count,
      total_sales,
      avg_satisfaction
    BULK COLLECT INTO v_dept_metrics
    FROM dept_metrics;

    -- Log results for each department
    FORALL i IN 1..v_dept_metrics.COUNT
      INSERT INTO CROSS_DEPT_ANALYTICS_LOG (
        analysis_id,
        analysis_date,
        department_id,
        employee_count,
        total_sales,
        customer_satisfaction,
        analysis_type
      ) VALUES (
        seq_cross_dept_analytics_log.NEXTVAL,
        v_analysis_date,
        v_dept_metrics(i).dept_id,
        v_dept_metrics(i).employee_count,
        v_dept_metrics(i).total_sales,
        v_dept_metrics(i).avg_satisfaction,
        'DEPARTMENT_PERFORMANCE'
      );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_department_performance;
END cross_department_analysis;
/