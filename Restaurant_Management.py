from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

# --- Database Configuration ---
db = mysql.connector.connect(
    host="localhost",
    user="allen",
    password="password123",
    database="restaurant"
)
cursor = db.cursor(dictionary=True)

# --- Sample Endpoints ---

# Get available menu items
@app.route('/get-menu', methods=['GET'])
def get_menu():
    cursor.execute("SELECT * FROM Menu WHERE is_available = TRUE")
    menu = cursor.fetchall()
    return jsonify(menu)

# Get today's total sales
@app.route('/sales-summary', methods=['GET'])
def get_sales_summary():
    cursor.execute("""
        SELECT SUM(total_amount) AS revenue_today
        FROM Orders
        WHERE DATE(order_time) = CURDATE() AND order_status = 'completed'
    """)
    summary = cursor.fetchone()
    return jsonify(summary)

# Place a new order
@app.route('/place-order', methods=['POST'])
def place_order():
    data = request.get_json()
    customer_id = data['customer_id']
    table_id = data['table_id']
    order_items = data['items']  # List of {menu_id, quantity}

    total_amount = 0
    for item in order_items:
        cursor.execute("SELECT price FROM Menu WHERE menu_id = %s", (item['menu_id'],))
        price = cursor.fetchone()['price']
        total_amount += price * item['quantity']

    cursor.execute(
        "INSERT INTO Orders (customer_id, table_id, total_amount) VALUES (%s, %s, %s)",
        (customer_id, table_id, total_amount)
    )
    order_id = cursor.lastrowid

    for item in order_items:
        cursor.execute("SELECT price FROM Menu WHERE menu_id = %s", (item['menu_id'],))
        price = cursor.fetchone()['price']
        cursor.execute(
            "INSERT INTO OrderItem (order_id, menu_id, quantity, item_price) VALUES (%s, %s, %s, %s)",
            (order_id, item['menu_id'], item['quantity'], price)
        )

    db.commit()
    return jsonify({"message": "Order placed successfully", "order_id": order_id})

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
