import json
import os
import pytest
from parser import WikivoyageParser

def dump(obj):
    # canonical JSON for deep compare
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def wrap(children):
    """Wrap a list of child nodes in the default root envelope."""
    return {
        "type": "root",
        "properties": {},
        "children": children
    }

@pytest.fixture
def parser():
    return WikivoyageParser()

def test_empty_input_is_root_only(parser):
    got = parser.parse("")
    assert dump(got) == dump(wrap([]))

def test_plain_text_node(parser):
    got = parser.parse("Just some plain text.")
    expected = wrap([
        {"type":"text","properties":{"markdown":"Just some plain text."},"children":[]}
    ])
    assert dump(got) == dump(expected)

def test_template_node(parser):
    got = parser.parse("{{foo|a=1|b=two}}")
    expected = wrap([
        {
            "type":"template",
            "properties":{"name":"foo","params":{"a":"1","b":"two"}},
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_see_listing_full_properties(parser):
    snippet = (
        "{{see"
        "|name=Statue"
        "|alt=Monument"
        "|url=http://x"
        "|email=a@b.com"
        "|address=1 Road"
        "|lat=1.23"
        "|long=4.56"
        "|directions=North"
        "|phone=12345"
        "|tollfree=800"
        "|fax=54321"
        "|hours=24/7"
        "|price=Free"
        "|lastedit=2020-01-01"
        "|wikipedia=Statue"
        "|wikidata=Q1"
        "|content=Big statue"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"see",
            "properties":{
                "name":"Statue","alt":"Monument","url":"http://x",
                "email":"a@b.com","address":"1 Road","lat":"1.23","long":"4.56",
                "directions":"North","phone":"12345","tollfree":"800",
                "fax":"54321","hours":"24/7","price":"Free",
                "lastedit":"2020-01-01","wikipedia":"Statue","wikidata":"Q1",
                "content":"Big statue"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_do_listing_full_properties(parser):
    snippet = (
        "{{do"
        "|name=Walk"
        "|alt=Stroll"
        "|url=http://walk"
        "|email=hi@walk"
        "|address=Main Street"
        "|lat=2.34"
        "|long=5.67"
        "|directions=East"
        "|phone=222-333"
        "|tollfree=800-DO-WALK"
        "|fax=999-888"
        "|hours=All day"
        "|price=Free"
        "|lastedit=2021-02-02"
        "|wikipedia=Walking"
        "|wikidata=Q2"
        "|content=Enjoy a walk"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"do",
            "properties":{
                "name":"Walk","alt":"Stroll","url":"http://walk",
                "email":"hi@walk","address":"Main Street","lat":"2.34","long":"5.67",
                "directions":"East","phone":"222-333","tollfree":"800-DO-WALK",
                "fax":"999-888","hours":"All day","price":"Free",
                "lastedit":"2021-02-02","wikipedia":"Walking","wikidata":"Q2",
                "content":"Enjoy a walk"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_buy_listing_full_properties(parser):
    snippet = (
        "{{buy"
        "|name=Shirt"
        "|alt=Tees"
        "|url=http://shop"
        "|email=sales@shop"
        "|address=Market St"
        "|lat=3.45"
        "|long=6.78"
        "|directions=West"
        "|phone=444-555"
        "|tollfree=800-BUY-TEE"
        "|fax=777-666"
        "|hours=9–6"
        "|price=$20"
        "|lastedit=2022-03-03"
        "|wikipedia=Shopping"
        "|wikidata=Q3"
        "|content=Quality tees"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"buy",
            "properties":{
                "name":"Shirt","alt":"Tees","url":"http://shop",
                "email":"sales@shop","address":"Market St","lat":"3.45","long":"6.78",
                "directions":"West","phone":"444-555","tollfree":"800-BUY-TEE",
                "fax":"777-666","hours":"9–6","price":"$20",
                "lastedit":"2022-03-03","wikipedia":"Shopping","wikidata":"Q3",
                "content":"Quality tees"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_eat_listing_full_properties(parser):
    snippet = (
        "{{eat"
        "|name=Diner"
        "|alt=Cafe"
        "|url=http://eat"
        "|email=food@eat"
        "|address=Food Lane"
        "|lat=4.56"
        "|long=7.89"
        "|directions=South"
        "|phone=666-777"
        "|tollfree=800-EAT-YUM"
        "|fax=555-444"
        "|hours=Breakfast"
        "|price=$10–$30"
        "|lastedit=2023-04-04"
        "|wikipedia=Dining"
        "|wikidata=Q4"
        "|content=Best pancakes"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"eat",
            "properties":{
                "name":"Diner","alt":"Cafe","url":"http://eat",
                "email":"food@eat","address":"Food Lane","lat":"4.56","long":"7.89",
                "directions":"South","phone":"666-777","tollfree":"800-EAT-YUM",
                "fax":"555-444","hours":"Breakfast","price":"$10–$30",
                "lastedit":"2023-04-04","wikipedia":"Dining","wikidata":"Q4",
                "content":"Best pancakes"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_drink_listing_full_properties(parser):
    snippet = (
        "{{drink"
        "|name=Pub"
        "|alt=Bar"
        "|url=http://drink"
        "|email=cheers@drink"
        "|address=Bar Street"
        "|lat=5.67"
        "|long=8.90"
        "|directions=Center"
        "|phone=888-999"
        "|tollfree=800-DRINK"
        "|fax=333-222"
        "|hours=Evening"
        "|price=$7–$30"
        "|lastedit=2024-05-05"
        "|wikipedia=Nightlife"
        "|wikidata=Q5"
        "|content=Great brews"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"drink",
            "properties":{
                "name":"Pub","alt":"Bar","url":"http://drink",
                "email":"cheers@drink","address":"Bar Street","lat":"5.67","long":"8.90",
                "directions":"Center","phone":"888-999","tollfree":"800-DRINK",
                "fax":"333-222","hours":"Evening","price":"$7–$30",
                "lastedit":"2024-05-05","wikipedia":"Nightlife","wikidata":"Q5",
                "content":"Great brews"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_sleep_listing_full_properties(parser):
    snippet = (
        "{{sleep"
        "|name=Hotel"
        "|alt=Inn"
        "|url=http://sleep"
        "|email=stay@sleep"
        "|address=Sleepy Ave"
        "|lat=6.78"
        "|long=9.01"
        "|directions=Uptown"
        "|phone=000-111"
        "|tollfree=800-SLEEP"
        "|fax=111-000"
        "|hours=24h"
        "|price=$100"
        "|lastedit=2025-06-06"
        "|wikipedia=Accommodation"
        "|wikidata=Q6"
        "|checkin=3PM"
        "|checkout=11AM"
        "|content=Cozy rooms"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"sleep",
            "properties":{
                "name":"Hotel","alt":"Inn","url":"http://sleep",
                "email":"stay@sleep","address":"Sleepy Ave","lat":"6.78","long":"9.01",
                "directions":"Uptown","phone":"000-111","tollfree":"800-SLEEP",
                "fax":"111-000","hours":"24h","price":"$100",
                "lastedit":"2025-06-06","wikipedia":"Accommodation","wikidata":"Q6",
                "checkin":"3PM","checkout":"11AM","content":"Cozy rooms"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_generic_listing_full_properties(parser):
    snippet = (
        "{{listing"
        "|name=Info"
        "|alt=Data"
        "|url=http://info"
        "|email=info@info"
        "|address=Down St"
        "|lat=7.89"
        "|long=0.12"
        "|directions=Here"
        "|phone=123-000"
        "|tollfree=800-INFO"
        "|fax=000-123"
        "|hours=All times"
        "|price=$0"
        "|lastedit=2026-07-07"
        "|wikipedia=InfoPage"
        "|wikidata=Q7"
        "|content=Useful info"
        "}}"
    )
    got = parser.parse(snippet)
    expected = wrap([
        {
            "type":"listing",
            "properties":{
                "name":"Info","alt":"Data","url":"http://info",
                "email":"info@info","address":"Down St","lat":"7.89","long":"0.12",
                "directions":"Here","phone":"123-000","tollfree":"800-INFO",
                "fax":"000-123","hours":"All times","price":"$0",
                "lastedit":"2026-07-07","wikipedia":"InfoPage","wikidata":"Q7",
                "content":"Useful info"
            },
            "children":[]
        }
    ])
    assert dump(got) == dump(expected)

def test_section_and_subsection(parser):
    got = parser.parse("Intro\n== First ==\nHello\n=== Sub ===\nWorld")
    sec = got["children"][1]
    assert sec["type"] == "section" and sec["properties"]["level"] == 2
    sub = sec["children"][1]
    assert sub["type"] == "section" and sub["properties"]["level"] == 3

def test_full_boston_snapshot(parser):
    here = os.path.dirname(__file__)
    inp = os.path.join(here, "fixtures", "boston_input.txt")
    out = os.path.join(here, "fixtures", "boston_output.json")
    wikicode = open(inp, encoding="utf-8").read()
    expected = json.load(open(out, encoding="utf-8"))
    got = parser.parse(wikicode)
    assert dump(got) == dump(expected)
