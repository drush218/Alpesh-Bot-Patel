"""In-memory stand-in for the supabase-py client: just the query methods the app uses."""

import copy
import itertools

FIXED_FACTORS = ["rates_policy", "rates_10y", "fx_usd", "oil", "natgas", "labour",
                 "consumer_spend", "credit_spreads", "inflation", "china_activity"]



class _Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], "select", None
        self.on_conflict = None

    def select(self, *_):
        self.op = "select"
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows
        return self

    def upsert(self, row, on_conflict=None):
        self.op, self.payload, self.on_conflict = "upsert", row, on_conflict
        return self

    def update(self, values):
        self.op, self.payload = "update", values
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def _match(self, row):
        return all(row.get(c) == v for c, v in self.filters)

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "select":
            data = [dict(r) for r in rows if self._match(r)]
        elif self.op == "insert":
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            data = []
            for r in new:
                r = copy.deepcopy(r)
                r.setdefault("id", next(self.db.ids))
                rows.append(r)
                data.append(dict(r))
        elif self.op == "upsert":
            keys = self.on_conflict.split(",")
            hit = [r for r in rows if all(r.get(k) == self.payload[k] for k in keys)]
            if hit:
                hit[0].update(self.payload)
                data = [dict(hit[0])]
            else:
                r = {**self.payload, "id": next(self.db.ids)}
                rows.append(r)
                data = [dict(r)]
        elif self.op == "update":
            data = []
            for r in rows:
                if self._match(r):
                    r.update(self.payload)
                    data.append(dict(r))
        else:  # delete, cascading to analysis children
            gone = [r for r in rows if self._match(r)]
            self.db.tables[self.table] = [r for r in rows if not self._match(r)]
            if self.table == "analyses":
                ids = {r["id"] for r in gone}
                for t, trs in self.db.tables.items():
                    self.db.tables[t] = [r for r in trs if r.get("analysis_id") not in ids]
            data = gone
        return type("Resp", (), {"data": data})()


class FakeSupabase:
    def __init__(self):
        self.ids = itertools.count(1)
        self.tables = {"macro_factors": [{"code": c, "name": c} for c in FIXED_FACTORS]}

    def table(self, name):
        return _Query(self, name)

    def rows(self, name, **where):
        return [r for r in self.tables.get(name, []) if all(r.get(k) == v for k, v in where.items())]
