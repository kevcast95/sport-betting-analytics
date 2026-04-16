import unittest

from apps.api.bt2_sofascore_observation_parse import sofa_lineup_flags_from_lineups_raw, sofa_market_flags_from_processed


class SofaLineupParseTest(unittest.TestCase):
    def test_starters_both_sides(self) -> None:
        def pl(pid: int, sub: bool) -> dict:
            return {"player": {"id": pid}, "substitute": sub}

        home_p = [pl(i, False) for i in range(11)]
        away_p = [pl(100 + i, False) for i in range(11)]
        raw = {"home": {"players": home_p}, "away": {"players": away_p}}
        hu, au, lav = sofa_lineup_flags_from_lineups_raw(raw)
        self.assertTrue(hu and au and lav)


class SofaMarketsParseTest(unittest.TestCase):
    def test_from_processed(self) -> None:
        proc = {
            "odds_featured": {
                "market_snapshot": {
                    "full_time_1x2": {
                        "home": {"current": 2.0},
                        "draw": {"current": 3.1},
                        "away": {"current": 4.0},
                    }
                }
            },
            "odds_all": {
                "extended_markets": {
                    "goals_depth": {
                        "over_under_2.5": {"over": 1.9, "under": 2.0},
                        "btts": {"yes": 1.8, "no": 2.1},
                    }
                }
            },
        }
        ft, ou, bt = sofa_market_flags_from_processed(proc)
        self.assertTrue(ft and ou and bt)


if __name__ == "__main__":
    unittest.main()
