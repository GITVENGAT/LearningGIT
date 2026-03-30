from flask import Flask, render_template, request, jsonify, session, redirect, send_file
import sqlite3
import requests
import uuid
import random
import os
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    # USERS
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )""")

    # POLL VOTES
    c.execute("""CREATE TABLE IF NOT EXISTS votes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver TEXT
    )""")

    # TICKET BOOKINGS
    c.execute("""CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        event TEXT
    )""")

    # 🛍️ MERCHANDISE PRODUCTS
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        team TEXT,
        name TEXT,
        price INTEGER,
        image TEXT
    )""")

    # 🛒 USER CART
    c.execute("""CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        product_id INTEGER,
        quantity INTEGER DEFAULT 1
    )""")

    # 📦 ORDERS
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        tracking_id TEXT,
        pincode TEXT,
        address TEXT,
        phone TEXT,
        alt_phone TEXT,
        email TEXT,
        status TEXT DEFAULT 'Order Confirmed'
    )""")

    conn.commit()
    conn.close()


# ✅ PRODUCT SEEDER
def seed_products():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM products")
    count = c.fetchone()[0]

    # insert only first time
    if count == 0:
        products = [
            ("Caps", "Red Bull", "Red Bull Racing Cap", 1499,
             "https://images.unsplash.com/photo-1521369909029-2afed882baee"),

            ("Flags", "Ferrari", "Ferrari Team Flag", 899,
             "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"),

            ("T-Shirts", "Mercedes", "Mercedes AMG Jersey", 2499,
             "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab"),

            ("Keychains", "McLaren", "McLaren Car Keychain", 499,
             "https://images.unsplash.com/photo-1518546305927-5a555bb7020d"),

            ("Headbands", "Aston Martin", "Aston Martin Race Headband", 699,
             "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c"),

            ("Driver Frames", "Ferrari", "Charles Leclerc Signed Frame", 4999,
             "https://images.unsplash.com/photo-1516035069371-29a1b244cc32")
        ]

        c.executemany("""
            INSERT INTO products(category, team, name, price, image)
            VALUES (?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()


# ✅ RUN DB SETUP
init_db()
seed_products()

# ---------------- PAGE ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/events")
def events():
    return render_template("events.html")

@app.route("/experience")
def experience():
    return render_template("experience.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login-page")
    return render_template("dashboard.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/signup-page")
def signup_page():
    return render_template("signup.html")

@app.route("/merchandise")
def merchandise():
    categories = [
        "Caps",
        "Flags",
        "T-Shirts",
        "Keychains",
        "Headbands",
        "Driver Frames"
    ]
    return render_template("merchandise.html", categories=categories)


@app.route("/category/<name>")
def category_page(name):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT * FROM products WHERE category=?", (name,))
    items = c.fetchall()

    conn.close()

    return render_template("category.html", items=items, category=name)

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("""
        INSERT INTO cart (username, product_id, quantity)
        VALUES (?, ?, 1)
    """, (session["user"], data["product_id"]))

    conn.commit()
    conn.close()

    return jsonify({"msg": "Added to cart"})


@app.route("/cart")
def view_cart():
    if "user" not in session:
        return redirect("/login-page")

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("""
        SELECT cart.id, products.name, products.price, products.image
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.username=?
    """, (session["user"],))

    items = c.fetchall()
    conn.close()

    return render_template("cart.html", items=items)

@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login-page")

    return render_template("checkout.html")


@app.route("/place-order", methods=["POST"])
def place_order():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json

    # 🇮🇳 India-only pincode validation
    pincode = str(data["pincode"])
    if len(pincode) != 6 or not pincode.isdigit():
        return jsonify({"msg": "Delivery available only inside India"})

    tracking_id = "F1-" + str(uuid.uuid4())[:8].upper()

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("""
        INSERT INTO orders(
            username, tracking_id, pincode,
            address, phone, alt_phone, email
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user"],
        tracking_id,
        pincode,
        data["address"],
        data["phone"],
        data["alt_phone"],
        data["email"]
    ))

    # 🧹 clear cart after order
    c.execute("DELETE FROM cart WHERE username=?", (session["user"],))

    conn.commit()
    conn.close()

    return jsonify({
        "msg": "Order placed successfully",
        "tracking_id": tracking_id,
        "status": "Order Confirmed → Packed → Shipped → Out for Delivery"
    })

@app.route("/my-orders")
def my_orders():
    if "user" not in session:
        return redirect("/login-page")

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("""
        SELECT tracking_id, address, phone, email, status
        FROM orders
        WHERE username=?
        ORDER BY id DESC
    """, (session["user"],))

    orders = c.fetchall()
    conn.close()

    return render_template("my_orders.html", orders=orders)

@app.route("/admin")
def admin():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    # total users
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    # total tickets
    c.execute("SELECT COUNT(*) FROM tickets")
    total_tickets = c.fetchone()[0]

    # total orders
    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    # total revenue
    c.execute("""
        SELECT COALESCE(SUM(products.price),0)
        FROM cart
        JOIN products ON cart.product_id = products.id
    """)
    revenue = c.fetchone()[0]

    # latest orders
    c.execute("""
        SELECT username, tracking_id, status
        FROM orders
        ORDER BY id DESC
    """)
    recent_orders = c.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_tickets=total_tickets,
        total_orders=total_orders,
        revenue=revenue,
        recent_orders=recent_orders
    )

@app.route("/payment")
def payment():
    if "user" not in session:
        return redirect("/login-page")

    return render_template("payment.html")


@app.route("/process-payment", methods=["POST"])
def process_payment():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json
    method = data["method"]

    transaction_id = "TXN" + str(random.randint(100000, 999999))

    return jsonify({
        "msg": "Payment successful",
        "transaction_id": transaction_id,
        "method": method
    })

@app.route("/invoice/<tracking_id>/<transaction_id>")
def invoice(tracking_id, transaction_id):
    if "user" not in session:
        return redirect("/login-page")

    filename = f"invoice_{tracking_id}.pdf"
    filepath = os.path.join("static", filename)

    c = canvas.Canvas(filepath)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(180, 800, "F1 Marketplace Invoice")

    c.setFont("Helvetica", 12)
    c.drawString(50, 760, f"Customer: {session['user']}")
    c.drawString(50, 740, f"Tracking ID: {tracking_id}")
    c.drawString(50, 720, f"Transaction ID: {transaction_id}")
    c.drawString(50, 700, "Status: Payment Successful")
    c.drawString(50, 680, "Delivery: India Only")
    c.drawString(50, 660, "Thank you for shopping with F1 Marketplace")

    c.save()

    return send_file(filepath, as_attachment=True)

# ---------------- AUTH ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("INSERT INTO users (username,password) VALUES (?,?)",
              (data["username"], data["password"]))

    conn.commit()
    conn.close()

    return jsonify({"msg": "Signup success"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (data["username"], data["password"]))

    user = c.fetchone()
    conn.close()

    if user:
        session["user"] = data["username"]
        return jsonify({"msg": "Login success"})
    
    return jsonify({"msg": "Invalid credentials"})

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ---------------- POLL ----------------
@app.route("/vote", methods=["POST"])
def vote():
    data = request.json
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("INSERT INTO votes (driver) VALUES (?)", (data["driver"],))

    conn.commit()
    conn.close()

    return jsonify({"msg": "Vote saved"})

@app.route("/poll-results")
def poll_results():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT driver, COUNT(*) FROM votes GROUP BY driver")
    results = c.fetchall()

    conn.close()
    return jsonify(results)

# ---------------- BOOK TICKET ----------------
@app.route("/book", methods=["POST"])
def book():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("INSERT INTO tickets (username,event) VALUES (?,?)",
              (session["user"], data["event"]))

    conn.commit()
    conn.close()

    return jsonify({"msg": "Ticket booked"})


@app.route("/my-tickets")
def my_tickets():
    if "user" not in session:
        return redirect("/login-page")

    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("SELECT event FROM tickets WHERE username=?", (session["user"],))
    data = c.fetchall()

    conn.close()

    return render_template("my_tickets.html", tickets=data)



# ---------------- F1 DATA API ----------------
@app.route("/teams")
def teams():
    data = requests.get("https://ergast.com/api/f1/current/constructors.json").json()
    return jsonify([t["name"] for t in data['MRData']['ConstructorTable']['Constructors']])

@app.route("/drivers")
def drivers():
    data = requests.get("https://ergast.com/api/f1/current/drivers.json").json()
    return jsonify([
        d["givenName"] + " " + d["familyName"]
        for d in data['MRData']['DriverTable']['Drivers']
    ])

@app.route("/results")
def results():
    data = requests.get("https://ergast.com/api/f1/current/last/results.json").json()
    return jsonify([
        r["Driver"]["familyName"]
        for r in data['MRData']['RaceTable']['Races'][0]['Results']
    ])

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)