from db_init import db

class MilkTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    load_batch_id = db.Column(db.String(100), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    facility = db.Column(db.String(100), nullable=False)
    bulk_sampler_license = db.Column(db.String(50), nullable=False)
    btu_no = db.Column(db.String(50), nullable=True)
    antibiotic_test_result = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    receiving_plant = db.Column(db.String(100), nullable=False, default='Cedar Grove Cheese Inc.')
    receiving_plant_location = db.Column(db.String(100), nullable=False, default='Plain, WI')
    farm_pickups = db.Column(db.Text)
    total_converted_pounds = db.Column(db.Float, nullable=False)
    processed = db.Column(db.Boolean, default=False)
    temperature = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<MilkTicket {self.load_batch_id}>'
