from functools import partial

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


class ReadOnlyDelegate(qtw.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        print('createEditor event fired')
        return


class TranStatusGraph(FigCanvas):
    def __init__(self, parent, transactions: pd.DataFrame):
        fig, self.ax = plt.subplots(dpi=120)
        super(TranStatusGraph, self).__init__(fig)
        self.setParent(parent)
        self.figure.set_tight_layout('tight')
        self.figure.autofmt_xdate(rotation=45)
        self.ax = transactions['sys_status'].value_counts()[:20].plot(kind='bar')


class SuppliersUI(qtw.QWidget):
    def __init__(self, parent):
        super(SuppliersUI, self).__init__(parent)
        self.entity_id = self.parent().entity_id
        self.ui = Ui_Suppliers()
        self.ui.setupUi(self)
        self.suppliers = pd.DataFrame()
        self.update_suppliers_table()
        delegate = ReadOnlyDelegate(self.ui.tbl_suppliers)
        self.ui.tbl_suppliers.setItemDelegateForColumn(0, delegate)
        self.ui.tbl_suppliers.setItemDelegateForColumn(1, delegate)
        self.ui.tbl_suppliers.setItemDelegateForColumn(6, delegate)
        self.ui.tbl_suppliers.cellChanged[int, int].connect(self.update_suppliers)
        self.current_supplier_transactions = pd.DataFrame(
            columns=db.import_transaction_headings
        ).set_index("sys_id")
        self.ui.tbl_suppliers.clicked.connect(self.supplier_selected)
        self.ui.btn_tran_search.clicked.connect(self.search_transactions)
        status_menu = qtw.QMenu()
        status_menu.triggered.connect(lambda x: self.update_selected_tran_status(x.text()))
        self.ui.btn_status_change.setMenu(status_menu)
        self.add_menu(db.statuses, status_menu)

    def update_suppliers_table(self):
        self.suppliers = db.get_suppliers_summary(self.entity_id)
        if len(self.suppliers) > 0:
            combo_box_options = ["0.Public Recipient", "1.Current Account", "2.Savings Account", "3.Transmission Account", "4.Bond Account", "5.Subscription Share Account"]
            common.pandas_to_table_widget(self.suppliers, self.ui.tbl_suppliers)
            i = self.ui.tbl_suppliers.rowCount()
            while i > 0:
                combo = qtw.QComboBox()
                combo.currentTextChanged.connect(partial(self.update_to_account, i - 1))
                for t in combo_box_options:
                    combo.addItem(t)
                combo.setCurrentText(self.suppliers.at[i - 1, "to_account_type"])
                self.ui.tbl_suppliers.setCellWidget(i - 1, 6, combo)
                i = i-1

    def update_to_account(self, row):
        widget = self.ui.tbl_suppliers.cellWidget(row, 6)
        if isinstance(widget, qtw.QComboBox):
            text = widget.currentText()
            print(text)
            index = self.suppliers.columns.get_loc("to_account_type")
            self.suppliers.iloc[row, index] = text
            db.save_suppliers_summary(self.suppliers, self.entity_id)

    def update_suppliers(self, row, column):
        text = self.ui.tbl_suppliers.item(row, column).text()
        self.suppliers.iloc[row, column] = text
        db.save_suppliers_summary(self.suppliers, self.entity_id)

    def supplier_selected(self):
        sel_index = self.ui.tbl_suppliers.selectedItems()[0].row()
        if sel_index >= 0:
            selected_supplier_code = self.suppliers.iloc[sel_index, 0]
            self.current_supplier_transactions = db.get_supplier_transactions(
                selected_supplier_code,
                self.entity_id
            )
            self.update_transaction_table()

    def update_transaction_table(self):
        common.pandas_to_table_widget(self.current_supplier_transactions, self.ui.tbl_transactions)
        if len(self.current_supplier_transactions) > 0:
            for i in range(self.ui.layout_graphs.count()):
                self.ui.layout_graphs.itemAt(i).widget().deleteLater()
            chart2 = TranStatusGraph(self, self.current_supplier_transactions)
            self.ui.layout_graphs.addWidget(chart2)

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
            column = self.current_supplier_transactions.columns.get_loc("sys_id")
            current_status = self.current_supplier_transactions.sys_status.iloc[i]
            self.current_supplier_transactions.at[i, "sys_prev_status"] = current_status
            self.current_supplier_transactions.at[i, 'sys_status'] = status
            transaction_ids.append(self.current_supplier_transactions.iloc[i, column])
        unique_tran_ids = common.unique(transaction_ids)
        db.update_transactions_status(unique_tran_ids, status, self.entity_id)
        self.update_transaction_table()

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
