# app.py - entry point for hosting (Render etc.).
# The Tkinter desktop version now lives in desktop_app.py.
import os

from web_app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
