-- Wait for database to be ready
WHENEVER SQLERROR EXIT SQL.SQLCODE;

-- Connect as SYSDBA to create test user
CONNECT sys/Welcome123 as sysdba

-- Create PDB if not exists and set it as current container
ALTER SESSION SET CONTAINER = FREEPDB1;

-- Create test user with more privileges for large-scale operations
CREATE USER testuser IDENTIFIED BY "testpass"
    DEFAULT TABLESPACE USERS
    TEMPORARY TABLESPACE TEMP;

-- Grant necessary privileges
GRANT CONNECT, RESOURCE TO testuser;
GRANT CREATE SESSION TO testuser;
GRANT CREATE TABLE TO testuser;
GRANT CREATE VIEW TO testuser;
GRANT CREATE SEQUENCE TO testuser;
GRANT UNLIMITED TABLESPACE TO testuser;
GRANT CREATE PROCEDURE TO testuser;
GRANT CREATE TRIGGER TO testuser;

-- Connect as test user
CONNECT testuser/testpass@//localhost:1521/FREEPDB1;

-- Create sequences for all primary keys
DECLARE
    v_sql VARCHAR2(1000);
BEGIN
    FOR i IN 1..1200 LOOP  -- Creating more sequences than needed
        v_sql := 'CREATE SEQUENCE seq_' || i || ' START WITH 1 INCREMENT BY 1 NOCACHE';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- HR Domain (50 tables)
CREATE TABLE departments (
    dept_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    location VARCHAR2(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE job_titles (
    title_id NUMBER PRIMARY KEY,
    title_name VARCHAR2(100) NOT NULL,
    min_salary NUMBER(10,2),
    max_salary NUMBER(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employee_grades (
    grade_id NUMBER PRIMARY KEY,
    grade_name VARCHAR2(50) NOT NULL,
    grade_level NUMBER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE employees (
    employee_id NUMBER PRIMARY KEY,
    dept_id NUMBER,
    title_id NUMBER,
    grade_id NUMBER,
    first_name VARCHAR2(50) NOT NULL,
    last_name VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) UNIQUE NOT NULL,
    hire_date DATE,
    salary NUMBER(10,2),
    status VARCHAR2(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'TERMINATED', 'ON_LEAVE', 'SUSPENDED')),
    manager_id NUMBER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dept FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
    CONSTRAINT fk_title FOREIGN KEY (title_id) REFERENCES job_titles(title_id),
    CONSTRAINT fk_grade FOREIGN KEY (grade_id) REFERENCES employee_grades(grade_id),
    CONSTRAINT fk_manager FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
);

CREATE TABLE employee_history (
    history_id NUMBER PRIMARY KEY,
    employee_id NUMBER,
    dept_id NUMBER,
    title_id NUMBER,
    grade_id NUMBER,
    salary NUMBER(10,2),
    status VARCHAR2(20),
    effective_from DATE,
    effective_to DATE,
    change_reason VARCHAR2(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_emp_hist FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- Generate 48 more HR-related tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    -- Generate HR attribute tables
    FOR i IN 1..48 LOOP
        v_sql := 'CREATE TABLE hr_attribute_' || i || ' (
            id NUMBER PRIMARY KEY,
            employee_id NUMBER,
            attribute_value VARCHAR2(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_emp_' || i || ' FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        )';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- Sales and Order Management Domain
CREATE TABLE customers (
    customer_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    email VARCHAR2(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generate 199 sales-related tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    FOR i IN 1..199 LOOP
        v_sql := 'CREATE TABLE sales_data_' || i || ' (
            id NUMBER PRIMARY KEY,
            customer_id NUMBER,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            amount NUMBER(10,2),
            CONSTRAINT fk_cust_' || i || ' FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- Product and Inventory Domain
CREATE TABLE product_categories (
    category_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    description VARCHAR2(500),
    parent_category_id NUMBER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_parent_category FOREIGN KEY (parent_category_id) REFERENCES product_categories(category_id)
);

CREATE TABLE products (
    product_id NUMBER PRIMARY KEY,
    category_id NUMBER,
    sku VARCHAR2(50) UNIQUE NOT NULL,
    name VARCHAR2(100) NOT NULL,
    description VARCHAR2(500),
    weight NUMBER(10,2),
    dimensions VARCHAR2(50),
    is_active CHAR(1) DEFAULT '1' CHECK (is_active IN ('0','1')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_category FOREIGN KEY (category_id) REFERENCES product_categories(category_id)
);

CREATE TABLE product_prices (
    price_id NUMBER PRIMARY KEY,
    product_id NUMBER,
    base_price NUMBER(10,2) NOT NULL,
    discount_price NUMBER(10,2),
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_product_price FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Order Management tables
CREATE TABLE order_status (
    status_id NUMBER PRIMARY KEY,
    status_name VARCHAR2(50) NOT NULL,
    description VARCHAR2(200)
);

CREATE TABLE orders (
    order_id NUMBER PRIMARY KEY,
    customer_id NUMBER,
    employee_id NUMBER,
    order_date TIMESTAMP,
    status_id NUMBER,
    total_amount NUMBER(10,2),
    shipping_address VARCHAR2(500),
    billing_address VARCHAR2(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_order_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CONSTRAINT fk_order_status FOREIGN KEY (status_id) REFERENCES order_status(status_id)
);

CREATE TABLE order_items (
    item_id NUMBER PRIMARY KEY,
    order_id NUMBER,
    product_id NUMBER,
    quantity NUMBER NOT NULL,
    unit_price NUMBER(10,2) NOT NULL,
    discount_amount NUMBER(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_item_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
    CONSTRAINT fk_order_item_product FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Generate 199 inventory-related tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    FOR i IN 1..199 LOOP
        v_sql := 'CREATE TABLE inventory_data_' || i || ' (
            id NUMBER PRIMARY KEY,
            product_id NUMBER,
            quantity NUMBER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_prod_' || i || ' FOREIGN KEY (product_id) REFERENCES products(product_id)
        )';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- Finance Domain
CREATE TABLE accounts (
    account_id NUMBER PRIMARY KEY,
    customer_id NUMBER,
    account_number VARCHAR2(20) UNIQUE NOT NULL,
    account_type VARCHAR2(50) NOT NULL,
    balance NUMBER(15,2),
    status VARCHAR2(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'FROZEN', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_account_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE transactions (
    transaction_id NUMBER PRIMARY KEY,
    account_id NUMBER,
    order_id NUMBER NULL,
    transaction_type VARCHAR2(20) CHECK (transaction_type IN ('PURCHASE', 'REFUND', 'DEPOSIT', 'WITHDRAWAL')),
    amount NUMBER(15,2),
    status VARCHAR2(20) DEFAULT 'COMPLETED' CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'REVERSED')),
    transaction_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_trans_account FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    CONSTRAINT fk_trans_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- Generate 199 finance-related tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    FOR i IN 1..199 LOOP
        v_sql := 'CREATE TABLE finance_data_' || i || ' (
            id NUMBER PRIMARY KEY,
            account_id NUMBER,
            transaction_amount NUMBER(15,2),
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_acc_' || i || ' FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- Operations Domain
CREATE TABLE facilities (
    facility_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    location VARCHAR2(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generate 199 operations-related tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    FOR i IN 1..199 LOOP
        v_sql := 'CREATE TABLE operations_data_' || i || ' (
            id NUMBER PRIMARY KEY,
            facility_id NUMBER,
            operation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR2(20),
            CONSTRAINT fk_fac_' || i || ' FOREIGN KEY (facility_id) REFERENCES facilities(facility_id)
        )';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- Customer Service Domain
CREATE TABLE tickets (
    ticket_id NUMBER PRIMARY KEY,
    customer_id NUMBER,
    status VARCHAR2(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ticket_cust FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Generate 149 customer service related tables
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    FOR i IN 1..149 LOOP
        v_sql := 'CREATE TABLE service_data_' || i || ' (
            id NUMBER PRIMARY KEY,
            ticket_id NUMBER,
            resolution_time TIMESTAMP,
            satisfaction_score NUMBER(2),
            CONSTRAINT fk_tick_' || i || ' FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        )';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

-- Create indexes for better performance
DECLARE
    v_sql VARCHAR2(4000);
BEGIN
    -- Create indexes for HR tables
    FOR i IN 1..48 LOOP
        EXECUTE IMMEDIATE 'CREATE INDEX idx_hr_' || i || '_emp ON hr_attribute_' || i || '(employee_id)';
    END LOOP;

    -- Create indexes for Sales tables
    FOR i IN 1..199 LOOP
        EXECUTE IMMEDIATE 'CREATE INDEX idx_sales_' || i || '_cust ON sales_data_' || i || '(customer_id)';
    END LOOP;

    -- Create indexes for Inventory tables
    FOR i IN 1..199 LOOP
        EXECUTE IMMEDIATE 'CREATE INDEX idx_inv_' || i || '_prod ON inventory_data_' || i || '(product_id)';
    END LOOP;

    -- Create indexes for Finance tables
    FOR i IN 1..199 LOOP
        EXECUTE IMMEDIATE 'CREATE INDEX idx_fin_' || i || '_acc ON finance_data_' || i || '(account_id)';
    END LOOP;

    -- Create indexes for Operations tables
    FOR i IN 1..199 LOOP
        EXECUTE IMMEDIATE 'CREATE INDEX idx_ops_' || i || '_fac ON operations_data_' || i || '(facility_id)';
    END LOOP;

    -- Create indexes for Customer Service tables
    FOR i IN 1..149 LOOP
        EXECUTE IMMEDIATE 'CREATE INDEX idx_serv_' || i || '_tick ON service_data_' || i || '(ticket_id)';
    END LOOP;

    -- Create additional indexes for performance
    EXECUTE IMMEDIATE 'CREATE INDEX idx_emp_manager ON employees(manager_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_emp_title ON employees(title_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_emp_grade ON employees(grade_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_emp_status ON employees(status)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_prod_category ON products(category_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_price_product ON product_prices(product_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_price_effective ON product_prices(effective_from, effective_to)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_order_customer ON orders(customer_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_order_employee ON orders(employee_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_order_status ON orders(status_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_order_date ON orders(order_date)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_trans_order ON transactions(order_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_trans_account ON transactions(account_id)';
    EXECUTE IMMEDIATE 'CREATE INDEX idx_trans_date ON transactions(transaction_date)';
END;
/