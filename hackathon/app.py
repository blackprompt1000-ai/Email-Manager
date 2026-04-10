"""
app.py — Flask web server for the Email Rectifier Assistant (v2).

New in v2:
  - Background inbox scanner (unlimited emails, batched IMAP)
  - Smart dynamic preference form endpoints
  - Preference-aware email reprocessing
  - Analytics endpoint
  - OpenEnv agent endpoints (state / step / reset)
"""

import json
import threading
from flask import Flask, render_template, request, jsonify, session

from auth import AuthManager
from email_client import EmailClient, PROVIDER_PRESETS
from ai_processor import process_email, get_inbox_insights, analyze_inbox, reprocess_with_preferences
from utils import TaskManager
from preferences import PreferencesManager
from openenv_agent import EmailEnv

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "email-rectifier-secret-key-2026"

# ── Shared State ────────────────────────────────────────────────────────────
auth_manager    = AuthManager()
prefs_manager   = PreferencesManager()
email_clients: dict  = {}   # token -> EmailClient
task_manager    = TaskManager()
env_agents: dict     = {}   # token -> EmailEnv
scan_state: dict     = {}   # token -> scan progress dict


# ── Auth Helpers ────────────────────────────────────────────────────────────

def _get_token():
    return session.get("token") or request.headers.get("X-Auth-Token", "")


def _require_auth():
    token = _get_token()
    if not token:
        return None, (jsonify({"success": False, "message": "Not authenticated."}), 401)
    username = auth_manager.verify_session(token)
    if not username:
        return None, (jsonify({"success": False, "message": "Session expired. Please login again."}), 401)
    return username, None


def _get_or_reconnect_email_client():
    token  = _get_token()
    client = email_clients.get(token)

    if client and client._connection:
        try:
            client._connection.noop()
            return client
        except Exception:
            del email_clients[token]
            client = None

    email_creds = session.get("email_creds")
    if email_creds:
        try:
            new_client = EmailClient(
                email_address=email_creds["email_address"],
                password=email_creds["email_password"],
                provider=email_creds.get("provider", "gmail"),
                host=email_creds.get("custom_host") if email_creds.get("provider") == "custom" else None,
                port=email_creds.get("custom_port") if email_creds.get("provider") == "custom" else None,
            )
            result = new_client.connect()
            if result["success"]:
                email_clients[token] = new_client
                return new_client
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Root route — returns HTTP 200 (renders UI or JSON based on Accept header)."""
    accept = request.headers.get("Accept", "")
    if "text/html" in accept or not accept:
        return render_template("index.html")
    return jsonify({"status": "ok", "service": "Email Rectifier Assistant", "version": "2.0.0"})


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint — always returns HTTP 200."""
    return jsonify({"status": "ok", "service": "Email Rectifier Assistant"})


@app.route("/reset", methods=["POST"])
def root_reset():
    """
    Root-level /reset for Hugging Face Space + OpenEnv compatibility.
    Initializes environment with demo data (no auth required).
    """
    env = EmailEnv()
    # Use demo emails processed through AI pipeline
    demo_emails = [
        {"id": "demo-1", "sender": "noreply@paypal.com",
         "subject": "Payment received $49.99", "body": "Your payment was processed. Transaction ID: TXN-123."},
        {"id": "demo-2", "sender": "hr@techcorp.com",
         "subject": "Performance Review Q1", "body": "Your review is Monday at 10 AM. Attendance mandatory."},
        {"id": "demo-3", "sender": "winner@lucky.xyz",
         "subject": "You Won!!!", "body": "Claim your prize. Send $500 processing fee via wire transfer."},
    ]
    from ai_processor import process_email as _ai_process
    processed = [{**em, "ai": _ai_process(em)} for em in demo_emails]
    state = env.reset(processed, {"life_mode": "Work", "fraud_sensitivity": "MEDIUM"})
    return jsonify({"success": True, "state": state, "message": "Environment reset."})


# ══════════════════════════════════════════════════════════════════════════════
# AUTH API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/signup", methods=["POST"])
def api_signup():
    data = request.json or {}
    result = auth_manager.signup(data.get("username", ""), data.get("password", ""), data.get("confirm_password", ""))
    if result.get("success"):
        session["token"]    = result["token"]
        session["username"] = data["username"].strip().lower()
    return jsonify(result)


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    result = auth_manager.login(data.get("username", ""), data.get("password", ""))
    if result.get("success"):
        session["token"]    = result["token"]
        session["username"] = data["username"].strip().lower()
    return jsonify(result)


@app.route("/api/logout", methods=["POST"])
def api_logout():
    token = _get_token()
    if token:
        auth_manager.logout(token)
        if token in email_clients:
            email_clients[token].disconnect()
            del email_clients[token]
        scan_state.pop(token, None)
        env_agents.pop(token, None)
    session.clear()
    return jsonify({"success": True, "message": "Logged out."})


@app.route("/api/reset-password", methods=["POST"])
def api_reset_password():
    data = request.json or {}
    result = auth_manager.reset_password(
        data.get("username", ""), data.get("new_password", ""), data.get("confirm_new_password", "")
    )
    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL CONNECTION API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/providers", methods=["GET"])
def api_providers():
    return jsonify({"providers": list(PROVIDER_PRESETS.keys()), "presets": PROVIDER_PRESETS})


@app.route("/api/connect-email", methods=["POST"])
def api_connect_email():
    username, err = _require_auth()
    if err:
        return err

    data            = request.json or {}
    email_address   = data.get("email_address", "")
    email_password  = data.get("email_password", "")
    provider        = data.get("provider", "gmail")
    custom_host     = data.get("custom_host", "")
    custom_port     = data.get("custom_port", 993)

    if not email_address or not email_password:
        return jsonify({"success": False, "message": "Email and password are required."})

    try:
        client = EmailClient(
            email_address=email_address,
            password=email_password,
            provider=provider,
            host=custom_host if provider == "custom" else None,
            port=int(custom_port) if provider == "custom" else None,
        )
        result = client.connect()
        if result["success"]:
            token = _get_token()
            email_clients[token] = client
            session["email_connected"] = True
            session["email_address"]   = email_address
            session["email_creds"] = {
                "email_address": email_address,
                "email_password": email_password,
                "provider": provider,
                "custom_host": custom_host,
                "custom_port": int(custom_port),
            }
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/api/disconnect-email", methods=["POST"])
def api_disconnect_email():
    token = _get_token()
    if token in email_clients:
        email_clients[token].disconnect()
        del email_clients[token]
    session.pop("email_connected", None)
    session.pop("email_address", None)
    session.pop("email_creds", None)
    return jsonify({"success": True, "message": "Email disconnected."})


# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND SCAN API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/start-scan", methods=["POST"])
def api_start_scan():
    """Start a full background inbox scan (user-selected email count, batched IMAP)."""
    username, err = _require_auth()
    if err:
        return err

    client = _get_or_reconnect_email_client()
    if not client:
        return jsonify({"success": False, "message": "No email account connected."})

    token = _get_token()

    # Don't double-start
    if scan_state.get(token, {}).get("status") == "scanning":
        return jsonify({"success": True, "message": "Scan already in progress."})

    # Read user-specified email count (default 100, cap 500)
    data = request.json or {}
    max_emails = min(int(data.get("max_emails", 100)), 500)

    scan_state[token] = {
        "status":   "scanning",
        "fetched":  0,
        "total":    0,
        "emails":   [],
        "analysis": None,
        "error":    None,
    }

    def _do_scan():
        try:
            def progress(fetched, total):
                scan_state[token]["fetched"] = fetched
                scan_state[token]["total"]   = total

            result = client.fetch_all_emails_batched(batch_size=50, max_emails=max_emails, progress_callback=progress)

            if not result["success"]:
                scan_state[token]["status"] = "error"
                scan_state[token]["error"]  = result["message"]
                return

            raw_emails = result["emails"]

            # AI-process each email
            processed = []
            for em in raw_emails:
                ai_result = process_email(em)
                task_manager.extract_and_store_tasks(em.get("id", ""), ai_result)
                processed.append({**em, "ai": ai_result})

            analysis = analyze_inbox(processed)

            scan_state[token]["emails"]   = processed
            scan_state[token]["analysis"] = analysis
            scan_state[token]["status"]   = "complete"

        except Exception as exc:
            scan_state[token]["status"] = "error"
            scan_state[token]["error"]  = str(exc)

    t = threading.Thread(target=_do_scan, daemon=True)
    t.start()
    return jsonify({"success": True, "message": f"Scan started ({max_emails} emails)."})


@app.route("/api/scan-progress", methods=["GET"])
def api_scan_progress():
    """Poll scan status and progress."""
    token = _get_token()
    s = scan_state.get(token, {})
    return jsonify({
        "success": True,
        "status":  s.get("status", "idle"),
        "fetched": s.get("fetched", 0),
        "total":   s.get("total", 0),
        "pct":     round(s["fetched"] / s["total"] * 100) if s.get("total") else 0,
        "error":   s.get("error"),
    })


@app.route("/api/scan-analysis", methods=["GET"])
def api_scan_analysis():
    """Return analysis results once scan is complete."""
    token = _get_token()
    s = scan_state.get(token, {})
    if s.get("status") != "complete":
        return jsonify({"success": False, "message": "Scan not complete yet."})
    return jsonify({
        "success":     True,
        "analysis":    s.get("analysis", {}),
        "email_count": len(s.get("emails", [])),
    })


# ══════════════════════════════════════════════════════════════════════════════
# PREFERENCES API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/preferences", methods=["GET"])
def api_get_preferences():
    username, err = _require_auth()
    if err:
        return err
    saved = prefs_manager.load(username)
    return jsonify({"success": True, "preferences": saved or PreferencesManager.get_defaults()})


@app.route("/api/preferences", methods=["POST"])
def api_save_preferences():
    username, err = _require_auth()
    if err:
        return err
    prefs = request.json or {}
    prefs_manager.save(username, prefs)
    return jsonify({"success": True, "message": "Preferences saved."})


# ══════════════════════════════════════════════════════════════════════════════
# REPROCESS API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/reprocess", methods=["POST"])
def api_reprocess():
    """
    Save preferences and re-process previously scanned emails.
    Resets the OpenEnv agent with the new email list + preferences.
    """
    username, err = _require_auth()
    if err:
        return err

    token = _get_token()
    prefs = request.json or {}
    prefs_manager.save(username, prefs)

    s = scan_state.get(token, {})
    if s.get("status") != "complete":
        return jsonify({"success": False, "message": "No completed scan found. Please scan first."})

    emails = s.get("emails", [])
    if not emails:
        return jsonify({"success": False, "message": "No emails to reprocess."})

    reprocessed = reprocess_with_preferences(emails, prefs)
    scan_state[token]["emails"] = reprocessed

    insights = get_inbox_insights(reprocessed)
    analysis = analyze_inbox(reprocessed)
    scan_state[token]["analysis"] = analysis

    # Reset OpenEnv agent
    env = EmailEnv()
    env.reset(reprocessed, prefs)
    env_agents[token] = env

    return jsonify({
        "success":  True,
        "emails":   reprocessed,
        "insights": insights,
        "analysis": analysis,
        "message":  f"Re-processed {len(reprocessed)} emails with your preferences.",
    })


# ══════════════════════════════════════════════════════════════════════════════
# LEGACY FETCH (kept for backward compat, now wraps scanner)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/fetch-emails", methods=["GET"])
def api_fetch_emails():
    """Legacy: fetch up to 100 emails and AI-process them in one shot."""
    username, err = _require_auth()
    if err:
        return err

    client = _get_or_reconnect_email_client()
    if not client:
        return jsonify({"success": False, "message": "No email account connected."})

    count  = min(request.args.get("count", 100, type=int), 200)
    result = client.fetch_emails(count=count)
    if not result["success"]:
        return jsonify(result)

    processed = []
    for em in result["emails"]:
        ai_result = process_email(em)
        task_manager.extract_and_store_tasks(em.get("id", ""), ai_result)
        processed.append({**em, "ai": ai_result})

    insights = get_inbox_insights(processed)
    return jsonify({
        "success":  True,
        "emails":   processed,
        "insights": insights,
        "message":  f"Fetched and analyzed {len(processed)} emails.",
    })


# ══════════════════════════════════════════════════════════════════════════════
# ACTION API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/apply-action", methods=["POST"])
def api_apply_action():
    username, err = _require_auth()
    if err:
        return err

    client = _get_or_reconnect_email_client()
    if not client:
        return jsonify({"success": False, "message": "No email account connected."})

    data     = request.json or {}
    email_id = data.get("email_id", "")
    action   = data.get("action", "")

    if not email_id or not action:
        return jsonify({"success": False, "message": "Email ID and action are required."})

    if action == "DELETE":
        result = client.delete_email(email_id)
    elif action == "BLOCK":
        result = client.move_to_spam(email_id)
    else:
        result = {"success": True, "message": f"Action '{action}' noted. Email unchanged."}

    return jsonify(result)


# ══════════════════════════════════════════════════════════════════════════════
# TASK API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/tasks", methods=["GET"])
def api_get_tasks():
    username, err = _require_auth()
    if err:
        return err
    status_filter = request.args.get("status", "all")
    if status_filter == "pending":
        tasks = task_manager.get_pending_tasks()
    elif status_filter == "completed":
        tasks = [t for t in task_manager.get_all_tasks() if t["status"] == "completed"]
    else:
        tasks = task_manager.get_all_tasks()
    return jsonify({
        "success":         True,
        "tasks":           tasks,
        "pending_count":   task_manager.pending_count,
        "completed_count": task_manager.completed_count,
    })


@app.route("/api/tasks/complete", methods=["POST"])
def api_complete_task():
    username, err = _require_auth()
    if err:
        return err
    task_id = (request.json or {}).get("task_id", "")
    if not task_id:
        return jsonify({"success": False, "message": "Task ID is required."})
    result = task_manager.complete_task(task_id)
    if result:
        return jsonify({"success": True, "message": "Task completed!", "task": result})
    return jsonify({"success": False, "message": "Task not found."})


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/analytics", methods=["GET"])
def api_analytics():
    """Return analytics from the most recent scan."""
    username, err = _require_auth()
    if err:
        return err
    token = _get_token()
    s = scan_state.get(token, {})
    analysis = s.get("analysis")
    if not analysis:
        return jsonify({"success": False, "message": "No scan data available."})

    # OpenEnv session analytics
    env = env_agents.get(token)
    env_analytics = env.get_session_analytics() if env else {}

    return jsonify({
        "success":       True,
        "inbox_analysis": analysis,
        "agent_analytics": env_analytics,
        "task_summary": {
            "pending":   task_manager.pending_count,
            "completed": task_manager.completed_count,
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
# OPENENV AGENT API
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/openenv/state", methods=["GET"])
def api_env_state():
    username, err = _require_auth()
    if err:
        return err
    token = _get_token()
    env = env_agents.get(token)
    if not env:
        return jsonify({"success": False, "message": "Agent not initialized. Please reprocess emails first."})
    return jsonify({"success": True, "state": env.state()})


@app.route("/api/openenv/step", methods=["POST"])
def api_env_step():
    username, err = _require_auth()
    if err:
        return err
    token  = _get_token()
    action = (request.json or {}).get("action", "FYI")
    env    = env_agents.get(token)
    if not env:
        return jsonify({"success": False, "message": "Agent not initialized."})
    state, reward, done, info = env.step(action)
    return jsonify({"success": True, "state": state, "reward": reward, "done": done, "info": info})


@app.route("/api/openenv/reset", methods=["POST"])
def api_env_reset():
    username, err = _require_auth()
    if err:
        return err
    token  = _get_token()
    s      = scan_state.get(token, {})
    emails = s.get("emails", [])
    prefs  = prefs_manager.load(username) or PreferencesManager.get_defaults()

    env = EmailEnv()
    env.reset(emails, prefs)
    env_agents[token] = env
    return jsonify({"success": True, "state": env.state(), "message": "Agent reset."})


@app.route("/api/openenv/history", methods=["GET"])
def api_env_history():
    username, err = _require_auth()
    if err:
        return err
    token = _get_token()
    env   = env_agents.get(token)
    if not env:
        return jsonify({"success": False, "message": "Agent not initialized."})
    return jsonify({"success": True, "history": env.get_history(), "analytics": env.get_session_analytics()})


# ══════════════════════════════════════════════════════════════════════════════
# STATUS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/status", methods=["GET"])
def api_status():
    token    = _get_token()
    username = auth_manager.verify_session(token) if token else None
    email_connected = bool(token and (token in email_clients or session.get("email_creds")))
    prefs    = prefs_manager.load(username) if username else None
    s        = scan_state.get(token, {})
    return jsonify({
        "authenticated":    username is not None,
        "username":         username,
        "email_connected":  email_connected,
        "email_address":    session.get("email_address", ""),
        "scan_status":      s.get("status", "idle"),
        "has_preferences":  prefs is not None,
    })


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n[*] Email Rectifier Assistant v2")
    print("=" * 50)
    print("  Open in your browser: http://localhost:7860")
    print("=" * 50 + "\n")
    app.run(debug=False, host="0.0.0.0", port=7860)
