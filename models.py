from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class S3File(db.Model):
    __tablename__ = 's3_files'

    filename = db.Column(db.String, primary_key=True)
    size = db.Column(db.Integer)
    updated_at = db.Column(db.String)

class MacAddress(db.Model):
    __tablename__ = 'mac_addresses'

    mac_address = db.Column(db.String, primary_key=True)
    updated_at = db.Column(db.String)

class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Primary Key
    aws_access_key_id = db.Column(db.String)
    aws_secret_access_key = db.Column(db.String)
    bucket_name = db.Column(db.String)
    dt_rule = db.Column(db.Text, nullable=False)
    max_file_size = db.Column(db.Integer, nullable=False)
    use_cloud = db.Column(db.Boolean, nullable=False)
    delete_scans = db.Column(db.Boolean, nullable=False)
    delete_scans_days_old = db.Column(db.Integer)
    delete_scans_percent_remaining = db.Column(db.Integer)
    device_name_includes = db.Column(db.String)
    id_file_starts_with = db.Column(db.String)
    alert_email = db.Column(db.String)
    updated_at = db.Column(db.String)
