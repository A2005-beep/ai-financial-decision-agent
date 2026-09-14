import pandas as pd

class FXConverter:
    def __init__(self, fx_df):
        self.fx_df = fx_df
        # Create lookup: (rate_date, from_currency, to_currency) -> rate
        self.rates = {}
        for _, row in fx_df.iterrows():
            d = str(row['rate_date'])
            fc = str(row['from_currency'])
            tc = str(row['to_currency'])
            r = float(row['rate'])
            self.rates[(d, fc, tc)] = r
            if r > 0:
                self.rates[(d, tc, fc)] = 1.0 / r

    def convert(self, amount, from_curr, to_curr, date_str):
        if from_curr == to_curr or amount == 0:
            return amount
        d = str(date_str)
        # Direct date match
        if (d, from_curr, to_curr) in self.rates:
            return amount * self.rates[(d, from_curr, to_curr)]
        
        # Match nearest available date for this currency pair
        matching_dates = [k[0] for k in self.rates.keys() if k[1] == from_curr and k[2] == to_curr]
        if matching_dates:
            closest_date = min(matching_dates, key=lambda x: abs(pd.to_datetime(x) - pd.to_datetime(d)))
            return amount * self.rates[(closest_date, from_curr, to_curr)]
        
        # Try indirect via USD or EUR
        for mid in ['USD', 'EUR']:
            pair1 = (d, from_curr, mid)
            pair2 = (d, mid, to_curr)
            if pair1 in self.rates and pair2 in self.rates:
                return amount * self.rates[pair1] * self.rates[pair2]
                
        return amount
