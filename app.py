from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = "secretkey"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS votes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver TEXT
    )""")

    # ✅ ADD THIS
    c.execute("""CREATE TABLE IF NOT EXISTS tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        event TEXT
    )""")

    conn.commit()
    conn.close()    

init_db()

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