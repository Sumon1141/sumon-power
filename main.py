from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import requests
import os
import json
from urllib.parse import urlparse

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILES_PATH = os.path.join(BASE_DIR, 'profiles.json')

def load_profiles():
    if not os.path.exists(PROFILES_PATH):
        return {}
    with open(PROFILES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_profiles(p):
    with open(PROFILES_PATH, 'w', encoding='utf-8') as f:
        json.dump(p, f, indent=2, ensure_ascii=False)

@app.route('/')
def index():
    profiles = load_profiles()
    return render_template('index.html', profiles=profiles)

@app.route('/create-profile', methods=['POST'])
def create_profile():
    name = request.form.get('name')
    ua = request.form.get('user_agent')
    if not name:
        return redirect(url_for('index'))
    profiles = load_profiles()
    profiles[name] = {
        'user_agent': ua or 'Mozilla/5.0 (Android)',
        'description': request.form.get('description') or ''
    }
    save_profiles(profiles)
    return redirect(url_for('index'))

@app.route('/view', methods=['POST'])
def view():
    target = request.form.get('url')
    profile = request.form.get('profile')
    if not target:
        return redirect(url_for('index'))
    # normalize url
    if not urlparse(target).scheme:
        target = 'http://' + target
    profiles = load_profiles()
    profile_obj = profiles.get(profile, {})
    headers = {}
    if profile_obj.get('user_agent'):
        headers['User-Agent'] = profile_obj['user_agent']

    try:
        resp = requests.get(target, headers=headers, timeout=15)
    except Exception as e:
        return f"Failed to fetch target URL: {e}", 500

    content_type = resp.headers.get('Content-Type','')
    body = resp.content

    # Only attempt injection for HTML pages
    if 'text/html' in content_type.decode() if isinstance(content_type, bytes) else 'text/html' in content_type:
        try:
            text = resp.text
            # read injection JS
            with open(os.path.join(BASE_DIR, 'static', 'injection.js'), 'r', encoding='utf-8') as f:
                inj = f.read()
            # prepare script tag with profile-specific UA
            script = '<script>window.__sp_profile = ' + json.dumps(profile_obj) + ';</script>\n'
            script += '<script>' + inj + '</script>\n'
            # try inject before </body>, if not found insert before </head>
            if '</body>' in text:
                text = text.replace('</body>', script + '</body>')
            elif '</head>' in text:
                text = text.replace('</head>', script + '</head>')
            else:
                text = script + text
            return text
        except Exception as e:
            return f"Failed to inject script: {e}", 500
    else:
        # for non-html, just return raw content with original content-type
        from flask import Response
        response = Response(body)
        response.headers['Content-Type'] = resp.headers.get('Content-Type','application/octet-stream')
        return response

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
