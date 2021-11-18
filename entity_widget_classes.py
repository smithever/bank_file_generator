import uuid
from functools import partial
from PyQt5 import QtWidgets as qtw
import pandas as pd
import os
from database import DatabaseService
from edit_entity import Ui_EditEntityForm
from select_entity import Ui_SelectEntityForm
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

db = DatabaseService()
banks = [
    "FNB",
    "Nedbank"
]

class EditEntity(qtw.QWidget):
    def __init__(self):
        super().__init__()
        self.ui = Ui_EditEntityForm()
        self.ui.setupUi(self)
        for item in banks:
            self.ui.combo_bank.addItem(item)

    def edit(self, entities: pd.DataFrame, entity_id: str):
        new_entities = entities.loc[entities['sys_id'] == entity_id]
        self.ui.txt_entity_name.setText(new_entities['name'].iloc[0])
        self.ui.combo_bank.setCurrentText(new_entities['bank_name'].iloc[0])
        self.ui.txt_account_number.setText(new_entities['account_number'].iloc[0])
        self.ui.txt_account_details.setText(new_entities['account_description'].iloc[0])
        self.ui.btn_save_entity.clicked.connect(partial(self.save_entity_clicked, entities, None, True, entity_id))

    def new(self, entities: pd.DataFrame, callback):
        self.ui.btn_save_entity.clicked.connect(partial(self.save_entity_clicked, entities, callback, False, None))
        self.show()

    def save_entity_clicked(self, entities: pd.DataFrame, callback, is_edit: bool, entity_id):
        name = self.ui.txt_entity_name.text()
        bank = self.ui.combo_bank.currentText()
        acc_number = self.ui.txt_account_number.text()
        acc_description = self.ui.txt_account_details.text()
        if len(name) < 2 or len(acc_number) < 3 or len(acc_description) < 2:
            return qtw.QMessageBox.about(self, "Info!", "Please complete all fields")
        if len(entities[entities['name'] == name]) > 0 and not is_edit:
            return qtw.QMessageBox.about(self, "Info!", "Entity with name already exists")
        else:
            new = {
                "sys_id": str(uuid.uuid4()),
                "name": str(name),
                "bank_name": str(bank),
                "account_number": acc_number,
                "account_description": str(acc_description)
            }
            if not is_edit:
                new = entities.append(new, ignore_index=True)
                new.reset_index(drop=False)
                db.save_entities(new)
                callback(new)
                self.close()
                return
            if is_edit:
                item_index = entities.index[entities['sys_id'] == entity_id].tolist()[0]
                entities.at[item_index, 'name'] = str(name)
                entities.at[item_index, 'bank_name'] = str(bank)
                entities.at[item_index, 'account_number'] = acc_number
                entities.at[item_index, 'account_description'] = acc_description
                entities.reset_index()
                db.save_entities(entities)
                return qtw.QMessageBox.about(self, "Info!", "Entity updated successfully")
            else:
                pass


class SelectEntity(qtw.QWidget):
    def __init__(self, parent):
        super(SelectEntity, self).__init__(parent)
        self.entities: pd.DataFrame = db.get_entities()
        print(self.entities.count())
        self.ui = Ui_SelectEntityForm()
        self.ui.setupUi(self)
        self.ui.btn_load_entity.clicked.connect(self.load_clicked)
        self.ui.btn_add_entity.clicked.connect(self.edit_entity_clicked)
        i = len(self.entities)
        while 0 < i <= len(self.entities):
            self.ui.list_entities.addItem(str(self.entities.iloc[i-1, 2]))
            i = i - 1
        self.selected_entity = ""

    def load_clicked(self):
        m = EditEntity()
        sel_index = self.ui.list_entities.currentIndex().row()
        if sel_index >= 0:
            self.selected_entity = self.entities.iloc[sel_index, 1]
            self.parent().load(self.selected_entity)
            print(f"load clicked {self.selected_entity}")

    def edit_entity_clicked(self):
        w = EditEntity()
        w.new(self.entities, self.callback)

    def callback(self, df: pd.DataFrame):
        print("Callback init")
        self.ui.list_entities.clear()
        self.entities = df
        i = len(self.entities)
        while 0 < i <= len(self.entities):
            self.ui.list_entities.addItem(str(self.entities.iloc[i - 1, 2]))
            i = i - 1

    def hide_callback(self):
        self.hide()