import sys
from database import DatabaseService
from PyQt5 import QtWidgets as qtw
from main_app import Ui_Main_App
import os
from import_service import ImportFile
from entity_widget_classes import EditEntity, SelectEntity
from imports_widget_class import ImportsUI
from suppliers_widget_class import SuppliersUI
from exports_widget_class import ExportsUI
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


db = DatabaseService()
file_import = ImportFile()


class MainAppUI(qtw.QWidget):
    def __init__(self, parent):
        super(MainAppUI, self).__init__(parent)
        self.ui = Ui_Main_App()
        self.ui.setupUi(self)
        self.entity_id = self.parent().entity_id
        self.edit_w = EditEntity()
        self.entities = db.get_entities()
        self.edit_w.edit(self.entities, self.parent().entity_id)
        self.ui.layout_edit_entity.addWidget(self.edit_w)
        self.imports_w = ImportsUI(self)
        self.ui.layout_imports.addWidget(self.imports_w)
        self.suppliers_w = SuppliersUI(self)
        self.ui.layout_suppliers.addWidget(self.suppliers_w)
        self.exports_w = ExportsUI(self)
        self.ui.layouts_exports.addWidget(self.exports_w)
        self.ui.tab_Widget.setCurrentIndex(0)
        self.ui.tab_Widget.tabBarClicked.connect(self.handle_tabbar_clicked)

    def handle_tabbar_clicked(self, index):
        print(index)
        if index == 1:
            self.imports_w.update_import_tables(True)
        if index == 2:
            self.suppliers_w.update_suppliers_table()
            self.suppliers_w.update_transaction_table()
        if index == 3:
            self.exports_w.update_tables()


class MainApp(qtw.QMainWindow):
    def __init__(self):
        super(MainApp, self).__init__()
        self.entity_id = ""
        self.entities = db.get_entities()
        self.setObjectName("Bank File Generator")
        self.resize(309, 480)
        self.central_widget = qtw.QWidget(self)
        self.setCentralWidget(SelectEntity(self))
        self.show()

    def load(self, entity_id):
        print(f"loading main app: {entity_id}")
        self.entity_id = entity_id
        self.resize(800, 480)
        self.setCentralWidget(MainAppUI(self))
        self.showMaximized()

    def show_message(self, message: str):
        qtw.QMessageBox.about(self, message)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    widget = MainApp()
    sys.exit(app.exec_())





# TODO: https://businessbanking.nedsecure.co.za/TrainingPages/steps/Import%20batch%20paym%20CSV%20format/Import%20batch%20paym%20CSV%20format.htm#
# TODO: https://www.mailers.fnbweb.co.za/Campaigns/Mailers/ClientManagement/2015/Oct2015_Client%20Mailer/Payment%20CSV%20Imports%20Help%20Guide%20-%20South%20Africa_Oct%202015.pdf