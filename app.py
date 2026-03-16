from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>F1 Ticket Booking</title>
        <style>
            body{
                background-color:#0b0b0b;
                color:white;
                text-align:center;
                font-family:Arial;
            }
            h1{
                color:red;
                margin-top:80px;
            }
            .btn{
                padding:15px 30px;
                background:red;
                color:white;
                border:none;
                font-size:18px;
                cursor:pointer;
            }
        </style>
    </head>
    <body>
        <h1>Formula 1 Grand Prix Tickets</h1>
        <p>Book tickets for the fastest racing event on earth</p>
        <button class="btn">Book Now</button>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)