from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/events", methods=["GET"])
def get_events():
    return jsonify({"events": ["Event A", "Event B"]})

@app.route("/events", methods=["POST"])
def create_event():
    data = request.get_json()
    return jsonify({"message": f"Event '{data.get('title')}' created!"})

if __name__ == "__main__":
    app.run(port=5001)