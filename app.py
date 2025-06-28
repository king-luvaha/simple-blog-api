import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure MySQL using env variables
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 3308))

mysql = MySQL(app)

# Helper function to serialize rows
def serialize_post(row):
    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "category": row[3],
        "tags": json.loads(row[4]),
        "createdAt": row[5].isoformat(),
        "updatedAt": row[6].isoformat()
    }

@app.route('/posts', methods=['POST'])
def create_post():
    data = request.get_json()
    if not all(field in data for field in ['title', 'content', 'category', 'tags']):
        return jsonify({"error": "Missing fields"}), 400

    now = datetime.utcnow()
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO posts (title, content, category, tags, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data['title'], data['content'], data['category'], json.dumps(data['tags']), now, now))
    mysql.connection.commit()
    post_id = cursor.lastrowid
    cursor.close()

    return jsonify({
        "id": post_id,
        **data,
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }), 201

@app.route('/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    data = request.get_json()
    if not all(field in data for field in ['title', 'content', 'category', 'tags']):
        return jsonify({"error": "Missing fields"}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Post not found"}), 404

    now = datetime.utcnow()
    cursor.execute("""
        UPDATE posts SET title = %s, content = %s, category = %s, tags = %s, updated_at = %s
        WHERE id = %s
    """, (data['title'], data['content'], data['category'], json.dumps(data['tags']), now, post_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({
        "id": post_id,
        **data,
        "createdAt": row[5].isoformat(),
        "updatedAt": now.isoformat()
    })

@app.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM posts WHERE id = %s", (post_id,))
    if not cursor.fetchone():
        return jsonify({"error": "Post not found"}), 404

    cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
    mysql.connection.commit()
    cursor.close()
    return '', 204

@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (post_id,))
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return jsonify({"error": "Post not found"}), 404
    return jsonify(serialize_post(row))

@app.route('/posts', methods=['GET'])
def get_all_posts():
    term = request.args.get('term', '')
    cursor = mysql.connection.cursor()
    if term:
        query = """
            SELECT * FROM posts
            WHERE title LIKE %s OR content LIKE %s OR category LIKE %s
        """
        wildcard = f"%{term}%"
        cursor.execute(query, (wildcard, wildcard, wildcard))
    else:
        cursor.execute("SELECT * FROM posts")
    rows = cursor.fetchall()
    cursor.close()
    return jsonify([serialize_post(row) for row in rows])

if __name__ == '__main__':
    app.run(debug=True)
