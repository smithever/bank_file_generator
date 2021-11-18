import datetime
import uuid
from database import DatabaseService
import pandas as pd

db = DatabaseService()


def check_for_duplicates(invoices, entity_id):
    duplicates: list = db.get_duplicated_id_source(invoices["id_source"].tolist(), entity_id)
    if len(duplicates) > 0:
        for duplicate in duplicates:
            item_index = invoices.index[invoices['id_source'] == duplicate].tolist()[0]
            invoices.at[item_index, 'sys_status'] = "DUPLICATE"


def update_supplier(data):
    next_opening = data.supplier.astype(str).str.startswith("Opening").idxmax()
    while next_opening != 0:
        next_closing = data.supplier.astype(str).str.startswith("Closing").idxmax()
        client = data.at[next_opening - 1, 'supplier']
        while next_opening <= next_closing:
            data.at[next_opening, 'supplier'] = client
            next_opening = next_opening + 1
        next_opening = data.supplier.astype(str).str.startswith("Opening").idxmax()


class ImportFile:
    def __init__(self):
        pass

    def load_new(self, file_location, entity_id) -> pd.DataFrame:
        filename = str(file_location).split("/")[-1]
        exist = db.get_file_import_transactions(filename, entity_id)
        if len(exist) > 0:
            raise Exception("File name already imported")
            return
        data = pd.read_excel(file_location)
        header = data.columns[0]
        data_2 = data.rename(columns={
            header: 'supplier',
            data.columns[2]: 'id_source',
            data.columns[4]: 'description',
            data.columns[6]: 'amount'
        })
        update_supplier(data_2)
        invoices = data_2.loc[data_2.id_source.astype(str).str.startswith("PNA")]
        pd.options.mode.chained_assignment = None
        invoices["supplier_code"] = invoices.loc[:, "supplier"].astype(str).str.split(":").str[0]
        invoices["supplier_name"] = invoices.loc[:, "supplier"].astype(str).str.split(":").str[1]
        invoices["sys_status"] = "NEW"
        invoices["sys_prev_status"] = None
        invoices["sys_import_file_name"] = filename
        invoices["sys_import_date"] = datetime.datetime.now()
        invoices["sys_export_file_name"] = None
        invoices["sys_export_date"] = None
        invoices["sys_id"] = [str(uuid.uuid4()) for _ in range(len(invoices.index))]
        check_for_duplicates(invoices, entity_id)
        db.save_file_import_transactions(invoices, entity_id)
        return invoices[db.import_transaction_headings]
