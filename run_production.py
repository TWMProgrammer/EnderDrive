import os
import sys
import platform
import subprocess
import signal
from logging.config import dictConfig

def configure_flask_logging():
    """Configure Flask logging to match development server format"""
    dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '%(message)s',
            }
        },
        'handlers': {
            'wsgi': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'default'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        }
    })

def start_production_server():
    """
    Start the production server using Gunicorn on Linux or a compatible solution on Windows.
    """
    # Set default host based on platform
    if platform.system() == 'Windows':
        host = os.environ.get('HOST', '127.0.0.1')  # Default to localhost for Windows
    else:
        host = os.environ.get('HOST', '0.0.0.0')  # Default to all interfaces for Linux
    
    port = os.environ.get('PORT', '5000')
    workers = os.environ.get('WORKERS', '4')
    
    # Set Flask logging level to INFO to see all Flask logs
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = '0'
    
    # Configure Flask logging to match development server
    configure_flask_logging()
    
    # Check if running on Windows or Linux
    if platform.system() == 'Windows':
        # On Windows, use waitress as a production WSGI server
        try:
            print("Running on Windows. Starting Waitress...")
            print(f"Starting production server on {host}:{port} with {workers} workers")
            from waitress import serve
            from wsgi import application
            
            # Configure Flask to log access logs like development server
            import flask.logging
            from werkzeug.middleware.proxy_fix import ProxyFix
            
            # Wrap the application with ProxyFix to ensure correct IP addresses in logs
            application.wsgi_app = ProxyFix(application.wsgi_app)
            
            # Add a custom request logger
            @application.after_request
            def log_request(response):
                if not request_is_static_file():
                    application.logger.info(f'{request.remote_addr} - - [{get_formatted_time()}] "{request.method} {request.path} {request.environ.get("SERVER_PROTOCOL", "HTTP/1.0")}" {response.status_code} -')
                return response
            
            def request_is_static_file():
                """Check if the request is for a static file"""
                return request.path.startswith('/static/')
            
            def get_formatted_time():
                """Get the current time in the format used by Flask development server"""
                from datetime import datetime
                return datetime.now().strftime('%d/%b/%Y %H:%M:%S')
            
            # Import Flask request object
            from flask import request
            
            # Start the waitress server
            serve(application, host=host, port=int(port), threads=int(workers)*2)
            
        except KeyboardInterrupt:
            print("\nShutting down the server...")
            sys.exit(0)
    else:
        # On Linux, use Gunicorn directly
        try:
            print("Running on Linux. Starting Gunicorn...")
            print(f"Starting production server on {host}:{port} with {workers} workers")
            from wsgi import application
            
            # Configure Flask to log access logs like development server
            import flask.logging
            from werkzeug.middleware.proxy_fix import ProxyFix
            from flask import request
            
            # Wrap the application with ProxyFix to ensure correct IP addresses in logs
            application.wsgi_app = ProxyFix(application.wsgi_app)
            
            # Add a custom request logger
            @application.after_request
            def log_request(response):
                if not request_is_static_file():
                    application.logger.info(f'{request.remote_addr} - - [{get_formatted_time()}] "{request.method} {request.path} {request.environ.get("SERVER_PROTOCOL", "HTTP/1.0")}" {response.status_code} -')
                return response
            
            def request_is_static_file():
                """Check if the request is for a static file"""
                return request.path.startswith('/static/')
            
            def get_formatted_time():
                """Get the current time in the format used by Flask development server"""
                from datetime import datetime
                return datetime.now().strftime('%d/%b/%Y %H:%M:%S')
            
            cmd = [
                "gunicorn",
                "--bind", f"{host}:{port}",
                "--workers", workers,
                "--timeout", "120",
                "--log-level", "info",
                "--access-logformat", '%(h)s - - [%(t)s] - [Worker: %(p)s] "%(r)s" %(s)s',
                "--error-logfile", "-",
                "--access-logfile", "-",
                "--logger-class", "gunicorn.glogging.Logger",
                "--capture-output",
                "--enable-stdio-inheritance",
                "--worker-class", "sync",
                "wsgi:application"
            ]
            
            # Set environment variables for Flask logging
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'  # Ensure Python output is unbuffered
            env['GUNICORN_CMD_ARGS'] = '--preload'  # Enable preloading for better logging
            
            process = subprocess.Popen(cmd, env=env)
            
            def signal_handler(sig, frame):
                print("\nShutting down the server...")
                process.terminate()
                sys.exit(0)
            
            signal.signal(signal.SIGINT, signal_handler)
            process.wait()
            
        except KeyboardInterrupt:
            print("\nShutting down the server...")
            sys.exit(0)

if __name__ == "__main__":
    start_production_server()
