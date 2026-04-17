"""Headers mínimos para requests SofaScore (mismo criterio que `core/sofascore_http.py`)."""


def sfs_request_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (compatible; BT2-S65-experiment/1.0; +https://github.com/kevcast95/sport-betting-analytics)"
        ),
        "Accept": "application/json",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
    }
