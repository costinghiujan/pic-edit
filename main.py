import sys
import logging
from PySide6.QtWidgets import QApplication

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

def run_app():
    logging.info("Starting Photo Editor application...")
    try:
        app = QApplication(sys.argv)
        logging.info("QApplication initialized.")

        from src.ui_main import MainWindow
        logging.info("MainWindow class imported successfully.")

        window = MainWindow()
        logging.info("MainWindow instance created.")

        window.show()
        logging.info("Main window displayed. Entering Qt event loop.")

        sys.exit(app.exec())
    except Exception as err:
        logging.critical("Application crashed during startup: %s", err, exc_info=True)

if __name__ == "__main__":
    run_app()