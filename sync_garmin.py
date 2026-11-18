import os
from garminconnect import Garmin
import google.auth
import gspread

if os.path.exists('.env'):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def format_duration(seconds):
    return round(seconds / 60, 2) if seconds else 0

def format_pace(distance_meters, duration_seconds):
    if not distance_meters or not duration_seconds:
        return 0
    distance_km = distance_meters / 1000
    pace_seconds = duration_seconds / distance_km
    return round(pace_seconds / 60, 2)

def main():
    print("Starting Garmin running activities sync...")
    
    garmin_email = os.environ.get('GARMIN_EMAIL')
    garmin_password = os.environ.get('GARMIN_PASSWORD')
    sheet_id = os.environ.get('SHEET_ID')
    
    if not all([garmin_email, garmin_password, sheet_id]):
        print("❌ Missing required environment variables")
        print(f"   GARMIN_EMAIL: {'✓' if garmin_email else '✗'}")
        print(f"   GARMIN_PASSWORD: {'✓' if garmin_password else '✗'}")
        print(f"   SHEET_ID: {'✓' if sheet_id else '✗'}")
        return
    
    print("Connecting to Garmin...")
    try:
        garmin = Garmin(garmin_email, garmin_password)
        garmin.login()
        print("✅ Connected to Garmin")
    except Exception as e:
        print(f"❌ Failed to connect to Garmin: {e}")
        return
    
    print("Fetching recent activities...")
    try:
        activities = garmin.get_activities(0, 20)
        print(f"Found {len(activities)} total activities")
    except Exception as e:
        print(f"❌ Failed to fetch activities: {e}")
        return
    
    running_activities = [
        activity for activity in activities 
        if activity.get('activityType', {}).get('typeKey', '').lower() in ['running', 'treadmill_running', 'trail_running']
    ]
    
    print(f"Found {len(running_activities)} running activities")
    
    if not running_activities:
        print("No running activities found in recent data")
        return
    
    print("Connecting to Google Sheets...")
    try:
        creds, _ = google.auth.default(
            scopes=[
                'https://googleapis.com',
                'https://googleapis.com'
            ]
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        print("✅ Connected to Google Sheets")
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheets: {e}")
        return
    
    existing_data = sheet.get_all_values()
    if not existing_data:
        headers = [
            "Date", "Activity Name", "Distance (km)", "Duration (min)",
            "Avg Pace (min/km)", "Avg HR", "Max HR", "Calories",
            "Avg Cadence", "Elevation Gain (m)", "Activity Type"
        ]
        sheet.append_row(headers)
        existing_data = [headers]
    
    existing_dates = set()
    if len(existing_data) > 1:
        for row in existing_data[1:]:
            if row and row[0]:
                existing_dates.add(row[0])
    print(f"Found {len(existing_dates)} existing entries")
    
    new_entries = 0
    for activity in reversed(running_activities):
        try:
            activity_date = activity.get('startTimeLocal', '')[:10]
            
            if activity_date in existing_dates:
                print(f"Skipping {activity_date} - already exists")
                continue
            
            activity_name = activity.get('activityName', 'Run')
            distance_meters = activity.get('distance', 0)
            distance_km = round(distance_meters / 1000, 2) if distance_meters else 0
            duration_seconds = activity.get('duration', 0)
            duration_min = format_duration(duration_seconds)
            avg_pace = format_pace(distance_meters, duration_seconds)
            avg_hr = activity.get('averageHR', 0) or 0
            max_hr = activity.get('maxHR', 0) or 0
            calories = activity.get('calories', 0) or 0
            avg_cadence = activity.get('averageRunningCadenceInStepsPerMinute', 0) or 0
            elevation_gain = round(activity.get('elevationGain', 0), 1) if activity.get('elevationGain') else 0
            activity_type = activity.get('activityType', {}).get('typeKey', 'running')
            
            row = [
                activity_date,
                activity_name,
                distance_km,
                duration_min,
                avg_pace,
                avg_hr,
                max_hr,
                calories,
                avg_cadence,
                elevation_gain,
                activity_type
            ]
            
            sheet.append_row(row)
            existing_dates.add(activity_date)
            print(f"✅ Added: {activity_date} - {activity_name} ({distance_km} km)")
            new_entries += 1
            
        except Exception as e:
            print(f"❌ Error processing activity: {e}")
            continue
    
    if new_entries > 0:
        print(f"\n🎉 Successfully added {new_entries} new running activities!")
    else:
        print("\n✓ No new activities to add")

if __name__ == "__main__":
    main()
