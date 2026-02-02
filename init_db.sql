SET client_encoding = 'UTF8';

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS stores (
    id_store SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    address VARCHAR(500),
    phone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS warehouses (
    id_warehouse SERIAL PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    address VARCHAR(500),
    phone VARCHAR(50),
    area NUMERIC(12,2) DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS products (
    id_product SERIAL PRIMARY KEY,
    article VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(300) NOT NULL,
    category_id INTEGER REFERENCES categories(id),
    unit VARCHAR(50) NOT NULL DEFAULT 'шт',
    purchase_price NUMERIC(12,2) NOT NULL CHECK (purchase_price >= 0),
    retail_price NUMERIC(12,2) NOT NULL CHECK (retail_price >= 0),
    min_stock_level INTEGER NOT NULL DEFAULT 5 CHECK (min_stock_level >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS employees (
    id_employee SERIAL PRIMARY KEY,
    login VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(300) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'seller')),
    store_id INTEGER REFERENCES stores(id_store),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT seller_store_check CHECK (
        (role = 'admin' AND store_id IS NULL) OR
        (role = 'seller' AND store_id IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS shifts (
    id_shift SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id_employee),
    store_id INTEGER NOT NULL REFERENCES stores(id_store),
    shift_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    shift_end TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'open',
    CONSTRAINT shift_duration_check CHECK (shift_end IS NULL OR shift_end > shift_start)
);

CREATE TABLE IF NOT EXISTS operations (
    id_operation SERIAL PRIMARY KEY,
    operation_type VARCHAR(20) NOT NULL,
    shift_id INTEGER REFERENCES shifts(id_shift),
    employee_id INTEGER NOT NULL REFERENCES employees(id_employee),
    store_id INTEGER NOT NULL REFERENCES stores(id_store),
    operation_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    total_revenue NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_profit NUMERIC(14,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    original_operation_id INTEGER REFERENCES operations(id_operation)
);

CREATE TABLE IF NOT EXISTS operation_items (
    id SERIAL PRIMARY KEY,
    operation_id INTEGER NOT NULL REFERENCES operations(id_operation) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id_product),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12,2) NOT NULL,
    purchase_price NUMERIC(12,2) NOT NULL,
    total_price NUMERIC(12,2) NOT NULL,
    cost NUMERIC(12,2) NOT NULL,
    profit NUMERIC(12,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS store_product_stock (
    store_id INTEGER NOT NULL REFERENCES stores(id_store),
    product_id INTEGER NOT NULL REFERENCES products(id_product),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (store_id, product_id)
);

CREATE TABLE IF NOT EXISTS warehouse_product_stock (
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id_warehouse),
    product_id INTEGER NOT NULL REFERENCES products(id_product),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (warehouse_id, product_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id_product),
    store_id INTEGER REFERENCES stores(id_store),
    warehouse_id INTEGER REFERENCES warehouses(id_warehouse),
    current_quantity INTEGER NOT NULL,
    threshold INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unread',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT notif_location_check CHECK (
        (store_id IS NOT NULL AND warehouse_id IS NULL) OR
        (store_id IS NULL AND warehouse_id IS NOT NULL) OR
        (store_id IS NULL AND warehouse_id IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_shifts_employee_store ON shifts(employee_id, store_id);
CREATE INDEX IF NOT EXISTS idx_shifts_end ON shifts(shift_end);
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'operations' AND column_name = 'original_operation_id') THEN
    ALTER TABLE operations ADD COLUMN original_operation_id INTEGER REFERENCES operations(id_operation);
  END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_operations_shift ON operations(shift_id);
CREATE INDEX IF NOT EXISTS idx_operations_type ON operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_operations_created ON operations(created_at);
CREATE INDEX IF NOT EXISTS idx_operations_original ON operations(original_operation_id);
CREATE INDEX IF NOT EXISTS idx_store_stock_store ON store_product_stock(store_id);
CREATE INDEX IF NOT EXISTS idx_store_stock_product ON store_product_stock(product_id);
CREATE INDEX IF NOT EXISTS idx_wh_stock_warehouse ON warehouse_product_stock(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_wh_stock_product ON warehouse_product_stock(product_id);
