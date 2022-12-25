"""timeTB package initializer."""
# -*- coding: utf-8 -*-
import flask
app = flask.Flask(__name__)

import timeTB.routing
import timeTB.model

if __name__ == "__main__":
    app.run(debug=True)