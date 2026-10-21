/*
 * HR Attribute Analysis
 * Analyzes employee attributes and their changes over time
 */
CREATE OR REPLACE PACKAGE hr_analytics AS
  -- Analysis parameters
  TYPE r_attribute_change IS RECORD (
    employee_id NUMBER,
    attribute_value VARCHAR2(100),
    change_frequency NUMBER,
    first_recorded DATE,
    last_modified DATE
  );
  
  TYPE t_attribute_changes IS TABLE OF r_attribute_change;
  
  -- Main procedures
  PROCEDURE analyze_attribute_changes(p_months_back IN NUMBER DEFAULT 24);
  PROCEDURE detect_unusual_patterns;
END hr_analytics;
/

CREATE OR REPLACE PACKAGE BODY hr_analytics AS
  PROCEDURE analyze_attribute_changes(p_months_back IN NUMBER DEFAULT 24) IS
    v_attribute_data t_attribute_changes;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := ADD_MONTHS(v_analysis_date, -p_months_back);
  BEGIN
    -- Combine HR attribute data from multiple tables
    WITH combined_attributes AS (
      SELECT EMPLOYEE_ID, ATTRIBUTE_VALUE, CREATED_AT
      FROM HR_ATTRIBUTE_34
      WHERE CREATED_AT >= v_start_date
      UNION ALL
      SELECT EMPLOYEE_ID, ATTRIBUTE_VALUE, CREATED_AT
      FROM HR_ATTRIBUTE_25
      WHERE CREATED_AT >= v_start_date
      UNION ALL
      SELECT EMPLOYEE_ID, ATTRIBUTE_VALUE, CREATED_AT
      FROM HR_ATTRIBUTE_9
      WHERE CREATED_AT >= v_start_date
    ),
    attribute_metrics AS (
      SELECT 
        EMPLOYEE_ID,
        ATTRIBUTE_VALUE,
        COUNT(*) as change_count,
        MIN(CREATED_AT) as first_recorded,
        MAX(CREATED_AT) as last_modified,
        LAG(ATTRIBUTE_VALUE) OVER (
          PARTITION BY EMPLOYEE_ID 
          ORDER BY CREATED_AT
        ) as prev_value
      FROM combined_attributes
      GROUP BY EMPLOYEE_ID, ATTRIBUTE_VALUE, CREATED_AT
    )
    SELECT 
      EMPLOYEE_ID,
      ATTRIBUTE_VALUE,
      COUNT(*) as change_frequency,
      MIN(first_recorded) as first_recorded,
      MAX(last_modified) as last_modified
    BULK COLLECT INTO v_attribute_data
    FROM attribute_metrics
    WHERE ATTRIBUTE_VALUE != NVL(prev_value, ATTRIBUTE_VALUE)
    GROUP BY EMPLOYEE_ID, ATTRIBUTE_VALUE;

    -- Store analysis results
    FORALL i IN 1..v_attribute_data.COUNT
      INSERT INTO ATTRIBUTE_CHANGE_HISTORY (
        employee_id,
        current_value,
        change_frequency,
        first_recorded_date,
        last_modified_date,
        analysis_date,
        analysis_period_months
      ) VALUES (
        v_attribute_data(i).employee_id,
        v_attribute_data(i).attribute_value,
        v_attribute_data(i).change_frequency,
        v_attribute_data(i).first_recorded,
        v_attribute_data(i).last_modified,
        v_analysis_date,
        p_months_back
      );

    -- Check for unusual patterns
    detect_unusual_patterns;

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_attribute_changes;

  PROCEDURE detect_unusual_patterns IS
    v_std_dev NUMBER;
    v_mean_changes NUMBER;
  BEGIN
    -- Calculate statistical measures for change frequency
    SELECT 
      STDDEV(change_frequency),
      AVG(change_frequency)
    INTO v_std_dev, v_mean_changes
    FROM ATTRIBUTE_CHANGE_HISTORY
    WHERE analysis_date = (
      SELECT MAX(analysis_date)
      FROM ATTRIBUTE_CHANGE_HISTORY
    );

    -- Flag unusual patterns
    INSERT INTO ATTRIBUTE_ANOMALIES (
      employee_id,
      detection_date,
      anomaly_type,
      change_frequency,
      deviation_from_mean
    )
    SELECT 
      employee_id,
      SYSDATE,
      CASE 
        WHEN change_frequency > v_mean_changes + (2 * v_std_dev) 
          THEN 'HIGH_FREQUENCY_CHANGES'
        WHEN change_frequency < v_mean_changes - (2 * v_std_dev)
          THEN 'LOW_FREQUENCY_CHANGES'
      END,
      change_frequency,
      ROUND((change_frequency - v_mean_changes) / v_std_dev, 2)
    FROM ATTRIBUTE_CHANGE_HISTORY
    WHERE analysis_date = (
      SELECT MAX(analysis_date)
      FROM ATTRIBUTE_CHANGE_HISTORY
    )
    AND (
      change_frequency > v_mean_changes + (2 * v_std_dev)
      OR change_frequency < v_mean_changes - (2 * v_std_dev)
    );
  END detect_unusual_patterns;
END hr_analytics;
/

-- Create analytics log table if not exists
CREATE TABLE HR_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    total_employees NUMBER,
    avg_salary NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_hr_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view of HR data
CREATE OR REPLACE VIEW combined_hr_data AS
SELECT 
    e.employee_id,
    e.first_name,
    e.last_name,
    e.email,
    e.hire_date,
    e.salary,
    e.dept_id,
    d.name as department_name,
    d.location as department_location,
    a.attribute_value,
    a.created_at as attribute_date
FROM employees e
JOIN departments d ON e.dept_id = d.dept_id
LEFT JOIN hr_attribute_34 a ON e.employee_id = a.employee_id;

-- Analysis package
CREATE OR REPLACE PACKAGE hr_analysis AS
  -- Types for employee analysis
  TYPE r_employee_stats IS RECORD (
    employee_id NUMBER,
    department_id NUMBER,
    salary NUMBER,
    tenure_years NUMBER,
    attribute_score NUMBER
  );
  
  TYPE t_employee_stats IS TABLE OF r_employee_stats;
  
  -- Procedures
  PROCEDURE analyze_employee_attributes;
END hr_analysis;
/

CREATE OR REPLACE PACKAGE BODY hr_analysis AS
  PROCEDURE analyze_employee_attributes IS
    v_employee_stats t_employee_stats;
    v_analysis_date DATE := SYSDATE;
  BEGIN
    -- Calculate employee statistics
    WITH employee_metrics AS (
      SELECT 
        employee_id,
        dept_id,
        salary,
        MONTHS_BETWEEN(SYSDATE, hire_date)/12 as years_employed,
        CASE 
          WHEN attribute_value = 'HIGH' THEN 3
          WHEN attribute_value = 'MEDIUM' THEN 2
          ELSE 1
        END as attribute_score
      FROM combined_hr_data
    )
    SELECT 
      employee_id,
      dept_id,
      salary,
      years_employed,
      attribute_score
    BULK COLLECT INTO v_employee_stats
    FROM employee_metrics;

    -- Log results
    INSERT INTO HR_ANALYTICS_LOG (
      analysis_id,
      analysis_date,
      total_employees,
      avg_salary,
      analysis_type
    ) VALUES (
      seq_hr_analytics_log.NEXTVAL,
      v_analysis_date,
      v_employee_stats.COUNT,
      (SELECT AVG(salary) FROM TABLE(v_employee_stats)),
      'EMPLOYEE_ATTRIBUTES'
    );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_employee_attributes;
END hr_analysis;
/