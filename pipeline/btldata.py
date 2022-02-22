#!/usr/bin/env python
"""
The btldata module is a library to help interact with the btldata database.
This is the database that the 2020-era website ran off of, that is synced to some Russian database.
"""
import MySQLdb
import os
import sys

DIR = os.path.dirname(os.path.realpath(__file__))


class Connection(object):
    def __init__(self):
        ini_path = os.path.join(DIR, "btldata.ini")
        lines = [line.strip() for line in open(ini_path)]
        self.config = dict(line.split("=") for line in lines if line)
        self.connect()

    def connect(self):
        retries = 10
        for _ in range(retries):
            try:
                self.conn = MySQLdb.connect(**self.config)
                return
            except MySQLdb.OperationalError as e:
                print(f"mysql connection error: {e}")
                time.sleep(10)
        raise IOError(f"mysql connection failed even after {retries} retries")

    def fetchall(self, command, args=()):
        cur = self.conn.cursor()
        cur.execute(command ,args)
        result = cur.fetchall()
        cur.close()
        return result

    def iter_tables(self):
        for row in self.fetchall("SHOW TABLES"):
            yield row[0]

    def describe(self, table):
        assert table.isalnum()
        for row in self.fetchall(f"DESCRIBE {table}"):
            print(row)

    def count_files(self):
        rows = self.fetchall(f"SELECT COUNT(*) from files")
        assert len(rows) == 1
        return rows[0][0]

    def fetch_iter(self, command, args=()):
        cur = self.conn.cursor()
        cur.execute(command, args)
        for row in cur:
            yield row
        cur.close()

    def fetch_by_filename(self, filename):
        """
        Return id, url.
        Returns (None, None) if nothing matches.
        """
        basename = filename.split("/")[-1]
        rows = self.fetchall(f"SELECT id, url FROM files WHERE url LIKE %s", ("%" + basename,))
        if not rows:
            return None, None
        assert len(rows) == 1
        file_id, url = rows[0]
        return file_id, url

    def get_url(self, file_id):
        assert int(file_id) > 0
        rows = self.fetchall(f"SELECT url FROM files WHERE id = %s", (file_id,))
        if not rows:
            return None, None
        assert len(rows) == 1
        url = rows[0][0]
        return url
    
    def set_url(self, file_id, url):
        assert int(file_id) > 0
        assert url is not None
        cur = self.conn.cursor()
        cur.execute("UPDATE files SET url = %s WHERE id = %s", (url, file_id))
        self.conn.commit()
        cur.close()

        
if __name__ == "__main__":
    c = Connection()

    for arg in sys.argv[1:]:
        try:
            file_id = int(arg)
            url = c.get_url(file_id)
        except ValueError:
            filename = arg
            file_id, url = c.fetch_by_filename(filename)
        print(file_id, url)
