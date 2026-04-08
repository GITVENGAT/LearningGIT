from flask import Flask, render_template, request, jsonify, session, redirect, send_file
import sqlite3
import requests
import uuid
import random
import os
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "f1-super-secret-key")

# ---------------- RACE SCHEDULE ----------------
race_schedule = [
    {"track": "Japanese GP", "place": "Suzuka", "date": "2026-04-05", "time": "13:30 IST"},
    {"track": "Chinese GP", "place": "Shanghai", "date": "2026-04-12", "time": "12:30 IST"},
    {"track": "Miami GP", "place": "USA", "date": "2026-04-19", "time": "01:30 IST"},
    {"track": "Emilia Romagna GP", "place": "Imola", "date": "2026-05-03", "time": "18:30 IST"},
    {"track": "Monaco GP", "place": "Monte Carlo", "date": "2026-05-24", "time": "18:30 IST"},
    {"track": "British GP", "place": "Silverstone", "date": "2026-07-05", "time": "19:30 IST"}
]


# ---------------- DATABASE ----------------
def init_db():
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS votes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            driver TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            event TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            team TEXT,
            name TEXT,
            price INTEGER,
            image TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS cart(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            UNIQUE(username, product_id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            tracking_id TEXT,
            pincode TEXT,
            address TEXT,
            phone TEXT,
            alt_phone TEXT,
            email TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'Order Confirmed'
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS tracking_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT,
            stage TEXT,
            timestamp TEXT
        )""")


# ---------------- PRODUCT SEEDER ----------------
def seed_products():
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products")
        count = c.fetchone()[0]

        if count == 0:
            products = [
                ("Caps", "Red Bull", "Red Bull Racing Cap", 1499, "https://images.unsplash.com/photo-1521369909029-2afed882baee"),
                ("Flags", "Ferrari", "Ferrari Team Flag", 899, "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee"),
                ("T-Shirts", "Mercedes", "Mercedes AMG Jersey", 2499, "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab"),
                ("Keychains", "McLaren", "McLaren Car Keychain", 499, "https://images.unsplash.com/photo-1518546305927-5a555bb7020d"),
                ("Headbands", "Aston Martin", "Aston Martin Race Headband", 699, "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c"),
                ("Driver Frames", "Ferrari", "Charles Leclerc Signed Frame", 4999, "https://images.unsplash.com/photo-1516035069371-29a1b244cc32")
            ]

            c.executemany(
                "INSERT INTO products(category, team, name, price, image) VALUES (?, ?, ?, ?, ?)",
                products
            )


init_db()
seed_products()


# ---------------- PAGE ROUTES ----------------
@app.route("/")
def home():
    timeline = [
        ("1950", "The first Formula 1 World Championship begins at Silverstone."),
        ("1988", "McLaren dominates with Ayrton Senna and Alain Prost."),
        ("2004", "Michael Schumacher wins his 7th world title."),
        ("2021", "Max Verstappen wins in dramatic Abu Dhabi finale."),
        ("2024", "The new hybrid era reaches peak competitiveness.")
    ]

    latest_news = [
        "🔴 Ferrari unveils latest race package upgrade",
        "🔵 Red Bull confirms aero changes for next GP",
        "🟠 McLaren dominates practice sessions",
        "⚫ Mercedes focusing on tyre strategy",
        "🟢 Aston Martin announces new simulator tech"
    ]

    return render_template("index.html", timeline=timeline, latest_news=latest_news)


@app.route("/events")
def events():
    for i, race in enumerate(race_schedule):
        race["booking"] = "Book Now" if i < 3 else "Opening Soon"
    return render_template("events.html", races=race_schedule)


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
    categories = ["Caps", "Flags", "T-Shirts", "Keychains", "Headbands", "Driver Frames"]
    return render_template("merchandise.html", categories=categories)


@app.route("/category/<name>")
def category_page(name):
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE category=?", (name,))
        items = c.fetchall()
    return render_template("category.html", items=items, category=name)


# ---------------- CART ----------------
@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()

        # check if product already exists in user's cart
        c.execute(
            "SELECT id, quantity FROM cart WHERE username=? AND product_id=?",
            (session["user"], data["product_id"])
        )
        existing = c.fetchone()

        if existing:
            c.execute(
                "UPDATE cart SET quantity = quantity + 1 WHERE id=?",
                (existing[0],)
            )
            msg = "Quantity updated in cart"
        else:
            c.execute(
                "INSERT INTO cart (username, product_id, quantity) VALUES (?, ?, 1)",
                (session["user"], data["product_id"])
            )
            msg = "Added to cart"

    return jsonify({"msg": msg})


@app.route("/update-cart/<int:cart_id>/<action>")
def update_cart(cart_id, action):
    if "user" not in session:
        return redirect("/login-page")

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()

        if action == "increase":
            c.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=? AND username=?", (cart_id, session["user"]))
        elif action == "decrease":
            c.execute("SELECT quantity FROM cart WHERE id=? AND username=?", (cart_id, session["user"]))
            item = c.fetchone()
            if item and item[0] > 1:
                c.execute("UPDATE cart SET quantity = quantity - 1 WHERE id=? AND username=?", (cart_id, session["user"]))
            else:
                c.execute("DELETE FROM cart WHERE id=? AND username=?", (cart_id, session["user"]))
        elif action == "remove":
            c.execute("DELETE FROM cart WHERE id=? AND username=?", (cart_id, session["user"]))

    return redirect("/cart")


@app.route("/cart")
def view_cart():
    if "user" not in session:
        return redirect("/login-page")

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT cart.id, products.id, products.name,
                   products.price, products.image,
                   products.team, cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.username=?
        """, (session["user"],))
        raw_items = c.fetchall()

        items = []
        teams_in_cart = []
        for row in raw_items:
            item = {
                "cart_id": row[0],
                "product_id": row[1],
                "name": row[2],
                "price": row[3],
                "image": row[4],
                "team": row[5],
                "qty": row[6]
            }
            items.append(item)
            teams_in_cart.append(row[5])

        recommendations = []
        if teams_in_cart:
            preferred_team = teams_in_cart[0]
            c.execute("""
                SELECT id, name, price, image
                FROM products
                WHERE team=?
                AND id NOT IN (
                    SELECT product_id
                    FROM cart
                    WHERE username=?
                )
                LIMIT 4
            """, (preferred_team, session["user"]))

            recommendations = c.fetchall()

        # fallback trending products if no team-based recommendations
        if not recommendations:
            c.execute("""SELECT id, name, price, image FROM products ORDER BY RANDOM() LIMIT 4""")
            recommendations = c.fetchall()

    subtotal = sum(item["price"] * item["qty"] for item in items)
    delivery = 99 if subtotal > 0 else 0
    total = subtotal + delivery

    return render_template("cart.html", items=items, subtotal=subtotal, delivery=delivery, total=total, recommendations=recommendations)


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
    pincode = str(data["pincode"])
    if len(pincode) != 6 or not pincode.isdigit():
        return jsonify({"msg": "Delivery available only inside India"})

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT COALESCE(SUM(products.price * cart.quantity), 0)
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.username=?
        """, (session["user"],))
        subtotal = c.fetchone()[0]
        delivery = 99 if subtotal > 0 else 0
        total_amount = subtotal + delivery

        tracking_id = "F1-" + str(uuid.uuid4())[:8].upper()

        c.execute("""
            INSERT INTO orders(username, tracking_id, pincode, address, phone, alt_phone, email, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user"], tracking_id, pincode,
            data["address"], data["phone"], data["alt_phone"],
            data["email"], total_amount
        ))

        now = datetime.now()
        stages = [
            ("Exported", now),
            ("Received at Shipyard", now + timedelta(hours=2)),
            ("Packaged", now + timedelta(hours=5)),
            ("Transported to Nearest Hub", now + timedelta(hours=10)),
            ("Received at Nearest Hub", now + timedelta(hours=15)),
            ("Out for Delivery", now + timedelta(days=1, hours=3)),
            ("Order Delivered", now + timedelta(days=1, hours=8))
        ]

        for stage, time_obj in stages:
            c.execute(
                "INSERT INTO tracking_logs(tracking_id, stage, timestamp) VALUES (?, ?, ?)",
                (tracking_id, stage, time_obj.strftime("%d-%m-%Y %I:%M %p"))
            )

        c.execute("DELETE FROM cart WHERE username=?", (session["user"],))

    return jsonify({
        "msg": "Order placed successfully",
        "tracking_id": tracking_id,
        "amount": total_amount,
        "status": "Exported"
    })


@app.route("/my-orders")
def my_orders():
    if "user" not in session:
        return redirect("/login-page")

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT tracking_id, address, phone, email, status
            FROM orders
            WHERE username=?
            ORDER BY id DESC
        """, (session["user"],))
        raw_orders = c.fetchall()

        orders = []
        for row in raw_orders:
            tracking_id = row[0]
            c.execute("""
                SELECT stage, timestamp
                FROM tracking_logs
                WHERE tracking_id=?
                ORDER BY id
            """, (tracking_id,))
            raw_logs = c.fetchall()

            logs = [{"stage": stage, "time": timestamp} for stage, timestamp in raw_logs]
            progress_index = 0
            for i, log in enumerate(logs):
                if row[4].lower() in log["stage"].lower():
                    progress_index = i

            orders.append({
                "tracking_id": tracking_id,
                "address": row[1],
                "phone": row[2],
                "email": row[3],
                "status": row[4],
                "logs": logs,
                "progress_index": progress_index
            })

    return render_template("my_orders.html", orders=orders)


# ---------------- NOTIFICATIONS ----------------
@app.route("/notifications")
def notifications():
    if "user" not in session:
        return redirect("/login-page")

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT message FROM notifications WHERE username=? ORDER BY id DESC", (session["user"],))
        messages = c.fetchall()

    return render_template("notifications.html", messages=messages)


# ---------------- RECOMMENDATIONS ----------------
@app.route("/recommendations", methods=["GET", "POST"])
def recommendations():
    if "user" not in session:
        return redirect("/login-page")

    products = []
    selected_team = None
    selected_color = None
    selected_type = None

    if request.method == "POST":
        selected_team = request.form.get("team")
        selected_color = request.form.get("color")
        selected_type = request.form.get("type")

        with sqlite3.connect("db.sqlite3") as conn:
            c = conn.cursor()
            query = "SELECT id, name, price, image FROM products WHERE 1=1"
            params = []

            if selected_team and selected_team != "Any":
                query += " AND team=?"
                params.append(selected_team)

            if selected_type and selected_type != "Any":
                query += " AND category=?"
                params.append(selected_type)

            c.execute(query, params)
            products = c.fetchall()

    return render_template("recommendations.html", products=products, selected_team=selected_team, selected_color=selected_color, selected_type=selected_type)


# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM orders")
        total_orders = c.fetchone()[0]

        c.execute("SELECT COALESCE(SUM(amount), 0) FROM orders")
        revenue = c.fetchone()[0]

        c.execute("SELECT id, username, tracking_id, status FROM orders ORDER BY id DESC")
        recent_orders = c.fetchall()

    return render_template("admin.html", total_users=total_users, total_tickets=total_tickets, total_orders=total_orders, revenue=revenue, recent_orders=recent_orders)


@app.route("/update-order-status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    new_status = request.form["status"]

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT username, tracking_id FROM orders WHERE id=?", (order_id,))
        order = c.fetchone()

        if order:
            username, tracking_id = order
            c.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
            message = f"📦 Order {tracking_id} status updated to: {new_status}"
            c.execute("INSERT INTO notifications(username, message) VALUES (?, ?)", (username, message))

    return redirect("/admin")


# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()

        c.execute("SELECT event, COUNT(*) FROM tickets GROUP BY event")
        ticket_data = c.fetchall()

        c.execute("SELECT pincode, COUNT(*) FROM orders GROUP BY pincode")
        order_data = c.fetchall()

        c.execute("""
            SELECT products.category, COUNT(*)
            FROM cart
            JOIN products ON cart.product_id = products.id
            GROUP BY products.category
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)
        category_data = c.fetchall()

        c.execute("""
            SELECT products.team, COUNT(*)
            FROM cart
            JOIN products ON cart.product_id = products.id
            GROUP BY products.team
            ORDER BY COUNT(*) DESC
            LIMIT 5
        """)
        team_data = c.fetchall()

        c.execute("SELECT id, amount FROM orders ORDER BY id")
        revenue_data = c.fetchall()

    return render_template(
        "analytics.html",
        ticket_labels=[x[0] for x in ticket_data],
        ticket_values=[x[1] for x in ticket_data],
        order_labels=[x[0] for x in order_data],
        order_values=[x[1] for x in order_data],
        category_labels=[x[0] for x in category_data],
        category_values=[x[1] for x in category_data],
        team_labels=[x[0] for x in team_data],
        team_values=[x[1] for x in team_data],
        revenue_labels=[f"Order {x[0]}" for x in revenue_data],
        revenue_values=[x[1] for x in revenue_data]
    )


# ---------------- PAYMENT ----------------
@app.route("/payment")
def payment():
    if "user" not in session:
        return redirect("/login-page")

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT products.price, cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.username=?
        """, (session["user"],))
        items = c.fetchall()

    subtotal = sum(item[0] * item[1] for item in items)
    delivery = 99 if subtotal > 0 else 0
    total = subtotal + delivery

    return render_template("payment.html", subtotal=subtotal, delivery=delivery, total=total)


@app.route("/process-payment", methods=["POST"])
def process_payment():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json
    method = data["method"]

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""
            SELECT products.price, cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.username=?
        """, (session["user"],))
        items = c.fetchall()
        if not items:
             return jsonify({"msg": "Cart is empty"})
    subtotal = sum(item[0] * item[1] for item in items)
    delivery = 99 if subtotal > 0 else 0
    total = subtotal + delivery
    transaction_id = "TXN" + str(random.randint(100000, 999999))

    return jsonify({
        "msg": "Payment successful",
        "transaction_id": transaction_id,
        "method": method,
        "amount_paid": total
    })


@app.route("/invoice/<tracking_id>/<transaction_id>")
def invoice(tracking_id, transaction_id):
    if "user" not in session:
        return redirect("/login-page")

    filename = f"invoice_{tracking_id}.pdf"
    os.makedirs("static", exist_ok=True)
    filepath = os.path.join("static", filename)

    pdf = canvas.Canvas(filepath)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(180, 800, "F1 Marketplace Invoice")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 760, f"Customer: {session['user']}")
    pdf.drawString(50, 740, f"Tracking ID: {tracking_id}")
    pdf.drawString(50, 720, f"Transaction ID: {transaction_id}")
    pdf.drawString(50, 700, "Status: Payment Successful")
    pdf.drawString(50, 680, "Delivery: India Only")
    pdf.drawString(50, 660, "Thank you for shopping with F1 Marketplace")
    pdf.save()

    return send_file(filepath, as_attachment=True)


# ---------------- AUTH ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    hashed_password = generate_password_hash(data["password"])

    try:
        with sqlite3.connect("db.sqlite3") as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (data["username"], hashed_password)
            )
        return jsonify({"msg": "Signup success"})

    except sqlite3.IntegrityError:
        return jsonify({"msg": "Username already exists"})
    

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE username=?",
            (data["username"],)
        )
        user = c.fetchone()

    if user and len(user) > 2 and check_password_hash(user[2], data["password"]):
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
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO votes (driver) VALUES (?)", (data["driver"],))
    return jsonify({"msg": "Vote saved"})


@app.route("/poll-results")
def poll_results():
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT driver, COUNT(*) FROM votes GROUP BY driver")
        results = c.fetchall()
    return jsonify(results)


# ---------------- TICKETS ----------------
@app.route("/book", methods=["POST"])
def book():
    if "user" not in session:
        return jsonify({"msg": "Login required"})

    data = request.json
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO tickets (username, event) VALUES (?, ?)", (session["user"], data["event"]))
    return jsonify({"msg": "Ticket booked"})


@app.route("/my-tickets")
def my_tickets():
    if "user" not in session:
        return redirect("/login-page")

    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT event FROM tickets WHERE username=?", (session["user"],))
        data = c.fetchall()

    enriched_tickets = []
    for ticket in data:
        event_name = ticket[0]
        for race in race_schedule:
            if race["track"] == event_name:
                enriched_tickets.append(race)

    return render_template("my_tickets.html", tickets=enriched_tickets)


# ---------------- F1 LIVE API ----------------
@app.route("/teams")
def teams():
    data = requests.get("https://ergast.com/api/f1/current/constructors.json").json()
    return jsonify([t["name"] for t in data["MRData"]["ConstructorTable"]["Constructors"]])


@app.route("/drivers")
def drivers():
    data = requests.get("https://ergast.com/api/f1/current/drivers.json").json()
    return jsonify([
        d["givenName"] + " " + d["familyName"]
        for d in data["MRData"]["DriverTable"]["Drivers"]
    ])


@app.route("/results")
def results():
    data = requests.get("https://ergast.com/api/f1/current/last/results.json").json()
    return jsonify([
        r["Driver"]["familyName"]
        for r in data["MRData"]["RaceTable"]["Races"][0]["Results"]
    ])

from flask import Flask
from .routes import bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "f1-super-secret-key")

# Register blueprint
app.register_blueprint(bp)