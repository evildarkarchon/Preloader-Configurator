from pathlib import Path

from lxml import etree
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class XMLModifier(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Preloader Configurator")

        # Create layout
        self.main_layout = QVBoxLayout()

        # Create form for static elements
        self.form_layout = QFormLayout()

        # Load method (always visible)
        self.load_method_combo = QComboBox()
        self.load_method_combo.addItems(["ImportAddressHook", "OnThreadAttach", "OnProcessAttach"])
        self.load_method_combo.setToolTip(
            "Load method for xSE plugins, 'ImportAddressHook' by default. Don't change unless required."
        )
        self.load_method_combo.setEnabled(False)
        self.form_layout.addRow("Load Method:", self.load_method_combo)

        # Advanced Options section (initially hidden)
        self.original_library_label = QLabel("Original Library:")
        self.original_library_edit = QLineEdit()
        self.original_library_edit.setToolTip(
            "If you have a mod that uses the same DLL as the preloader, you can rename the DLL from your mod and set its new name here. DO NOT CHANGE unless you know what you're doing."
        )
        self.form_layout.addRow(self.original_library_label, self.original_library_edit)

        self.import_library_label = QLabel("ImportAddressHook Library Name:")
        self.import_library_edit = QLineEdit()
        self.import_library_edit.setToolTip("The name of a DLL that contains the function to hook. DO NOT CHANGE unless you know what you're doing.")
        self.form_layout.addRow(self.import_library_label, self.import_library_edit)

        self.import_function_label = QLabel("ImportAddressHook Function Name:")
        self.import_function_edit = QLineEdit()
        self.import_function_edit.setToolTip("The function to hook. Must be exported from the specified DLL. DO NOT CHANGE unless you know what you're doing.")
        self.form_layout.addRow(self.import_function_label, self.import_function_edit)

        self.thread_number_label = QLabel("OnThreadAttach Thread Number:")
        self.thread_number_edit = QLineEdit()
        self.thread_number_edit.setToolTip(
            "Specifies the thread number that will trigger the plugin loading. Must be a positive number."
        )
        self.form_layout.addRow(self.thread_number_label, self.thread_number_edit)

        self.install_exception_label = QLabel("Install Exception Handler:")
        self.install_exception_combo = QComboBox()
        self.install_exception_combo.addItems(["true", "false"])
        self.install_exception_combo.setToolTip(
            "Usually vectored exception handler is installed right before plugins loading and removed after it's done."
        )
        self.form_layout.addRow(self.install_exception_label, self.install_exception_combo)

        self.keep_exception_label = QLabel("Keep Exception Handler:")
        self.keep_exception_combo = QComboBox()
        self.keep_exception_combo.addItems(["false", "true"])
        self.keep_exception_combo.setToolTip(
            "Allows you to keep the exception handler if you need more information in case the host process crashes."
        )
        self.form_layout.addRow(self.keep_exception_label, self.keep_exception_combo)

        self.load_delay_label = QLabel("Load Delay (ms):")
        self.load_delay_edit = QLineEdit()
        self.load_delay_edit.setToolTip(
            "Sets the amount of time the preloader will pause the loading thread, in milliseconds. 0 means no delay."
        )
        self.form_layout.addRow(self.load_delay_label, self.load_delay_edit)

        self.hook_delay_label = QLabel("Hook Delay (ms):")
        self.hook_delay_edit = QLineEdit()
        self.hook_delay_edit.setToolTip(
            "HookDelay works only for 'ImportAddressHook' methods and additionally waits before hooking the required function."
        )
        self.form_layout.addRow(self.hook_delay_label, self.hook_delay_edit)

        # Processes section
        self.processes_label = QLabel("Processes:")
        self.processes_form_layout = QVBoxLayout()
        self.form_layout.addRow(self.processes_label, self.processes_form_layout)
        self.process_items: list[tuple[QLabel, QComboBox]] = []
        self.add_process_item("Fallout3.exe", False)
        self.add_process_item("FalloutNV.exe", False)
        self.add_process_item("Fallout4.exe", True)
        self.add_process_item("TESV.exe", True)
        self.add_process_item("SkyrimSE.exe", True)

        # Advanced Options Checkbox
        self.advanced_options_checkbox = QCheckBox("Show Advanced Options")
        self.advanced_options_checkbox.stateChanged.connect(self.toggle_advanced_options)
        self.main_layout.addWidget(self.advanced_options_checkbox)

        # Buttons
        self.open_button = QPushButton("Open Configuration File")
        self.open_button.clicked.connect(self.open_xml)
        self.main_layout.addWidget(self.open_button)

        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_xml)
        self.save_as_button = QPushButton("Save As")
        self.save_as_button.clicked.connect(self.save_as_xml)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.save_as_button)
        self.main_layout.addLayout(button_layout)

        # Set the layout
        self.main_layout.addLayout(self.form_layout)
        self.setLayout(self.main_layout)

        # Placeholder for the XML tree and file path
        self.xml_tree = None
        self.opened_file_path: str | None = None

        # Initially disable all widgets except the Open button
        self.set_widgets_enabled(False)
        self.open_button.setEnabled(True)

        # Initially hide advanced options and adjust window size
        self.toggle_advanced_options()

    def add_process_item(self, name: str, allow: bool) -> None:
        """Helper method to add process editing fields."""
        process_layout = QHBoxLayout()
        name_label = QLabel(name)
        allow_combo = QComboBox()
        allow_combo.addItems(["true", "false"])
        allow_combo.setCurrentText("true" if allow else "false")
        allow_combo.setToolTip(
            "Only processes in this list with 'Allow' set to 'true' will be allowed to preload."
        )

        process_layout.addWidget(name_label)
        process_layout.addWidget(allow_combo)
        self.processes_form_layout.addLayout(process_layout)

        # Store the widgets for later updates
        self.process_items.append((name_label, allow_combo))

    def set_widgets_enabled(self, enabled: bool) -> None:
        """Enable or disable all input widgets."""
        for widget in [
            self.load_method_combo, self.original_library_edit, self.import_library_edit, self.import_function_edit,
            self.thread_number_edit, self.install_exception_combo, self.keep_exception_combo,
            self.load_delay_edit, self.hook_delay_edit, self.save_button, self.save_as_button
        ]:
            widget.setEnabled(enabled)
        # Also enable or disable all process items
        for _label, combo in self.process_items:
            combo.setEnabled(enabled)

    def toggle_advanced_options(self) -> None:
        """Show or hide advanced options and adjust window size."""
        is_checked = self.advanced_options_checkbox.isChecked()

        # Hide or show widgets
        for widget in [
            self.original_library_label, self.original_library_edit, self.import_library_label, self.import_library_edit,
            self.import_function_label, self.import_function_edit, self.thread_number_label, self.thread_number_edit,
            self.install_exception_label, self.install_exception_combo, self.keep_exception_label, self.keep_exception_combo,
            self.load_delay_label, self.load_delay_edit, self.hook_delay_label, self.hook_delay_edit, self.processes_label
        ]:
            widget.setVisible(is_checked)

        # Also show or hide all process items
        for label, combo in self.process_items:
            label.setVisible(is_checked)
            combo.setVisible(is_checked)

        # Resize the window based on the content
        self.adjustSize()

        if not is_checked:
            # Explicitly set the window size smaller when advanced options are hidden
            self.resize(self.sizeHint())

    def open_xml(self) -> None:
        """Load the XML file and populate the form with values."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open XML File", "", "XML Files (*.xml)")
        if not file_path:
            return

        xml_content = Path(file_path).read_bytes()

        # Parse the XML content
        parser = etree.XMLParser()
        self.xml_tree = etree.XML(xml_content, parser)

        # Store the path to save the file back to
        self.opened_file_path = file_path

        # Populate fields
        self.populate_fields_with_values()

        # Enable all widgets once the file is loaded
        self.set_widgets_enabled(True)

    def populate_fields_with_values(self) -> None:
        """Populate the form fields with values from the XML."""
        if self.xml_tree is not None:
            original_library = self.xml_tree.find(".//OriginalLibrary")
            if original_library is not None:
                self.original_library_edit.setText(original_library.text)

            load_method = self.xml_tree.find(".//LoadMethod")
            if load_method is not None:
                self.load_method_combo.setCurrentText(load_method.attrib.get("Name", "ImportAddressHook"))

            import_address_hook = self.xml_tree.find(".//ImportAddressHook")
            if import_address_hook is not None:
                self.import_library_edit.setText(import_address_hook.findtext("LibraryName"))
                self.import_function_edit.setText(import_address_hook.findtext("FunctionName"))

            on_thread_attach = self.xml_tree.find(".//OnThreadAttach")
            if on_thread_attach is not None:
                self.thread_number_edit.setText(on_thread_attach.findtext("ThreadNumber"))

            install_exception_element = self.xml_tree.find(".//InstallExceptionHandler")
            install_exception = install_exception_element.text if install_exception_element is not None else "false"
            self.install_exception_combo.setCurrentText(install_exception)

            keep_exception_element = self.xml_tree.find(".//KeepExceptionHandler")
            keep_exception = keep_exception_element.text if keep_exception_element is not None else "false"
            self.keep_exception_combo.setCurrentText(keep_exception)

            load_delay = self.xml_tree.findtext(".//LoadDelay", "0")
            self.load_delay_edit.setText(load_delay)
            self.hook_delay_edit.setText(self.xml_tree.findtext(".//HookDelay", "0"))

        for name_label, combo in self.process_items:
            if self.xml_tree is not None:
                item = self.xml_tree.find(f".//Processes/Item[@Name='{name_label.text()}']")
                if item is not None:
                    combo.setCurrentText(item.attrib.get("Allow", "false"))

    def save_xml(self) -> None:
        """Save the modified XML back to the original file."""
        if self.xml_tree is None or self.opened_file_path is None:
            return

        self.update_xml_values()

        Path(self.opened_file_path).write_bytes(etree.tostring(self.xml_tree, pretty_print=True, encoding="utf-8"))  # type: ignore[reportCallIssue]

    def save_as_xml(self) -> None:
        """Save the modified XML to a new file."""
        if self.xml_tree is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save XML File As", "", "XML Files (*.xml)")
        if not file_path:
            return

        self.update_xml_values()

        Path(file_path).write_bytes(etree.tostring(self.xml_tree, pretty_print=True, encoding="utf-8"))  # type: ignore[reportCallIssue]

    def update_xml_values(self) -> None:
        """Update the XML tree with values from the form."""
        if self.xml_tree is not None:
            original_library = self.xml_tree.find(".//OriginalLibrary")
            if original_library is not None:
                original_library.text = self.original_library_edit.text()

        if self.xml_tree is not None:
            load_method = self.xml_tree.find(".//LoadMethod")
            if load_method is not None:
                load_method.attrib["Name"] = self.load_method_combo.currentText()

        if self.xml_tree is not None:
            import_address_hook = self.xml_tree.find(".//ImportAddressHook")
            if import_address_hook is not None:
                library_name = import_address_hook.find("LibraryName")
                if library_name is not None:
                    library_name.text = self.import_library_edit.text()
                function_name = import_address_hook.find("FunctionName")
                if function_name is not None:
                    function_name.text = self.import_function_edit.text()

        if self.xml_tree is not None:
            on_thread_attach = self.xml_tree.find(".//OnThreadAttach")
            if on_thread_attach is not None:
                thread_number = on_thread_attach.find("ThreadNumber")
                if thread_number is not None:
                    thread_number.text = self.thread_number_edit.text()

        if self.xml_tree is not None:
            install_exception_element = self.xml_tree.find(".//InstallExceptionHandler")
            if install_exception_element is not None:
                install_exception_element.text = self.install_exception_combo.currentText()
            keep_exception_element = self.xml_tree.find(".//KeepExceptionHandler")
            if keep_exception_element is not None:
                keep_exception_element.text = self.keep_exception_combo.currentText()
            load_delay_element = self.xml_tree.find(".//LoadDelay")
            if load_delay_element is not None:
                load_delay_element.text = self.load_delay_edit.text()
            hook_delay_element = self.xml_tree.find(".//HookDelay")
            if hook_delay_element is not None:
                hook_delay_element.text = self.hook_delay_edit.text()

        for name_label, combo in self.process_items:
            if self.xml_tree is not None:
                item = self.xml_tree.find(f".//Processes/Item[@Name='{name_label.text()}']")
                if item is not None:
                    item.attrib["Allow"] = combo.currentText()

if __name__ == "__main__":
    app = QApplication([])

    window = XMLModifier()
    window.show()

    app.exec()
