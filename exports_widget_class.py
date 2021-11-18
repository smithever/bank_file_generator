from exports import Ui_Exports
from database import DatabaseService
from PyQt5 import QtWidgets as qtw
import os
from suppliers import Ui_Suppliers
import global_functions as common
import pandas as pd
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigCanvas
import matplotlib.pyplot as plt

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

db = DatabaseService()


class ExportsUI(qtw.QWidget):
    def __init__(self, parent):
        super(ExportsUI, self).__init__(parent)
        self.ui = Ui_Exports()
        self.ui.setupUi(self)
        self.entity_id = self.parent().entity_id
        self.export_files = db.get_exported_file_summary(self.entity_id)
        self.export_ready_transactions = db.get_export_ready_transactions(self.entity_id)
        self.update_tables()
        self.ui.btn_search.clicked.connect(self.search_transactions)
        self.ui.btn_export_all.clicked.connect(self.clicked_export_all)
        self.ui.btn_export_selected.clicked.connect(self.clicked_export_selected)

    def update_tables(self):
        if len(self.export_files) > 0:
            common.pandas_to_table_widget(self.export_files, self.ui.table_export_files)
        if len(self.export_ready_transactions) > 0:
            common.pandas_to_table_widget(self.export_ready_transactions, self.ui.table_transactions)

    def search_transactions(self):
        s: str = self.ui.txt_search.text()
        # Clear current selection.
        self.ui.table_transactions.setCurrentItem(None)
        if not s:
            # Empty string, don't search.
            return
        matching_items = self.ui.table_transactions.findItems(s, Qt.MatchContains)
        if matching_items:
            # We have found something.
            item = matching_items[0]  # Take the first.
            self.ui.table_transactions.setCurrentItem(item)

    def clicked_export_all(self):
        self.export_transactions(self.export_ready_transactions)
        pass

    def clicked_export_selected(self):
        selected_transactions = self.ui.table_transactions.selectedItems()
        if len(selected_transactions) == 0:
            qtw.QMessageBox.about(self, "Info!", "No transactions selected")
            return
        indexes = common.unique([tran.row() for tran in selected_transactions])
        self.export_transactions(self.export_ready_transactions.iloc[indexes])
        pass

    def export_transactions(self, export_trans: pd.DataFrame):
        options = qtw.QFileDialog.Options()
        options |= qtw.QFileDialog.DontUseNativeDialog
        dialog = qtw.QFileDialog()
        dialog.setDefaultSuffix("csv")
        file_path, _ = dialog.getSaveFileName(self, "QFileDialog.getOpenFileName()",
                                              "",
                                              "CSV (*.csv)", options=options)
        if file_path:
            if not str(file_path).endswith(".csv"):
                file_path = file_path.__add__(".csv")
                entity = db.get_single_entity(self.entity_id)
                export_trans = pd.DataFrame()
                if entity.at[0, "bank_name"] == "FNB":
                    pass
                if entity.at[0, "bank_name"] == "Nedbank":
                    export_trans = db.get_export_transaction_nedbank(self.entity_id, export_trans['sys_id'].tolist())
                if len(export_trans) > 0:
                    if len(export_trans.loc[export_trans['to_account_number'] == ""]) > 0:
                        qtw.QMessageBox.about(f"Please ensure that 'to_account_number' for suppliers is not empty'")
                        return
                    if len(export_trans.loc[export_trans['to_branch_code'] == ""]) > 0:
                        qtw.QMessageBox.about(f"Please ensure that 'to_branch_code' for suppliers is not empty'")
                        return
                    file_name = file_path.split('/')[-1]
                    db.update_transactions_exported(self.entity_id, export_trans['sys_id'].tolist(), file_name)
                    export_trans.to_csv(f"./exports/{file_name}")
                    export_trans.to_csv(file_path)
                    qtw.QMessageBox.about(f"File exported")

                    ## export the dataframe to a csv file
