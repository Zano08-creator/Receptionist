"""
Piccolo web server usato solo per il piano gratuito di Render.

Render (piano free, tipo "Web Service") mette in pausa il servizio dopo
un periodo di inattività se non riceve richieste HTTP. Questo server
espone una singola pagina "/" che risponde sempre "Elyndra è sveglia",
e viene usata anche come bersaglio dell'auto-ping ogni 14 minuti fatto
dal bot stesso (vedi keep_alive_ping in index.py).
"""

import os
import threading
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "🧝‍♀️ Elyndra la Receptionist è sveglia e vigile."


def _run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    """Avvia il web server in un thread separato, senza bloccare il bot."""
    t = threading.Thread(target=_run, daemon=True)
    t.start()
