/*
 * Service Satisfaction Analysis
 * Analyzes satisfaction trends across multiple service tables
 */

-- Create analytics log table if not exists
CREATE TABLE SERVICE_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    avg_satisfaction NUMBER,
    total_tickets NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_service_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view of service data
CREATE OR REPLACE VIEW combined_service_data AS
SELECT 
    s.id,
    s.ticket_id,
    s.satisfaction_score,
    s.resolution_time,
    t.created_at
FROM service_data_1 s
JOIN tickets t ON s.ticket_id = t.ticket_id;

-- Analysis procedure
CREATE OR REPLACE PROCEDURE analyze_service_satisfaction AS
  v_avg_satisfaction NUMBER;
  v_total_tickets NUMBER;
BEGIN
  WITH resolution_categories AS (
    SELECT 
      TICKET_ID,
      SATISFACTION_SCORE,
      CASE 
        WHEN RESOLUTION_TIME IS NULL THEN 'PENDING'
        WHEN RESOLUTION_TIME <= CREATED_AT + INTERVAL '24' HOUR THEN 'QUICK'
        WHEN RESOLUTION_TIME <= CREATED_AT + INTERVAL '72' HOUR THEN 'NORMAL'
        ELSE 'DELAYED'
      END AS resolution_category
    FROM combined_service_data
  )
  SELECT 
    resolution_category,
    ROUND(AVG(SATISFACTION_SCORE), 2) as avg_satisfaction,
    COUNT(*) as ticket_count
  INTO v_avg_satisfaction, v_total_tickets
  FROM resolution_categories
  GROUP BY resolution_category
  ORDER BY avg_satisfaction DESC;

  -- Log results
  INSERT INTO SERVICE_ANALYTICS_LOG (
    analysis_id,
    analysis_date,
    avg_satisfaction,
    total_tickets,
    analysis_type
  ) VALUES (
    seq_service_analytics_log.NEXTVAL,
    SYSDATE,
    v_avg_satisfaction,
    v_total_tickets,
    'SATISFACTION_TREND'
  );

  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END analyze_service_satisfaction;
/