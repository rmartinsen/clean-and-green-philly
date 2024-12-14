from datetime import datetime

from classes.backup_archive_database import (
    BackupArchiveDatabase,
    backup_schema_name,
    date_time_format,
)
from classes.diff_report import DiffReport
from classes.featurelayer import google_cloud_bucket
from config.psql import conn, local_engine
from sqlalchemy import inspect


class TestDiffBackup:
    """
    test methods for data diffing and backing up
    """

    backup = BackupArchiveDatabase()

    def test_backup(self):
        """
        test the backup workflow without archiving
        """
        assert backup_schema_name not in inspect(local_engine).get_schema_names()
        TestDiffBackup.backup.backup_schema()
        assert backup_schema_name in inspect(local_engine).get_schema_names()

    def test_archive(self):
        """
        test the backup archiving
        """
        TestDiffBackup.backup.archive_backup_schema()
        conn.commit()
        assert backup_schema_name not in inspect(local_engine).get_schema_names()

    def test_prune_old_archives(self):
        """
        test dropping backups that are too old
        """
        TestDiffBackup.backup.prune_old_archives()
        conn.commit()

    def test_diff(self):
        """
        test the diff, assumes the backup_ table is there
        """
        diff = DiffReport(timestamp_string=TestDiffBackup.backup.timestamp_string)
        diff.run()

    def test_generate_table_detail_report(self):
        """print out the html for the vacant_properties diff"""
        diff = DiffReport()
        html = diff.generate_table_detail_report("vacant_properties")
        print(html)

    def test_detail_report(self):
        """print out the url for the generated and uploaded detail report for vacant_properties diff"""
        diff = DiffReport(timestamp_string=datetime.now().strftime(date_time_format))
        url = diff.detail_report("vacant_properties")
        print(url)

    def test_upload_to_gcp(self):
        """test a simple upload to Google cloud"""
        bucket = google_cloud_bucket()
        blob = bucket.blob("test.txt")
        blob.upload_from_string("test")

    def test_send_report_to_slack(self):
        """CAREFUL: if configured, this will send a message to Slack, potentially our prod channel"""
        diff = DiffReport()
        diff.report = "This is the report"
        diff.send_report_to_slack()

    def test_email_report(self):
        """CAREFUL: if configured, this will send email if configured"""
        diff = DiffReport()
        diff.report = "This is the report"
        diff.email_report()

    def test_is_backup_schema_exists(self):
        """test method for whether the backup schema exists """    
        if TestDiffBackup.backup.is_backup_schema_exists():
            TestDiffBackup.backup.archive_backup_schema()
            conn.commit()
            assert not TestDiffBackup.backup.is_backup_schema_exists()
        else:
            TestDiffBackup.backup.backup_schema()
            assert TestDiffBackup.backup.is_backup_schema_exists()
            TestDiffBackup.backup.archive_backup_schema()
            conn.commit()
            assert not TestDiffBackup.backup.is_backup_schema_exists()

    
    def test_backup_tiles_file(self):
        """ test backing up the tiles file """
        TestDiffBackup.backup.backup_tiles_file()

