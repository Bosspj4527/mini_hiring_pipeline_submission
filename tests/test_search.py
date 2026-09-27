from datetime import datetime, timedelta, timezone
from app.search import parse_query

def test_typos_are_left_as_name_query():
    p=parse_query('Find Priya Sharam')
    assert p['name_query']=='priya sharam'

def test_stage_and_week():
    p=parse_query('Who has been stuck in Screening for more than a week?')
    assert p['stage']=='Screening' and p['stuck_days']==7

def test_since_monday():
    p=parse_query('Who moved to Interview since Monday?')
    assert p['stage']=='Interview' and p['since'] is not None

def test_offer_not_hired():
    p=parse_query("Who reached the Offer stage but didn't get hired?")
    assert p['offer_not_hired'] is True
