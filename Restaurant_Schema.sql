create database restaurant;
use restaurant;

-- MENU
CREATE TABLE Menu (menu_id INT PRIMARY KEY AUTO_INCREMENT, item_name VARCHAR(100) NOT NULL, description TEXT, price DECIMAL(10, 2) NOT NULL, category VARCHAR(50), is_available BOOLEAN DEFAULT TRUE);

-- CUSTOMER
CREATE TABLE Customer (customer_id INT PRIMARY KEY AUTO_INCREMENT,name VARCHAR(100),phone VARCHAR(15), email VARCHAR(100), created_at DATETIME DEFAULT CURRENT_TIMESTAMP);

-- TABLELIST
CREATE TABLE TableList (table_id INT PRIMARY KEY AUTO_INCREMENT, table_number INT NOT NULL, seating_capacity INT, is_available BOOLEAN DEFAULT TRUE);

-- ORDERS
CREATE TABLE Orders (order_id INT PRIMARY KEY AUTO_INCREMENT, customer_id INT, table_id INT, order_time DATETIME DEFAULT CURRENT_TIMESTAMP, total_amount DECIMAL(10, 2), order_status VARCHAR(20) DEFAULT 'pending',FOREIGN KEY (customer_id) REFERENCES Customer(customer_id), FOREIGN KEY (table_id) REFERENCES TableList(table_id));

-- ORDERITEM	
CREATE TABLE OrderItem (order_item_id INT PRIMARY KEY AUTO_INCREMENT,order_id INT,menu_id INT,quantity INT NOT NULL,item_price DECIMAL(10, 2),FOREIGN KEY (order_id) REFERENCES Orders(order_id), FOREIGN KEY (menu_id) REFERENCES Menu(menu_id));

-- RESERVATION
CREATE TABLE Reservation (reservation_id INT PRIMARY KEY AUTO_INCREMENT,customer_id INT,reservation_time DATETIME,party_size INT,table_id INT,status VARCHAR(20) DEFAULT 'booked',FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),FOREIGN KEY (table_id) REFERENCES TableList(table_id));

-- INGREDIENTS
CREATE TABLE Ingredient (ingredient_id INT PRIMARY KEY AUTO_INCREMENT,name VARCHAR(100) NOT NULL,unit VARCHAR(20),cost_per_unit DECIMAL(10, 2));

-- MENUINGREDIENT
CREATE TABLE MenuIngredient (menu_id INT,ingredient_id INT,quantity_required DECIMAL(10, 2),PRIMARY KEY (menu_id, ingredient_id),FOREIGN KEY (menu_id) REFERENCES Menu(menu_id),FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id));

-- INVENTORY
CREATE TABLE Inventory (inventory_id INT PRIMARY KEY AUTO_INCREMENT,ingredient_id INT,quantity_in_stock DECIMAL(10, 2),last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id));

-- PURCHASEORDER
CREATE TABLE PurchaseOrder (purchase_id INT PRIMARY KEY AUTO_INCREMENT,ingredient_id INT,quantity_ordered DECIMAL(10, 2),order_date DATE,expected_delivery DATE,FOREIGN KEY (ingredient_id) REFERENCES Ingredient(ingredient_id));

-- STAFFROLE
CREATE TABLE Role (role_id INT PRIMARY KEY AUTO_INCREMENT,role_name VARCHAR(50) NOT NULL);

-- STAFF
CREATE TABLE Staff (staff_id INT PRIMARY KEY AUTO_INCREMENT,name VARCHAR(100),phone VARCHAR(15),email VARCHAR(100),role_id INT,salary DECIMAL(10, 2),is_active BOOLEAN DEFAULT TRUE,FOREIGN KEY (role_id) REFERENCES Role(role_id));

-- SHIFT
CREATE TABLE Shift (shift_id INT PRIMARY KEY AUTO_INCREMENT,staff_id INT,shift_date DATE,start_time TIME,end_time TIME,FOREIGN KEY (staff_id) REFERENCES Staff(staff_id));

-- FEEDBACK
CREATE TABLE Feedback (feedback_id INT PRIMARY KEY AUTO_INCREMENT,customer_id INT,order_id INT,rating INT CHECK (rating BETWEEN 1 AND 5),comments TEXT,submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY (customer_id) REFERENCES Customer(customer_id),FOREIGN KEY (order_id) REFERENCES Orders(order_id));

-- PAYMENTS
CREATE TABLE Payments (payment_id INT PRIMARY KEY AUTO_INCREMENT,order_id INT,payment_method VARCHAR(20),amount DECIMAL(10, 2),payment_time DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY (order_id) REFERENCES Orders(order_id));

-- LOYALTYPROFILE
CREATE TABLE loyalty_profile (phone VARCHAR(20) PRIMARY KEY,customer_name VARCHAR(100),total_points INT DEFAULT 0,total_visits INT DEFAULT 0,total_spent DECIMAL(10,2) DEFAULT 0.0,last_visit DATETIME);

-- LOYALTYTRANSACTIONS
CREATE TABLE loyalty_transactions (transaction_id INT PRIMARY KEY AUTO_INCREMENT,phone VARCHAR(20),order_id INT,points_earned INT DEFAULT 0,points_redeemed INT DEFAULT 0,transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP);
