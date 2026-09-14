# Image extraction mapping for financial events with blank amount

IMAGE_EVENT_AMOUNTS = {
    "image_01": 4365000.0,
    "image_02": 100000.0,
    "image_03": 41272.0,
    "image_04": 2854.0,
    "image_05": 704.05,
    "image_06": 1995.0,
    "image_07": 8528.0,
    "image_08": 15339.0,
    "image_09": 723.0,
    "image_10": 79679.26,
    "image_11": 3650.0,
    "image_12": 33.50,
    "image_13": 2298.0,
    "image_14": 4543.0,
    "image_15": 9968.0,
    "image_16": 393.22,
}

def fill_missing_event_amounts(events_df, images_df):
    events = events_df.copy()
    img_map = dict(zip(images_df['related_event_id'], images_df['image_id']))
    
    for idx, row in events[events['amount'].isna()].iterrows():
        eid = row['event_id']
        if eid in img_map:
            img_id = img_map[eid]
            if img_id in IMAGE_EVENT_AMOUNTS:
                events.at[idx, 'amount'] = IMAGE_EVENT_AMOUNTS[img_id]
    return events
