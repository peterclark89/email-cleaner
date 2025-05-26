import os
import json
import logging
from flask import Flask, request, jsonify, render_template_string
from mail_scanner import scan_senders    # your existing scanner

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# same mapping you had before
JSON_FILES = {
    'whitelist': 'whitelist.json',
    'approved': 'approved_senders.json',
    'oneoff'  : 'oneoff.json'
}

def _classify_sender(sender: str, action: str):
    """
    Core logic to append `sender` to the JSON file for `action`.
    """
    path = JSON_FILES[action]
    # load existing list (migrating dict or legacy formats if needed)
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        if isinstance(data, dict) and action != 'whitelist':
            # approved/oneoff might have been {"senders":[...]}
            data = data.get('senders', [])
        if isinstance(data, dict) and action == 'whitelist':
            # whitelist might have been {"emails": [...], "domains": [...]}
            data = data.get('emails', [])
        if not isinstance(data, list):
            data = []
    except FileNotFoundError:
        data = []

    if sender not in data:
        data.append(sender)

    # write back a simple list (we preserve your legacy one-key format)
    payload = data if action != 'whitelist' else {'emails': data, 'domains': []}
    with open(path, 'w') as f:
        json.dump(payload, f, indent=2)

# JSON API endpoint
@app.route('/api/classify', methods=['POST'])
def api_classify():
    body = request.get_json()
    sender = body.get('sender')
    action = body.get('action')
    if not sender or action not in JSON_FILES:
        return jsonify({'status':'error','message':'Invalid parameters'}), 400

    try:
        _classify_sender(sender, action)
    except Exception as e:
        app.logger.exception("Failed classification")
        return jsonify({'status':'error','message':str(e)}), 500

    return jsonify({'status':'ok','sender':sender,'action':action})

# Management UI
@app.route('/manage')
def manage():
    _, unknown = scan_senders(limit=None)
    senders = sorted(unknown.keys())

    html = render_template_string("""
<!doctype html>
<html>
<head>
  <title>Manage Unknown Senders</title>
  <style>
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
    tr.whitelist  { background: #cfc; }
    tr.approved   { background: #ccf; }
    tr.oneoff     { background: #fcc; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
  </style>
</head>
<body>
  <h1>Unknown Senders</h1>
  <p>Click a button to classify. Row will gray-out and color-code itself.</p>
  <table>
    <thead>
      <tr><th>Email</th><th>Whitelist</th><th>Auto-Cleanup</th><th>One-Off</th></tr>
    </thead>
    <tbody>
    {% for sender in senders %}
      <tr id="row-{{ loop.index0 }}">
        <td>{{ sender }}</td>
        <td><button onclick="classify({{ loop.index0 }}, '{{ sender }}','whitelist')">Whitelist</button></td>
        <td><button onclick="classify({{ loop.index0 }}, '{{ sender }}','approved')">Cleanup</button></td>
        <td><button onclick="classify({{ loop.index0 }}, '{{ sender }}','oneoff')">One-Off</button></td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <script>
    function classify(rowIdx, sender, action) {
      fetch('/api/classify', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({sender: sender, action: action})
      })
      .then(r=>r.json())
      .then(obj=>{
        if(obj.status==='ok') {
          let row = document.getElementById('row-'+rowIdx);
          row.classList.add(action);
          // disable all buttons in this row
          row.querySelectorAll('button').forEach(b=>b.disabled=true);
        } else {
          alert('Error: '+obj.message);
        }
      })
      .catch(err=>alert('Request failed: '+err));
    }
  </script>
</body>
</html>
    """, senders=senders)

    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0', port=port, debug=True)
