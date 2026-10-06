from flask import Flask

def start_app():
    app = Flask(__name__)

    from minify import bp as minify_bp

    app.register_blueprint(minify_bp, url_prefix='/')

    return app