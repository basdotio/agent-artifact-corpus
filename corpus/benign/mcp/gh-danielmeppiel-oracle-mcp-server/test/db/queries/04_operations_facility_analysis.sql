/*
 * Operations Facility Analysis
 * Analyzes facility performance and operational status across multiple data sources
 */
CREATE OR REPLACE PACKAGE facility_operations AS
  -- Status constants
  c_status_active CONSTANT VARCHAR2(10) := 'ACTIVE';
  c_status_maintenance CONSTANT VARCHAR2(20) := 'MAINTENANCE';
  c_status_shutdown CONSTANT VARCHAR2(10) := 'SHUTDOWN';
  
  -- Custom types
  TYPE r_facility_status IS RECORD (
    facility_id NUMBER,
    current_status VARCHAR2(20),
    uptime_percentage NUMBER,
    last_maintenance DATE,
    operation_count NUMBER
  );
  
  TYPE t_facility_status IS TABLE OF r_facility_status;
  
  -- Main procedures
  PROCEDURE analyze_facility_performance(p_days_back IN NUMBER DEFAULT 90);
  PROCEDURE schedule_maintenance(p_facility_id IN NUMBER);
END facility_operations;
/

CREATE OR REPLACE PACKAGE BODY facility_operations AS
  PROCEDURE analyze_facility_performance(p_days_back IN NUMBER DEFAULT 90) IS
    v_facility_stats t_facility_status;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_days_back;
  BEGIN
    -- Combine operations data from multiple tables
    WITH combined_operations AS (
      SELECT FACILITY_ID, STATUS, OPERATION_DATE
      FROM OPERATIONS_DATA_54
      WHERE OPERATION_DATE >= v_start_date
      UNION ALL
      SELECT FACILITY_ID, STATUS, OPERATION_DATE
      FROM OPERATIONS_DATA_65
      WHERE OPERATION_DATE >= v_start_date
      UNION ALL
      SELECT FACILITY_ID, STATUS, OPERATION_DATE
      FROM OPERATIONS_DATA_167
      WHERE OPERATION_DATE >= v_start_date
    ),
    facility_metrics AS (
      SELECT 
        FACILITY_ID,
        LAST_VALUE(STATUS) OVER (
          PARTITION BY FACILITY_ID 
          ORDER BY OPERATION_DATE 
          ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) as current_status,
        ROUND(
          AVG(CASE WHEN STATUS = c_status_active THEN 1 ELSE 0 END) * 100,
          2
        ) as uptime_percentage,
        MAX(CASE WHEN STATUS = c_status_maintenance 
            THEN OPERATION_DATE ELSE NULL END) as last_maintenance,
        COUNT(*) as operation_count
      FROM combined_operations
      GROUP BY FACILITY_ID
    )
    SELECT 
      facility_id,
      current_status,
      uptime_percentage,
      last_maintenance,
      operation_count
    BULK COLLECT INTO v_facility_stats
    FROM facility_metrics;

    -- Process and store analysis results
    FORALL i IN 1..v_facility_stats.COUNT
      INSERT INTO FACILITY_PERFORMANCE_LOG (
        facility_id,
        analysis_date,
        current_status,
        uptime_percentage,
        last_maintenance_date,
        total_operations,
        analysis_period_days
      ) VALUES (
        v_facility_stats(i).facility_id,
        v_analysis_date,
        v_facility_stats(i).current_status,
        v_facility_stats(i).uptime_percentage,
        v_facility_stats(i).last_maintenance,
        v_facility_stats(i).operation_count,
        p_days_back
      );

    -- Schedule maintenance for facilities with low uptime
    FOR i IN 1..v_facility_stats.COUNT LOOP
      IF v_facility_stats(i).uptime_percentage < 85 THEN
        schedule_maintenance(v_facility_stats(i).facility_id);
      END IF;
    END LOOP;

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_facility_performance;

  PROCEDURE schedule_maintenance(p_facility_id IN NUMBER) IS
    v_next_maintenance DATE;
    v_maintenance_duration NUMBER;
  BEGIN
    -- Calculate next maintenance window
    SELECT 
      TRUNC(SYSDATE) + 
      CASE 
        WHEN TO_CHAR(SYSDATE, 'D') IN (1, 7) THEN 2  -- Weekend
        ELSE 1  -- Weekday
      END,
      CASE 
        WHEN uptime_percentage < 70 THEN 48  -- Extended maintenance
        ELSE 24  -- Standard maintenance
      END
    INTO v_next_maintenance, v_maintenance_duration
    FROM FACILITY_PERFORMANCE_LOG
    WHERE facility_id = p_facility_id
    AND analysis_date = (
      SELECT MAX(analysis_date)
      FROM FACILITY_PERFORMANCE_LOG
      WHERE facility_id = p_facility_id
    );

    -- Schedule maintenance
    INSERT INTO MAINTENANCE_SCHEDULE (
      facility_id,
      scheduled_date,
      duration_hours,
      priority,
      status
    ) VALUES (
      p_facility_id,
      v_next_maintenance,
      v_maintenance_duration,
      CASE 
        WHEN v_maintenance_duration > 24 THEN 'HIGH'
        ELSE 'NORMAL'
      END,
      'SCHEDULED'
    );
  END schedule_maintenance;
END facility_operations;
/

-- Create analytics log table if not exists
CREATE TABLE OPERATIONS_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    total_facilities NUMBER,
    active_operations NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_operations_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view of operations data
CREATE OR REPLACE VIEW combined_operations_data AS
SELECT 
    o.id,
    o.facility_id,
    o.operation_date,
    o.status,
    f.name as facility_name,
    f.location as facility_location
FROM operations_data_54 o
JOIN facilities f ON o.facility_id = f.facility_id;

-- Analysis package
CREATE OR REPLACE PACKAGE operations_analysis AS
  -- Types for operation tracking
  TYPE r_facility_status IS RECORD (
    facility_id NUMBER,
    total_operations NUMBER,
    active_operations NUMBER,
    last_operation_date DATE
  );
  
  TYPE t_facility_status IS TABLE OF r_facility_status;
  
  -- Procedures
  PROCEDURE analyze_facility_operations(p_date_range_days IN NUMBER DEFAULT 30);
END operations_analysis;
/

CREATE OR REPLACE PACKAGE BODY operations_analysis AS
  PROCEDURE analyze_facility_operations(p_date_range_days IN NUMBER DEFAULT 30) IS
    v_facility_stats t_facility_status;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_date_range_days;
  BEGIN
    -- Calculate facility statistics
    WITH daily_operations AS (
      SELECT 
        facility_id,
        COUNT(*) as operation_count,
        COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_count,
        operation_date
      FROM combined_operations_data
      WHERE operation_date >= v_start_date
      GROUP BY facility_id, operation_date
    )
    SELECT 
      facility_id,
      SUM(operation_count) as total_operations,
      SUM(active_count) as active_operations,
      MAX(operation_date) as last_operation_date
    BULK COLLECT INTO v_facility_stats
    FROM daily_operations
    GROUP BY facility_id;

    -- Log results
    INSERT INTO OPERATIONS_ANALYTICS_LOG (
      analysis_id,
      analysis_date,
      total_facilities,
      active_operations,
      analysis_type
    ) VALUES (
      seq_operations_analytics_log.NEXTVAL,
      v_analysis_date,
      v_facility_stats.COUNT,
      (SELECT SUM(active_operations) FROM TABLE(v_facility_stats)),
      'FACILITY_OPERATIONS'
    );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_facility_operations;
END operations_analysis;
/