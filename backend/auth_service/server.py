from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    return jsonify({"message": f"User {data.get('email')} registered!"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    return jsonify({"message": f"Welcome {data.get('email')}!"})

if __name__ == "__main__":
    app.run(port=5000)