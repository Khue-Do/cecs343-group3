
from flask import Flask, request, jsonify
from order_records import OrderRecords

app = Flask(__name__)
records = OrderRecords()


@app.post("/orders")
def save_order():
    data = request.get_json()

    try:
        order = records.save_order(
            data["order_id"],
            data["ticket"],
            data["total"],
            data["transaction"],
            data["payment"]
        )
        return jsonify(order), 201
    except (KeyError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.get("/orders/<order_id>")
def view_order(order_id):
    try:
        return jsonify(records.view_order(order_id))
    except KeyError:
        return jsonify({"error": "Order not found"}), 404
