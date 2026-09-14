import pandas as pd
import numpy as np

events_df = pd.read_csv("dataset/financial_events.csv")
images_df = pd.read_csv("dataset/images.csv")
profiles_df = pd.read_csv("dataset/financial_profiles.csv")

u_id = "user_01"
u_prof = profiles_df[profiles_df["user_id"] == u_id].iloc[0]
u_events = events_df[events_df["user_id"] == u_id].copy()
u_events = u_events[~u_events["status"].isin(["cancelled", "failed"])]

req_date = pd.to_datetime("2024-03-03")
start_bal = 58481.1

# Manually build cash flows using ONLY scheduled/pending/confirmed events 
# (no recurring inference at all - use pure event-driven approach)
print("ALL user_01 events:")
print(u_events[["event_id","description","category","direction","amount","settlement_date","status","flexibility"]].to_string())
