from typing import Optional
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


class DialogService:
    """Encapsulates system file dialogs and alert popups."""

    @staticmethod
    def open_raw_file(parent: Optional[QWidget] = None) -> Optional[str]:
        file_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Select RAW Image",
            "",
            "Canon RAW Files (*.CR2);;All Files (*)"
        )
        return file_path if file_path else None

    @staticmethod
    def save_jpeg_file(parent: Optional[QWidget] = None, default_name: str = "output.jpg") -> Optional[str]:
        save_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Export Image as JPEG",
            default_name,
            "JPEG Image (*.jpg *.jpeg)"
        )
        return save_path if save_path else None

    @staticmethod
    def confirm_discard_changes(parent: Optional[QWidget] = None) -> bool:
        reply = QMessageBox.question(
            parent,
            "Unsaved Changes",
            "There are unsaved adjustments on the current image. Do you want to discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def show_error(title: str, message: str, parent: Optional[QWidget] = None) -> None:
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def show_info(title: str, message: str, parent: Optional[QWidget] = None) -> None:
        QMessageBox.information(parent, title, message)