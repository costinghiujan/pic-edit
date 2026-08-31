from typing import Optional
from PySide6.QtCore import QObject, QTimer

from src.engine import ImageEngine
from src.utils import DialogService
from src.widgets.image_canvas import ImageCanvas
from src.widgets.sidebar import Sidebar


class EditorController(QObject):
    """
    Coordinates interactions between ImageEngine, ImageCanvas, and Sidebar.
    Handles I/O workflows, rendering throttle, and Before/After states.
    """

    def __init__(self, engine: ImageEngine, canvas: ImageCanvas, sidebar: Sidebar, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.canvas = canvas
        self.sidebar = sidebar
        self._parent_widget = parent

        # 60 FPS Throttling Timer
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(16)
        self._render_timer.timeout.connect(self.execute_pipeline_update)

        # Wire up sidebar signals
        self.sidebar.adjustmentsChanged.connect(self.schedule_render)

        self.canvas.cropBoxChanged.connect(self._on_crop_box_changed)
        self.sidebar.crop_section.aspectRatioChanged.connect(self.canvas.set_aspect_ratio)

    def _on_crop_box_changed(self) -> None:
        rect = self.canvas.get_crop_rect()
        self.sidebar.crop_section.set_crop_rect(rect)
        # No physical render slice needed while dragging inside crop tab

    def schedule_render(self) -> None:
        if self.engine.has_image and not self._render_timer.isActive():
            self._render_timer.start()

    def execute_pipeline_update(self) -> None:
        active_filters = self.sidebar.get_active_filters()
        is_modified = self.sidebar.is_modified()

        preview = self.engine.update_pipeline(active_filters, is_modified=is_modified)
        self.canvas.set_numpy_image(preview)
        self.sidebar.update_histograms(preview)

    def import_image(self) -> bool:
        if self.engine.is_modified and not DialogService.confirm_discard_changes(self._parent_widget):
            return False

        file_path = DialogService.open_raw_file(self._parent_widget)
        if not file_path:
            return False

        if self.engine.load(file_path):
            self.sidebar.reset_all()
            self.sidebar.set_enabled(True)

            preview = self.engine.update_pipeline([], is_modified=False)
            self.canvas.set_numpy_image(preview)
            self.sidebar.update_histograms(preview)
            return True
        else:
            DialogService.show_error("Error", f"Failed to load image: {file_path}", self._parent_widget)
            return False

    def show_original_preview(self) -> bool:
        """Switches canvas to original base buffer (Before mode)."""
        if self.engine.has_image and self.engine._preview_base is not None:
            self.canvas.set_numpy_image(self.engine._preview_base)
            return True
        return False

    def restore_edited_preview(self) -> None:
        """Restores current edited buffer (After mode)."""
        if self.engine.has_image and self.engine._current_preview is not None:
            self.canvas.set_numpy_image(self.engine._current_preview)

    def confirm_close(self) -> bool:
        if self.engine.is_modified:
            return DialogService.confirm_discard_changes(self._parent_widget)
        return True

    def set_workspace_tab(self, index: int) -> None:
        """Called when user switches tabs on the ActivityBar."""
        # 1. If we were in Crop tab (index 1), grab the latest crop rectangle from canvas
        if self.sidebar.stack.currentIndex() == 1:
            current_crop = self.canvas.get_crop_rect()
            self.sidebar.crop_section.set_crop_rect(current_crop)

        # 2. Switch tab in UI
        self.sidebar.set_current_tab(index)
        is_crop_tab = (index == 1)

        # 3. Notify crop section
        self.sidebar.crop_section.set_workspace_active(is_crop_tab)

        # 4. Toggle canvas interactive overlay
        self.canvas.set_crop_mode(
            enabled=is_crop_tab,
            aspect_ratio=self.sidebar.crop_section._active_ratio
        )

        # 5. Trigger immediate pipeline re-render (commits or uncommits the physical crop)
        self.execute_pipeline_update()

    def export_image(self) -> None:
        if not self.engine.has_image:
            return

        # Ensure latest crop rectangle is saved if user exports directly while inside Crop tab
        if self.sidebar.stack.currentIndex() == 1:
            self.sidebar.crop_section.set_crop_rect(self.canvas.get_crop_rect())

        # Ensure crop section is set to export mode (applies physical crop slice)
        self.sidebar.crop_section._is_active_workspace = False

        save_path = DialogService.save_jpeg_file(self._parent_widget)
        if not save_path:
            return

        # Collect full active pipeline (Tone adjustments + Curves + Geometry)
        active_filters = self.sidebar.get_active_filters()
        self.engine._filters = active_filters

        if self.engine.export_jpeg(save_path):
            DialogService.show_info("Export Complete", f"Image exported successfully to:\n{save_path}", self._parent_widget)
        else:
            DialogService.show_error("Export Failed", "Could not export image. Check application logs.", self._parent_widget)