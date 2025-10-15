from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/ai/describe", methods=["POST"])
def describe():
    data = request.get_json()
    return jsonify({"description": f"Auto description for: {data.get('prompt')}"})

if __name__ == "__main__":
    app.run(port=5003)
