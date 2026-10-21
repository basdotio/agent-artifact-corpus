/*
 * Seasonal Trend Analysis
 * Analyzes seasonal patterns in sales and service metrics
 */
CREATE OR REPLACE PACKAGE seasonal_analysis AS
  -- Season definitions
  TYPE r_season_window IS RECORD (
    season_name VARCHAR2(20),
    start_month NUMBER,
    end_month NUMBER
  );
  
  TYPE t_season_metrics IS RECORD (
    season_name VARCHAR2(20),
    avg_sales NUMBER,
    peak_sales_day VARCHAR2(20),
    service_load NUMBER,
    correlation_factor NUMBER
  );
  
  TYPE t_season_array IS TABLE OF t_season_metrics;
  
  -- Main procedures
  PROCEDURE analyze_seasonal_patterns(p_years_back IN NUMBER DEFAULT 2);
  FUNCTION get_season_name(p_date IN DATE) RETURN VARCHAR2;
  PROCEDURE analyze_seasonal_trends(p_years_back IN NUMBER DEFAULT 1);
END seasonal_analysis;
/

CREATE OR REPLACE PACKAGE BODY seasonal_analysis AS
  FUNCTION get_season_name(p_date IN DATE) RETURN VARCHAR2 IS
    v_month NUMBER := EXTRACT(MONTH FROM p_date);
  BEGIN
    RETURN CASE
      WHEN v_month IN (12, 1, 2) THEN 'WINTER'
      WHEN v_month IN (3, 4, 5) THEN 'SPRING'
      WHEN v_month IN (6, 7, 8) THEN 'SUMMER'
      ELSE 'FALL'
    END;
  END get_season_name;

  PROCEDURE analyze_seasonal_patterns(p_years_back IN NUMBER DEFAULT 2) IS
    v_metrics t_season_array;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := ADD_MONTHS(v_analysis_date, -12 * p_years_back);
  BEGIN
    -- Analyze seasonal sales patterns
    WITH combined_sales AS (
      SELECT 
        TRANSACTION_DATE,
        AMOUNT,
        get_season_name(TRANSACTION_DATE) as season,
        TO_CHAR(TRANSACTION_DATE, 'DAY') as day_of_week
      FROM (
        SELECT TRANSACTION_DATE, AMOUNT FROM SALES_DATA_151
        WHERE TRANSACTION_DATE >= v_start_date
        UNION ALL
        SELECT TRANSACTION_DATE, AMOUNT FROM SALES_DATA_142
        WHERE TRANSACTION_DATE >= v_start_date
      )
    ),
    sales_by_season AS (
      SELECT 
        season,
        AVG(AMOUNT) as avg_daily_sales,
        STATS_MODE(day_of_week) as peak_sales_day
      FROM combined_sales
      GROUP BY season
    ),
    -- Analyze seasonal service patterns
    service_patterns AS (
      SELECT 
        get_season_name(RESOLUTION_TIME) as season,
        COUNT(*) as ticket_count,
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
      GROUP BY get_season_name(RESOLUTION_TIME)
    ),
    -- Combine metrics
    seasonal_metrics AS (
      SELECT 
        s.season,
        s.avg_daily_sales,
        s.peak_sales_day,
        sp.ticket_count as service_load,
        CORR(
          cs.AMOUNT,
          sp2.SATISFACTION_SCORE
        ) OVER (PARTITION BY s.season) as sales_service_correlation
      FROM sales_by_season s
      JOIN service_patterns sp ON sp.season = s.season
      JOIN combined_sales cs ON cs.season = s.season
      JOIN (
        SELECT SATISFACTION_SCORE, get_season_name(RESOLUTION_TIME) as season
        FROM SERVICE_DATA_62
        UNION ALL
        SELECT SATISFACTION_SCORE, get_season_name(RESOLUTION_TIME)
        FROM SERVICE_DATA_65
      ) sp2 ON sp2.season = s.season
    )
    -- Store results
    INSERT INTO SEASONAL_ANALYSIS_RESULTS (
      analysis_date,
      season_name,
      average_daily_sales,
      peak_sales_day,
      service_ticket_load,
      sales_service_correlation,
      analysis_period_years
    )
    SELECT 
      v_analysis_date,
      season,
      avg_daily_sales,
      peak_sales_day,
      service_load,
      sales_service_correlation,
      p_years_back
    FROM seasonal_metrics;

    -- Generate seasonal recommendations
    INSERT INTO SEASONAL_RECOMMENDATIONS (
      season_name,
      recommendation_date,
      category,
      action_items,
      priority
    )
    SELECT 
      season,
      v_analysis_date,
      CASE 
        WHEN service_load > AVG(service_load) OVER () THEN 'STAFFING'
        WHEN avg_daily_sales < AVG(avg_daily_sales) OVER () THEN 'SALES'
        ELSE 'MAINTENANCE'
      END,
      'Recommendations based on ' || p_years_back || ' years of data',
      CASE 
        WHEN ABS(sales_service_correlation) > 0.7 THEN 'HIGH'
        WHEN ABS(sales_service_correlation) > 0.4 THEN 'MEDIUM'
        ELSE 'LOW'
      END
    FROM seasonal_metrics;

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_seasonal_patterns;

  PROCEDURE analyze_seasonal_trends(p_years_back IN NUMBER DEFAULT 1) IS
    v_seasonal_stats t_seasonal_metrics;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := ADD_MONTHS(v_analysis_date, -12 * p_years_back);
  BEGIN
    -- Calculate seasonal metrics
    WITH seasonal_metrics AS (
      SELECT 
        CASE 
          WHEN EXTRACT(MONTH FROM transaction_date) IN (12,1,2) THEN 'WINTER'
          WHEN EXTRACT(MONTH FROM transaction_date) IN (3,4,5) THEN 'SPRING'
          WHEN EXTRACT(MONTH FROM transaction_date) IN (6,7,8) THEN 'SUMMER'
          ELSE 'FALL'
        END as season,
        SUM(sale_amount) as total_sales,
        AVG(satisfaction_score) as avg_satisfaction,
        COUNT(CASE WHEN operation_status = 'ACTIVE' THEN 1 END) / 
          NULLIF(COUNT(operation_status), 0) as efficiency
      FROM combined_seasonal_data
      WHERE transaction_date >= v_start_date
      GROUP BY CASE 
        WHEN EXTRACT(MONTH FROM transaction_date) IN (12,1,2) THEN 'WINTER'
        WHEN EXTRACT(MONTH FROM transaction_date) IN (3,4,5) THEN 'SPRING'
        WHEN EXTRACT(MONTH FROM transaction_date) IN (6,7,8) THEN 'SUMMER'
        ELSE 'FALL'
      END
    )
    SELECT 
      season,
      total_sales,
      avg_satisfaction,
      efficiency
    BULK COLLECT INTO v_seasonal_stats
    FROM seasonal_metrics;

    -- Log results for each season
    FORALL i IN 1..v_seasonal_stats.COUNT
      INSERT INTO SEASONAL_ANALYTICS_LOG (
        analysis_id,
        analysis_date,
        season,
        total_sales,
        avg_satisfaction,
        operational_efficiency,
        analysis_type
      ) VALUES (
        seq_seasonal_analytics_log.NEXTVAL,
        v_analysis_date,
        v_seasonal_stats(i).season,
        v_seasonal_stats(i).sales_volume,
        v_seasonal_stats(i).satisfaction_score,
        v_seasonal_stats(i).efficiency_score,
        'SEASONAL_TRENDS'
      );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_seasonal_trends;
END seasonal_analysis;
/

-- Create analytics log table if not exists
CREATE TABLE SEASONAL_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    season VARCHAR2(20),
    total_sales NUMBER,
    avg_satisfaction NUMBER,
    operational_efficiency NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_seasonal_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view for seasonal analysis
CREATE OR REPLACE VIEW combined_seasonal_data AS
SELECT 
    s.id as sale_id,
    s.customer_id,
    s.amount as sale_amount,
    s.transaction_date,
    sv.satisfaction_score,
    sv.resolution_time,
    o.status as operation_status,
    o.operation_date
FROM sales_data_151 s
LEFT JOIN service_data_9 sv ON s.customer_id = sv.id
LEFT JOIN operations_data_54 o ON s.customer_id = o.facility_id;