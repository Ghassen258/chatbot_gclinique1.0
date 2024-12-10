import webview
import subprocess
import threading
import time
import re
import os
import sys
import logging

LOG_FILENAME = os.path.join(os.path.dirname(__file__), 'app_log.txt')
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s'
)


def get_base_path():
    """Determine the base path of the application."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundled executable
        return sys._MEIPASS
    else:
        # Running in a development environment
        return os.path.abspath(os.path.dirname(__file__))


def start_streamlit_and_get_port():
    """Start Streamlit and find its active port from the logs."""
    base_path = get_base_path()
    app_path = os.path.join(base_path, "app.py")
    port_pattern = re.compile(r"http://localhost:(\d+)")
    port = None

    def run_streamlit():
        nonlocal port
        streamlit_executable = os.path.join(base_path, "streamlit", "streamlit.exe")

        if not os.path.exists(streamlit_executable):
            logging.error("Streamlit executable not found in the bundled application.")
            raise FileNotFoundError("Streamlit executable not found in the bundled application.")

        process = subprocess.Popen(
            [streamlit_executable, "run", app_path, "--server.headless", "true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in iter(process.stdout.readline, ""):
            logging.debug(line.strip())
            match = port_pattern.search(line)
            if match:
                port = match.group(1)
                break
        process.stdout.close()

    threading.Thread(target=run_streamlit, daemon=True).start()

    timeout = 15  # Wait up to 15 seconds for Streamlit to start
    for _ in range(timeout):
        if port:
            break
        time.sleep(1)

    return f"http://localhost:{port}" if port else None


def install_odbc_driver():
    """Install ODBC driver if not found."""
    base_path = get_base_path()
    driver_installer = os.path.join(base_path, "drivers", "msodbcsql17.msi")
    if os.path.exists(driver_installer):
        try:
            subprocess.check_call(['msiexec', '/i', driver_installer, '/quiet', '/norestart'])
            logging.info("ODBC Driver installed successfully.")
        except subprocess.CalledProcessError as e:
            logging.exception("Failed to install ODBC Driver: %s", e)
            sys.exit("ODBC Driver installation failed. Please install it manually.")
    else:
        logging.error(f"ODBC Driver installer not found at {driver_installer}.")
        sys.exit("ODBC Driver installer not found. Please install it manually.")


def check_odbc_driver():
    """Check if ODBC Driver 17 is installed, otherwise install it."""
    try:
        import pyodbc
        drivers = pyodbc.drivers()
        if "ODBC Driver 17 for SQL Server" not in drivers:
            logging.info("ODBC Driver 17 for SQL Server not found. Installing...")
            install_odbc_driver()
    except ImportError:
        logging.error("pyodbc is not installed.")
        sys.exit("pyodbc is not installed. Please install it before running.")


def try_webview(app_url):
    """
    Attempt to create a WebView window with the EdgeChromium backend.
    If this fails, we will return False and fallback to browser.
    """
    try:
        webview.create_window("Chatbot App", app_url, width=1200, height=800, gui='edgechromium')
        webview.start()
        return True
    except Exception as e:
        logging.exception("Failed to create WebView window: %s", e)
        return False


def main():
    # Check ODBC first
    check_odbc_driver()

    # Start Streamlit
    app_url = start_streamlit_and_get_port()
    if not app_url:
        logging.error("Failed to detect Streamlit port. Using default http://localhost:8501")
        app_url = "http://localhost:8501"

    # Try using WebView
    if not try_webview(app_url):
        # If WebView fails, fallback to default browser
        import webbrowser
        webbrowser.open_new_tab(app_url)


if __name__ == "__main__":
    main()
