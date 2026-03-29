from flask import Flask, render_template, jsonify, send_from_directory
import os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from database.db import init_db, get_all_events, get_weekly_stats, get_person_stats, get_all_persons, get_summary

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))

RESULT_DIR = os.path.join(BASE_DIR, 'result')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/summary')
def api_summary():
    return jsonify(get_summary())

@app.route('/api/events')
def api_events():
    return jsonify(get_all_events())

@app.route('/api/weekly')
def api_weekly():
    return jsonify(get_weekly_stats())

@app.route('/api/persons')
def api_persons():
    return jsonify(get_all_persons())

@app.route('/api/person/<name>/stats')
def api_person_stats(name):
    return jsonify({
        'stats': get_person_stats(name),
        'events': [e for e in get_all_events() if e['person_name'] == name][:20]
    })

@app.route('/result/<path:filename>')
def result_image(filename):
    return send_from_directory(RESULT_DIR, filename)

if __name__ == '__main__':
    init_db()
    print("🌐 เปิด Dashboard ที่: http://localhost:5000")
    app.run(debug=True, port=5000)