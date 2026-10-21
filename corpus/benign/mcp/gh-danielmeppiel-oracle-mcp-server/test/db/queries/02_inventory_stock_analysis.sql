/*
 * Inventory Stock Analysis
 * Analyzes inventory trends across multiple warehouses and products
 */
CREATE OR REPLACE PACKAGE inventory_analysis AS
  -- Stock level thresholds
  low_stock_threshold CONSTANT NUMBER := 10;
  critical_stock_threshold CONSTANT NUMBER := 5;
  
  -- Types for inventory tracking
  TYPE product_stock_record IS RECORD (
    product_id NUMBER,
    total_quantity NUMBER,
    last_updated DATE,
    stock_status VARCHAR2(20)
  );
  
  TYPE product_stock_table IS TABLE OF product_stock_record;
  
  -- Main analysis procedure
  PROCEDURE analyze_stock_levels;
  
  -- Helper function to check stock status
  FUNCTION get_stock_status(p_quantity IN NUMBER) RETURN VARCHAR2;
END inventory_analysis;
/

CREATE OR REPLACE PACKAGE BODY inventory_analysis AS
  FUNCTION get_stock_status(p_quantity IN NUMBER) RETURN VARCHAR2 IS
  BEGIN
    RETURN CASE
      WHEN p_quantity <= critical_stock_threshold THEN 'CRITICAL'
      WHEN p_quantity <= low_stock_threshold THEN 'LOW'
      ELSE 'NORMAL'
    END;
  END get_stock_status;

  PROCEDURE analyze_stock_levels IS
    v_stock_data product_stock_table;
  BEGIN
    -- Combine inventory data from multiple tables
    WITH combined_inventory AS (
      SELECT PRODUCT_ID, QUANTITY, LAST_UPDATED
      FROM INVENTORY_DATA_39
      UNION ALL
      SELECT PRODUCT_ID, QUANTITY, LAST_UPDATED
      FROM INVENTORY_DATA_6
      UNION ALL
      SELECT PRODUCT_ID, QUANTITY, LAST_UPDATED
      FROM INVENTORY_DATA_183
    ),
    aggregated_stock AS (
      SELECT 
        PRODUCT_ID,
        SUM(QUANTITY) as total_quantity,
        MAX(LAST_UPDATED) as last_updated
      FROM combined_inventory
      GROUP BY PRODUCT_ID
    )
    SELECT 
      product_id,
      total_quantity,
      last_updated,
      get_stock_status(total_quantity) as stock_status
    BULK COLLECT INTO v_stock_data
    FROM aggregated_stock;

    -- Process and store results
    FORALL i IN 1..v_stock_data.COUNT
      INSERT INTO INVENTORY_ALERTS (
        product_id,
        total_quantity,
        last_check_date,
        stock_status,
        alert_generated_at
      ) VALUES (
        v_stock_data(i).product_id,
        v_stock_data(i).total_quantity,
        v_stock_data(i).last_updated,
        v_stock_data(i).stock_status,
        SYSDATE
      );

    -- Generate alerts for critical stock
    FOR i IN 1..v_stock_data.COUNT LOOP
      IF v_stock_data(i).stock_status = 'CRITICAL' THEN
        -- Trigger alert procedure (implementation not shown)
        NULL;
      END IF;
    END LOOP;

    COMMIT;
  EXCEPTION
    WHEN OTHERS THEN
      ROLLBACK;
      RAISE;
  END analyze_stock_levels;
END inventory_analysis;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE INVENTORY_ANALYTICS_LOG';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/
-- Create analytics log table if not exists
CREATE TABLE INVENTORY_ANALYTICS_LOG (
    analysis_id NUMBER PRIMARY KEY,
    analysis_date DATE,
    total_products NUMBER,
    low_stock_count NUMBER,
    analysis_type VARCHAR2(50)
);

-- Create sequence for analytics log
DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count 
    FROM USER_SEQUENCES 
    WHERE SEQUENCE_NAME = 'SEQ_INVENTORY_ANALYTICS_LOG';
    
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE seq_inventory_analytics_log START WITH 1 INCREMENT BY 1';
    END IF;
END;
/

-- Create combined view of inventory data
CREATE OR REPLACE VIEW combined_inventory_data AS
SELECT 
    i.id,
    i.product_id,
    i.quantity,
    i.last_updated,
    p.name as product_name,
    p.price
FROM inventory_data_1 i
JOIN products p ON i.product_id = p.product_id;

-- Analysis procedure
CREATE OR REPLACE PROCEDURE analyze_inventory_levels AS
  v_total_products NUMBER;
  v_low_stock NUMBER;
BEGIN
  WITH stock_categories AS (
    SELECT 
      product_id,
      quantity,
      CASE 
        WHEN quantity < 10 THEN 'LOW'
        WHEN quantity < 50 THEN 'MEDIUM'
        ELSE 'HIGH'
      END AS stock_level
    FROM combined_inventory_data
  )
  SELECT 
    COUNT(DISTINCT product_id) as total_products,
    COUNT(CASE WHEN stock_level = 'LOW' THEN 1 END) as low_stock_count
  INTO v_total_products, v_low_stock
  FROM stock_categories;

  -- Log results
  INSERT INTO INVENTORY_ANALYTICS_LOG (
    analysis_id,
    analysis_date,
    total_products,
    low_stock_count,
    analysis_type
  ) VALUES (
    seq_inventory_analytics_log.NEXTVAL,
    SYSDATE,
    v_total_products,
    v_low_stock,
    'STOCK_LEVEL_ANALYSIS'
  );

  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END analyze_inventory_levels;
/