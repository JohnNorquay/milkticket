import pandas as pd

def load_excel_data(file_path):
    try:
        # Load the Excel file into a DataFrame
        df = pd.read_excel(file_path)

        # List of relevant columns to keep
        columns_to_keep = [
            'user or driver', 'trailer', 'trailer_vin', 'wash_facility', 'wash_type',
            'wash_attendant', 'main_seal_id', 'drain_seal_id', 'seal_id_3', 'seal_id_4',
            'facility', 'Grade A Cert', 'Grade A Exp', 'comment', 'commodity',
            'timestamp', 'state', 'load_batch_id', 'BTU No', 'bulk_sampler_license',
            'bulk_sampler_license_exp', 'temperature', 'stick_reading', 'weight',
            'antibiotic_test_positive', 'antibiotic_test_result', 'antibiotic_test_timestamp', 'sanitizer'
        ]

        # Filter the DataFrame to include only the columns we care about
        df = df[columns_to_keep]

        # Separate 'unloaded' and 'loaded' records
        unloaded_tickets = df[df['state'] == 'unloaded']
        loaded_tickets = df[df['state'] == 'loaded']

        # Create a dictionary to hold grouped tickets by load_batch_id
        grouped_tickets = {}

        # Iterate through each unloaded ticket to build grouped data
        for _, unloaded_row in unloaded_tickets.iterrows():
            load_batch_id = unloaded_row['load_batch_id']

            # Get all loaded records for this load_batch_id
            related_loaded_records = loaded_tickets[loaded_tickets['load_batch_id'] == load_batch_id]

            # Convert loaded records to dictionary format for farm pickups
            farm_pickups = related_loaded_records.to_dict(orient='records')

            # Store unloaded ticket details and associated farm pickups in the grouped_tickets dictionary
            grouped_tickets[load_batch_id] = {
                'milk_ticket': unloaded_row.to_dict(),  # Convert unloaded row to dictionary
                'farm_pickups': farm_pickups            # List of dictionaries representing farm pickups
            }

        return grouped_tickets

    except Exception as e:
        print(f"Error loading spreadsheet: {e}")
        return {}
