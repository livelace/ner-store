import os
import re
import sys
import sqlite3
import time

from datetime import datetime
from flask import Flask, abort, request, json, make_response, send_file, render_template
from langdetect import detect

DB_PATH = "/tmp/db.sqlite3"


def add_record(text, language, url, timestamp):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO records (text, language, url, timestamp) VALUES (?, ?, ?, ?)''', [
        text,
        language,
        url,
        timestamp
    ])
    conn.commit()


def get_stat(language):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT count(id) FROM records WHERE language="{}"'.format(language))
    results = cursor.fetchall()
    conn.commit()

    return results


def get_text():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT text FROM records')
    results = cursor.fetchall()
    conn.commit()

    return results


# ----------------------------------------------------------------------------------------------------------------------
# Initialize database


if not os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE records (
                id INTEGER PRIMARY KEY NOT NULL,
                text TEXT NOT NULL,
                language TEXT NOT NULL,
                url TEXT NOT NULL,
                timestamp INTEGER NOT NULL
            )
        ''')
        results = cursor.fetchall()
        conn.commit()
    except Exception as e:
        print("ERROR: Cannot initialize database: {}".format(e))
        sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------------
# Start Flask server

app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
def root():

    # Handle POST requests with data
    if request.method == 'POST':
        data = list(request.form.keys())[0]
        data = json.loads(data)

        text = data['content']
        url = data['url']

        # Cleaning sentences from tags, it needs for language detection
        cleaned_text = re.sub("<.*?>", '', text)
        cleaned_text = re.sub("    ", ' ', cleaned_text)
        cleaned_text = re.sub("   ", ' ', cleaned_text)
        cleaned_text = re.sub("  ", ' ', cleaned_text)

        language = detect(cleaned_text)
        timestamp = time.mktime(datetime.utcnow().timetuple())

        if language != "ru" and language != "en":
            language = "unknown"

        try:
            add_record(text, language, url, timestamp)
            return "{}"
        except Exception as e:
            abort(make_response("ERROR: Cannot add record to the database:".format(e), 400))

    # Show statistics
    elif request.method == 'GET':
        try:
            en = get_stat("en")
            ru = get_stat("ru")

            return """
            Count of sentences:<br><br>
            English: {0}<br>
            Russian: {1}<br><br>
            <a href="{2}db">Download entire database</a><br>
            <a href="{2}text">View all sentences as text</a>
            """.format(en[0][0], ru[0][0], request.host_url)
        except Exception as e:
            abort(make_response("ERROR: Cannot get statistics:".format(e), 500))


# Allow to download database
@app.route("/db", methods=['GET'])
def db():
    if request.method == 'GET':
        try:
            return send_file(DB_PATH, as_attachment=True)
        except Exception as e:
            abort(make_response("ERROR: Cannot upload database: {}".format(e), 500))


# Return sentences as text
@app.route("/text", methods=['GET'])
def text():
    if request.method == 'GET':
        try:
            return render_template('text.html', sentences=get_text())
        except Exception as e:
            abort(make_response("ERROR: Cannot get sentences as text: {}".format(e), 500))


if __name__ == "__main__":
    app.run(host='0.0.0.0')
