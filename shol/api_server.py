from flask import Flask, jsonify, render_template
from .monitor import ProcessHistory
from .logger_db import engine, events
import psutil
from .utils import BASE_DIR
from .logger_db import session
from sqlalchemy import select

app = Flask(__name__, template_folder=str(BASE_DIR / "web" / "templates"))
ph = ProcessHistory()

@app.route("/")
def index():
    # update a fresh sample for demo simplicity
    ph.sample()
    latest = ph.get_all_latest()
    # convert to simple JSON-friendly objects
    procs = []
    for p in latest:
        procs.append({
            "pid": p['pid'],
            "name": p.get('name'),
            "cmdline": p.get('cmdline_str'),
            "cpu": p.get('cpu_percent'),
            "mem": p.get('memory_percent'),
            "status": p.get('status')
        })
    # fetch last 30 events
    with engine.connect() as conn:
        res = conn.execute(select([events]).order_by(events.c.ts.desc()).limit(30))
        logs = [dict(r) for r in res]
    return render_template("index.html", procs=procs, logs=logs)

@app.route("/api/procs")
def api_procs():
    ph.sample()
    return jsonify(ph.get_all_latest())

@app.route("/api/logs")
def api_logs():
    with engine.connect() as conn:
        res = conn.execute(select([events]).order_by(events.c.ts.desc()).limit(100))
        logs = [dict(r) for r in res]
    return jsonify(logs)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
