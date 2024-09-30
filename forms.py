from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, DateTimeField, SubmitField
from wtforms.validators import DataRequired

class MilkTicketForm(FlaskForm):
    load_batch_id = StringField('Load Batch ID', validators=[DataRequired()])
    driver_name = StringField('Driver Name', validators=[DataRequired()])
    facility = StringField('Facility', validators=[DataRequired()])
    bulk_sampler_license = StringField('Bulk Sampler License', validators=[DataRequired()])
    btu_no = StringField('BTU No')
    antibiotic_test_result = StringField('Antibiotic Test Result')
    temperature = FloatField('Temperature')
    timestamp = DateTimeField('Timestamp', format='%Y-%m-%d %H:%M:%S', validators=[DataRequired()])
    submit = SubmitField('Submit')

class LogoutForm(FlaskForm):
    submit = SubmitField('Logout')