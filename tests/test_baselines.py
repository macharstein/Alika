from copy import deepcopy
from lionsim.config import load_config
from lionsim.simulator import simulate_day
from lionsim.reports import build_reports, target_rows


def test_history_cues_exclude_future_and_include_report_boundary():
    config=load_config()
    day=simulate_day(config)
    day.events=[{'t':'2026-01-01T07:00:00','token':'ENTER_SHADE','zone':'Shade'},
                {'t':'2026-01-01T08:00:00','token':'DRINK','zone':'Waterhole'},
                {'t':'2026-01-01T08:00:01','token':'CATCH','zone':'Hunting ground'}]
    reports=build_reports(day,config)
    row=target_rows(day,reports)[0]
    assert row['shade_entry_hour_bucket']==7
    assert row['drinks_so_far']==1
    assert row['catch_so_far']==0
    changed=deepcopy(day)
    changed.latents={}
    changed.events[-1]['token']='CHASE_START'
    changed_row=target_rows(changed,reports)[0]
    assert changed_row==row
