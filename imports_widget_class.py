from PyQt5 import QtWidgets as qtw
import pandas as pd
import os
from imports import Ui_imports
from database import DatabaseService
import global_functions as common
from import_service import ImportFile
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigCanvas
from PyQt5.QtCore import Qt
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

db = DatabaseService()
file_import = ImportFile()


class TranStatusGraph(FigCanvas):
    def __init__(self, parent, transactions: pd.DataFrame):
        fig, self.ax = plt.subplots(dpi=120)
        super(TranStatusGraph, self).__init__(fig)
        self.setParent(parent)
        self.figure.set_tight_layout('tight')
        self.figure.autofmt_xdate(rotation=45)
        self.ax = transactions['sys_status'].value_counts()[:20].plot(kind='bar')


class ImportsUI(qtw.QWidget):
    def __init__(self, parent):
        super(ImportsUI, self).__init__(parent)
        self.ui = Ui_imports()
        self.ui.setupUi(self)
        self.entity_id = self.parent().entity_id
        self.ui.btn_new_import.clicked.connect(self.import_new_file)
        self.ui.btn_delete_file.clicked.connect(self.delete_file)
        self.current_import_file_transactions = pd.DataFrame(
            columns=db.import_transaction_headings
        ).set_index("sys_id")
        self.files = db.get_imported_file_summary(self.entity_id)
        self.update_import_tables(True)
        self.ui.tbl_files.clicked.connect(self.file_selected)
        self.ui.btn_tran_search.clicked.connect(self.search_transactions)
        status_menu = qtw.QMenu()
        status_menu.triggered.connect(lambda x: self.update_selected_tran_status(x.text()))
        self.ui.btn_tran_change_status.setMenu(status_menu)
        self.add_menu(db.statuses, status_menu)

    def file_selected(self):
        sel_index = self.ui.tbl_files.selectedItems()[0].row()
        if sel_index >= 0:
            selected_file = self.files.iloc[sel_index, 0]
            self.current_import_file_transactions = db.get_file_import_transactions(
                selected_file,
                self.entity_id
            )
            self.update_import_tables(False)

    def import_new_file(self):
        options = qtw.QFileDialog.Options()
        options |= qtw.QFileDialog.DontUseNativeDialog
        file_path, _ = qtw.QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                                       "Excel Files (*.xl*)", options=options)
        if file_path:
            try:
                self.current_import_file_transactions = file_import.load_new(file_path, self.entity_id)
            except Exception as e:
                qtw.QMessageBox.about(self, "Error!", str(e))
            else:
                self.update_import_tables(True)
        pass

    def delete_file(self):
        sel_index = self.ui.tbl_files.selectedItems()[0].row()
        self.ui.tbl_files.setCurrentItem(self.ui.tbl_files.selectedItems()[0])
        if sel_index >= 0:
            selected_file = self.files.iloc[sel_index, 0]
            choice = qtw.QMessageBox.question(
                self,
                "Alert!",
                f"Are you sure you want to delete {selected_file}, and all associated transactions!",
                qtw.QMessageBox.Yes | qtw.QMessageBox.No
            )
            if choice == qtw.QMessageBox.Yes:
                db.delete_file_import_transactions(selected_file, self.entity_id)
                self.current_import_file_transactions = pd.DataFrame(
                    columns=db.import_transaction_headings
                ).set_index("sys_id")
                self.update_import_tables(True)
        else:
            qtw.QMessageBox.about(self, "Info!", "Please select a file to delete")

    def update_import_tables(self, update_file: bool):
        common.pandas_to_table_widget(self.current_import_file_transactions, self.ui.tbl_transactions)
        if update_file:
            self.files = db.get_imported_file_summary(self.entity_id)
            common.pandas_to_table_widget(self.files, self.ui.tbl_files)
            self.ui.tbl_files.selectRow(0)
        if len(self.current_import_file_transactions) > 0:
            for i in range(self.ui.layout_graphs.count()):
                self.ui.layout_graphs.itemAt(i).widget().deleteLater()
            chart = TranStatusGraph(self, self.current_import_file_transactions)
            self.ui.layout_graphs.addWidget(chart)

    def search_transactions(self):
        s: str = self.ui.txt_tran_search.text()
        # Clear current selection.
        self.ui.tbl_transactions.setCurrentItem(None)
        if not s:
            # Empty string, don't search.
            return
        matching_items = self.ui.tbl_transactions.findItems(s, Qt.MatchContains)
        if matching_items:
            # We have found something.
            item = matching_items[0]  # Take the first.
            self.ui.tbl_transactions.setCurrentItem(item)

    def add_menu(self, data, menu_obj):
        if isinstance(data, dict):
            for k, v in data.items():
                sub_menu = qtw.QMenu(k, menu_obj)
                menu_obj.addMenu(sub_menu)
                self.add_menu(v, sub_menu)
        elif isinstance(data, list):
            for element in data:
                self.add_menu(element, menu_obj)
        else:
            action = menu_obj.addAction(data)
            action.setIconVisibleInMenu(False)

    def update_selected_tran_status(self, status: str):
        selected_transactions = self.ui.tbl_transactions.selectedItems()
        show_warning = False
        if len(selected_transactions) == 0:
            qtw.QMessageBox.about(self, "Info!", "No transactions selected")
            return
        if status == "NEW":
            show_warning = True
        if show_warning:
            choice = qtw.QMessageBox.question(
                self,
                "Alert!",
                "Are you sure you want to set the transactions to NEW this can result in duplicate processing",
                qtw.QMessageBox.Yes | qtw.QMessageBox.No
            )
            if choice == qtw.QMessageBox.No:
                return
        transaction_ids = []
        for tran in selected_transactions:
            i = tran.row()
            column = self.current_import_file_transactions.columns.get_loc("sys_id")
            current_status = self.current_import_file_transactions.at[i, 'sys_status']
            self.current_import_file_transactions.at[i, "sys_prev_status"] = current_status
            self.current_import_file_transactions.at[i, 'sys_status'] = status
            transaction_ids.append(self.current_import_file_transactions.iloc[i, column])
        unique_tran_ids = common.unique(transaction_ids)
        db.update_transactions_status(unique_tran_ids, status, self.entity_id)
        self.update_import_tables(False)
