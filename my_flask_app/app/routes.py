from flask import Blueprint, render_template, request, session, redirect, jsonify, send_file
import sqlite3
import os
import uuid
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas

bp = Blueprint('main', __name__)

# ---------------- RACE SCHEDULE ----------------
race_schedule = [
    {"track": "Japanese GP", "place": "Suzuka", "date": "2026-04-05", "time": "13:30 IST"},
    {"track": "Chinese GP", "place": "Shanghai", "date": "2026-04-12", "time": "12:30 IST"},
    {"track": "Miami GP", "place": "USA", "date": "2026-04-19", "time": "01:30 IST"},
    {"track": "Emilia Romagna GP", "place": "Imola", "date": "2026-05-03", "time": "18:30 IST"},
    {"track": "Monaco GP", "place": "Monte Carlo", "date": "2026-05-24", "time": "18:30 IST"},
    {"track": "British GP", "place": "Silverstone", "date": "2026-07-05", "time": "19:30 IST"}
]

# ---------------- PAGE ROUTES ----------------
@bp.route("/")
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

@bp.route("/events")
def events():
    for i, race in enumerate(race_schedule):
        race["booking"] = "Book Now" if i < 3 else "Opening Soon"
    return render_template("events.html", races=race_schedule)

@bp.route("/experience")
def experience():
    return render_template("experience.html")

@bp.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login-page")
    return render_template("dashboard.html")

@bp.route("/login-page")
def login_page():
    return render_template("login.html")

@bp.route("/signup-page")
def signup_page():
    return render_template("signup.html")

@bp.route("/merchandise")
def merchandise():
    categories = ["Caps", "Flags", "T-Shirts", "Keychains", "Headbands", "Driver Frames"]
    return render_template("merchandise.html", categories=categories)

@bp.route("/category/<name>")
def category_page(name):
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE category=?", (name,))
        items = c.fetchall()
    return render_template("category.html", items=items, category=name)

# ---------------- AUTH ----------------
@bp.route("/signup", methods=["POST"])
def signup():
    data = request.json
    hashed_password = generate_password_hash(data["password"])
    try:
        with sqlite3.connect("db.sqlite3") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (data["username"], hashed_password))
        return jsonify({"msg": "Signup success"})
    except sqlite3.IntegrityError:
        return jsonify({"msg": "Username already exists"})

@bp.route("/login", methods=["POST"])
def login():
    data = request.json
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (data["username"],))
        user = c.fetchone()
    if user and len(user) > 2 and check_password_hash(user[2], data["password"]):
        session["user"] = data["username"]
        return jsonify({"msg": "Login success"})
    return jsonify({"msg": "Invalid credentials"})

@bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# ---------------- CART ----------------
@bp.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user" not in session:
        return jsonify({"msg": "Login required"})
    data = request.json
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT id, quantity FROM cart WHERE username=? AND product_id=?", (session["user"], data["product_id"]))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=?", (existing[0],))
            msg = "Quantity updated in cart"
        else:
            c.execute("INSERT INTO cart (username, product_id, quantity) VALUES (?, ?, 1)", (session["user"], data["product_id"]))
            msg = "Added to cart"
    return jsonify({"msg": msg})

@bp.route("/update-cart/<int:cart_id>/<action>")
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

@bp.route("/cart")
def view_cart():
    if "user" not in session:
        return redirect("/login-page")
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""SELECT cart.id, products.id, products.name, products.price, products.image, products.team, cart.quantity
                     FROM cart JOIN products ON cart.product_id = products.id
                     WHERE cart.username=?""", (session["user"],))
        raw_items = c.fetchall()
        items = []
        teams_in_cart = []
        for row in raw_items:
            item = {"cart_id": row[0], "product_id": row[1], "name": row[2], "price": row[3], "image": row[4], "team": row[5], "qty": row[6]}
            items.append(item)
            teams_in_cart.append(row[5])
        recommendations = []
        if teams_in_cart:
            preferred_team = teams_in_cart[0]
            c.execute("""SELECT id, name, price, image FROM products
                         WHERE team=? AND id NOT IN (SELECT product_id FROM cart WHERE username=?) LIMIT 4""",
                      (preferred_team, session["user"]))
            recommendations = c.fetchall()
        if not recommendations:
            c.execute("SELECT id, name, price, image FROM products ORDER BY RANDOM() LIMIT 4")
            recommendations = c.fetchall()
    subtotal = sum(item["price"] * item["qty"] for item in items)
    delivery = 99 if subtotal > 0 else 0
    total = subtotal + delivery
    return render_template("cart.html", items=items, subtotal=subtotal, delivery=delivery, total=total, recommendations=recommendations)

# ---------------- CHECKOUT & PAYMENT ----------------
@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user" not in session:
        return redirect("/login-page")
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("""SELECT cart.id, products.id, products.name, products.price, products.image, cart.quantity
                     FROM cart JOIN products ON cart.product_id = products.id
                     WHERE cart.username=?""", (session["user"],))
        cart_items = c.fetchall()
    subtotal = sum(item[3] * item[5] for item in cart_items)
    delivery = 99 if subtotal > 0 else 0
    total = subtotal + delivery

    if request.method == "POST":
        order_id = str(uuid.uuid4())[:8]
        with sqlite3.connect("db.sqlite3") as conn:
            c = conn.cursor()
            c.execute("INSERT INTO orders (order_id, username, total, status) VALUES (?, ?, ?, ?)",
                      (order_id, session["user"], total, "Pending"))
            for item in cart_items:
                c.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                          (order_id, item[1], item[5], item[3]))
            c.execute("DELETE FROM cart WHERE username=?", (session["user"],))
        return redirect(f"/payment/{order_id}")
    return render_template("checkout.html", items=cart_items, subtotal=subtotal, delivery=delivery, total=total)

@bp.route("/payment/<order_id>", methods=["GET", "POST"])
def payment(order_id):
    if "user" not in session:
        return redirect("/login-page")
    if request.method == "POST":
        # Simulate payment success
        with sqlite3.connect("db.sqlite3") as conn:
            c = conn.cursor()
            c.execute("UPDATE orders SET status='Paid' WHERE order_id=?", (order_id,))
        return render_template("payment_success.html", order_id=order_id)
    return render_template("payment.html", order_id=order_id)

# ---------------- ORDER HISTORY & INVOICE ----------------
@bp.route("/orders")
def orders():
    if "user" not in session:
        return redirect("/login-page")
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE username=? ORDER BY created_at DESC", (session["user"],))
        user_orders = c.fetchall()
    return render_template("orders.html", orders=user_orders)

@bp.route("/invoice/<order_id>")
def invoice(order_id):
    if "user" not in session:
        return redirect("/login-page")
    # generate simple PDF invoice
    file_path = f"invoices/{order_id}.pdf"
    os.makedirs("invoices", exist_ok=True)
    c = canvas.Canvas(file_path)
    c.drawString(50, 800, f"Invoice for Order: {order_id}")
    c.drawString(50, 780, f"Customer: {session['user']}")
    c.drawString(50, 760, f"Date: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    c.save()
    return send_file(file_path, as_attachment=True)

# ---------------- NOTIFICATIONS ----------------
@bp.route("/notifications")
def notifications():
    if "user" not in session:
        return redirect("/login-page")
    notifications = [
        "Your order #AB1234 has been shipped!",
        "New F1 race announced: Miami GP!",
        "20% off on all McLaren merchandise this week!"
    ]
    return render_template("notifications.html", notifications=notifications)

# ---------------- RECOMMENDATIONS ----------------
@bp.route("/recommendations")
def recommendations():
    if "user" not in session:
        return redirect("/login-page")
    recommended_items = []
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, price, image FROM products ORDER BY RANDOM() LIMIT 6")
        recommended_items = c.fetchall()
    return render_template("recommendations.html", recommendations=recommended_items)

# ---------------- POLLS & TICKETS ----------------
@bp.route("/poll", methods=["GET", "POST"])
def poll():
    poll_data = {"Best Team 2026": ["Mercedes", "Red Bull", "Ferrari", "McLaren"]}
    selected = None
    if request.method == "POST":
        selected = request.form.get("team_choice")
        # store vote logic can be added here
    return render_template("poll.html", poll_data=poll_data, selected=selected)

@bp.route("/tickets")
def tickets():
    if "user" not in session:
        return redirect("/login-page")
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM tickets WHERE username=?", (session["user"],))
        user_tickets = c.fetchall()
    return render_template("tickets.html", tickets=user_tickets)

# ---------------- ADMIN DASHBOARD ----------------
@bp.route("/admin")
def admin_dashboard():
    if "user" not in session or session["user"] != "admin":
        return redirect("/")
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders")
        total_orders = c.fetchone()[0]
    return render_template("admin_dashboard.html", total_users=total_users, total_orders=total_orders)

# ---------------- F1 API ENDPOINT ----------------
@bp.route("/api/f1/races")
def api_races():
    return jsonify(race_schedule)

@bp.route("/api/f1/latest")
def api_latest():
    latest_results = [
        {"race": "Japanese GP", "winner": "Max Verstappen", "team": "Red Bull", "time": "1:28:43"},
        {"race": "Chinese GP", "winner": "Lewis Hamilton", "team": "Mercedes", "time": "1:30:11"}
    ]
    return jsonify(latest_results)