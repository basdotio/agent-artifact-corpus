-- Create analytics log table if not exists
CREATE TABLE FINANCE_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    total_accounts NUMBER,
    total_transactions NUMBER,
    total_amount NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
CREATE SEQUENCE seq_finance_analytics_log START WITH 1 INCREMENT BY 1;

-- Create combined view of finance data
CREATE OR REPLACE VIEW combined_finance_data AS
SELECT 
    f.id,
    f.account_id,
    f.transaction_amount,
    f.transaction_date,
    a.account_number,
    a.balance
FROM finance_data_87 f
JOIN accounts a ON f.account_id = a.account_id;

/*
 * Financial Transaction Analysis
 * Analyzes transaction patterns and account activity
 */
CREATE OR REPLACE PACKAGE financial_analysis AS
  -- Constants for analysis
  TYPE r_transaction_summary IS RECORD (
    account_id NUMBER,
    total_amount NUMBER,
    transaction_count NUMBER,
    avg_transaction NUMBER,
    last_transaction_date DATE
  );
  
  TYPE t_transaction_summary IS TABLE OF r_transaction_summary;
  
  -- Procedures and functions
  PROCEDURE analyze_account_activity(p_date_range_days IN NUMBER DEFAULT 30);
  FUNCTION calculate_account_risk(p_account_id IN NUMBER) RETURN NUMBER;
END financial_analysis;
/

CREATE OR REPLACE PACKAGE BODY financial_analysis AS
  PROCEDURE analyze_account_activity(p_date_range_days IN NUMBER DEFAULT 30) IS
    v_summaries t_transaction_summary;
    v_analysis_date DATE := SYSDATE;
    v_start_date DATE := v_analysis_date - p_date_range_days;
  BEGIN
    -- Get transaction summaries
    WITH daily_transactions AS (
      SELECT 
        account_id,
        SUM(transaction_amount) as daily_total,
        COUNT(*) as daily_count,
        transaction_date
      FROM combined_finance_data
      WHERE transaction_date >= v_start_date
      GROUP BY account_id, transaction_date
    )
    SELECT 
      account_id,
      SUM(daily_total) as total_amount,
      SUM(daily_count) as transaction_count,
      AVG(daily_total) as avg_transaction,
      MAX(transaction_date) as last_transaction_date
    BULK COLLECT INTO v_summaries
    FROM daily_transactions
    GROUP BY account_id;

    -- Log results
    INSERT INTO FINANCE_ANALYTICS_LOG (
      analysis_id,
      analysis_date,
      total_accounts,
      total_transactions,
      total_amount,
      analysis_type
    ) VALUES (
      seq_finance_analytics_log.NEXTVAL,
      v_analysis_date,
      v_summaries.COUNT,
      (SELECT SUM(transaction_count) FROM TABLE(v_summaries)),
      (SELECT SUM(total_amount) FROM TABLE(v_summaries)),
      'ACCOUNT_ACTIVITY'
    );

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_account_activity;

  FUNCTION calculate_account_risk(p_account_id IN NUMBER) RETURN NUMBER IS
    v_risk_score NUMBER;
  BEGIN
    SELECT 
      CASE
        WHEN avg_daily_amount > 10000 THEN 3  -- High risk
        WHEN avg_daily_amount > 5000 THEN 2   -- Medium risk
        ELSE 1                                -- Low risk
      END INTO v_risk_score
    FROM (
      SELECT AVG(transaction_amount) as avg_daily_amount
      FROM combined_finance_data
      WHERE account_id = p_account_id
      AND transaction_date >= SYSDATE - 30
    );
    
    RETURN v_risk_score;
  END calculate_account_risk;
END financial_analysis;
/