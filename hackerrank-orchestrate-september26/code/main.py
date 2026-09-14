"""Generate deterministic Buy or Wait? predictions from the participant dataset."""

from pathlib import Path
import argparse

import pandas as pd

from engine.cashflow_model import CashFlowModel
from engine.fx import FXConverter
from engine.image_reader import fill_missing_event_amounts
from engine.messages_parser import MessageProcessor
from engine.plan_evaluator import PlanEvaluator


OUTPUT_COLUMNS = [
    "request_id", "amount_safe_to_pay", "affordability_status",
    "recommended_payment_method", "payment_plan",
    "earliest_date_for_full_payment", "spending_changes_needed",
    "decision_explanation",
]


def explanation(request, prediction):
    method = prediction["recommended_payment_method"]
    safe = prediction["amount_safe_to_pay"]
    if method == "full_payment":
        suffix = " with permitted spending changes" if prediction["spending_changes_needed"] != "none" else ""
        return f"A full payment of {request['requested_amount']:g} is safe on the request date{suffix}."
    if method == "installments":
        return "The supplied installment schedule stays above the required minimum balance."
    if method == "partial_payment":
        return f"Pay {safe:g} now and the remaining balance on the first safe full-payment date."
    if method == "wait":
        return f"Waiting until {prediction['earliest_date_for_full_payment']} protects the minimum balance."
    return "No eligible payment plan keeps the projected balance above the required minimum."


def generate(dataset_dir: Path, output_path: Path) -> pd.DataFrame:
    events = pd.read_csv(dataset_dir / "financial_events.csv")
    images = pd.read_csv(dataset_dir / "images.csv")
    profiles = pd.read_csv(dataset_dir / "financial_profiles.csv")
    requests = pd.read_csv(dataset_dir / "requests.csv")
    options = pd.read_csv(dataset_dir / "request_payment_options.csv")
    messages = pd.read_csv(dataset_dir / "messages.csv")
    fx = FXConverter(pd.read_csv(dataset_dir / "exchange_rates.csv"))
    events = fill_missing_event_amounts(events, images)
    message_processor = MessageProcessor(messages)
    evaluator = PlanEvaluator(fx)
    profiles_by_user = profiles.set_index("user_id")
    events_by_user = {user_id: frame for user_id, frame in events.groupby("user_id")}
    rows = []

    for _, request in requests.iterrows():
        profile = profiles_by_user.loc[request["user_id"]]
        user_events = events_by_user.get(request["user_id"], events.iloc[0:0])
        adjustments = message_processor.process_user_messages(request["user_id"], request["request_date"])
        model = CashFlowModel(profile, user_events, fx, adjustments)
        model.build(request["request_date"])
        prediction = evaluator.evaluate_request(request, profile, model, options)
        prediction["amount_safe_to_pay"] = round(float(prediction["amount_safe_to_pay"]), 2)
        prediction["decision_explanation"] = explanation(request, prediction)
        rows.append({column: prediction.get(column, "") if column != "request_id" else request["request_id"] for column in OUTPUT_COLUMNS})

    result = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    result.to_csv(output_path, index=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("dataset"))
    parser.add_argument("--output", type=Path, default=Path("output.csv"))
    args = parser.parse_args()
    result = generate(args.dataset, args.output)
    print(f"Wrote {len(result)} predictions to {args.output}")


if __name__ == "__main__":
    main()
