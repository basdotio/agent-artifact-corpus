-- Connect as test user
CONNECT testuser/testpass@//localhost:1521/FREEPDB1;

-- Insert sample data into main tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    -- Insert departments
    INSERT INTO departments 
    SELECT LEVEL, 
           'Department ' || LEVEL, 
           'Location ' || LEVEL, 
           CURRENT_TIMESTAMP 
    FROM dual 
    CONNECT BY LEVEL <= 10;

    -- Insert job titles with realistic salary ranges
    INSERT INTO job_titles (title_id, title_name, min_salary, max_salary)
    VALUES 
    (1, 'Junior Associate', 35000, 55000),
    (2, 'Associate', 45000, 75000),
    (3, 'Senior Associate', 65000, 95000),
    (4, 'Manager', 85000, 120000),
    (5, 'Senior Manager', 100000, 150000),
    (6, 'Director', 130000, 200000),
    (7, 'VP', 180000, 300000),
    (8, 'SVP', 250000, 400000),
    (9, 'EVP', 300000, 500000),
    (10, 'C-Level', 400000, 1000000);

    -- Insert employee grades
    INSERT INTO employee_grades (grade_id, grade_name, grade_level)
    VALUES 
    (1, 'Entry Level', 1),
    (2, 'Junior', 2),
    (3, 'Intermediate', 3),
    (4, 'Senior', 4),
    (5, 'Expert', 5),
    (6, 'Master', 6);

    -- Insert employees with realistic data distribution - managers first
    -- First pass: Insert managers (no manager references)
    INSERT INTO employees (
        employee_id, dept_id, title_id, grade_id, first_name, last_name, 
        email, hire_date, salary, status, manager_id
    )
    SELECT 
        LEVEL,
        MOD(LEVEL, 10) + 1,
        CASE 
            WHEN LEVEL <= 5 THEN TRUNC(DBMS_RANDOM.VALUE(8, 11))  -- Top management
            ELSE TRUNC(DBMS_RANDOM.VALUE(6, 8))                   -- Mid management
        END,
        CASE 
            WHEN LEVEL <= 5 THEN 6  -- Top management grade
            ELSE 5                  -- Mid management grade
        END,
        'FirstName' || LEVEL,
        'LastName' || LEVEL,
        'email' || LEVEL || '@example.com',
        SYSDATE - TRUNC(DBMS_RANDOM.VALUE(1500, 3650)),  -- Longer tenure for managers
        CASE 
            WHEN LEVEL <= 5 THEN ROUND(DBMS_RANDOM.VALUE(400000, 1000000), -3)
            ELSE ROUND(DBMS_RANDOM.VALUE(200000, 400000), -3)
        END,
        'ACTIVE',  -- Managers are always active
        NULL       -- Top level has no managers
    FROM dual 
    CONNECT BY LEVEL <= 20;  -- Create 20 managers first

    -- Second pass: Insert regular employees with manager references
    INSERT INTO employees (
        employee_id, dept_id, title_id, grade_id, first_name, last_name, 
        email, hire_date, salary, status, manager_id
    )
    SELECT 
        LEVEL + 20,  -- Start IDs after managers
        MOD(LEVEL, 10) + 1,
        TRUNC(DBMS_RANDOM.VALUE(1, 4)),  -- Regular employee titles
        TRUNC(DBMS_RANDOM.VALUE(1, 4)),  -- Regular employee grades
        'FirstName' || (LEVEL + 20),
        'LastName' || (LEVEL + 20),
        'email' || (LEVEL + 20) || '@example.com',
        SYSDATE - TRUNC(DBMS_RANDOM.VALUE(1, 1500)),
        ROUND(DBMS_RANDOM.VALUE(35000, 100000), -3),
        CASE 
            WHEN DBMS_RANDOM.VALUE(0, 1) > 0.95 THEN 'TERMINATED'
            WHEN DBMS_RANDOM.VALUE(0, 1) > 0.90 THEN 'ON_LEAVE'
            ELSE 'ACTIVE'
        END,
        TRUNC(DBMS_RANDOM.VALUE(1, 20))  -- Randomly assign to one of the 20 managers
    FROM dual 
    CONNECT BY LEVEL <= 80;  -- Create 80 regular employees

    -- Insert customers
    INSERT INTO customers 
    SELECT LEVEL,
           'Customer ' || LEVEL,
           'customer' || LEVEL || '@example.com',
           CURRENT_TIMESTAMP
    FROM dual 
    CONNECT BY LEVEL <= 1000;

    -- Insert product categories
    INSERT INTO product_categories (category_id, name, description, parent_category_id)
    VALUES
    (1, 'Electronics', 'Electronic devices and accessories', NULL),
    (2, 'Computers', 'Computer systems and parts', 1),
    (3, 'Smartphones', 'Mobile phones and accessories', 1),
    (4, 'Clothing', 'Apparel and accessories', NULL),
    (5, 'Men''s Wear', 'Men''s clothing', 4),
    (6, 'Women''s Wear', 'Women''s clothing', 4);

    -- Insert products with more realistic data
    INSERT INTO products (
        product_id, category_id, sku, name, description, 
        weight, dimensions, is_active
    )
    SELECT 
        LEVEL,
        MOD(LEVEL, 6) + 1,
        'SKU-' || LPAD(LEVEL, 6, '0'),
        'Product ' || LEVEL,
        'Description for product ' || LEVEL,
        ROUND(DBMS_RANDOM.VALUE(0.1, 50), 2),
        ROUND(DBMS_RANDOM.VALUE(1, 100)) || 'x' || 
        ROUND(DBMS_RANDOM.VALUE(1, 100)) || 'x' || 
        ROUND(DBMS_RANDOM.VALUE(1, 100)),
        CASE WHEN DBMS_RANDOM.VALUE(0, 1) > 0.1 THEN '1' ELSE '0' END
    FROM dual 
    CONNECT BY LEVEL <= 1000;

    -- Insert product prices with history
    INSERT INTO product_prices (
        price_id, product_id, base_price, discount_price,
        effective_from, effective_to
    )
    SELECT 
        LEVEL,
        MOD(LEVEL-1, 1000) + 1,
        ROUND(DBMS_RANDOM.VALUE(10, 5000), 2),
        CASE WHEN DBMS_RANDOM.VALUE(0, 1) > 0.7 
             THEN ROUND(DBMS_RANDOM.VALUE(5, 4000), 2)
             ELSE NULL
        END,
        SYSDATE - INTERVAL '1' YEAR + (MOD(LEVEL-1, 4) * INTERVAL '3' MONTH),
        CASE WHEN MOD(LEVEL-1, 4) < 3 
             THEN SYSDATE - INTERVAL '1' YEAR + ((MOD(LEVEL-1, 4) + 1) * INTERVAL '3' MONTH)
             ELSE NULL
        END
    FROM dual 
    CONNECT BY LEVEL <= 4000;

    -- Insert order statuses
    INSERT INTO order_status (status_id, status_name, description)
    VALUES
    (1, 'PENDING', 'Order created but not confirmed'),
    (2, 'CONFIRMED', 'Order confirmed, awaiting processing'),
    (3, 'PROCESSING', 'Order is being processed'),
    (4, 'SHIPPED', 'Order has been shipped'),
    (5, 'DELIVERED', 'Order has been delivered'),
    (6, 'CANCELLED', 'Order was cancelled'),
    (7, 'RETURNED', 'Order was returned');

    -- Insert accounts with varying types and balances
    INSERT INTO accounts 
    SELECT LEVEL,
           MOD(LEVEL, 1000) + 1,
           'ACC' || LPAD(LEVEL, 10, '0'),
           CASE 
               WHEN LEVEL <= 200 THEN 'SAVINGS'
               WHEN LEVEL <= 400 THEN 'CHECKING'
               WHEN LEVEL <= 600 THEN 'CREDIT'
               ELSE 'LOAN'
           END,
           10000 + MOD(LEVEL, 90000),
           CASE 
               WHEN DBMS_RANDOM.VALUE(0, 1) > 0.95 THEN 'CLOSED'
               WHEN DBMS_RANDOM.VALUE(0, 1) > 0.90 THEN 'FROZEN'
               ELSE 'ACTIVE'
           END,
           CURRENT_TIMESTAMP
    FROM dual 
    CONNECT BY LEVEL <= 1000;

    -- Insert facilities
    INSERT INTO facilities 
    SELECT LEVEL,
           'Facility ' || LEVEL,
           'Location ' || LEVEL,
           CURRENT_TIMESTAMP
    FROM dual 
    CONNECT BY LEVEL <= 100;

    -- Insert tickets
    INSERT INTO tickets 
    SELECT LEVEL,
           MOD(LEVEL, 1000) + 1,
           CASE MOD(LEVEL, 3) 
               WHEN 0 THEN 'OPEN'
               WHEN 1 THEN 'IN_PROGRESS'
               ELSE 'CLOSED'
           END,
           CURRENT_TIMESTAMP
    FROM dual 
    CONNECT BY LEVEL <= 1000;

    -- Insert orders with realistic patterns
    INSERT INTO orders (
        order_id,
        customer_id,
        employee_id,
        order_date,
        status_id,
        shipping_address,
        billing_address,
        created_at
    )
    SELECT 
        LEVEL as order_id,
        TRUNC(DBMS_RANDOM.VALUE(1, 1000)) as customer_id,
        TRUNC(DBMS_RANDOM.VALUE(1, 100)) as employee_id,
        SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 365), 'DAY') as order_date,
        CASE 
            WHEN DBMS_RANDOM.VALUE(0, 1) > 0.95 THEN 6  -- CANCELLED
            WHEN DBMS_RANDOM.VALUE(0, 1) > 0.90 THEN 7  -- RETURNED
            ELSE TRUNC(DBMS_RANDOM.VALUE(1, 6))         -- Other statuses
        END as status_id,
        'Shipping Address ' || LEVEL,
        'Billing Address ' || LEVEL,
        SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 365), 'DAY')
    FROM dual 
    CONNECT BY LEVEL <= 5000;

    -- Insert order items with varying quantities and prices
    INSERT INTO order_items (
        item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        discount_amount
    )
    WITH random_items AS (
        SELECT 
            LEVEL as item_id,
            TRUNC(DBMS_RANDOM.VALUE(1, 5000)) as order_id,
            TRUNC(DBMS_RANDOM.VALUE(1, 1000)) as product_id,
            TRUNC(DBMS_RANDOM.VALUE(1, 10)) as quantity
        FROM dual 
        CONNECT BY LEVEL <= 15000
    ),
    latest_prices AS (
        SELECT 
            product_id,
            base_price,
            discount_price,
            ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY effective_from DESC) as rn
        FROM product_prices
        WHERE effective_from <= SYSDATE
        AND (effective_to IS NULL OR effective_to > SYSDATE)
    )
    SELECT 
        ri.item_id,
        ri.order_id,
        ri.product_id,
        ri.quantity,
        COALESCE(lp.discount_price, lp.base_price) as unit_price,
        CASE 
            WHEN lp.discount_price IS NOT NULL 
            THEN ROUND((lp.base_price - lp.discount_price) * ri.quantity, 2)
            ELSE 0
        END as discount_amount
    FROM random_items ri
    JOIN latest_prices lp ON ri.product_id = lp.product_id AND lp.rn = 1;

    -- Update order totals based on items
    UPDATE orders o
    SET total_amount = (
        SELECT SUM((quantity * unit_price) - discount_amount)
        FROM order_items oi
        WHERE oi.order_id = o.order_id
    );

    -- Create transactions for orders
    INSERT INTO transactions (
        transaction_id,
        account_id,
        order_id,
        transaction_type,
        amount,
        status,
        transaction_date,
        created_at
    )
    SELECT 
        seq_1000.NEXTVAL,
        a.account_id,
        o.order_id,
        CASE 
            WHEN o.status_id = 7 THEN 'REFUND'     -- RETURNED orders
            ELSE 'PURCHASE'                         -- All other orders
        END,
        CASE 
            WHEN o.status_id = 7 THEN -o.total_amount  -- Negative amount for refunds
            ELSE o.total_amount                        -- Positive amount for purchases
        END,
        CASE 
            WHEN o.status_id IN (1, 2) THEN 'PENDING'  -- PENDING or CONFIRMED orders
            WHEN o.status_id = 6 THEN 'FAILED'         -- CANCELLED orders
            ELSE 'COMPLETED'                           -- All other orders
        END,
        o.order_date,
        o.created_at
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN accounts a ON c.customer_id = a.customer_id
    WHERE ROWNUM <= 5000;

    -- Populate HR attribute tables with realistic employee attributes
    FOR i IN 1..48 LOOP
        v_sql := 'INSERT INTO hr_attribute_' || i || ' 
            SELECT 
                seq_' || i || '.NEXTVAL, 
                e.employee_id,
                CASE MOD(lvl.col, 5) 
                    WHEN 0 THEN ''Experience Level '' || TRUNC(DBMS_RANDOM.VALUE(1, 10))
                    WHEN 1 THEN ''Certification '' || TRUNC(DBMS_RANDOM.VALUE(1, 5))
                    WHEN 2 THEN ''Skill Rating '' || TRUNC(DBMS_RANDOM.VALUE(1, 100))
                    WHEN 3 THEN ''Training Score '' || TRUNC(DBMS_RANDOM.VALUE(60, 100))
                    ELSE ''Performance Index '' || TRUNC(DBMS_RANDOM.VALUE(1, 5))
                END,
                SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 365), ''DAY'')
            FROM employees e,
                 (SELECT LEVEL as col FROM dual CONNECT BY LEVEL <= 10) lvl';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;

    -- Populate Sales tables with transaction data
    FOR i IN 1..199 LOOP
        v_sql := 'INSERT INTO sales_data_' || i || '
            SELECT 
                seq_' || (i+100) || '.NEXTVAL,
                c.customer_id,
                SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 730), ''DAY''),
                ROUND(DBMS_RANDOM.VALUE(10, 5000), 2)
            FROM customers c,
                 (SELECT LEVEL as col FROM dual CONNECT BY LEVEL <= 50) l';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;

    -- Populate Inventory tables with stock data
    FOR i IN 1..199 LOOP
        v_sql := 'INSERT INTO inventory_data_' || i || '
            SELECT 
                seq_' || (i+300) || '.NEXTVAL,
                p.product_id,
                TRUNC(DBMS_RANDOM.VALUE(0, 1000)),
                SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 90), ''DAY'')
            FROM products p,
                 (SELECT LEVEL as col FROM dual CONNECT BY LEVEL <= 20) l';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;

    -- Populate Finance tables with transaction data
    FOR i IN 1..199 LOOP
        v_sql := 'INSERT INTO finance_data_' || i || '
            SELECT 
                seq_' || (i+500) || '.NEXTVAL,
                a.account_id,
                CASE WHEN DBMS_RANDOM.VALUE(0, 1) < 0.5 
                    THEN ROUND(-DBMS_RANDOM.VALUE(100, 10000), 2)
                    ELSE ROUND(DBMS_RANDOM.VALUE(100, 10000), 2)
                END,
                SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 365), ''DAY'')
            FROM accounts a,
                 (SELECT LEVEL as col FROM dual CONNECT BY LEVEL <= 30) l';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;

    -- Populate Operations tables with facility operations data
    FOR i IN 1..199 LOOP
        v_sql := 'INSERT INTO operations_data_' || i || '
            SELECT 
                seq_' || (i+700) || '.NEXTVAL,
                f.facility_id,
                SYSTIMESTAMP - NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 180), ''DAY''),
                CASE TRUNC(DBMS_RANDOM.VALUE(1, 4))
                    WHEN 1 THEN ''OPERATIONAL''
                    WHEN 2 THEN ''MAINTENANCE''
                    WHEN 3 THEN ''SHUTDOWN''
                    ELSE ''STARTUP''
                END
            FROM facilities f,
                 (SELECT LEVEL as col FROM dual CONNECT BY LEVEL <= 40) l';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;

    -- Populate Customer Service tables with service interaction data
    FOR i IN 1..149 LOOP
        v_sql := 'INSERT INTO service_data_' || i || '
            SELECT 
                seq_' || (i+900) || '.NEXTVAL,
                t.ticket_id,
                t.created_at + NUMTODSINTERVAL(DBMS_RANDOM.VALUE(1, 72), ''HOUR''),
                TRUNC(DBMS_RANDOM.VALUE(1, 11))
            FROM tickets t,
                 (SELECT LEVEL as col FROM dual CONNECT BY LEVEL <= 5) l
            WHERE t.status = ''CLOSED''';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;

    COMMIT;
END;
/

-- Analyze tables for better query performance
BEGIN
    FOR tab IN (SELECT table_name FROM user_tables) LOOP
        EXECUTE IMMEDIATE 'ANALYZE TABLE ' || tab.table_name || ' COMPUTE STATISTICS';
    END LOOP;
END;
/

COMMIT;