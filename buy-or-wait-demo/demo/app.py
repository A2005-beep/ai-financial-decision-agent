"""
Buy or Wait? — an AI financial decision agent
Interactive demo built on top of a deterministic cash-flow forecasting engine.

Pick any of the 250 real requests in the dataset and watch the agent reconstruct
the user's financial state, forecast 90 days forward, and decide whether they
can safely afford what they're asking for.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from engine.cashflow_model import CashFlowModel
from engine.fx import FXConverter
from engine.image_reader import fill_missing_event_amounts
from engine.messages_parser import MessageProcessor
from engine.plan_evaluator import PlanEvaluator

DATASET_DIR = Path(__file__).parent / "dataset"

STATUS_COLORS = {
    "affordable_now": "🟢",
    "affordable_with_plan": "🟡",
    "affordable_later": "🟠",
    "not_affordable": "🔴",
}


@st.cache_data
def load_data():
    events = pd.read_csv(DATASET_DIR / "financial_events.csv")
    images = pd.read_csv(DATASET_DIR / "images.csv")
    profiles = pd.read_csv(DATASET_DIR / "financial_profiles.csv")
    requests = pd.read_csv(DATASET_DIR / "requests.csv")
    options = pd.read_csv(DATASET_DIR / "request_payment_options.csv")
    messages = pd.read_csv(DATASET_DIR / "messages.csv")
    rates = pd.read_csv(DATASET_DIR / "exchange_rates.csv")
    events = fill_missing_event_amounts(events, images)
    return events, profiles, requests, options, messages, rates


def format_money(amount, currency):
    try:
        return f"{currency} {float(amount):,.2f}"
    except (ValueError, TypeError):
        return f"{currency} {amount}"


def run_agent(request, profiles, events, options, messages, rates):
    fx = FXConverter(rates)
    message_processor = MessageProcessor(messages)
    evaluator = PlanEvaluator(fx)
    profile = profiles.set_index("user_id").loc[request["user_id"]]
    user_events = events[events["user_id"] == request["user_id"]]
    adjustments = message_processor.process_user_messages(request["user_id"], request["request_date"])
    model = CashFlowModel(profile, user_events, fx, adjustments)
    model.build(request["request_date"])
    prediction = evaluator.evaluate_request(request, profile, model, options)
    prediction["amount_safe_to_pay"] = round(float(prediction["amount_safe_to_pay"]), 2)
    _, daily_balances = model.simulate_90_days(request["request_date"])
    return profile, prediction, daily_balances


st.set_page_config(page_title="Buy or Wait? — AI Financial Agent", page_icon="💸", layout="centered")

st.title("💸 Buy or Wait?")
st.caption(
    "An AI financial decision agent that decides whether a user can safely afford a "
    "requested expense — accounting for recurring costs, pending payments, essential "
    "spending, confirmed income, and evidence buried in messages and receipts."
)

events, profiles, requests, options, messages, rates = load_data()

request_labels = {
    row["request_id"]: f"{row['request_id']} — {row['user_id']} — {row['request_type']} "
    f"({format_money(row['requested_amount'], profiles.set_index('user_id').loc[row['user_id'], 'home_currency'])})"
    for _, row in requests.iterrows()
}

selected_id = st.selectbox(
    "Choose a request from the dataset",
    options=list(request_labels.keys()),
    format_func=lambda rid: request_labels[rid],
)

request = requests[requests["request_id"] == selected_id].iloc[0]

st.markdown(f"> *\u201c{request['request_text']}\u201d*")

with st.spinner("Reconstructing financial state and forecasting 90 days forward..."):
    profile, prediction, daily_balances = run_agent(request, profiles, events, options, messages, rates)

currency = profile["home_currency"]
status = prediction["affordability_status"]
icon = STATUS_COLORS.get(status, "⚪")

col1, col2 = st.columns(2)
with col1:
    st.metric("Decision", f"{icon} {status.replace('_', ' ').title()}")
with col2:
    st.metric("Recommended method", prediction["recommended_payment_method"].replace("_", " ").title())

st.subheader("Details")
st.write(f"**Amount safe to pay today:** {format_money(prediction['amount_safe_to_pay'], currency)}")
st.write(f"**Requested amount:** {format_money(request['requested_amount'], currency)}")
if prediction["payment_plan"] and prediction["payment_plan"] != "none":
    st.write(f"**Payment plan:** {prediction['payment_plan'].replace('|', '  ·  ')}")
if prediction["earliest_date_for_full_payment"]:
    st.write(f"**Earliest date for full payment:** {prediction['earliest_date_for_full_payment']}")
if prediction["spending_changes_needed"] and prediction["spending_changes_needed"] != "none":
    st.write(f"**Suggested spending changes:** {prediction['spending_changes_needed'].replace('|', '  ·  ')}")

st.info(
    f"Pay {format_money(prediction['amount_safe_to_pay'], currency)} against a request of "
    f"{format_money(request['requested_amount'], currency)}, keeping the balance above the "
    f"required minimum of {format_money(profile['minimum_balance_to_keep'], currency)} "
    f"throughout the 90-day forecast."
)

st.subheader("90-day balance forecast")
forecast_df = pd.DataFrame(
    {"date": pd.to_datetime(list(daily_balances.keys())), "balance": list(daily_balances.values())}
).set_index("date")
st.line_chart(forecast_df)
st.caption(f"Dashed reference: minimum balance to keep is {format_money(profile['minimum_balance_to_keep'], currency)}.")

with st.expander("User's financial profile"):
    st.write(f"**Home currency:** {currency}")
    st.write(f"**Current available balance:** {format_money(profile['current_available_balance'], currency)}")
    st.write(f"**Minimum balance to keep:** {format_money(profile['minimum_balance_to_keep'], currency)}")
    st.write(f"**Financial priorities:** {profile['financial_priorities']}")
    st.write(f"**Payment methods considered:** {profile['payment_methods_user_will_consider']}")

st.divider()
st.caption(
    "Built for the HackerRank Orchestrate hackathon (Sept 2026). The agent reconstructs each "
    "user's cash flow from raw transaction history, salary schedules, pending payments, and "
    "evidence extracted from messages and receipt images — then simulates 90 days forward to "
    "find the safest payment plan. Deterministic and fully explainable: every decision traces "
    "back to a specific forecasted balance."
)
