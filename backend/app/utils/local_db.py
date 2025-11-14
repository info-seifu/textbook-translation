"""
JSONベースのローカルデータベース
Supabaseの代わりにJSONファイルでデータを管理
"""
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4
from pathlib import Path
import threading


class LocalDatabase:
    """JSONベースのローカルデータベース"""

    def __init__(self, db_file: str = "storage/database.json"):
        self.db_file = Path(db_file)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

        # データベースの初期化
        if not self.db_file.exists():
            self._save_db({
                'translation_jobs': [],
                'translation_outputs': [],
                'figures': []
            })

    def _load_db(self) -> Dict:
        """データベースを読み込み"""
        with open(self.db_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_db(self, data: Dict):
        """データベースを保存"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def table(self, table_name: str):
        """テーブルを取得"""
        return TableQuery(self, table_name)


class TableQuery:
    """テーブルクエリ（Supabase互換インターフェース）"""

    def __init__(self, db: LocalDatabase, table_name: str):
        self.db = db
        self.table_name = table_name
        self.filters = []
        self.select_fields = None
        self.single_result = False

    def select(self, fields: str = '*'):
        """SELECT句"""
        self.select_fields = fields
        return self

    def insert(self, data: Dict) -> 'QueryResponse':
        """INSERT"""
        with self.db.lock:
            db_data = self.db._load_db()

            if self.table_name not in db_data:
                db_data[self.table_name] = []

            # IDがなければ生成
            if 'id' not in data:
                data['id'] = str(uuid4())

            # created_atがなければ追加
            if 'created_at' not in data:
                data['created_at'] = datetime.now().isoformat()

            # updated_atを追加（translation_jobsの場合）
            if self.table_name == 'translation_jobs' and 'updated_at' not in data:
                data['updated_at'] = datetime.now().isoformat()

            db_data[self.table_name].append(data)
            self.db._save_db(db_data)

            return QueryResponse(data=[data])

    def update(self, data: Dict) -> 'TableQuery':
        """UPDATE句"""
        self.update_data = data

        # updated_atを自動更新
        if self.table_name == 'translation_jobs':
            self.update_data['updated_at'] = datetime.now().isoformat()

        return self

    def eq(self, field: str, value: Any) -> 'TableQuery':
        """WHERE句（等価）"""
        self.filters.append(('eq', field, value))
        return self

    def single(self) -> 'TableQuery':
        """単一結果を取得"""
        self.single_result = True
        return self

    def execute(self) -> 'QueryResponse':
        """クエリを実行"""
        with self.db.lock:
            db_data = self.db._load_db()

            if self.table_name not in db_data:
                return QueryResponse(data=None if self.single_result else [])

            records = db_data[self.table_name]

            # フィルタ適用
            for filter_type, field, value in self.filters:
                if filter_type == 'eq':
                    records = [r for r in records if r.get(field) == value]

            # UPDATE処理
            if hasattr(self, 'update_data'):
                updated_records = []
                for record in records:
                    record.update(self.update_data)
                    updated_records.append(record)

                # データベースに反映
                all_records = db_data[self.table_name]
                for i, r in enumerate(all_records):
                    for updated in updated_records:
                        if r.get('id') == updated.get('id'):
                            all_records[i] = updated

                self.db._save_db(db_data)
                records = updated_records

            # 単一結果
            if self.single_result:
                return QueryResponse(data=records[0] if records else None)

            return QueryResponse(data=records)


class QueryResponse:
    """クエリレスポンス（Supabase互換）"""

    def __init__(self, data: Any):
        self.data = data


# グローバルインスタンス
_local_db = LocalDatabase()


def get_local_db() -> LocalDatabase:
    """ローカルデータベースを取得"""
    return _local_db
