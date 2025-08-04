#Required Libraries

import mysql.connector
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, Listbox, StringVar
from ttkbootstrap import Style
from datetime import datetime
from tkinter import Toplevel
from ttkbootstrap.tooltip import ToolTip
from tkinter import simpledialog
import pywhatkit as kit
import smtplib
from email.message import EmailMessage
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import random
import pandas as pd
import seaborn as sns


#MySQL Connection

db = mysql.connector.connect(
    host="localhost",
    user="allen",
    password="password123",
    database="restaurant"
)
cursor = db.cursor()

# Main Window Screen Setup

root = ttk.Window(themename="superhero")
root.title("Restaurant POS System")
root.geometry("2000x2000")
root.withdraw()  


logged_in_staff = {}

#  Staff Login Screen

def staff_login_window():
    login_win = tk.Toplevel(root)
    login_win.title("Staff Login")
    login_win.geometry("450x350")
    login_win.grab_set()
    login_win.configure(bg="#2C2F33")

    ttk.Label(login_win, text="Staff Login", font=("Segoe UI", 16, "bold"), bootstyle="SUCCESS").pack(pady=20)

    staff_id_var = tk.StringVar()
    name_var = tk.StringVar()

    ttk.Label(login_win, text="Staff ID:", bootstyle="SUCCESS",font=("Segoe UI", 12, "bold")).pack(pady=5)
    ttk.Entry(login_win, textvariable=staff_id_var, width=30).pack()

    ttk.Label(login_win, text="Name:", bootstyle="SUCCESS", font=("Segoe UI", 12, "bold")).pack(pady=5)
    ttk.Entry(login_win, textvariable=name_var, width=30).pack()

    def submit_login():
        staff_id = staff_id_var.get().strip()
        name = name_var.get().strip()

        if not staff_id or not name:
            messagebox.showerror("Input Error", "Both Staff ID and Name are required.")
            return

        cursor.execute("SELECT name FROM Staff WHERE staff_id = %s", (staff_id,))
        result = cursor.fetchone()

        if result and result[0].lower() == name.lower():
            login_time = datetime.now()
            cursor.execute("INSERT INTO Shift (staff_id, shift_date, start_time) VALUES (%s, %s, %s)",
                           (staff_id, login_time.date(), login_time.strftime("%H:%M:%S")))
            db.commit()

            logged_in_staff["staff_id"] = staff_id
            logged_in_staff["name"] = name

            login_win.destroy()
            show_main_interface()
        else:
            messagebox.showerror("Login Failed", "Invalid Staff ID or Name.")

    ttk.Button(login_win, text="Login", command=submit_login, bootstyle="success").pack(pady=20)


staff_login_window()

selected_items = []

# Staff Data Main Screen

def show_main_interface():

    root.deiconify()
    
    kfc_frame = ttk.Frame(root)
    kfc_frame.place(x=865, y=5, width=175, height=80)
    ttk.Label(kfc_frame, text="POS", font=("Segoe UI", 36, "bold")).pack(expand=True)

    staff_frame = ttk.Frame(root)
    staff_frame.place(x=20, y=10, width=200, height=30)
    staff_frame2 = ttk.Frame(root)
    staff_frame2.place(x=20, y=50, width=300, height=30)
    ttk.Label(staff_frame, text=f"Staff ID: {logged_in_staff['staff_id']}", font=("Segoe UI", 12, "bold")).pack(anchor='w')
    ttk.Label(staff_frame2, text=f"Name: {logged_in_staff['name']}", font=("Segoe UI", 12, "bold")).pack(anchor='w')

# Refreshing Menu Screen

active_category = None

# Menu Map

menu_tree = ttk.Treeview(root, columns=("ID", "Name", "Category", "Price"), show="headings", height=20, bootstyle="info")
menu_tree.heading("ID", text="ID")
menu_tree.heading("Name", text="Name")
menu_tree.heading("Category", text="Category")
menu_tree.heading("Price", text="Price")
menu_tree.column("ID", width=100)
menu_tree.column("Name", width=300)
menu_tree.column("Category", width=200)
menu_tree.column("Price", width=160)
menu_tree.place(x=600, y=160)


# Refreshing the Menu Map based on category

def refresh_menu_tree(category=None):
    for row in menu_tree.get_children():
        menu_tree.delete(row)

    if category:
        cursor.execute("SELECT menu_id, item_name, category, price FROM Menu WHERE is_available = TRUE AND category = %s", (category,))
    else:
        cursor.execute("SELECT menu_id, item_name, category, price FROM Menu WHERE is_available = TRUE")

    for item_id, name, category, price in cursor.fetchall():
        menu_tree.insert("", "end", values=(item_id, name, category, f"₹{price}"))


# Creating Category Buttons

def create_category_buttons():
    category_frame = ttk.Frame(root)
    category_frame.place(x=600, y=100)

    cursor.execute("SELECT DISTINCT category FROM Menu WHERE is_available = TRUE")
    categories = [row[0] for row in cursor.fetchall()]

    def handle_category_click(cat):
        global active_category
        active_category = cat
        refresh_menu_tree(cat)

    for idx, cat in enumerate(categories):
        btn = ttk.Button(category_frame, text=cat, width=15, bootstyle="primary-outline",
                         command=lambda c=cat: handle_category_click(c))
        btn.grid(row=0, column=idx, padx=5, pady=5)

    show_all_btn = ttk.Button(category_frame, text="All", width=10, bootstyle="secondary",
                              command=lambda: refresh_menu_tree(None))
    show_all_btn.grid(row=0, column=len(categories), padx=5)

create_category_buttons()
refresh_menu_tree()

#Adding Item to Order

def add_selected_item():
    selected = menu_tree.selection()
    for item in selected:
        values = menu_tree.item(item)["values"]
        item_id = values[0]
        selected_items.append(item_id)
        order_listbox.insert(END, f"{values[1]} ({values[2]}) - {values[3]}")

#Remove Item from Order

def remove_selected_item():
    selected_index = order_listbox.curselection()
    if not selected_index:
        messagebox.showwarning("Selection Error", "Please select an item to remove.")
        return
    index = selected_index[0]
    order_listbox.delete(index)
    del selected_items[index]

#Place Order

current_order_id = None
current_bill_amount = None


def place_order():
    global current_order_id, current_bill_amount
    customer = customer_name.get().strip()
    email = customer_email.get().strip()
    phone = customer_phone.get().strip()
    table = table_number.get().strip()

    if not customer or not email or not table or not selected_items or not phone:
        messagebox.showerror("Input Error", "Fill all fields including phone, email and select items")
        return

    try:

        cursor.execute("INSERT INTO Customer (name, email) VALUES (%s, %s)", (customer, email))
        customer_id = cursor.lastrowid

        cursor.execute("SELECT table_id FROM TableList WHERE table_number = %s", (table,))
        table_result = cursor.fetchone()
        if not table_result:
            messagebox.showerror("Table Error", f"Table {table} does not exist.")
            return
        table_id = table_result[0]

        cursor.execute("""
            INSERT INTO Orders (customer_id, table_id, order_status) 
            VALUES (%s, %s, 'pending')
        """, (customer_id, table_id))
        order_id = cursor.lastrowid
        current_order_id = order_id

        total_amount = 0
        for item_id in selected_items:
            cursor.execute("SELECT price FROM Menu WHERE menu_id = %s", (item_id,))
            price = cursor.fetchone()[0]
            total_amount += price
            cursor.execute("""
                INSERT INTO OrderItem (order_id, menu_id, quantity, item_price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item_id, 1, price))
        current_bill_amount = total_amount


        cursor.execute("UPDATE Orders SET total_amount = %s WHERE order_id = %s", (total_amount, order_id))

        points_earned = int(total_amount)
        cursor.execute("""
            INSERT INTO loyalty_profile (phone, customer_name, total_points, total_visits, total_spent, last_visit)
            VALUES (%s, %s, %s, 1, %s, NOW())
            ON DUPLICATE KEY UPDATE
                total_points = total_points + VALUES(total_points),
                total_visits = total_visits + 1,
                total_spent = total_spent + VALUES(total_spent),
                last_visit = NOW(),
                customer_name = VALUES(customer_name)
        """, (phone, customer, points_earned, total_amount))

        cursor.execute("""
            INSERT INTO loyalty_transactions (phone, order_id, points_earned)
            VALUES (%s, %s, %s)
        """, (phone, order_id, points_earned))

        db.commit()

        messagebox.showinfo("Success", f"Order #{order_id} placed successfully!\nLoyalty: +{points_earned} points")
        selected_items.clear()
        order_listbox.delete(0, END)

    except Exception as e:
        db.rollback()
        messagebox.showerror("Database Error", f"An error occurred:\n{e}")

def get_all_order_ids():
    cursor.execute("SELECT order_id FROM Orders")
    return [row[0] for row in cursor.fetchall()]


# Feedback Window Screen

def open_feedback_window():
    feedback_win = tk.Toplevel(root)
    feedback_win.title("Submit Feedback")
    feedback_win.geometry("580x580")
    feedback_win.config(bg="#2C2F33")
    feedback_win.resizable(False, False)
    feedback_win.grab_set()  

    ttk.Label(feedback_win, text="Customer Feedback", font=("Segoe UI", 14, "bold"), bootstyle="SUCCESS").pack(pady=(20, 10))

    ttk.Label(feedback_win, text="Order ID:", bootstyle="SUCCESS", font=("Segoe UI", 11, "bold")).pack(pady=8)
    order_ids = get_all_order_ids()
    selected_order = ttk.Combobox(feedback_win, values=order_ids, state="readonly", width=30)
    if order_ids:
        selected_order.current(0)
    selected_order.pack()

    ttk.Label(feedback_win, text="Rating (1–5):", bootstyle="SUCCESS", font=("Segoe UI", 12, "bold")).pack(pady=10)

    star_frame = ttk.Frame(feedback_win)
    star_frame.pack(pady=5)

    rating_var = tk.IntVar(value=0)
    star_buttons = []

    def update_stars(selected_rating):
        rating_var.set(selected_rating)
        for i, btn in enumerate(star_buttons, start=1):
            if i <= selected_rating:
                btn.config(text="★", foreground="#FFD700")  
            else:
                btn.config(text="☆", foreground="gray")     

    for i in range(1, 6):
        btn = ttk.Label(star_frame, text="☆", font=("Segoe UI", 20), foreground="gray", cursor="hand2")
        btn.pack(side="left", padx=5)
        btn.bind("<Enter>", lambda e, idx=i: update_stars(idx))
        btn.bind("<Leave>", lambda e: update_stars(rating_var.get()))
        btn.bind("<Button-1>", lambda e, idx=i: update_stars(idx))
        star_buttons.append(btn)

    
    ttk.Label(feedback_win, text="Comments:", bootstyle="SUCCESS", font=("Segoe UI", 11, "bold")).pack(pady=8)
    comments_entry = tk.Text(feedback_win, height=5, width=50, wrap="word", bg="#23272A", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 10), bd=1)
    comments_entry.pack(pady=(0, 10))

    
    def submit_feedback():
        order_id = selected_order.get()
        rating = rating_var.get()
        comments = comments_entry.get("1.0", tk.END).strip()

        if not order_id or not rating:
            messagebox.showerror("Error", "Order ID and Rating are required.")
            return

        cursor.execute("SELECT customer_id FROM Orders WHERE order_id = %s", (order_id,))
        result = cursor.fetchone()
        if not result:
            messagebox.showerror("Error", "Order not found.")
            return
        customer_id = result[0]

        cursor.execute(
            "INSERT INTO Feedback (customer_id, order_id, rating, comments) VALUES (%s, %s, %s, %s)",
            (customer_id, order_id, rating, comments)
        )
        db.commit()
        messagebox.showinfo("Success", "Feedback submitted successfully!")
        feedback_win.destroy()

    btn_frame = ttk.Frame(feedback_win)
    btn_frame.pack(pady=15)

    ttk.Button(btn_frame, text="Submit", bootstyle="success-outline", command=submit_feedback, width=15).grid(row=0, column=0, padx=10)
    ttk.Button(btn_frame, text="Cancel", bootstyle="success-outline", command=feedback_win.destroy, width=15).grid(row=0, column=1, padx=10)


# Payments Window Screen

import qrcode
from PIL import Image, ImageTk

def make_payment():
    payment_win = tk.Toplevel(root)
    payment_win.title("Payment")
    payment_win.geometry("550x600")
    payment_win.configure(bg="#2C2F33")
    payment_win.grab_set()

    ttk.Label(payment_win, text="Order ID:", font=("Segoe UI", 12, "bold"), bootstyle="SUCCESS").grid(row=0, column=0, padx=20, pady=15, sticky="w")

    order_ids = get_all_order_ids()
    selected_order = ttk.Combobox(payment_win, values=order_ids, font=("Segoe UI", 11), bootstyle="SUCCESS", state="readonly")
    selected_order.grid(row=0, column=1, pady=15, sticky="ew")

    ttk.Label(payment_win, text="Payment Method:", font=("Segoe UI", 12, "bold"), bootstyle="SUCCESS").grid(row=1, column=0, padx=20, pady=10, sticky="w")

    payment_method = ttk.Combobox(payment_win, values=["UPI", "Cash", "Card", "Crypto", "Net Banking"], font=("Segoe UI", 11), bootstyle="SUCCESS", state="readonly")
    payment_method.grid(row=1, column=1, pady=10, sticky="ew")

    ttk.Label(payment_win, text="Amount:", font=("Segoe UI", 12, "bold"), bootstyle="SUCCESS").grid(row=2, column=0, padx=20, pady=10, sticky="w")

    amount_entry = ttk.Entry(payment_win, font=("Segoe UI", 11), bootstyle="SUCCESS")
    amount_entry.grid(row=2, column=1, pady=10, sticky="ew")

    payment_win.columnconfigure(1, weight=1)

    details_frame = ttk.Frame(payment_win, padding=10)
    details_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=10)
    details_frame.columnconfigure(0, weight=1)

    qr_label = ttk.Label(details_frame)
    qr_label.grid(row=0, column=0, pady=5)

    details_text = ttk.Label(details_frame, text="", wraplength=450, font=("Segoe UI", 10), bootstyle="INFO")
    details_text.grid(row=1, column=0, pady=5)

    card_entry_label = ttk.Label(details_frame, text="Enter Last 4 Digits of Card:", font=("Segoe UI", 10, "bold"))
    card_entry = ttk.Entry(details_frame, font=("Segoe UI", 10))

    def show_method_details(method):
        
        qr_label.configure(image="")
        qr_label.image = None
        details_text.configure(text="")
        card_entry_label.grid_forget()
        card_entry.grid_forget()

        if method == "UPI":
            upi_string = "upi://pay?pa=UPI_ID&pn=NAME&am=0&cu=INR"  #Insert your own UPI_ID and Name
            qr = qrcode.make(upi_string)
            qr = qr.resize((180, 180))
            qr_img = ImageTk.PhotoImage(qr)
            qr_label.configure(image=qr_img)
            qr_label.image = qr_img
            details_text.configure(text="Scan the UPI QR code above to complete the payment.")

        elif method == "Cash":
            details_text.configure(text="Please collect the exact amount in cash from the customer and provide a receipt.")

        elif method == "Card":
            details_text.configure(text="Swipe or tap the card. Ensure the POS machine confirms success.")
            card_entry_label.grid(row=2, column=0, sticky="w", pady=5)
            card_entry.grid(row=3, column=0, sticky="ew", pady=5)

        elif method == "Crypto":
            details_text.configure(text="Send the payment to wallet address:\n0x1234567890abcdef1234567890abcdef12345678")

        elif method == "Net Banking":
            details_text.configure(text="Redirect the customer to the bank portal: https://bankpayment.example.com\nAsk for screenshot proof after transaction.")

    def handle_method_change(event):
        show_method_details(payment_method.get())

    payment_method.bind("<<ComboboxSelected>>", handle_method_change)

    def update_amount(event):
        order_id = selected_order.get()
        if order_id:
            cursor.execute("SELECT total_amount FROM Orders WHERE order_id = %s", (order_id,))
            result = cursor.fetchone()
            if result:
                amount_entry.delete(0, tk.END)
                amount_entry.insert(0, str(result[0]))

    selected_order.bind("<<ComboboxSelected>>", update_amount)

    def submit_payment():
        order_id = selected_order.get()
        method = payment_method.get()
        amount = amount_entry.get()

        if not order_id or not method or not amount:
            messagebox.showerror("Input Error", "All fields are required.")
            return

        if method == "Card" and not card_entry.get().isdigit():
            messagebox.showerror("Input Error", "Please enter last 4 digits of the card.")
            return

        try:
            cursor.execute(
                "INSERT INTO Payments (order_id, payment_method, amount) VALUES (%s, %s, %s)",
                (order_id, method, amount)
            )
            db.commit()
            messagebox.showinfo("Success", f"Payment of ₹{amount} received for Order #{order_id}")
            payment_win.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    submit_btn = ttk.Button(payment_win, text="Submit Payment", command=submit_payment, bootstyle="SUCCESS")
    submit_btn.grid(row=5, column=0, columnspan=2, pady=25)

#Make a Reservation


def make_reservation_window():
    win = Toplevel(root)
    win.title("Make Reservation")
    win.geometry("400x350")

    ttk.Label(win, text="Customer Name", bootstyle="SUCCESS").pack(pady=5)
    name_entry = ttk.Entry(win, width=30)
    name_entry.pack()

    ttk.Label(win, text="Party Size", bootstyle="SUCCESS").pack(pady=5)
    party_entry = ttk.Entry(win, width=30)
    party_entry.pack()

    ttk.Label(win, text="Table Number", bootstyle="SUCCESS").pack(pady=5)
    table_entry = ttk.Entry(win, width=30)
    table_entry.pack()

    ttk.Label(win, text="Reservation Time (YYYY-MM-DD HH:MM)", bootstyle="SUCCESS").pack(pady=5)
    time_entry = ttk.Entry(win, width=30)
    time_entry.pack()

    def save_reservation():
        name = name_entry.get().strip()
        party_size = party_entry.get().strip()
        table_number = table_entry.get().strip()
        reservation_time = time_entry.get().strip()

        if not name or not party_size or not table_number or not reservation_time:
            messagebox.showerror("Error", "Please fill all fields")
            return

        
        cursor.execute("INSERT INTO Customer (name) VALUES (%s)", (name,))
        customer_id = cursor.lastrowid

       
        cursor.execute("SELECT table_id FROM TableList WHERE table_number = %s", (table_number,))
        result = cursor.fetchone()
        if not result:
            messagebox.showerror("Error", f"Table {table_number} not found")
            return
        table_id = result[0]

        cursor.execute("""
            INSERT INTO Reservation (customer_id, reservation_time, party_size, table_id, status)
            VALUES (%s, %s, %s, %s, 'booked')
        """, (customer_id, reservation_time, party_size, table_id))
        db.commit()

        messagebox.showinfo("Success", "Reservation made successfully!")
        win.destroy()

    ttk.Button(win, text="Submit Reservation", command=save_reservation, bootstyle="SUCCESS").pack(pady=15)

# Viewing Reservations

def view_todays_reservations():
    win = Toplevel(root)
    win.title("Today's Reservations")
    win.geometry("700x400")

    tree = ttk.Treeview(win, columns=("ID", "Name", "Time", "Size", "Table", "Status"), show="headings", bootstyle="SUCCESS")
    for col in tree["columns"]:
        tree.heading(col, text=col)
        tree.column(col, width=100)
    tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

    today = datetime.now().date()
    cursor.execute("""
        SELECT r.reservation_id, c.name, r.reservation_time, r.party_size, t.table_number, r.status
        FROM Reservation r
        JOIN Customer c ON r.customer_id = c.customer_id
        JOIN TableList t ON r.table_id = t.table_id
        WHERE DATE(r.reservation_time) = %s
    """, (today,))
    for row in cursor.fetchall():
        tree.insert("", END, values=row)

# Clock on the main screen

def update_clock():
    now = datetime.now()
    current_time = now.strftime("%I:%M:%S %p")
    current_date = now.strftime("%A, %d %B %Y")
    clock_label.config(text=f"{current_time}\n{current_date}")
    root.after(1000, update_clock)  

# CRM Tools - Email Mailing 

def email_receipt():
    try:
        
        order_id = simpledialog.askinteger("Order ID", "Enter Order ID:")
        recipient_email = simpledialog.askstring("Customer Email", "Enter Customer's Email:")
        if not order_id or not recipient_email:
            return  

        cursor.execute("""
            SELECT o.order_time, o.table_id, o.total_amount, c.name
            FROM orders o
            JOIN customer c ON o.customer_id = c.customer_id
            WHERE o.order_id = %s AND c.email = %s;
        """, (order_id, recipient_email))
        order = cursor.fetchone()

        if not order:
            messagebox.showerror("Error", "No order found with that ID and email.")
            return

        order_time, table_id, total_amount, customer_name = order

       
        cursor.execute("""
            SELECT m.item_name, oi.quantity, oi.item_price
            FROM orderitem oi
            JOIN menu m ON oi.menu_id = m.menu_id
            WHERE oi.order_id = %s;
        """, (order_id,))
        items = cursor.fetchall()

        receipt_lines = []
        receipt_lines.append("Thank you for dining with us!")
        receipt_lines.append("----------------------------------------")
        receipt_lines.append(f"Customer Name: {customer_name}")
        receipt_lines.append(f"Table Number: {table_id}")
        receipt_lines.append(f"Order Date & Time: {order_time}")
        receipt_lines.append("----------------------------------------")
        receipt_lines.append("Order Details:")

        for name, qty, price in items:
            subtotal = qty * price
            receipt_lines.append(f"- {name} x{qty}: ₹{subtotal:.2f}")

        receipt_lines.append("----------------------------------------")
        receipt_lines.append(f"Total: ₹{total_amount:.2f}")
        receipt_lines.append("----------------------------------------")
        receipt_lines.append("We hope you enjoyed your meal.\nPlease visit again!\n\nWarm regards,\n KFC")


        receipt_text = "\n".join(receipt_lines)

        msg = EmailMessage()
        msg['Subject'] = f"Your Receipt for Order #{order_id}"
        msg['From'] = "Name@gmail.com"
        msg['To'] = recipient_email
        msg.set_content(receipt_text)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("NAME@gmail.com", "CODE")   # Insert your own Name as well as the verification code to your mail
            smtp.send_message(msg)

        messagebox.showinfo("Email Sent", f"Receipt sent to {recipient_email}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to send receipt:\n{e}")
        
#CRM Tools - WhatsApp Message

def send_custom_whatsapp_message():
    try:
        
        phone_number = simpledialog.askstring("Send Promotion", "Enter customer's phone number (without +91):")
        if not phone_number:
            return

        
        message = simpledialog.askstring("Message", "Enter the promotional message to send:")
        if not message:
            return

        now = datetime.now()
        hours = now.hour
        minutes = now.minute + 1 

        kit.sendwhatmsg(f"+91{phone_number}", message, hours, minutes)

        messagebox.showinfo("Success", f"Message scheduled to {phone_number} at {hours}:{minutes}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send message:\n{e}")

#Add Menu Item

def open_add_menu_window():
    add_window = Toplevel(root)
    add_window.title("Add Menu Item")
    add_window.geometry("400x400")

    ttk.Label(add_window, text="Item Name:").pack(pady=5)
    name_entry = ttk.Entry(add_window)
    name_entry.pack(pady=5)

    ttk.Label(add_window, text="Description:").pack(pady=5)
    desc_entry = ttk.Entry(add_window)
    desc_entry.pack(pady=5)

    ttk.Label(add_window, text="Price:").pack(pady=5)
    price_entry = ttk.Entry(add_window)
    price_entry.pack(pady=5)

    ttk.Label(add_window, text="Category:").pack(pady=5)
    category_entry = ttk.Entry(add_window)
    category_entry.pack(pady=5)

    is_available_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(add_window, text="Available", variable=is_available_var).pack(pady=5)

    def add_menu_item():
        name = name_entry.get().strip()
        desc = desc_entry.get().strip()
        price = price_entry.get().strip()
        category = category_entry.get().strip()
        is_available = is_available_var.get()

        if not name or not price:
            messagebox.showerror("Input Error", "Name and Price are required.")
            return

        try:
            cursor.execute("""
                INSERT INTO Menu (item_name, description, price, category, is_available)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, desc, float(price), category, is_available))
            db.commit()
            messagebox.showinfo("Success", f"Menu item '{name}' added successfully.")
            add_window.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    ttk.Button(add_window, text="Add Item", command=add_menu_item).pack(pady=10)

# Checking and Restocking Ingredients

def get_low_stock_items(cursor, threshold=10):
    cursor.execute("""
        SELECT i.ingredient_id, i.name, inv.quantity_in_stock 
        FROM Inventory inv 
        JOIN Ingredient i ON inv.ingredient_id = i.ingredient_id
        WHERE inv.quantity_in_stock < %s
    """, (threshold,))
    return cursor.fetchall()

from datetime import datetime, date, timedelta

def send_restock_whatsapp_and_log(phone_number, cursor, conn, threshold=10):
    low_items = get_low_stock_items(cursor, threshold)

    if not low_items:
        messagebox.showinfo("Inventory", "No ingredients need restocking.")
        return

    message = "🛒 Restock Request:\n"
    for item in low_items:
        ingredient_id, name, current_qty = item
        qty_to_order = 100 - current_qty  
        message += f"{name} - Order {qty_to_order} units\n"

        
        cursor.execute("""
            INSERT INTO PurchaseOrder (ingredient_id, quantity_ordered, order_date, expected_delivery)
            VALUES (%s, %s, %s, %s)
        """, (ingredient_id, qty_to_order, date.today(), date.today() + timedelta(days=3)))

    conn.commit()

    now = datetime.now()
    kit.sendwhatmsg(f"+91{phone_number}", message, now.hour, now.minute + 2)

# Mark Items as Stored

def mark_restocked_items(cursor, conn):
    today = date.today()

    cursor.execute("""
        SELECT po.ingredient_id, po.quantity_ordered
        FROM PurchaseOrder po
        WHERE po.expected_delivery = %s
    """, (today,))
    delivered = cursor.fetchall()

    for ingredient_id, qty in delivered:

        cursor.execute("""
            UPDATE Inventory 
            SET quantity_in_stock = quantity_in_stock + %s, last_updated = CURRENT_TIMESTAMP
            WHERE ingredient_id = %s
        """, (qty, ingredient_id))

    conn.commit()
    messagebox.showinfo("Inventory Updated", f"Inventory updated with {len(delivered)} delivered items.")

# Create Delivery Order

def open_delivery_fee_window():
    def get_coordinates(location_name):
        location = geolocator.geocode(location_name)
        if location:
            return (location.latitude, location.longitude)
        else:
            raise ValueError(f"Could not find location: {location_name}")

    def calculate_delivery():
        try:
            customer_location = address_entry.get()
            if not customer_location:
                messagebox.showerror("Error", "Please enter a delivery location.")
                return

            rest_coords = get_coordinates(RESTAURANT_LOCATION)
            cust_coords = get_coordinates(customer_location)

            distance_km = geodesic(rest_coords, cust_coords).km
            distance_km = round(distance_km, 2)
            fee = int(distance_km * FEE_PER_KM)

            result_var.set(f"Distance: {distance_km} km\nDelivery Fee: ₹{fee}")
            calculated_fee.set(fee)
        except Exception as e:
            messagebox.showerror("Error", f"Could not calculate delivery.\n{e}")

    def add_fee_to_order():
        try:
            order_id = selected_order.get()
            fee = calculated_fee.get()

            if not order_id:
                messagebox.showerror("Error", "Please select an Order ID.")
                return
            if fee == 0:
                messagebox.showerror("Error", "Calculate the delivery fee first.")
                return

            cursor.execute("UPDATE Orders SET total_amount = total_amount + %s WHERE order_id = %s", (fee, order_id))
            db.commit()
            messagebox.showinfo("Success", f"₹{fee} delivery fee added to Order #{order_id}")
            popup.destroy()
        except Exception as e:
            messagebox.showerror("Database Error", str(e))

    RESTAURANT_LOCATION = "Ayyanthole, Thrissur, Kerala, India"
    FEE_PER_KM = 10
    geolocator = Nominatim(user_agent="restaurant-pos")

    popup = tk.Toplevel()
    popup.title("Calculate Delivery Fee")
    popup.geometry("500x400")
    popup.resizable(False, False)

    ttk.Label(popup, text="Enter Delivery Location:").pack(pady=10)
    address_entry = ttk.Entry(popup, width=40)
    address_entry.pack(pady=5)

    ttk.Label(popup, text="Select Order ID:").pack(pady=10)
    order_ids = get_all_order_ids() 
    selected_order = ttk.Combobox(popup, values=order_ids, state="readonly")
    selected_order.pack(pady=5)

    ttk.Button(popup, text="Calculate", bootstyle="success", command=calculate_delivery).pack(pady=10)

    result_var = tk.StringVar()
    ttk.Label(popup, textvariable=result_var, font=("Segoe UI", 12, "bold")).pack(pady=10)

    ttk.Button(popup, text="Add Fee to Order", bootstyle="warning", command=add_fee_to_order).pack(pady=15)

    calculated_fee = tk.IntVar(value=0)

#Create Table Map


table_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
STATUS_COLOR = {
    "Available": "success",   
    "Reserved": "warning",   
    "Booked": "danger"       
}


def get_table_status(table_id):
    cursor.execute("""
        SELECT status FROM Reservation
        WHERE table_id = %s AND DATE(reservation_time) = CURDATE()
        ORDER BY reservation_time DESC LIMIT 1
    """, (table_id,))
    result = cursor.fetchone()
    return result[0] if result else "Available"


def handle_table_click(table_id):
    cursor.execute("""
        SELECT * FROM Reservation
        WHERE table_id = %s AND DATE(reservation_time) = CURDATE()
        ORDER BY reservation_time DESC LIMIT 1
    """, (table_id,))
    result = cursor.fetchone()
    if result:
        res_id, tid, res_time, party, cust_id, status = result
        messagebox.showinfo(
            title="Table Info",
            message=f"Table {table_id} is {status}\n"
                    f"Reservation ID: {res_id}\n"
                    f"Time: {res_time.strftime('%I:%M %p')}\n"
                    f"Party Size: {party}\n"
                    f"Customer ID: {cust_id}"
        )
    else:
        messagebox.showinfo("Table Info", f"Table {table_id} is Available.")


table_window = None
table_frame = None


def open_table_map_window():
    global table_window, table_frame

   
    if table_window and table_window.winfo_exists():
        table_window.lift()
        return

    table_window = tk.Toplevel(root)
    table_window.title("Live Table Map")
    table_window.geometry("700x600")
    table_window.configure(bg="#1e1e1e")

    table_frame = ttk.LabelFrame(table_window, text="Table Map", bootstyle="info")
    table_frame.pack(padx=20, pady=20, fill='both', expand=True)

    
    refresh_table_map()



def refresh_table_map():
    global table_frame
    for widget in table_frame.winfo_children():
        widget.destroy()

    for idx, table_id in enumerate(table_ids):
        status = get_table_status(table_id)
        style = STATUS_COLOR.get(status, "secondary")

        btn = ttk.Button(
            table_frame,
            text=f"Table {table_id}",
            bootstyle=style,
            width=15,
            command=lambda tid=table_id: handle_table_click(tid)
        )
        btn.grid(row=idx // 4, column=idx % 4, padx=10, pady=10)

    if table_window and table_window.winfo_exists():
        table_window.after(10000, refresh_table_map)


ttk.Button(
    root,
    text="VIEW TABLE MAP",
    bootstyle="SUCCESS",
    command=open_table_map_window
).place(x=30, y=450)


#View a heatmap of Sales

def show_sales_heatmap():
    cursor.execute("""
        SELECT order_time, total_amount
        FROM Orders
        WHERE order_time IS NOT NULL AND total_amount IS NOT NULL
    """)
    data = cursor.fetchall()

    df = pd.DataFrame(data, columns=["order_time", "total_amount"])

    df["order_time"] = pd.to_datetime(df["order_time"], errors='coerce')
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors='coerce')


    df.dropna(subset=["order_time", "total_amount"], inplace=True)

    df["hour"] = df["order_time"].dt.hour
    df["weekday"] = df["order_time"].dt.day_name()

    pivot_table = df.pivot_table(
        index="weekday",
        columns="hour",
        values="total_amount",
        aggfunc="sum",
        fill_value=0
    )

 
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot_table = pivot_table.reindex(weekday_order)

 
    heatmap_window = Toplevel(root)
    heatmap_window.title("Sales Heatmap")
    heatmap_window.geometry("900x600")

  
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(pivot_table, ax=ax, cmap="YlOrRd", annot=True, fmt=".0f", linewidths=0.5)
    ax.set_title("Hourly Sales by Weekday", fontsize=14)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Day of Week")

  
    canvas = FigureCanvasTkAgg(fig, master=heatmap_window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

sales_frame = ttk.LabelFrame(root, text="Dashboard", padding=10, bootstyle="info")
sales_frame.place(x=30, y=325, width=320, height=250)

# Update Live Sale Dashboard


def update_dashboard():
    for widget in sales_frame.winfo_children():
        widget.destroy()

    cursor.execute("SELECT SUM(total_amount) FROM Orders WHERE DATE(order_time) = CURDATE()")
    total_sales = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT COUNT(DISTINCT table_id)
        FROM Orders
        WHERE DATE(order_time) = CURDATE() 
    """)
    active_tables = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT AVG(total_amount)
        FROM Orders
        WHERE DATE(order_time) = CURDATE()
    """)
    avg_order_value = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT COUNT(*)
        FROM Reservation
        WHERE reservation_time >= NOW() AND status = 'Pending'
    """)
    pending_reservations = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT M.item_name, COUNT(*) AS sold_count
        FROM OrderItem OI
        JOIN Menu M ON OI.menu_id = M.menu_id
        JOIN Orders O ON O.order_id = OI.order_id
        WHERE DATE(O.order_time) = CURDATE()
        GROUP BY OI.menu_id
        ORDER BY sold_count DESC
        LIMIT 3
    """)
    top_dishes = cursor.fetchall()

    ttk.Label(sales_frame, text="📊 Live Sales Dashboard", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=5)
    ttk.Label(sales_frame, text=f"🧾 Total Sales Today: ₹{total_sales:.2f}", font=("Segoe UI", 12)).pack(anchor="w", padx=10)
    ttk.Label(sales_frame, text=f"🍽️ Active Tables: {active_tables}", font=("Segoe UI", 12)).pack(anchor="w", padx=10)
    ttk.Label(sales_frame, text=f"💸 Avg. Order Value: ₹{avg_order_value:.2f}", font=("Segoe UI", 12)).pack(anchor="w", padx=10)
    ttk.Label(sales_frame, text=f"📅 Pending Reservations: {pending_reservations}", font=("Segoe UI", 12)).pack(anchor="w", padx=10)

    ttk.Label(sales_frame, text="🏆 Top 3 Best-Selling Dishes:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
    for name, count in top_dishes:
        ttk.Label(sales_frame, text=f"• {name} - {count} sold", font=("Segoe UI", 10)).pack(anchor="w", padx=20)

    now = datetime.now().strftime("%I:%M:%S %p")
    ttk.Label(sales_frame, text=f"🔁 Last Updated: {now}", font=("Segoe UI", 9, "italic")).pack(anchor="e", padx=10, pady=(10, 0))


def auto_refresh_dashboard():
    update_dashboard()
    root.after(60000, auto_refresh_dashboard)

auto_refresh_dashboard()

# View Bar graph of Underperforming Dishes + Suggest Improvements

def show_underperforming_dishes():
    window = tk.Toplevel(root)
    window.title("📉 Underperforming Menu Items")
    window.geometry("850x600")
    window.configure(bg="#1f1f1f")

    ttk.Label(window, text="Low-Selling Dishes (Last 30 Days)", font=("Segoe UI", 14, "bold"), bootstyle="info").pack(pady=10)

    cursor.execute("""
        SELECT 
            M.item_name,
            COALESCE(SUM(OI.quantity), 0) AS total_sold
        FROM 
            Menu M
        LEFT JOIN OrderItem OI ON M.menu_id = OI.menu_id
        LEFT JOIN Orders O ON O.order_id = OI.order_id AND O.order_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY M.menu_id, M.item_name
        HAVING total_sold <= 5
        ORDER BY total_sold ASC
    """)
    data = cursor.fetchall()

    if not data:
        ttk.Label(window, text="🎉 All dishes are performing well!", font=("Segoe UI", 11)).pack(pady=20)
        return

    item_names = [item for item, sold in data]
    sold_counts = [sold for item, sold in data]

    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=100)
    bars = ax.barh(item_names, sold_counts, color="#e76f51", edgecolor="black")

    ax.set_xlabel("Quantity Sold", fontsize=10, labelpad=10)
    ax.set_title("Low-Performing Dishes (Last 30 Days)", fontsize=14, fontweight='bold', color="#333")
    ax.invert_yaxis()
    ax.set_facecolor("#fdf0e0")
    fig.patch.set_facecolor('#fdf0e0')
    ax.grid(axis="x", linestyle="--", alpha=0.5)

    for bar in bars:
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2, 
                f"{int(bar.get_width())}", va='center', fontsize=9, color="black")

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(pady=(5, 15))

    rec_frame = ttk.LabelFrame(window, text="📌 Actionable Recommendations", padding=10, bootstyle="warning")
    rec_frame.pack(fill="both", expand=True, padx=20, pady=10)

    suggestions = [
        "Run a limited-time discount offer",
        "Promote this dish on the digital menu",
        "Pair it with a popular combo",
        "Add a visual photo on the ordering screen",
        "Consider replacing or tweaking the recipe",
        "Offer a sample for customer feedback",
        "Make it today’s special to increase visibility"
    ]

    for dish, count in data:
        rec = random.choice(suggestions)
        msg = f"• '{dish}' sold only {count} times → {rec}."
        ttk.Label(rec_frame, text=msg, wraplength=700, font=("Segoe UI", 10)).pack(anchor="w", pady=2)

    ttk.Button(window, text="Close", command=window.destroy, bootstyle="danger").pack(pady=10)

# Loyalty and Rewards Programs

phone_entry = ttk.Entry(root, width=25)
phone_entry.pack(pady=5)
phone_entry.insert(0, "Check Loyalty Points")
phone_entry.place(x=50,y=675)

def show_loyalty_status(phone, db):
    cursor.execute("""
        SELECT customer_name, total_points, total_visits, total_spent, last_visit
        FROM loyalty_profile
        WHERE phone = %s
    """, (phone,))
    result = cursor.fetchone()

    if result:
        name, points, visits, spent, last_visit = result
        eligible = "Yes ✅" if points >= 200 else "No ❌"
        msg = f"""
Customer: {name}
Phone: {phone}
Points: {points}
Visits: {visits}
Spent: ₹{spent}
Last Visit: {last_visit.strftime('%Y-%m-%d')}
Eligible for Discount: {eligible}
"""
    else:
        msg = "No loyalty record found for this phone number."

    messagebox.showinfo("Loyalty Status", msg)


def apply_loyalty_discount(phone, order_id, bill_amount, db):
    cursor.execute("SELECT total_points FROM loyalty_profile WHERE phone = %s", (phone,))
    result = cursor.fetchone()

    if not result:
        return bill_amount, 0

    current_points = result[0]
    if current_points < 200:
        return bill_amount, 0

    points_to_redeem = (current_points // 100) * 100
    discount = points_to_redeem // 10
    final_amount = bill_amount - discount

    cursor.execute("""
        UPDATE loyalty_profile
        SET total_points = total_points - %s
        WHERE phone = %s
    """, (points_to_redeem, phone))

    cursor.execute("""
        INSERT INTO loyalty_transactions (phone, order_id, points_redeemed)
        VALUES (%s, %s, %s)
    """, (phone, order_id, points_to_redeem))

    db.commit()
    return final_amount, discount


def update_loyalty_points(phone, name, order_id, bill_amount, db):
    points_earned = int(bill_amount)

    cursor.execute("""
        INSERT INTO loyalty_profile (phone, customer_name, total_points, total_visits, total_spent, last_visit)
        VALUES (%s, %s, %s, 1, %s, NOW())
        ON DUPLICATE KEY UPDATE
            total_points = total_points + VALUES(total_points),
            total_visits = total_visits + 1,
            total_spent = total_spent + VALUES(total_spent),
            last_visit = NOW(),
            customer_name = VALUES(customer_name)
    """, (phone, name, points_earned, bill_amount))

    cursor.execute("""
        INSERT INTO loyalty_transactions (phone, order_id, points_earned)
        VALUES (%s, %s, %s)
    """, (phone, order_id, points_earned))

    db.commit()
    

def apply_discount_and_checkout(phone, current_order_id, current_bill_amount, db):
    if current_bill_amount is None:
        messagebox.showerror("Error", "Bill amount not available. Place the order first.")
        return

    final, discount = apply_loyalty_discount(phone, current_order_id, current_bill_amount, db)
    if discount > 0:
        messagebox.showinfo("Discount Applied", f"₹{discount} discount applied!\nFinal Amount: ₹{final}")
    else:
        messagebox.showinfo("No Discount", "Not enough points to redeem.")
    return final


style = Style("darkly")  

# Buttons And Widgets

def CreateToolTip(widget, text):
    ToolTip(widget, text=text)


buttons = [
    {"text": "Give Feedback", "tooltip": "Collect customer feedback", "command": open_feedback_window, "bootstyle": "info"},
    {"text": "Make Payment", "tooltip": "Initiate payment", "command": make_payment, "bootstyle": "warning"},
    {"text": "Make Reservation", "tooltip": "Book a table", "command": make_reservation_window, "bootstyle": "info"},
    {"text": "Today's Reservations", "tooltip": "See today’s bookings", "command": view_todays_reservations, "bootstyle": "warning"},
    {"text": "Email Receipt", "tooltip": "Send bill via email", "command": email_receipt, "bootstyle": "info"},
    {"text": "Send Promo (WhatsApp)", "tooltip": "Send promo to customers", "command": send_custom_whatsapp_message, "bootstyle": "danger"},
    {"text": "Add Menu Item", "tooltip": "Insert a new menu item", "command": open_add_menu_window, "bootstyle": "light"},
    {"text": "Check & Restock", "tooltip": "Request ingredient restock", "command": lambda: send_restock_whatsapp_and_log("9876543210", cursor, db), "bootstyle": "danger"},
    {"text": "Mark Delivered", "tooltip": "Confirm inventory received", "command": lambda: mark_restocked_items(cursor, db), "bootstyle": "light"},
    {"text": "Create Delivery Order", "tooltip": "Order delivery and add fee", "command": open_delivery_fee_window, "bootstyle": "danger"},
    {"text": "Sales Analysis", "tooltip": "View peak sales timings", "command": show_sales_heatmap, "bootstyle": "Success"},
    {"text": "Analyze Menu Performance", "tooltip": "See underperforming dishes", "command": show_underperforming_dishes, "bootstyle": "danger"},
    {"text": "Check Loyalty Points", "tooltip": "View Loyalty Points",  "command": lambda: show_loyalty_status(phone_entry.get(), db), "bootstyle": "Success"},
    {"text": "Apply Loyalty Discount", "tooltip": "Apply the discount", "command": lambda: apply_discount_and_checkout(phone_entry.get(), current_order_id, current_bill_amount, db), "bootstyle": "danger"},
    {"text": "Table View", "tooltip": "View available tables", "command": open_table_map_window, "bootstyle": "Success"}
]


btn_frame = tk.Frame(root, bg="#1c1c1c")
btn_frame.pack(side="bottom", pady=30)


cols = 5
for i, btn in enumerate(buttons):
    b = ttk.Button(
        btn_frame,
        text=btn["text"],
        command=btn["command"],
        bootstyle=f"{btn['bootstyle']} outline",  
        width=40
    )
    b.grid(row=i // cols, column=i % cols, padx=12, pady=12)
    CreateToolTip(b, btn["tooltip"])

btn_add = ttk.Button(
    root,
    text="Add to Order",
    command=add_selected_item,
    bootstyle="primary outline",
    width=20
)
btn_add.place(x=850, y=625) 
CreateToolTip(btn_add, "Add selected item")


btn_remove = ttk.Button(
    root,
    text="Remove from Order",
    command=remove_selected_item,
    bootstyle="danger outline",
    width=18
)
btn_remove.place(x=1500, y=675)

CreateToolTip(btn_remove, "Delete item from current order")


btn_place = ttk.Button(
    root,
    text="Place Order",
    command=place_order,
    bootstyle="success outline",
    width=18
)
btn_place.place(x=1700, y=675)  
CreateToolTip(btn_place, "Finalize and place order")

clock_label = ttk.Label(root, font=("Segoe UI", 12, "bold"))
clock_label.place(x=1600, y=20) 
update_clock()

ttk.Label(root, text="Order Preview:", font=("Segoe UI", 14)).place(x=1580, y=105)
order_listbox = Listbox(root, width=45, height=24)
order_listbox.place(x=1500, y=140)

font_label = ("Segoe UI", 12)

ttk.Label(root, text="Customer Name:", font=font_label).place(x=30, y=100)
customer_name = ttk.Entry(root, width=30)
customer_name.place(x=185, y=100)

ttk.Label(root, text="Customer Mail:", font=font_label).place(x=30, y=150)
customer_email = ttk.Entry(root, width=30)
customer_email.place(x=185, y=150)

ttk.Label(root, text="Table Number:", font=font_label).place(x=30, y=200)
table_number = ttk.Entry(root, width=30)
table_number.place(x=185, y=200)

ttk.Label(root, text="Customer Phone:", font=font_label).place(x=30, y=250)
customer_phone = ttk.Entry(root, width=30)
customer_phone.place(x=185, y=250)


# Run the Main Window

root.mainloop()

