-- Connect as SYSDBA to create simple schema user
CONNECT sys/Welcome123 as sysdba

-- Set current container to PDB
ALTER SESSION SET CONTAINER = FREEPDB1;

-- Create a new user for the simple schema
CREATE USER simpleschema IDENTIFIED BY "simplepass"
    DEFAULT TABLESPACE USERS
    TEMPORARY TABLESPACE TEMP;

-- Grant necessary privileges
GRANT CONNECT, RESOURCE TO simpleschema;
GRANT CREATE SESSION TO simpleschema;
GRANT CREATE TABLE TO simpleschema;
GRANT CREATE VIEW TO simpleschema;
GRANT CREATE SEQUENCE TO simpleschema;
GRANT UNLIMITED TABLESPACE TO simpleschema;

-- Connect as simple schema user
CONNECT simpleschema/simplepass@//localhost:1521/FREEPDB1;

-- Create simple tables
CREATE TABLE categories (
    category_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    description VARCHAR2(500)
);

CREATE TABLE items (
    item_id NUMBER PRIMARY KEY,
    category_id NUMBER,
    name VARCHAR2(100) NOT NULL,
    price NUMBER(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_category FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Create sequences
CREATE SEQUENCE seq_category START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE seq_item START WITH 1 INCREMENT BY 1;

-- Insert sample data into categories
INSERT INTO categories (category_id, name, description)
VALUES (seq_category.NEXTVAL, 'Electronics', 'Electronic devices and gadgets');

INSERT INTO categories (category_id, name, description)
VALUES (seq_category.NEXTVAL, 'Books', 'Books and publications');

INSERT INTO categories (category_id, name, description)
VALUES (seq_category.NEXTVAL, 'Clothing', 'Apparel and accessories');

-- Insert sample data into items
INSERT INTO items (item_id, category_id, name, price)
VALUES (seq_item.NEXTVAL, 1, 'Smartphone', 699.99);

INSERT INTO items (item_id, category_id, name, price)
VALUES (seq_item.NEXTVAL, 1, 'Laptop', 1299.99);

INSERT INTO items (item_id, category_id, name, price)
VALUES (seq_item.NEXTVAL, 2, 'Python Programming', 49.99);

INSERT INTO items (item_id, category_id, name, price)
VALUES (seq_item.NEXTVAL, 2, 'Database Design', 39.99);

INSERT INTO items (item_id, category_id, name, price)
VALUES (seq_item.NEXTVAL, 3, 'T-Shirt', 19.99);

INSERT INTO items (item_id, category_id, name, price)
VALUES (seq_item.NEXTVAL, 3, 'Jeans', 59.99);

-- Create indexes for better performance
CREATE INDEX idx_item_category ON items(category_id);

-- Analyze tables for better query performance
ANALYZE TABLE categories COMPUTE STATISTICS;
ANALYZE TABLE items COMPUTE STATISTICS;

COMMIT;

-- Connect back as SYSDBA to grant cross-schema privileges
CONNECT sys/Welcome123 as sysdba

-- Set current container to PDB
ALTER SESSION SET CONTAINER = FREEPDB1;

-- Grant SELECT ANY TABLE to testuser after all tables are created
GRANT SELECT ANY TABLE TO testuser;