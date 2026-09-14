import pandas as pd
import numpy as np
from itertools import combinations


def format_amount(value):
    """Render a CSV plan amount without scientific notation."""
    value = round(float(value), 2)
    return f"{value:.2f}" if value % 1 else str(int(value))

class PlanEvaluator:
    def __init__(self, fx_converter):
        self.fx = fx_converter

    def find_amount_safe_to_pay(self, cashflow_model, request_date, requested_amount):
        """
        Find the maximum safe payment on request_date (capped at requested_amount).
        Binary search between 0 and requested_amount.
        """
        min_b_unpaid, _ = cashflow_model.simulate_90_days(request_date)
        # Without any payment, the minimum buffer available across 90 days is min_b_unpaid - min_balance
        safe_buffer = max(0.0, min_b_unpaid - cashflow_model.min_balance)
        return min(requested_amount, round(safe_buffer, 2))

    def find_earliest_date_for_full_payment(self, cashflow_model, request_date, requested_amount):
        """
        Find the earliest date in the 90-day forecast where paying requested_amount in full
        keeps balance >= min_balance for the entire 90-day period.
        """
        req_dt = pd.to_datetime(request_date)
        for offset in range(91):
            check_date = (req_dt + pd.Timedelta(days=offset)).strftime('%Y-%m-%d')
            min_b, _ = cashflow_model.simulate_90_days(request_date, candidate_payments={check_date: requested_amount})
            if min_b >= cashflow_model.min_balance - 1e-4:
                return check_date
        return None

    def evaluate_request(self, request_row, profile_row, cashflow_model, payment_options_df):
        req_id = request_row['request_id']
        req_date = str(request_row['request_date'])
        req_amount = float(request_row['requested_amount'])
        desired_date = str(request_row['desired_completion_date'])
        allows_partial = str(request_row['allows_partial_payment']).lower() in ['true', '1', 'yes']
        
        allowed_methods = [m.strip() for m in str(profile_row['payment_methods_user_will_consider']).split('|')]
        max_inst_months = profile_row['max_installment_months']
        if pd.notna(max_inst_months):
            max_inst_months = float(max_inst_months)
        else:
            max_inst_months = 0.0

        # Step 1: Calculate amount_safe_to_pay & earliest_date_for_full_payment (without spending changes)
        amount_safe = self.find_amount_safe_to_pay(cashflow_model, req_date, req_amount)
        earliest_full_date = self.find_earliest_date_for_full_payment(cashflow_model, req_date, req_amount)

        # Step 2: Generate candidate plans
        candidates = []

        # Candidate A: Full payment today
        if 'full_payment' in allowed_methods and amount_safe >= req_amount - 1e-4:
            candidates.append({
                'status': 'affordable_now',
                'method': 'full_payment',
                'plan': f"{req_date}:{format_amount(req_amount)}",
                'completion_date': req_date,
                'spending_changes': 'none',
                'total_cost': req_amount,
                'first_payment_date': req_date,
                'num_payments': 1,
                'option_id': 'option_00'
            })

        # Candidate B: Installment options
        if 'installments' in allowed_methods and max_inst_months > 0:
            req_opts = payment_options_df[payment_options_df['request_id'] == req_id]
            for _, opt in req_opts.iterrows():
                if opt['payment_method'] == 'installments':
                    num_p = int(opt['number_of_payments'])
                    p_amt = float(opt['payment_amount'])
                    first_p_date = str(opt['first_payment_date'])
                    freq = int(opt['payment_frequency_days']) if pd.notna(opt['payment_frequency_days']) else 30
                    total_payable = float(opt['total_payable_amount'])
                    
                    # Check if within max_installment_months (months approx num_p * freq / 30)
                    duration_months = (num_p * freq) / 30.0
                    if duration_months <= max_inst_months + 0.5:
                        # Build payments schedule
                        p_dict = {}
                        p_list = []
                        cur_p_dt = pd.to_datetime(first_p_date)
                        last_p_date = first_p_date
                        for _ in range(num_p):
                            ds = cur_p_dt.strftime('%Y-%m-%d')
                            p_dict[ds] = p_dict.get(ds, 0.0) + p_amt
                            p_list.append(f"{ds}:{format_amount(p_amt)}")
                            last_p_date = ds
                            cur_p_dt += pd.Timedelta(days=freq)
                        
                        # Test if safe over 90 days
                        min_b, _ = cashflow_model.simulate_90_days(req_date, candidate_payments=p_dict)
                        if min_b >= cashflow_model.min_balance - 1e-4:
                            candidates.append({
                                'status': 'affordable_with_plan',
                                'method': 'installments',
                                'plan': '|'.join(p_list),
                                'completion_date': last_p_date,
                                'spending_changes': 'none',
                                'total_cost': total_payable,
                                'first_payment_date': first_p_date,
                                'num_payments': num_p,
                                'option_id': str(opt['payment_option_id'])
                            })

        # Candidate C: Partial payment
        if ('partial_payment' in allowed_methods and allows_partial and 
            amount_safe > 0 and amount_safe < req_amount and 
            earliest_full_date is not None and earliest_full_date <= desired_date):
            rem_amt = round(req_amount - amount_safe, 2)
            p1 = f"{req_date}:{format_amount(amount_safe)}"
            p2 = f"{earliest_full_date}:{format_amount(rem_amt)}"
            candidates.append({
                'status': 'affordable_with_plan',
                'method': 'partial_payment',
                'plan': f"{p1}|{p2}",
                'completion_date': earliest_full_date,
                'spending_changes': 'none',
                'total_cost': req_amount,
                'first_payment_date': req_date,
                'num_payments': 2,
                'option_id': 'option_partial'
            })

        # Candidate D: Wait (full payment later)
        if 'full_payment' in allowed_methods and earliest_full_date is not None and earliest_full_date > req_date:
            candidates.append({
                'status': 'affordable_later',
                'method': 'wait',
                'plan': f"{earliest_full_date}:{format_amount(req_amount)}",
                'completion_date': earliest_full_date,
                'spending_changes': 'none',
                'total_cost': req_amount,
                'first_payment_date': earliest_full_date,
                'num_payments': 1,
                'option_id': 'option_wait'
            })

        # Step 3: Check permitted changes to flexible recurring expenses. A
        # change is considered only when an unmodified full payment is unsafe.
        willing_stop = [c.strip() for c in str(profile_row['expense_categories_user_is_willing_to_stop']).split('|') if pd.notna(profile_row['expense_categories_user_is_willing_to_stop'])]
        willing_reduce = [c.strip() for c in str(profile_row['expense_categories_user_is_willing_to_reduce']).split('|') if pd.notna(profile_row['expense_categories_user_is_willing_to_reduce'])]
        
        full_payment_safe = any(c['method'] == 'full_payment' for c in candidates)
        if 'full_payment' in allowed_methods and not full_payment_safe:
            actions = []
            for rule in cashflow_model._monthly_rules:
                if rule['direction'] != 'debit':
                    continue
                category = rule['category']
                flexibility = rule['flexibility'].lower()
                event_id = rule['event_id']
                if category in willing_stop and 'stoppable' in flexibility:
                    actions.append((event_id, 'stop', f"stop:{event_id}"))
                if category in willing_reduce and 'reducible' in flexibility and rule['min_allowed'] is not None:
                    minimum = round(float(rule['min_allowed']), 2)
                    actions.append((event_id, minimum, f"reduce_to:{event_id}:{format_amount(minimum)}"))

            for count in range(1, min(3, len(actions)) + 1):
                for chosen in combinations(actions, count):
                    if len({item[0] for item in chosen}) != len(chosen):
                        continue
                    changes = {event_id: value for event_id, value, _ in chosen}
                    min_b, _ = cashflow_model.simulate_90_days(
                        req_date, candidate_payments={req_date: req_amount}, spending_changes=changes
                    )
                    if min_b >= cashflow_model.min_balance - 1e-4:
                        candidates.append({
                            'status': 'affordable_with_plan',
                            'method': 'full_payment',
                            'plan': f"{req_date}:{format_amount(req_amount)}",
                            'completion_date': req_date,
                            'spending_changes': '|'.join(item[2] for item in chosen),
                            'total_cost': req_amount,
                            'first_payment_date': req_date,
                            'num_payments': 1,
                            'option_id': 'option_changes',
                        })

        # Step 4: Rank candidates strictly according to the 6 rules
        # 1. Completes by desired_completion_date
        # 2. Requires no spending changes
        # 3. Minimizes total amount paid
        # 4. Starts payment earlier
        # 5. Uses fewer payments
        # 6. Tie-breaker: lowest payment_option_id
        
        if candidates:
            # Sort candidates
            def sort_key(c):
                on_time = 0 if c['completion_date'] <= desired_date else 1
                no_changes = 0 if c['spending_changes'] == 'none' else 1
                return (on_time, no_changes, c['total_cost'], c['first_payment_date'], c['num_payments'], c['option_id'])
            
            candidates.sort(key=sort_key)
            best = candidates[0]
            
            # If best candidate does not complete by desired_completion_date and is not wait, check if not_affordable
            if best['method'] == 'wait' and best['completion_date'] > desired_date:
                # Still affordable_later
                pass
            return {
                'amount_safe_to_pay': amount_safe,
                'affordability_status': best['status'],
                'recommended_payment_method': best['method'],
                'payment_plan': best['plan'],
                'earliest_date_for_full_payment': earliest_full_date if earliest_full_date else '',
                'spending_changes_needed': best['spending_changes']
            }
        else:
            return {
                'amount_safe_to_pay': amount_safe,
                'affordability_status': 'not_affordable',
                'recommended_payment_method': 'not_recommended',
                'payment_plan': 'none',
                'earliest_date_for_full_payment': earliest_full_date if earliest_full_date else '',
                'spending_changes_needed': 'none'
            }
