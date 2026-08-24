import os
import sqlite3
import json
import base64
import uuid as _uuid
from datetime import datetime as _dt
from flask import Flask, send_from_directory, request, jsonify

app = Flask(__name__)

CFG = {
    "PORT": 5000
}

# Wskazanie na plik bazy rejestr_usterek.db
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rejestr_usterek.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY,
            created TEXT NOT NULL,
            klient TEXT NOT NULL,
            model TEXT NOT NULL,
            projekt TEXT NOT NULL,
            vin TEXT,
            typ TEXT NOT NULL,
            element TEXT,
            opisProblem TEXT NOT NULL,
            opisNaprawa TEXT,
            status TEXT NOT NULL DEFAULT 'open'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lists (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            record_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            data BLOB NOT NULL,
            created TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "rejestr_usterek.html")

@app.route("/api/lists", methods=["GET"])
def get_lists():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM lists WHERE key = 'lists'")
    row = cursor.fetchone()
    conn.close()
    if row:
        return jsonify(json.loads(row["value"]))
    return jsonify({})

@app.route("/api/lists", methods=["PUT"])
def save_lists():
    data = request.get_json() or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO lists (key, value) VALUES ('lists', ?)",
        (json.dumps(data),)
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/records", methods=["GET"])
def get_records():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records ORDER BY created DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records", methods=["POST"])
def create_record():
    data = request.get_json() or {}
    
    # "projekt" jest opcjonalny
    required = ["klient", "model", "opisProblem", "typ"]
    for f in required:
        if not data.get(f):
            return jsonify({"error": f"Pole {f} jest wymagane."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO records (id, created, klient, model, projekt, vin, typ, element, opisProblem, opisNaprawa, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("id"),
        data.get("created"),
        data.get("klient", ""),
        data.get("model", ""),
        data.get("projekt", ""),
        data.get("vin", ""),
        data.get("typ", ""),
        data.get("element", ""),
        data.get("opisProblem", ""),
        data.get("opisNaprawa", ""),
        data.get("status", "open")
    ))
    conn.commit()
    conn.close()

    return jsonify(data), 201

@app.route("/api/records/<rec_id>", methods=["PUT"])
def update_record(rec_id):
    data = request.get_json() or {}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE records 
        SET klient=?, model=?, projekt=?, vin=?, typ=?, element=?, opisProblem=?, opisNaprawa=?, status=?
        WHERE id=?
    """, (
        data.get("klient", ""),
        data.get("model", ""),
        data.get("projekt", ""),
        data.get("vin", ""),
        data.get("typ", ""),
        data.get("element", ""),
        data.get("opisProblem", ""),
        data.get("opisNaprawa", ""),
        data.get("status", "open"),
        rec_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/records/<rec_id>/status", methods=["PATCH"])
def update_status(rec_id):
    data = request.get_json() or {}
    status = data.get("status", "open")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE records SET status=? WHERE id=?", (status, rec_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/records/<rec_id>", methods=["DELETE"])
def delete_record(rec_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM records WHERE id=?", (rec_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/records/<rec_id>/photos", methods=["GET"])
def get_photos(rec_id):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, filename, created FROM photos WHERE record_id=? ORDER BY created",
        (rec_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/records/<rec_id>/photos", methods=["POST"])
def add_photo(rec_id):
    data = request.get_json() or {}
    count = get_db_connection().execute(
        "SELECT COUNT(*) FROM photos WHERE record_id=?", (rec_id,)).fetchone()[0]
    if count >= 3:
        return jsonify({"error": "Maksymalnie 3 zdjęcia na usterkę."}), 400
    photo_id = str(_uuid.uuid4())
    img_data = base64.b64decode(data.get("data", ""))
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO photos (id, record_id, filename, data, created) VALUES (?,?,?,?,?)",
        (photo_id, rec_id, data.get("filename","foto.jpg"),
         img_data, _dt.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()
    return jsonify({"id": photo_id}), 201

@app.route("/api/photos/<photo_id>", methods=["GET"])
def get_photo(photo_id):
    conn = get_db_connection()
    row = conn.execute("SELECT filename, data FROM photos WHERE id=?", (photo_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Nie znaleziono."}), 404
    return jsonify({"filename": row["filename"],
                    "data": base64.b64encode(row["data"]).decode()})

@app.route("/api/photos/<photo_id>", methods=["DELETE"])
def delete_photo(photo_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)