"""起動: python app.py"""
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from pricing import InvalidQuote, catalog, quote

app = Flask(__name__)
app.json.ensure_ascii = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

@app.get("/")
def index():
    return jsonify(name="拓也の料金表API", version="1.0.0", endpoints={
        "prices": "GET /api/v1/prices", "quotes": "POST /api/v1/quotes"})

@app.get("/api/v1/prices")
def prices():
    return jsonify(catalog())

@app.post("/api/v1/quotes")
def quotes():
    # 計算のみで見積もりリソースは保存しないため200を返す。
    return jsonify(quote(request.get_json()))

@app.errorhandler(InvalidQuote)
def invalid_quote(error):
    return jsonify(error={"code": "invalid_request", "message": str(error)}), 400

@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error={"code": error.code, "message": error.description}), error.code

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
