import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta


def _sample_leakage_volume():
    return round(max(1, np.random.normal(1.5, 0.5)))

def generate_couple_water_consumption(date_range=None, start_date_str="2024-01-01", years=2, seed=42, household_id='couple_1', vacation_probability=0.05, has_leakage=False, stream=False):
    """
    Generates synthetic water consumption for a couple.
    Can generate an arbitrary interval (even 1 single hour) or a default 2-year range.

    :param date_range: Explicit pd.DatetimeIndex to generate data for. If None, uses start_date_str and years.
    :param start_date_str: Start date for default generation if date_range is None.
    :param years: Duration in years for default generation if date_range is None.
    :param seed: Random seed for reproducibility. Set to None to disable.
    :param household_id: Identifier for this household instance, used as a label in the output DataFrame.
    :param vacation_probability: Daily probability that all household members are absent (0.0-1.0). On vacation days, human consumption is zero; the water softener still runs on its timer.
    :param has_leakage: If True, a small leakage volume replaces every zero, day and night, simulating a continuous pipe/meter leak.
    :param stream: If False (default), returns a complete DataFrame. If True, returns a generator that yields one single-row DataFrame per hour.
    """
    # Initialize default date range if none is provided
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + relativedelta(years=years)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]

    # Seed for reproducibility: same seed produces identical output across runs, enabling stable train/val/test splits
    if seed is not None:
        np.random.seed(seed)

    # Anchor date to keep track of the water softener's 12-day cycle accurately over time
    base_start_date_str = start_date_str
    anchor_date = datetime.datetime.strptime(base_start_date_str, "%Y-%m-%d").date()

    # Average volume (L) when active. Hours 1-4 are 0.0 to model deep sleep: no consumption expected.
    # Zero-profile hours that still fire is_active (rare, due to low but non-zero probabilities) are
    # handled by the base_volume == 0.0 guard below, preventing noise from inflating them to ≥ 1 L.
    weekday_profile = {
        0: 1.5, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
        6: 5.5, 7: 4.5, 8: 6.0, 9: 7.5, 10: 7.0, 11: 6.5,
        12: 8.5, 13: 6.5, 14: 6.5, 15: 5.0, 16: 3.5, 17: 4.0,
        18: 6.0, 19: 6.5, 20: 8.0, 21: 6.5, 22: 3.5, 23: 1.5
    }
    weekend_profile = {
        0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
        6: 5.5, 7: 5.0, 8: 5.0, 9: 7.0, 10: 9.5, 11: 10.5,
        12: 11.0, 13: 9.5, 14: 8.5, 15: 6.0, 16: 2.5, 17: 2.5,
        18: 2.5, 19: 3.5, 20: 8.5, 21: 5.5, 22: 4.0, 23: 2.0
    }

    # Probability of ANY water activity happening in that hour
    weekday_activity_prob = {
        0: 0.20, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.15,
        6: 0.75, 7: 0.65, 8: 0.75, 9: 0.85, 10: 0.85, 11: 0.85,
        12: 0.85, 13: 0.80, 14: 0.80, 15: 0.75, 16: 0.60, 17: 0.60,
        18: 0.85, 19: 0.85, 20: 0.85, 21: 0.75, 22: 0.55, 23: 0.30
    }
    weekend_activity_prob = {
        0: 0.25, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.10,
        6: 0.70, 7: 0.70, 8: 0.70, 9: 0.80, 10: 0.90, 11: 0.90,
        12: 0.90, 13: 0.85, 14: 0.85, 15: 0.75, 16: 0.40, 17: 0.45,
        18: 0.50, 19: 0.60, 20: 0.85, 21: 0.70, 22: 0.60, 23: 0.30
    }

    water_softener_cycle = 12

    def _iter():
        current_day = None
        is_vacation_day = False
        for dt in date_range:
            hour = dt.hour
            is_weekend = dt.dayofweek >= 5
            # Calculate days since the absolute anchor date to ensure cycle consistency
            days_since_anchor = (dt.date() - anchor_date).days

            # Determine once per day whether the household is on vacation
            if dt.date() != current_day:
                current_day = dt.date()
                is_vacation_day = np.random.rand() < vacation_probability

            # Check if the water softener runs tonight
            if days_since_anchor % water_softener_cycle == 11 and hour in [3, 4]:
                volume = (24 if hour == 3 else 40) + np.random.randint(-2, 3)
                yield dt, round(volume)
                continue

            if is_vacation_day:
                yield dt, _sample_leakage_volume() if has_leakage else 0
                continue

            prob_profile = weekend_activity_prob if is_weekend else weekday_activity_prob
            vol_profile = weekend_profile if is_weekend else weekday_profile

            is_active = np.random.rand() < prob_profile[hour]

            if not is_active:
                yield dt, _sample_leakage_volume() if has_leakage else 0
            else:
                base_volume = vol_profile[hour]
                if base_volume == 0.0:
                    yield dt, _sample_leakage_volume() if has_leakage else 0
                else:
                    # Peaks in July: couples use more water in summer (garden, outdoor activities).
                    seasonal_factor = 1.0 + 0.2 * np.cos(2 * np.pi * (dt.month - 7) / 12)
                    volume = base_volume * seasonal_factor
                    # Noise std dev is lowest for couples (10%): two-person routine is more predictable.
                    # Ordering across types: couple (10%) < family (15%) < single (20%).
                    noise = np.random.normal(0, max(0.5, volume * 0.10))
                    yield dt, round(max(1, volume + noise))

    if stream:
        return (pd.DataFrame({'Timestamp': [dt], 'Volume_Liter': [vol], 'household_id': household_id})
                for dt, vol in _iter())

    timestamps, volumes = [], []
    for dt, vol in _iter():
        timestamps.append(dt)
        volumes.append(vol)
    return pd.DataFrame({'Timestamp': timestamps, 'Volume_Liter': volumes, 'household_id': household_id})


def generate_family_water_consumption(date_range=None, start_date_str="2024-01-01", years=2, seed=42, household_id='family_1', vacation_probability=0.05, has_leakage=False, stream=False):
    """
    Generates synthetic water consumption for a family.
    Can generate an arbitrary interval (even 1 single hour) or a default 2-year range.

    :param date_range: Explicit pd.DatetimeIndex to generate data for. If None, uses start_date_str and years.
    :param start_date_str: Start date for default generation if date_range is None.
    :param years: Duration in years for default generation if date_range is None.
    :param seed: Random seed for reproducibility. Set to None to disable.
    :param household_id: Identifier for this household instance, used as a label in the output DataFrame.
    :param vacation_probability: Daily probability that all household members are absent (0.0-1.0). On vacation days, human consumption is zero; the water softener still runs on its timer.
    :param has_leakage: If True, a small leakage volume replaces every zero, day and night, simulating a continuous pipe/meter leak.
    :param stream: If False (default), returns a complete DataFrame. If True, returns a generator that yields one single-row DataFrame per hour.
    """
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + relativedelta(years=years)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]

    # Seed for reproducibility: same seed produces identical output across runs, enabling stable train/val/test splits
    if seed is not None:
        np.random.seed(seed)

    # Anchor date to keep track of the water softener's 4-day cycle accurately over time
    base_start_date_str = start_date_str
    anchor_date = datetime.datetime.strptime(base_start_date_str, "%Y-%m-%d").date()

    # Hours 1-4 are 0.0: deep sleep, no consumption expected. See zero-guard in the loop body.
    weekday_profile = {
        0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 2.5,
        6: 8.0, 7: 25.0, 8: 20.0, 9: 10.0, 10: 8.0, 11: 9.0,
        12: 14.0, 13: 10.0, 14: 8.0, 15: 10.0, 16: 15.0, 17: 24.0,
        18: 28.0, 19: 25.0, 20: 16.0, 21: 10.0, 22: 5.0, 23: 3.0
    }
    weekend_profile = {
        0: 3.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
        6: 4.0, 7: 8.0, 8: 16.0, 9: 22.0, 10: 26.0, 11: 25.0,
        12: 24.0, 13: 20.0, 14: 18.0, 15: 16.0, 16: 18.0, 17: 20.0,
        18: 24.0, 19: 22.0, 20: 18.0, 21: 12.0, 22: 7.0, 23: 4.0
    }

    weekday_activity_prob = {
        0: 0.25, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.20,
        6: 0.85, 7: 0.95, 8: 0.90, 9: 0.80, 10: 0.75, 11: 0.80,
        12: 0.90, 13: 0.80, 14: 0.75, 15: 0.80, 16: 0.85, 17: 0.95,
        18: 0.95, 19: 0.95, 20: 0.90, 21: 0.80, 22: 0.60, 23: 0.40
    }
    weekend_activity_prob = {
        0: 0.35, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.10,
        6: 0.50, 7: 0.75, 8: 0.90, 9: 0.95, 10: 0.95, 11: 0.95,
        12: 0.95, 13: 0.90, 14: 0.90, 15: 0.85, 16: 0.85, 17: 0.90,
        18: 0.95, 19: 0.95, 20: 0.95, 21: 0.85, 22: 0.70, 23: 0.50
    }

    water_softener_cycle = 4

    def _iter():
        current_day = None
        is_vacation_day = False
        for dt in date_range:
            hour = dt.hour
            is_weekend = dt.dayofweek >= 5
            days_since_anchor = (dt.date() - anchor_date).days

            # Determine once per day whether the household is on vacation
            if dt.date() != current_day:
                current_day = dt.date()
                is_vacation_day = np.random.rand() < vacation_probability

            # Family uses a larger softener unit: 40 L + 60 L per regeneration cycle (vs. 24+40 L for couple/single).
            if days_since_anchor % water_softener_cycle == 3 and hour in [2, 3]:
                volume = (40 if hour == 2 else 60) + np.random.randint(-3, 4)
                yield dt, round(volume)
                continue

            if is_vacation_day:
                yield dt, _sample_leakage_volume() if has_leakage else 0
                continue

            prob_profile = weekend_activity_prob if is_weekend else weekday_activity_prob
            vol_profile = weekend_profile if is_weekend else weekday_profile

            is_active = np.random.rand() < prob_profile[hour]

            if not is_active:
                yield dt, _sample_leakage_volume() if has_leakage else 0
            else:
                base_volume = vol_profile[hour]
                if base_volume == 0.0:
                    yield dt, _sample_leakage_volume() if has_leakage else 0
                else:
                    # Peaks in July: families use significantly more water in summer (children home, garden, pool).
                    seasonal_factor = 1.0 + 0.25 * np.cos(2 * np.pi * (dt.month - 7) / 12)
                    volume = base_volume * seasonal_factor
                    # Noise std dev 15%: more variable than couple (more occupants, less predictable overlap).
                    noise = np.random.normal(0, max(0.5, volume * 0.15))
                    yield dt, round(max(1, volume + noise))

    if stream:
        return (pd.DataFrame({'Timestamp': [dt], 'Volume_Liter': [vol], 'household_id': household_id})
                for dt, vol in _iter())

    timestamps, volumes = [], []
    for dt, vol in _iter():
        timestamps.append(dt)
        volumes.append(vol)
    return pd.DataFrame({'Timestamp': timestamps, 'Volume_Liter': volumes, 'household_id': household_id})


def generate_single_water_consumption(date_range=None, start_date_str="2024-01-01", years=2, seed=42, household_id='single_1', vacation_probability=0.05, has_leakage=False, stream=False):
    """
    Generates synthetic water consumption for a single-person household.
    Can generate an arbitrary interval (even 1 single hour) or a default 2-year range.

    :param date_range: Explicit pd.DatetimeIndex to generate data for. If None, uses start_date_str and years.
    :param start_date_str: Start date for default generation if date_range is None.
    :param years: Duration in years for default generation if date_range is None.
    :param seed: Random seed for reproducibility. Set to None to disable.
    :param household_id: Identifier for this household instance, used as a label in the output DataFrame.
    :param vacation_probability: Daily probability that the household member is absent (0.0-1.0). On vacation days, human consumption is zero; the water softener still runs on its timer.
    :param has_leakage: If True, a small leakage volume replaces every zero, day and night, simulating a continuous pipe/meter leak.
    :param stream: If False (default), returns a complete DataFrame. If True, returns a generator that yields one single-row DataFrame per hour.
    """
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + relativedelta(years=years)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]

    # Seed for reproducibility: same seed produces identical output across runs, enabling stable train/val/test splits
    if seed is not None:
        np.random.seed(seed)

    # Anchor date to keep track of the water softener's 24-day cycle accurately over time
    base_start_date_str = start_date_str
    anchor_date = datetime.datetime.strptime(base_start_date_str, "%Y-%m-%d").date()

    # Hours 1-5 (weekday) and 2-5 (weekend) are 0.0: deep sleep, no consumption expected.
    # See zero-guard in the loop body.
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

    water_softener_cycle = 24

    def _iter():
        current_day = None
        is_vacation_day = False
        for dt in date_range:
            hour = dt.hour
            is_weekend = dt.dayofweek >= 5
            days_since_anchor = (dt.date() - anchor_date).days

            # Determine once per day whether the household member is on vacation
            if dt.date() != current_day:
                current_day = dt.date()
                is_vacation_day = np.random.rand() < vacation_probability

            if days_since_anchor % water_softener_cycle == 23 and hour in [3, 4]:
                volume = (24 if hour == 3 else 40) + np.random.randint(-1, 2)
                yield dt, round(volume)
                continue

            if is_vacation_day:
                yield dt, _sample_leakage_volume() if has_leakage else 0
                continue

            prob_profile = weekend_activity_prob if is_weekend else weekday_activity_prob
            vol_profile = weekend_profile if is_weekend else weekday_profile

            is_active = np.random.rand() < prob_profile[hour]

            # Single-only: 20% chance of daytime absence on weekends (shopping, sports, social).
            # Intentionally absent from couple/family, it serves as an ML-differentiating feature.
            if is_weekend and (9 <= hour <= 21) and (np.random.rand() < 0.20):
                is_active = False

            if not is_active:
                yield dt, _sample_leakage_volume() if has_leakage else 0
            else:
                base_volume = vol_profile[hour]
                if base_volume == 0.0:
                    yield dt, _sample_leakage_volume() if has_leakage else 0
                else:
                    # Peaks in July: minor summer uptick (more showers, drinking water).
                    # Amplitude is small (0.1) since a single person has no garden or pool effect.
                    seasonal_factor = 1.0 + 0.1 * np.cos(2 * np.pi * (dt.month - 7) / 12)
                    volume = base_volume * seasonal_factor
                    # Noise std dev is highest for singles (20%): irregular lifestyle produces most variability.
                    noise = np.random.normal(0, max(0.5, volume * 0.20))
                    yield dt, round(max(1, volume + noise))

    if stream:
        return (pd.DataFrame({'Timestamp': [dt], 'Volume_Liter': [vol], 'household_id': household_id})
                for dt, vol in _iter())

    timestamps, volumes = [], []
    for dt, vol in _iter():
        timestamps.append(dt)
        volumes.append(vol)
    return pd.DataFrame({'Timestamp': timestamps, 'Volume_Liter': volumes, 'household_id': household_id})


# =====================================================================
# DEMONSTRATIE: HOE DE FLEXIBELE FUNCTIES TE GEBRUIKEN
# =====================================================================

if __name__ == "__main__":
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

    # CASE 4: Iteratieve modus: voeg 1 uur per keer toe aan de dataframe (stream=True)
    hourly_index = pd.date_range(start="2026-06-01 00:00:00", periods=5, freq='h')
    gen = generate_single_water_consumption(date_range=hourly_index, stream=True)
    accumulated = pd.DataFrame()
    print("\nCase 4 (Iteratief, 1 uur per keer):")
    for hourly_df in gen:
        accumulated = pd.concat([accumulated, hourly_df], ignore_index=True)
        print(accumulated.tail(1).to_string(index=False))
