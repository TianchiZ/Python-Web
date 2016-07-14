import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField,  IntegerField

def next_id():
	return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

class Vendor(Model):
    __table__ = 'vendor'

    vendor_id =  IntegerField(primary_key=True)
    vendor_name = StringField(ddl='varchar(50)')

class DM(Model):
    __table__ = 'model'

    model_id =  IntegerField(primary_key=True)
    vendor_id = IntegerField()
    model_name = StringField(ddl='varchar(50)')

class Firmware(Model):
    __table__ = 'firmware'

    firmware_id = IntegerField(primary_key=True)
    user_id = StringField(ddl='varchar(50)')
    user_email = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    fw_vendor_name = StringField(ddl='varchar(50)')
    fw_model_name = StringField(ddl='varchar(50)')
    fw_type = StringField(ddl='varchar(50)')
    fw_drive_format = StringField(ddl='varchar(50)')
    fw_drive_linkspeed = StringField(ddl='varchar(50)')
    firmware_revision = StringField(ddl='varchar(50)')
    firmware_name = StringField(ddl='varchar(100)')
    changelist_name = StringField(ddl='varchar(100)')
    changelist_status = StringField(ddl='varchar(50)')
    fw_release_date = StringField(ddl='varchar(50)')
    created_at = FloatField(default=time.time)