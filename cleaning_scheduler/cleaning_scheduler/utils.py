from .models import Apartment, Booking, CleaningSchedule
from datetime import datetime, timedelta
import intervaltree
import logging

logger = logging.getLogger(__name__)

def validate_booking_dates(apartment, dtstart, dtend):
    # Check that the start date is not in the past
    if dtstart.date() < datetime.now().date():
        return 'Start date cannot be in the past'

    # Check that the end date is not before the start date
    if dtend < dtstart:
        return 'End date cannot be before start date'

    # Check for overlapping bookings
    overlapping_bookings = Booking.objects.filter(apartment=apartment, check_in_date__lt=dtend, check_out_date__gt=dtstart)
    if overlapping_bookings.exists():
        return f'Booking from {dtstart} to {dtend} overlaps with an existing booking'

    return None

def update_cleaning_schedule(user, new_bookings):

    # Determine the date range of interest based on new bookings
    date_min = min(booking.check_in_date for booking in new_bookings) - timedelta(days=30)
    date_max = max(booking.check_out_date for booking in new_bookings) + timedelta(days=30)

    # Step 1: Determine Cleaning Windows
    calculate_cleaning_windows(user, date_min, date_max)

    # Step 2: Identify Overlaps
    overlaps = find_cleaning_overlaps(date_min, date_max)

    # Step 3: Assign Cleaning Dates
    cleaning_dates = assign_cleaning_dates(overlaps)

    # Step 4: Update Database Accordingly

    # Fetch the current cleaning dates from the database
    current_cleaning_dates = CleaningSchedule.objects.filter(booking_id__in=cleaning_dates.keys()).values('booking_id', 'cleaning_date')
    

    # Convert the queryset to a dictionary for easy comparison
    current_cleaning_dates_dict = {item['booking_id']: item['cleaning_date'] for item in current_cleaning_dates}
    logger.info(f"current_cleaning_dates_dict: {current_cleaning_dates_dict}")

    # Iterate over the new cleaning dates
    for booking_id, new_cleaning_date in cleaning_dates.items():
        # If the new cleaning date is different from the current cleaning date, update or create the record
        if current_cleaning_dates_dict.get(booking_id) != new_cleaning_date:
            CleaningSchedule.objects.filter(booking_id=booking_id).update(cleaning_date=new_cleaning_date)


def calculate_cleaning_windows(user, date_min, date_max):
    logger.info("Calculating cleaning windows for each booking.")

    # Fetch bookings that are either within the date range or might influence cleaning windows around it
    all_bookings = Booking.objects.filter(
        apartment__owner=user,
        check_out_date__gte=date_min,
        check_in_date__lte=date_max
    ).order_by('apartment_id', 'check_out_date')

    for booking in all_bookings:
        apartment_id = booking.apartment_id
        check_out_date = booking.check_out_date

        # Start date of the cleaning window is the check-out date of the current booking
        window_start = check_out_date

        # Find the next booking for the same apartment
        next_booking = None
        for next_booking_candidate in all_bookings:
            if next_booking_candidate.apartment_id == apartment_id and next_booking_candidate.check_in_date > check_out_date:
                next_booking = next_booking_candidate
                break

        # Set the end date of the cleaning window
        if next_booking:
            window_end = next_booking.check_in_date
        else:
            # If there is no next booking for the same apartment, set the window end to None (open-ended)
            window_end = None

        # Save the cleaning window to the database
        CleaningSchedule.objects.update_or_create(
            booking_id=booking.id,
            defaults={
                'window_start': window_start,
                'window_end': window_end
            }
        )
        # Log the cleaning window for the current booking
        logger.info(f"Booking ID {booking.id} for Apartment {apartment_id} has a cleaning window from {window_start} to {'open-ended' if window_end is None else window_end}")
    
def find_cleaning_overlaps(date_min, date_max):

    logger.info("Finding cleaning overlaps within the specified date range.")

    # Fetch all cleaning schedules that could potentially overlap with the date range
    cleaning_schedules = CleaningSchedule.objects.filter(
        window_start__lte=date_max, 
        window_end__gte=date_min
    )

    # Create an interval tree
    tree = intervaltree.IntervalTree()

    # Populate the interval tree with cleaning windows
    for schedule in cleaning_schedules:
        booking_id = schedule.booking_id
        start = schedule.window_start
        # Treat None as a time that is later than all other times
        end = schedule.window_end if schedule.window_end is not None else datetime.max
        tree[start:end] = booking_id
        logger.debug(f'Added booking {booking_id} to the interval tree')

    # Initialize a set to store unique overlaps
    overlaps = set()

    # Check for overlaps
    for interval in tree:
        overlapping_intervals = [i for i in tree if i.overlaps(interval)]
        if len(overlapping_intervals) > 1:
            booking_ids = sorted(overlap.data for overlap in overlapping_intervals)
            # Find the smallest overlapping time frame
            overlap_start = max(overlap.begin for overlap in overlapping_intervals)
            overlap_end = min(overlap.end for overlap in overlapping_intervals)
            overlaps.add((tuple(booking_ids), overlap_start, overlap_end))

    # Log each unique overlap
    for booking_ids, overlap_start, overlap_end in overlaps:
        logger.info(f'Found overlap between bookings {booking_ids} from {overlap_start} to {overlap_end}')

    logger.info(f"overlaps: {list(overlaps)}")
    return list(overlaps)

def assign_cleaning_dates(overlaps):

    # Fetch all cleaning schedules
    cleaning_schedules = CleaningSchedule.objects.all()

    # Create a dictionary to store the cleaning windows
    cleaning_windows = {schedule.booking_id: (schedule.window_start, schedule.window_end) for schedule in cleaning_schedules}

    # Create a dictionary to store the cleaning dates for each booking
    cleaning_dates = {}
    logger.info('Starting to assign cleaning dates.')

    # Iterate over the cleaning windows
    for booking_id, (start, end) in cleaning_windows.items():
        logger.debug(f'Processing booking {booking_id} with cleaning window from {start} to {end}.')
        # If there are no overlaps for this booking, assign the end date as the cleaning date
        if not any(booking_id in booking_ids for booking_ids, _, _ in overlaps):
            cleaning_dates[booking_id] = end if end is not None else start
            logger.debug(f'No overlaps found for booking {booking_id}. Assigned cleaning date: {end}.')
        else:
            # If there are overlaps, find the earliest start date among the overlaps and assign it as the cleaning date
            overlap_start_dates = [overlap_start for booking_ids, overlap_start, _ in overlaps if booking_id in booking_ids]
            earliest_overlap_start_date = min(overlap_start_dates) if overlap_start_dates else None
            cleaning_dates[booking_id] = earliest_overlap_start_date
            logger.debug(f'Overlaps found for booking {booking_id}. Assigned cleaning date: {earliest_overlap_start_date}.')

    # Log the cleaning dates
    for booking_id, cleaning_date in cleaning_dates.items():
        logger.info(f'Assigned cleaning date for booking {booking_id}: {cleaning_date}')

    logger.info(f'cleaning_dates: {cleaning_dates}')
    return cleaning_dates
