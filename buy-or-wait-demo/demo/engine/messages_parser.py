import re
import pandas as pd

class MessageProcessor:
    def __init__(self, messages_df):
        self.messages_df = messages_df

    def process_user_messages(self, user_id, request_date, current_salary_amount=None):
        user_msgs = self.messages_df[self.messages_df['user_id'] == user_id]
        salary_override = None
        cancelled_events = set()
        amount_adjustments = {}

        for _, row in user_msgs.iterrows():
            text = str(row['message_text'])
            related_event = str(row['related_event_id']) if pd.notna(row['related_event_id']) else None
            
            # Check cancellations
            if any(w in text.lower() for w in ['cancelled', 'dibatalkan', 'reversed', 'voided']):
                if related_event:
                    cancelled_events.add(related_event)
            
            # Check unconfirmed bonuses/salary to ignore
            if any(w in text.lower() for w in ['menunggu', 'pending', 'not yet approved', 'unconfirmed', 'tentative']):
                continue
                
            # Check confirmed salary updates
            # English: monthly pay is EUR 1037.52, new base salary is USD 4500, etc.
            # Indonesian: Gaji bulanan Anda naik menjadi IDR 42750000, etc.
            sal_match = re.search(r'(?:gaji bulanan Anda naik menjadi|temporary monthly pay is|monthly pay is|new monthly salary is|gaji baru Anda adalah|salary is updated to)\s+([A-Z]{3})\s+([\d,.]+)', text, re.IGNORECASE)
            if sal_match:
                curr = sal_match.group(1)
                val_str = sal_match.group(2).replace(',', '')
                try:
                    salary_override = float(val_str)
                except ValueError:
                    pass

        return {
            'salary_override': salary_override,
            'cancelled_events': cancelled_events,
            'amount_adjustments': amount_adjustments
        }
