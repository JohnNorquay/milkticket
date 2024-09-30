from flask import render_template, redirect, url_for, flash, request
from models import MilkTicket
from db_init import db
from forms import MilkTicketForm
from app import app
from excel_processor import load_excel_data
from datetime import datetime
import json
import pandas as pd
import logging, math

# Setup basic logging configuration
logging.basicConfig(level=logging.DEBUG)

@app.route('/milk_ticket', methods=['GET', 'POST'])
@app.route('/milk_ticket/<string:load_batch_id>', methods=['GET', 'POST'])
def submit_ticket(load_batch_id=None):
    form = MilkTicketForm()

    # Fetch the next unprocessed ticket if one isn't provided
    if load_batch_id is None:
        # Query the next unprocessed ticket
        unprocessed_ticket = MilkTicket.query.filter_by(processed=False).first()
        if unprocessed_ticket is None:
            flash('All milk tickets have been processed.', 'success')
            return redirect(url_for('view_tickets'))
        load_batch_id = unprocessed_ticket.load_batch_id

    # Fetch the current milk ticket
    milk_ticket = MilkTicket.query.filter_by(load_batch_id=load_batch_id).first()
    if not milk_ticket:
        flash('No milk ticket found for the provided load batch ID.', 'error')
        return redirect(url_for('view_tickets'))

    # Pre-populate the form with the milk ticket data
    form.load_batch_id.data = milk_ticket.load_batch_id
    form.driver_name.data = milk_ticket.driver_name
    form.facility.data = milk_ticket.facility
    form.bulk_sampler_license.data = milk_ticket.bulk_sampler_license
    form.btu_no.data = milk_ticket.btu_no
    form.antibiotic_test_result.data = milk_ticket.antibiotic_test_result
    form.timestamp.data = milk_ticket.timestamp
    form.temperature.data = milk_ticket.temperature

    # Deserialize farm pickups from JSON to dictionary format
    farm_pickups = json.loads(milk_ticket.farm_pickups)

    # Get previous and next unprocessed tickets for navigation
    previous_ticket = MilkTicket.query.filter(MilkTicket.processed == False,
                                              MilkTicket.id < milk_ticket.id).order_by(MilkTicket.id.desc()).first()
    next_ticket = MilkTicket.query.filter(MilkTicket.processed == False,
                                          MilkTicket.id > milk_ticket.id).order_by(MilkTicket.id.asc()).first()

    if form.validate_on_submit():
        try:
            # Update milk ticket fields
            milk_ticket.driver_name = form.driver_name.data
            milk_ticket.facility = form.facility.data
            milk_ticket.bulk_sampler_license = form.bulk_sampler_license.data
            milk_ticket.btu_no = form.btu_no.data
            milk_ticket.antibiotic_test_result = form.antibiotic_test_result.data
            milk_ticket.timestamp = form.timestamp.data
            milk_ticket.temperature = form.temperature.data

            # Mark the ticket as processed
            milk_ticket.processed = True

            # Save to database
            db.session.commit()
            flash('Milk ticket submitted successfully', 'success')

            # Redirect to the next unprocessed ticket
            if next_ticket:
                return redirect(url_for('submit_ticket', load_batch_id=next_ticket.load_batch_id))
            else:
                flash('All tickets have been processed.', 'success')
                return redirect(url_for('view_tickets'))
        except Exception as e:
            db.session.rollback()
            flash(f'There was an error submitting the form. Error: {str(e)}', 'error')

    return render_template('milk_ticket_form.html',
                           form=form,
                           farm_pickups=farm_pickups,
                           total_converted_pounds=milk_ticket.total_converted_pounds,
                           tank_weight_id=tank_weight_id_from_data(milk_ticket),
                           previous_ticket=previous_ticket,
                           next_ticket=next_ticket)

def tank_weight_id_from_data(milk_ticket):
    if milk_ticket is None:
        return ''
    facility = milk_ticket.facility if milk_ticket.facility else ''
    temperature = milk_ticket.temperature if milk_ticket.temperature else ''
    return f"{facility[-7:]} {temperature}"


@app.route('/view_tickets')
def view_tickets():
    # Fetch all tickets from the database
    tickets = MilkTicket.query.all()
    return render_template('view_tickets.html', tickets=tickets)


# Function to process milk tickets from the Excel spreadsheet
def process_milk_tickets(file_path='vesseytransactions.xlsx', sheet_name='Worksheet', max_unloaded_tickets=5):
    try:
        # Read the entire Excel file
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        app.logger.debug(f"DataFrame loaded with {df.shape[0]} rows and {df.shape[1]} columns.")
    except FileNotFoundError:
        app.logger.error(f"Error: File '{file_path}' not found.")
        return []
    except Exception as e:
        app.logger.error(f"Error processing the file: {e}")
        return []

    # Filter to only 'unloaded' records to count completed milk tickets
    unloaded_tickets = df[df['state'] == 'unloaded']

    if unloaded_tickets.empty:
        app.logger.warning("No 'unloaded' records found in the dataset.")
        return []

    # Limit the number of 'unloaded' records to process
    unloaded_ticket_ids = unloaded_tickets['load_batch_id'].unique()[:max_unloaded_tickets]
    app.logger.debug(f"Processing a maximum of {len(unloaded_ticket_ids)} completed milk tickets based on 'unloaded' records.")

    # Group the DataFrame by 'load_batch_id'
    grouped_tickets = df.groupby("load_batch_id")

    # Initialize an empty list to store milk tickets
    milk_tickets = []

    # Iterate through each `load_batch_id` group that corresponds to a completed unloaded record
    for load_batch_id in unloaded_ticket_ids:
        group = grouped_tickets.get_group(load_batch_id)
        app.logger.debug(f"Processing load_batch_id: {load_batch_id}, number of records in this group: {group.shape[0]}")

        # Retrieve the 'unloaded' record for this group
        unloaded_record = group[group['state'] == 'unloaded']
        if unloaded_record.empty:
            app.logger.warning(f"Skipping load_batch_id {load_batch_id} due to missing 'unloaded' record (incomplete load).")
            continue

        # Create milk ticket dictionary using unloaded details
        milk_ticket = {
            "commodity": unloaded_record.iloc[0].get('commodity', ''),
            "date_and_time": unloaded_record.iloc[0].get('timestamp', ''),
            "producer_name": unloaded_record.iloc[0].get('user or driver', ''),
            "status": "Complete",
            "farm_pickups": []  # Initialize empty farm pickups list
        }

        # Process all 'loaded' records as farm pickups
        loaded_records = group[group['state'] == 'loaded']
        for _, row in loaded_records.iterrows():
            # Create a farm pickup dictionary using loaded details
            farm_pickup = {
                "Producer Number": str(row.get('facility', ''))[:3],
                "Converted Pounds": row.get('weight', 0),
                "Gauge Rod": row.get('stick_reading', 'N/A'),
                "Temp": row.get('temperature', 'N/A'),
                "Date & Time": row.get('timestamp', 'N/A')
            }
            # Append the farm pickup to the milk ticket's list of pickups
            milk_ticket["farm_pickups"].append(farm_pickup)

        # Append the processed milk ticket to the list
        milk_tickets.append(milk_ticket)
        app.logger.debug(f"Completed milk ticket for load_batch_id {load_batch_id}: {milk_ticket}")

    # Return the processed list of milk tickets
    app.logger.debug(f"Total milk tickets processed: {len(milk_tickets)}")
    return milk_tickets


# Route to process and display milk tickets
@app.route('/process_milk_tickets')
def show_processed_milk_tickets():
    # Call the function to process the tickets with a limit of 5 completed (unloaded) records for testing
    processed_tickets = process_milk_tickets(max_unloaded_tickets=5)
    app.logger.debug(f"Processed {len(processed_tickets)} milk tickets.")
    return render_template('processed_milk_tickets.html', tickets=processed_tickets)


def format_antibiotic_result(result):
    if not result:
        return '- 0 nf'
    # Ensure there is only one minus sign at the front
    result_str = str(result).strip()
    if not result_str.startswith('-'):
        result_str = '-' + result_str
    # Remove any existing 'nf' and reformat correctly
    result_str = result_str.replace('nf', '').strip()
    return f"{result_str} nf"

# Function to process all tickets from the spreadsheet
def update_processed_status_from_spreadsheet(spreadsheet_path, batch_size=None):
    app.logger.debug("Starting update_processed_status_from_spreadsheet function.")

    # Load all unloaded tickets from the Excel spreadsheet
    spreadsheet_data = load_excel_data(spreadsheet_path)
    app.logger.debug(f"Spreadsheet data loaded successfully with {len(spreadsheet_data)} tickets.")

    # Fetch all existing tickets from the database
    existing_tickets = {ticket.load_batch_id: ticket for ticket in MilkTicket.query.all()}
    app.logger.debug(f"Existing tickets in DB: {list(existing_tickets.keys())}")

    # Initialize counters
    processed_count = 0
    batch_count = 0

    try:
        # Iterate over all the tickets in the spreadsheet
        for load_batch_id, ticket_data in spreadsheet_data.items():
            unloaded_record = ticket_data['milk_ticket']

            # Check if this ticket already exists
            if load_batch_id in existing_tickets:
                app.logger.debug(f"Ticket {load_batch_id} already exists in the database. Skipping.")
                continue

            # Extract loaded records associated with this load batch ID
            loaded_records = [rec for rec in ticket_data.get('farm_pickups', []) if rec['state'].lower() == 'loaded']

            app.logger.debug(f"Loaded Records found for {load_batch_id}: {loaded_records}")

            # If no 'loaded' records are found, skip this ticket
            if not loaded_records:
                app.logger.warning(f"No loaded records found for load_batch_id {load_batch_id}. Skipping ticket.")
                continue

            # Create cleaned farm pickups from the loaded records
            cleaned_farm_pickups = []
            for pickup in loaded_records:
                cleaned_pickup = {
                    'Producer Number': pickup.get('facility', '')[:3],  # First 3 characters of facility
                    'Converted Pounds': pickup.get('weight', 0.0),
                    'Gauge Rod': pickup.get('stick_reading', 0.0),
                    'Temp': pickup.get('temperature', 0.0),
                    'Date & Time': pickup.get('timestamp', pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S'))
                }
                cleaned_farm_pickups.append(cleaned_pickup)

            # Calculate total converted pounds from the cleaned farm pickups
            total_converted_pounds = sum(pickup['Converted Pounds'] for pickup in cleaned_farm_pickups)

            # Modify this part inside the `update_processed_status_from_spreadsheet` function:
            bulk_sampler_license = unloaded_record.get('bulk_sampler_license', 'UNKNOWN')
            if pd.isna(bulk_sampler_license) or bulk_sampler_license == 'NaN':
                bulk_sampler_license = 'UNKNOWN'

            # Use the cleaned value when creating the MilkTicket:
            new_ticket = MilkTicket(
                load_batch_id=unloaded_record['load_batch_id'],
                driver_name=unloaded_record['user or driver'],
                facility=unloaded_record.get('facility', 'Unknown Facility'),
                bulk_sampler_license=bulk_sampler_license,  # Use cleaned value here
                btu_no=unloaded_record.get('BTU No', 'UNKNOWN'),
                antibiotic_test_result=format_antibiotic_result(unloaded_record.get('antibiotic_test_result', 'N/A')),
                timestamp=pd.to_datetime(unloaded_record['timestamp']),
                temperature=unloaded_record.get('temperature', 0.0),
                farm_pickups=json.dumps(cleaned_farm_pickups),  # Use cleaned pickups data
                total_converted_pounds=total_converted_pounds,
                processed=False  # Mark as unprocessed by default
            )
            db.session.add(new_ticket)
            processed_count += 1

            # Commit in batches to avoid database locking or timeouts
            if processed_count % batch_size == 0:
                db.session.commit()
                batch_count += 1
                app.logger.debug(f"Batch {batch_count} committed with {batch_size} tickets.")

        # Final commit for any remaining tickets
        db.session.commit()
        app.logger.debug(f"All {processed_count} tickets have been processed and updated in the database.")

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error committing changes to the database: {e}")
        flash('There was an error updating the processed status. Please check the logs.', 'error')

# Route to update the processed status from the spreadsheet
@app.route('/update_processed_status', methods=['GET'])
def update_processed_status():
    spreadsheet_path = "vesseytransactions.xlsx"  # Use your actual spreadsheet path here
    update_processed_status_from_spreadsheet(spreadsheet_path, batch_size=100)
    flash("Processed status updated from spreadsheet.")
    return redirect(url_for('view_tickets'))

