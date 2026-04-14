from apps.api.bt2_sportmonks_include_resolve import (
    bt2_sm_next_include_on_forbidden,
    bt2_sm_normalize_include_string,
    bt2_sm_parse_forbidden_include_from_sm_403,
    bt2_sm_strip_include_root,
)


def test_normalize_include_string() -> None:
    assert bt2_sm_normalize_include_string("a;;b; c ") == "a;b;c"


def test_strip_include_root_removes_nested() -> None:
    s = "odds;premiumOdds;premiumOdds.foo;scores"
    assert bt2_sm_strip_include_root(s, "premiumOdds") == "odds;scores"


def test_parse_forbidden_from_message() -> None:
    body = {"message": "You do not have access to the 'premiumOdds' include"}
    assert bt2_sm_parse_forbidden_include_from_sm_403(body) == "premiumOdds"


def test_next_include_strips_parsed_root() -> None:
    core = "participants;odds"
    cur = "participants;odds;premiumOdds;prematchNews"
    body = {"message": "You do not have access to the 'premiumOdds' include"}
    nxt = bt2_sm_next_include_on_forbidden(cur, core=core, response_body=body)
    assert nxt == bt2_sm_normalize_include_string("participants;odds;prematchNews")


def test_next_include_at_core_returns_none() -> None:
    core = "participants;odds"
    body = {"message": "You do not have access to the 'premiumOdds' include"}
    assert bt2_sm_next_include_on_forbidden(core, core=core, response_body=body) is None


def test_next_include_unparseable_falls_back_to_core() -> None:
    core = "a;b"
    cur = "a;b;c"
    nxt = bt2_sm_next_include_on_forbidden(cur, core=core, response_body="")
    assert nxt == "a;b"
