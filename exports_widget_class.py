import datetime

from exports import Ui_Exports
from database import DatabaseService
from PyQt5 import QtWidgets as qtw
import os
import global_functions as common
import pandas as pd
from PyQt5.QtCore import Qt
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

db = DatabaseService()

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class ExportsUI(qtw.QWidget):
    def __init__(self, parent):
        super(ExportsUI, self).__init__(parent)
        self.ui = Ui_Exports()
        self.ui.setupUi(self)
        self.entity_id = self.parent().entity_id
        self.export_files = pd.DataFrame
        self.export_ready_transactions = pd.DataFrame
        self.update_tables()
        self.ui.btn_search.clicked.connect(self.search_transactions)
        self.ui.btn_export_all.clicked.connect(self.clicked_export_all)
        self.ui.btn_export_selected.clicked.connect(self.clicked_export_selected)
        self.ui.table_export_files.clicked.connect(self.file_selected)

    def file_selected(self):
        sel_index = self.ui.table_export_files.selectedItems()[0].row()
        if sel_index >= 0:
            selected_file = self.export_files.at[sel_index, "File Name"]
            file_path = str(os.path.join(ROOT_DIR, f"csv_exports/{selected_file}"))
            file_data = pd.read_csv(file_path)
            common.pandas_to_table_widget(file_data, self.ui.table_file_transactions)

    def update_tables(self):
        self.export_files = db.get_exported_file_summary(self.entity_id)
        self.export_ready_transactions = db.get_export_ready_transactions(self.entity_id)
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

    def export_transactions(self, pde: pd.DataFrame):
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
                file_name = str(file_path).split("/")[-1]
                export_trans = pd.DataFrame()
                if file_name in self.export_files.values:
                    qtw.QMessageBox.about(self, "Info!", f"File name {file_name} already used. Please use a different "
                                                         f"file name")
                    return
                if entity.at[0, "bank_name"] == "FNB":
                    export_trans = db.get_export_transaction_fnb(self.entity_id, pde['sys_id'].tolist())
                if entity.at[0, "bank_name"] == "Nedbank":
                    export_trans = db.get_export_transaction_nedbank(self.entity_id, pde['sys_id'].tolist())
                if len(export_trans) > 0:
                    root_file_name = str(os.path.join(ROOT_DIR, f"csv_exports/{file_name}"))
                    if len(export_trans.loc[export_trans['to_account_number'] == ""]) > 0:
                        qtw.QMessageBox.about(self, "Info!", f"Please ensure that 'to_account_number' for suppliers "
                                                             f"is not empty'")
                        db.update_transactions_status(pde['sys_id'].tolist(), "NEW", self.entity_id)
                        return
                    if len(export_trans.loc[export_trans['to_branch_code'] == ""]) > 0:
                        qtw.QMessageBox.about(self, "Info!", f"Please ensure that 'to_branch_code' for suppliers is "
                                                             f"not empty'")
                        db.update_transactions_status(pde['sys_id'].tolist(), "NEW", self.entity_id)
                        return
                    try:
                        db.update_transactions_exported(self.entity_id, pde['sys_id'].tolist(), file_name)
                        export_trans.to_csv(root_file_name, index=False)
                        if entity.at[0, "bank_name"] == "Nedbank":
                            export_trans.to_csv(file_path, index=False)
                        if entity.at[0, "bank_name"] == "FNB":
                            generate_bankserv_fwf(self.entity_id, export_trans, file_path)
                    except RuntimeError as ex:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        if os.path.exists(root_file_name):
                            os.remove(root_file_name)
                        db.update_transactions_status(pde['sys_id'].tolist(), "NEW", self.entity_id)
                        qtw.QMessageBox.about(self, "Info!", f"Export has failed: {ex}")
                    else:
                        db.update_transactions_status(pde['sys_id'].tolist(), "EXPORTED", self.entity_id)
                        self.update_tables()
                        qtw.QMessageBox.about(self, "Info!", "File exported")
                    return


def generate_bankserv_fwf(entity_id, export_trans: pd.DataFrame, file_path):
    file = open(file_path, "w+")
    entity = db.get_single_entity(entity_id)
    # INSTALLATION HEADER RECORD
    ihr = f"02{filler(178)}"
    file.write(f"{ihr}\r\n")

    # USER HEADER RECORD
    uhr = f"04{filler(178)}"
    file.write(f"{uhr}\r\n")

    # CONTRA RECORD
    from_branch_code = entity.at[0, "branch_code"]  # TODO: need to add this to entity FUCK!!
    from_account_no = entity.at[0, "account_number"]
    action_date = datetime.datetime.now().strftime('%y%m%d')  #YYMMDD
    cr = f"12{from_branch_code[0:6]: >6}{from_account_no[0:11]: >11}{filler(39)}{action_date[0:6]: >6}{filler(116)}"
    file.write(f"{cr}\r\n")

    # STANDARD TRANSACTION RECORD
    for i in export_trans.index:
        user_sequence_number = "000001"
        to_branch_code = str(export_trans.at[i, "to_branch_code"])
        to_account_number = str(export_trans.at[i, "to_account_number"])
        to_type_of_account = str(export_trans.at[i, "to_account_type"])
        amount = str(export_trans.at[i, "amount"])  # This must be expressed in cents
        to_statement_description = str(export_trans.at[i, "to_statement_description"])
        to_account_holder_name = str(export_trans.at[i, "to_account_holder_name"])
        non_standard_account_number = filler(20)  # To be used if the recipient account number is more than 11 chars
        if len(to_account_number) > 11:
            non_standard_account_number = to_account_number
        std_tran = f"10{from_branch_code[:6]: >6}{from_account_no[:11]: >11}{filler(4)}{user_sequence_number[:6]: >6}{to_branch_code[:6]: >6}{to_account_number[:11]: >11}{to_type_of_account[:1]: >1}{amount[:11]: >11}{filler(12)}{to_statement_description[:20]: >20}{filler(10)}{to_account_holder_name[:15]: >15}{filler(15)}{non_standard_account_number[:20]: >20}{filler(30)}"
        file.write(f"{std_tran}\r\n")

    # USER TRAILER RECORD
    utr = f"92{filler(178)}"
    file.write(f"{utr}\r\n")
    # INSTALLATION TRAILER RECORD
    itr = f"94{filler(178)}"
    file.write(f"{itr}\r\n")


def filler(i: int):
    ret = ""
    while i > 0:
        ret = ret + "0"
        i = i - 1
    return ret

