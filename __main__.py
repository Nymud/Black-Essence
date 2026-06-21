"""Entry point.
- On Heroku (DYNO env var set): runs a lightweight web process that does nothing
  (Heroku requires a web process to stay alive; actual work is done via Scheduler)
- Locally: runs the full orchestrator with Telegram bot + APScheduler
"""
import os

if os.environ.get("DYNO"):
    # Running on Heroku — keep alive, Scheduler handles production cycles
    from flask import Flask
    app = Flask(__name__)

    @app.route("/")
    def health():
        return "Black Essence OK", 200

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
else:
    # Local dev — full orchestrator
    from orchestrator import main
    main()
