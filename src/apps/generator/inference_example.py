# Plan of attack:
# load models
# Loop:
# * generate new datarow per household
# * do inference for each model and concat this leakage label together with the new generated water consumption, household_id and timestamp to the Pandas dataframes

model_directory = "models"

# Load models into WaterLeakDetector instances
loaded_model_dict = {}
for h_id in household_ids:
    detector = WaterLeakDetector()
    detector.load(model_directory=model_directory, household_id=h_id)
    loaded_model_dict[h_id] = detector

# Initialize empty DataFrames to accumulate streaming prediction results
# NOTE: This will be replaced by Postgres TimescaleDB in the future
streaming_results_per_household = {h_id: pd.DataFrame() for h_id in household_ids}

# Streaming Loop (Simulating 100 incoming hourly steps across all households)
num_streaming_hours = 100
start_inference_date_str = "2026-01-01"

for h_idx, h_id in enumerate(household_ids):
    category = h_id.split("_")[0].lower()
    country = h_id.split("_")[1].lower()
    generation_func = generation_functions.get(category, generate_single_water_consumption)

    # Detector for this household
    detector = loaded_model_dict[h_id]

    # Historical training context buffer for streaming persistence
    history_buffer = training_data_per_household_dict[h_id]

    # Generate sequential dates for streaming iterations
    streaming_dates = pd.date_range(
        start=start_inference_date_str,
        periods=num_streaming_hours,
        freq="h"
    )

    for step_idx, current_timestamp in enumerate(streaming_dates):
        # Generate single incoming row for this specific hour
        single_row_df = next(generation_func(
            date_range=[current_timestamp],
            start_date_str=current_timestamp.strftime("%Y-%m-%d"),
            seed=42 + h_idx,
            household_id=h_id,
            vacation_probability=0.05,
            has_leakage_prob=0.30,  # 10% chance of triggering a leak during inference
            stream=True,
            country=country,
            history_buffer_df=history_buffer
        ))

        # Run inference using the loaded detector
        prediction_df = detector.predict_hourly(single_row_df, use_isolation_forest=True)

        # Concatenate result to the household's streaming DataFrame
        # NOTE: this will instead be inserted into a Postgres TimescaleDB table
        streaming_results_per_household[h_id] = pd.concat(
            [streaming_results_per_household[h_id], prediction_df],
            ignore_index=True
        )

        # Update historical buffer so streaming state maintains continuity
        history_buffer = pd.concat([history_buffer, single_row_df], ignore_index=True)


# Print the last 100 rows sorted by timestamp
for h_id, results_df in streaming_results_per_household.items():
    print(f"\n==========================================")
    print(f" Last 100 Streaming Predictions for Household: {h_id}")
    print(f"==========================================")
    print(results_df.tail(100).to_string(index=False))
