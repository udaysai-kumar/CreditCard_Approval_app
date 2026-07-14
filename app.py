"""
app.py
------
Main entry point for the AI Credit Card Approval Prediction System.
Uses the Flask application-factory + Blueprint pattern for a clean
MVC-style structure.
"""
from flask import Flask, render_template

import db
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from app_blueprints import auth, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)

    @app.context_processor
    def inject_globals():
        from flask import g
        return {"current_user": g.get("user")}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
