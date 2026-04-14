import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ui'))

from dash_app import app

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
