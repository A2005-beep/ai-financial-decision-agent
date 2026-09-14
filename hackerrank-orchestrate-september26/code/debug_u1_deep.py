import pandas as pd
from engine.image_reader import fill_missing_event_amounts
from engine.fx import FXConverter
from engine.messages_parser import MessageProcessor

events_df = pd.read_csv("dataset/financial_events.csv")
images_df = pd.read_csv("dataset/images.csv")
profiles_df = pd.read_csv("dataset/financial_profiles.csv")
fx_df = pd.read_csv("dataset/exchange_rates.csv")
messages_df = pd.read_csv("dataset/messages.csv")
samples_df = pd.read_csv("dataset/sample_requests.csv")

events_df = fill_missing_event_amounts(events_df, images_df)

u_id = "user_01"
u_events = events_df[events_df["user_id"] == u_id].sort_values("settlement_date")

# Show events from request_date 2024-03-03 onward (only settled + scheduled + pending)
req_date = "2024-03-03"
future = u_events[u_events["settlement_date"] >= req_date]
print("Events from 2024-03-03 onwards:")
print(future[["event_id","description","category","direction","amount","settlement_date","status","flexibility"]].to_string())

# Now let us manually simulate without any recurring projection
# just using scheduled + pending + day-0 settled events
print("\n\nGT analysis: If amount_safe_to_pay = 25256 (full requested)")
print("That means paying 25256 on day0 leaves min balance >= 18000 throughout 90 days")
print("Balance after day0 payment = 58481.1 - 25256 =", 58481.1 - 25256)
print("After April 2 rent (-5148):", 58481.1 - 25256 - 5148, "vs min 18000")
