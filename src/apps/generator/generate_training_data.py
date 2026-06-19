import pandas as pd
import numpy as np
import datetime

def generate_couple_water_consumption(date_range=None, start_date_str="2024-01-01", years=2, base_start_date_str="2024-01-01"):
    """
    Generates synthetic water consumption for a couple.
    Can generate an arbitrary interval (even 1 single hour) or a default 2-year range.

    :param date_range: Explicit pd.DatetimeIndex to generate data for. If None, uses start_date_str and years.
    :param start_date_str: Start date for default generation if date_range is None.
    :param years: Duration in years for default generation if date_range is None.
    :param base_start_date_str: The anchor date used to keep the water softener's 12-day cycle synchronized.
    """
    # Initialize default date range if none is provided
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + datetime.timedelta(days=years*365)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]

    # Anchor date to keep track of the water softener cycle accurately over time
    anchor_date = datetime.datetime.strptime(base_start_date_str, "%Y-%m-%d").date()

    # Average volume when active
    weekday_profile = {
        0: 1.5, 1: 1.5, 2: 2.0, 3: 1.5, 4: 1.5, 5: 1.5,
        6: 5.5, 7: 4.5, 8: 6.0, 9: 7.5, 10: 7.0, 11: 6.5,
        12: 8.5, 13: 6.5, 14: 6.5, 15: 5.0, 16: 3.5, 17: 4.0,
        18: 6.0, 19: 6.5, 20: 8.0, 21: 6.5, 22: 3.5, 23: 1.5
    }
    weekend_profile = {
        0: 2.0, 1: 2.0, 2: 2.0, 3: 1.5, 4: 1.5, 5: 1.5,
        6: 5.5, 7: 5.0, 8: 5.0, 9: 7.0, 10: 9.5, 11: 10.5,
        12: 11.0, 13: 9.5, 14: 8.5, 15: 6.0, 16: 2.5, 17: 2.5,
        18: 2.5, 19: 3.5, 20: 8.5, 21: 5.5, 22: 4.0, 23: 2.0
    }

    # Probability of ANY water activity happening in that hour
    weekday_activity_prob = {
        0: 0.20, 1: 0.20, 2: 0.10, 3: 0.05, 4: 0.05, 5: 0.15,
        6: 0.75, 7: 0.65, 8: 0.75, 9: 0.85, 10: 0.85, 11: 0.85,
        12: 0.85, 13: 0.80, 14: 0.80, 15: 0.75, 16: 0.60, 17: 0.60,
        18: 0.85, 19: 0.85, 20: 0.85, 21: 0.75, 22: 0.55, 23: 0.30
    }
    weekend_activity_prob = {
        0: 0.25, 1: 0.25, 2: 0.10, 3: 0.05, 4: 0.05, 5: 0.10,
        6: 0.70, 7: 0.70, 8: 0.70, 9: 0.80, 10: 0.90, 11: 0.90,
        12: 0.90, 13: 0.85, 14: 0.85, 15: 0.75, 16: 0.40, 17: 0.45,
        18: 0.50, 19: 0.60, 20: 0.85, 21: 0.70, 22: 0.60, 23: 0.30
    }

    volumes = []
    water_softener_cycle = 12

    for dt in date_range:
        hour = dt.hour
        is_weekend = dt.dayofweek >= 5
        # Calculate days since the absolute anchor date to ensure cycle consistency
        days_since_anchor = (dt.date() - anchor_date).days

        # Check if the water softener runs tonight
        if days_since_anchor % water_softener_cycle == 11 and hour in [3, 4]:
            if hour == 3:
                volume = 24 + np.random.randint(-2, 3)
            elif hour == 4:
                volume = 40 + np.random.randint(-2, 3)
            volumes.append(round(volume))
            continue

        prob_profile = weekend_activity_prob if is_weekend else weekday_activity_prob
        vol_profile = weekend_profile if is_weekend else weekday_profile

        is_active = np.random.rand() < prob_profile[hour]

        if not is_active:
            volumes.append(0)
        else:
            base_volume = vol_profile[hour]
            seasonal_factor = 1.0 + 0.2 * np.cos(2 * np.pi * (dt.month - 1) / 12)
            volume = base_volume * seasonal_factor
            noise = np.random.normal(0, max(0.5, volume * 0.25))
            volume = max(1, volume + noise)
            volumes.append(round(volume))

    return pd.DataFrame({'Timestamp': date_range, 'Volume_Liter': volumes})


def generate_family_water_consumption(date_range=None, start_date_str="2024-01-01", years=2, base_start_date_str="2024-01-01"):
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + datetime.timedelta(days=years*365)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]

    anchor_date = datetime.datetime.strptime(base_start_date_str, "%Y-%m-%d").date()

    weekday_profile = {
        0: 2.0, 1: 1.5, 2: 1.0, 3: 1.0, 4: 1.0, 5: 2.5,
        6: 8.0, 7: 25.0, 8: 20.0, 9: 10.0, 10: 8.0, 11: 9.0,
        12: 14.0, 13: 10.0, 14: 8.0, 15: 10.0, 16: 15.0, 17: 24.0,
        18: 28.0, 19: 25.0, 20: 16.0, 21: 10.0, 22: 5.0, 23: 3.0
    }
    weekend_profile = {
        0: 3.0, 1: 2.0, 2: 1.0, 3: 1.0, 4: 1.0, 5: 1.5,
        6: 4.0, 7: 8.0, 8: 16.0, 9: 22.0, 10: 26.0, 11: 25.0,
        12: 24.0, 13: 20.0, 14: 18.0, 15: 16.0, 16: 18.0, 17: 20.0,
        18: 24.0, 19: 22.0, 20: 18.0, 21: 12.0, 22: 7.0, 23: 4.0
    }

    weekday_activity_prob = {
        0: 0.25, 1: 0.15, 2: 0.08, 3: 0.04, 4: 0.04, 5: 0.20,
        6: 0.85, 7: 0.95, 8: 0.90, 9: 0.80, 10: 0.75, 11: 0.80,
        12: 0.90, 13: 0.80, 14: 0.75, 15: 0.80, 16: 0.85, 17: 0.95,
        18: 0.95, 19: 0.95, 20: 0.90, 21: 0.80, 22: 0.60, 23: 0.40
    }
    weekend_activity_prob = {
        0: 0.35, 1: 0.20, 2: 0.08, 3: 0.04, 4: 0.04, 5: 0.10,
        6: 0.50, 7: 0.75, 8: 0.90, 9: 0.95, 10: 0.95, 11: 0.95,
        12: 0.95, 13: 0.90, 14: 0.90, 15: 0.85, 16: 0.85, 17: 0.90,
        18: 0.95, 19: 0.95, 20: 0.95, 21: 0.85, 22: 0.70, 23: 0.50
    }

    volumes = []
    water_softener_cycle = 4

    for dt in date_range:
        hour = dt.hour
        is_weekend = dt.dayofweek >= 5
        days_since_anchor = (dt.date() - anchor_date).days

        if days_since_anchor % water_softener_cycle == 3 and hour in [2, 3]:
            if hour == 2:
                volume = 24 + np.random.randint(-3, 4)
            elif hour == 3:
                volume = 40 + np.random.randint(-3, 4)
            volumes.append(round(volume))
            continue

        prob_profile = weekend_activity_prob if is_weekend else weekday_activity_prob
        vol_profile = weekend_profile if is_weekend else weekday_profile

        is_active = np.random.rand() < prob_profile[hour]

        if not is_active:
            volumes.append(0)
        else:
            base_volume = vol_profile[hour]
            seasonal_factor = 1.0 + 0.25 * np.cos(2 * np.pi * (dt.month - 7) / 12)
            volume = base_volume * seasonal_factor
            noise = np.random.normal(0, max(1.0, volume * 0.30))
            volume = max(1, volume + noise)
            volumes.append(round(volume))

    return pd.DataFrame({'Timestamp': date_range, 'Volume_Liter': volumes})


def generate_single_water_consumption(date_range=None, start_date_str="2024-01-01", years=2, base_start_date_str="2024-01-01"):
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + datetime.timedelta(days=years*365)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]

    anchor_date = datetime.datetime.strptime(base_start_date_str, "%Y-%m-%d").date()

    weekday_profile = {
        0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
        6: 3.0, 7: 10.0, 8: 4.0, 9: 2.0, 10: 2.0, 11: 2.0,
        12: 3.0, 13: 2.0, 14: 2.0, 15: 2.0, 16: 3.0, 17: 6.0,
        18: 8.0, 19: 9.0, 20: 7.0, 21: 6.0, 22: 4.0, 23: 2.5
    }
    weekend_profile = {
        0: 3.0, 1: 2.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
        6: 2.0, 7: 2.0, 8: 4.0, 9: 7.0, 10: 10.0, 11: 9.0,
        12: 8.0, 13: 6.0, 14: 5.0, 15: 4.0, 16: 4.0, 17: 5.0,
        18: 6.0, 19: 7.0, 20: 8.0, 21: 7.0, 22: 5.0, 23: 3.0
    }

    weekday_activity_prob = {
        0: 0.08, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.02,
        6: 0.35, 7: 0.80, 8: 0.50, 9: 0.10, 10: 0.05, 11: 0.05,
        12: 0.15, 13: 0.05, 14: 0.05, 15: 0.05, 16: 0.20, 17: 0.65,
        18: 0.80, 19: 0.85, 20: 0.75, 21: 0.65, 22: 0.45, 23: 0.20
    }
    weekend_activity_prob = {
        0: 0.15, 1: 0.08, 2: 0.02, 3: 0.00, 4: 0.00, 5: 0.01,
        6: 0.08, 7: 0.20, 8: 0.50, 9: 0.75, 10: 0.85, 11: 0.85,
        12: 0.75, 13: 0.60, 14: 0.55, 15: 0.50, 16: 0.50, 17: 0.55,
        18: 0.65, 19: 0.75, 20: 0.80, 21: 0.70, 22: 0.55, 23: 0.30
    }

    volumes = []
    water_softener_cycle = 24

    for dt in date_range:
        hour = dt.hour
        is_weekend = dt.dayofweek >= 5
        days_since_anchor = (dt.date() - anchor_date).days

        if days_since_anchor % water_softener_cycle == 23 and hour in [3, 4]:
            if hour == 3:
                volume = 24 + np.random.randint(-1, 2)
            elif hour == 4:
                volume = 40 + np.random.randint(-1, 2)
            volumes.append(round(volume))
            continue

        prob_profile = weekend_activity_prob if is_weekend else weekday_activity_prob
        vol_profile = weekend_profile if is_weekend else weekday_profile

        is_active = np.random.rand() < prob_profile[hour]

        if is_weekend and (9 <= hour <= 21) and (np.random.rand() < 0.20):
            is_active = False

        if not is_active:
            volumes.append(0)
        else:
            base_volume = vol_profile[hour]
            seasonal_factor = 1.0 + 0.1 * np.cos(2 * np.pi * (dt.month - 1) / 12)
            volume = base_volume * seasonal_factor
            noise = np.random.normal(0, max(0.5, volume * 0.40))
            volume = max(1, volume + noise)
            volumes.append(round(volume))

    return pd.DataFrame({'Timestamp': date_range, 'Volume_Liter': volumes})


# =====================================================================
# DEMONSTRATIE: HOE DE FLEXIBELE FUNCTIES TE GEBRUIKEN
# =====================================================================

# CASE 1: Genereer de standaard historische dataset van 2 jaar (Default)
couple_2years_df = generate_couple_water_consumption()
print(f"Case 1 (Standaard 2 jaar) aantal rijen: {len(couple_2years_df)}")

# CASE 2: Genereer exact 1 enkel datapunt voor het volgende uur (bijv. live streaming / realtime voorspelling)
next_hour_index = pd.date_range(start="2026-01-01 14:00:00", end="2026-01-01 14:00:00", freq='h')
single_datapoint_df = generate_couple_water_consumption(date_range=next_hour_index)
print("\nCase 2 (1 specifiek uur):")
print(single_datapoint_df)

# CASE 3: Genereer een specifiek aangepast interval (bijvoorbeeld exact 1 specifieke week)
custom_week_index = pd.date_range(start="2025-06-01 00:00:00", end="2025-06-07 23:00:00", freq='h')
week_df = generate_family_water_consumption(date_range=custom_week_index)
print(f"\nCase 3 (1 specifieke week in de toekomst) aantal rijen: {len(week_df)}")
