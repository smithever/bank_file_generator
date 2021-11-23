import datetime
import dbm
import sqlite3
import uuid
from enum import Enum

import pandas as pd
import pandas.io.sql


class DatabaseService:
    def __init__(self):
        self.conn = sqlite3.connect("app.db")
        self.db = self.conn.cursor()
        self.statuses = ["NEW", "DELETED", "EXPORTED", "DUPLICATE"]
        self.import_transaction_headings = [
            "id_source",
            "supplier_code",
            "supplier_name",
            "description",
            "amount",
            "sys_status",
            "sys_prev_status",
            "sys_import_file_name",
            "sys_import_date",
            "sys_export_file_name",
            "sys_export_date",
            "sys_id"
        ]
        self.imported_file_summary_headings = [
            "File Name",
            "Date",
            "Records",
            "Export Value"
        ]
        self.entity_headings = [
            "sys_id",
            "name",
            "bank_name",
            "account_number",
            "account_description",
            "branch_code"
        ]
        self.supplier_summary_headings = [
            "supplier_code",
            "supplier_name",
            "to_account_number",
            "to_sub_account_number",
            "to_branch_code",
            "to_account_holder_name",
            "to_account_type",
            "sys_id"
        ]
        self.export_file_headings = [
            "File Name",
            "Date",
            "Records",
            "Export Value"
        ]

    def close(self):
        self.conn.close()
        self.db.close()

    def get_entities(self) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.entity_headings).set_index("sys_id")
        try:
            ret = pd.read_sql_query("SELECT * FROM entities", self.conn)
            return ret[self.entity_headings]
        except pandas.io.sql.DatabaseError:
            return ret

    def get_single_entity(self, entity_id) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.entity_headings).set_index("sys_id")
        try:
            return pd.read_sql_query(f"SELECT * FROM entities WHERE sys_id = '{entity_id}'", self.conn)
        except pandas.io.sql.DatabaseError:
            return ret

    def save_entities(self, df: pd.DataFrame):
        if not pd:
            return None
        else:
            save = df[self.entity_headings]
            save.to_sql("entities", self.conn, if_exists='replace')
            self.conn.commit()

    def get_file_import_transactions(self, filename: str, entity_id) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.import_transaction_headings).set_index("sys_id")
        try:
            return pd.read_sql_query(
                f"SELECT * FROM [import_transactions_{entity_id}] WHERE sys_import_file_name = '{filename}'",
                self.conn
            )
        except pandas.io.sql.DatabaseError:
            return ret

    def get_supplier_transactions(self, supplier_id: str, entity_id):
        ret = pd.DataFrame(columns=self.import_transaction_headings).set_index("sys_id")
        try:
            return pd.read_sql_query(
                f"SELECT * FROM [import_transactions_{entity_id}] WHERE supplier_code = '{supplier_id}'",
                self.conn
            )
        except pandas.io.sql.DatabaseError:
            return ret

    def save_file_import_transactions(self, df: pd.DataFrame, entity_id):
        if not pd:
            return None
        else:
            save = df[self.import_transaction_headings]
            save.to_sql(f"import_transactions_{entity_id}", self.conn, if_exists='append')
            self.conn.commit()

    def delete_file_import_transactions(self, filename: str, entity_id):
        if not filename:
            return None
        else:
            self.conn.execute(
                f"DELETE FROM [import_transactions_{entity_id}] WHERE sys_import_file_name = '{filename}'"
            )
            self.conn.commit()
            return

    def get_duplicated_id_source(self, id_source: list, entity_id) -> list:
        ret: list = []
        try:
            query = self.conn.execute(
                f"SELECT id_source FROM [import_transactions_{entity_id}] WHERE id_source IN {str(tuple(id_source)).replace(',)', ')')}"
            ).fetchall()
            ret = [i[0] for i in query]
            return ret
        except sqlite3.DatabaseError:
            return ret

    def update_transactions_status(self, transactions: list, status: str, entity_id):
        if transactions:
            query = self.conn.execute(
                f"UPDATE [import_transactions_{entity_id}] SET sys_prev_status = sys_status, sys_status = '{status}' "
                f"WHERE sys_id in {str(tuple(transactions)).replace(',)', ')')} "
            )
            self.conn.commit()
            return

    def get_imported_file_summary(self, entity_id) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.imported_file_summary_headings)
        try:
            ret = pd.read_sql_query(
                "SELECT sys_import_file_name as 'File Name',  sys_import_date as 'Date', COUNT(sys_id) as 'Records', "
                f"SUM(amount) as 'Export Value'  FROM [import_transactions_{entity_id}] GROUP BY sys_import_file_name",
                self.conn
            )
            return ret.sort_values(by="Date", ascending=False)
        except pandas.io.sql.DatabaseError:
            return ret

    def save_suppliers_summary(self, df: pd.DataFrame, entity_id):
        if not pd:
            return None
        else:
            save = df[self.supplier_summary_headings]
            save.to_sql(f"suppliers", self.conn, if_exists='replace')
            self.conn.commit()

    def get_suppliers_summary(self, entity_id) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.supplier_summary_headings)
        try:
            suppliers = pd.read_sql_query(
                f"SELECT * FROM [suppliers]",
                self.conn
            )
            if len(suppliers) > 0:
                missing = pd.read_sql_query(
                    f"SELECT DISTINCT(supplier_code), supplier_name FROM [import_transactions_{entity_id}] "
                    f"WHERE supplier_code not in {str(tuple(suppliers['supplier_code'].tolist())).replace(',)', ')')}",
                    self.conn
                )
                if len(missing) > 0:
                    if len(missing) > 0:
                        missing["sys_id"] = [str(uuid.uuid4()) for _ in range(len(missing.index))]
                        missing["to_account_number"] = ""
                        missing["to_sub_account_number"] = ""
                        missing["to_branch_code"] = ""
                        missing["to_account_holder_name"] = ""
                        missing["to_account_type"] = "1.Current Account"
                ret = suppliers.append(missing)
                return ret[self.supplier_summary_headings].sort_values(by="to_account_number", ascending=True)
        except pandas.io.sql.DatabaseError:
            try:
                new = pd.read_sql_query(
                    f"SELECT DISTINCT(supplier_code), supplier_name FROM [import_transactions_{entity_id}]",
                    self.conn
                )
                if len(new) > 0:
                    new["sys_id"] = [str(uuid.uuid4()) for _ in range(len(new.index))]
                    new["to_account_number"] = ""
                    new["to_sub_account_number"] = ""
                    new["to_branch_code"] = ""
                    new["to_account_holder_name"] = ""
                    new["to_account_type"] = "1.Current Account"
                return new[self.supplier_summary_headings]
            except pandas.io.sql.DatabaseError:
                return ret

    def get_exported_file_summary(self, entity_id) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.export_file_headings)
        try:
            ret = pd.read_sql_query(
                "SELECT sys_export_file_name as 'File Name',  sys_export_date as 'Date', COUNT(sys_id) as 'Records', "
                f"SUM(amount) as 'Export Value'  FROM [import_transactions_{entity_id}] "
                f"WHERE sys_export_file_name is not null GROUP BY sys_export_file_name",
                self.conn
            )
            return ret.sort_values(by="Date", ascending=False)
        except pandas.io.sql.DatabaseError:
            return ret

    def get_export_ready_transactions(self, entity_id):
        ret = pd.DataFrame(columns=self.import_transaction_headings).set_index("sys_id")
        try:
            return pd.read_sql_query(
                f"SELECT * FROM [import_transactions_{entity_id}] WHERE sys_status = 'NEW'",
                self.conn
            )
        except pandas.io.sql.DatabaseError:
            return ret

    def get_export_transaction_nedbank(self, entity_id, tran_ids) -> pd.DataFrame:
        ret = pd.DataFrame(columns=self.imported_file_summary_headings)
        try:
            sql = f"""SELECT
            (SELECT account_number FROM entities WHERE sys_id = '{entity_id}') AS 'from_account_number',
            (SELECT account_description FROM entities WHERE sys_id = '{entity_id}') AS
            'from_account_description',
            it.supplier_code AS 'own_statement_description',
            s.to_account_number,
            s.to_sub_account_number,
            s.to_branch_code,
            it.supplier_name,
            REPLACE(it.description, 'Supplier Invoice  - ', '') AS 'to_statement_description',
            it.amount
            FROM [import_transactions_{entity_id}] it
            INNER JOIN suppliers s
            ON s.supplier_code = it.supplier_code
            WHERE it.sys_id in {str(tuple(tran_ids)).replace(',)', ')')}"""
            ret = pd.read_sql_query(sql, self.conn)
            self.update_transactions_status(tran_ids, "EXPORTING", entity_id)
            return ret
        except pandas.io.sql.DatabaseError:
            return ret

    def update_transactions_exported(self, entity_id, tran_ids, filename) -> pd.DataFrame:
        if tran_ids:
            try:
                sql = f"""UPDATE [import_transactions_{entity_id}]
                SET sys_export_file_name = '{filename}',
                sys_export_date = '{datetime.datetime.now()}'
                WHERE sys_id in {str(tuple(tran_ids)).replace(',)', ')')}"""
                self.conn.execute(sql)
                self.conn.commit()
            except sqlite3.DatabaseError as er:
                raise RuntimeError(er)
            else:
                self.update_transactions_status(tran_ids, "EXPORTED", entity_id)

    def get_export_transaction_fnb(self, entity_id, tran_ids) -> pd.DataFrame:
        try:
            sql = f"""SELECT s.to_branch_code,
s.to_account_number,
substr(s.to_account_type, 0,2) as 'to_account_type',
CAST((it.amount * 100) as INT) as amount,
REPLACE(it.description, 'Supplier Invoice  - ', '') AS 'to_statement_description',
s.to_account_holder_name
FROM [import_transactions_{entity_id}] it
INNER JOIN suppliers s
ON s.supplier_code = it.supplier_code
WHERE it.sys_id in {str(tuple(tran_ids)).replace(',)', ')')}"""
            print(sql)
            ret = pd.read_sql_query(sql, self.conn)
            self.update_transactions_status(tran_ids, "EXPORTING", entity_id)
            return ret
        except pandas.io.sql.DatabaseError:
            print("get_export_transaction_fnb has failed")
            return
