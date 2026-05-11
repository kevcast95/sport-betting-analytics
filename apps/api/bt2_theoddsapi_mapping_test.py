import unittest

from apps.api.bt2_theoddsapi_mapping import (
    TOA_LIGUE_1_SPORT_KEY,
    TOA_SPORT_KEYS_BY_SM_LEAGUE_ID,
    TOA_SPORT_LABELS,
    TOA_TIER_S_SPORT_KEYS,
    toa_sport_key_for_sm_league_id,
)


class TestTheOddsApiMapping(unittest.TestCase):
    def test_ligue_1_uses_valid_toa_v4_key(self) -> None:
        self.assertEqual(TOA_LIGUE_1_SPORT_KEY, "soccer_france_ligue_one")
        self.assertEqual(TOA_SPORT_KEYS_BY_SM_LEAGUE_ID[301], "soccer_france_ligue_one")
        self.assertIn("soccer_france_ligue_one", TOA_TIER_S_SPORT_KEYS)
        self.assertNotIn("soccer_france_ligue" + "_1", TOA_TIER_S_SPORT_KEYS)
        self.assertEqual(TOA_SPORT_LABELS["soccer_france_ligue_one"], "Ligue 1")

    def test_lookup_handles_str_and_unknown(self) -> None:
        self.assertEqual(toa_sport_key_for_sm_league_id("301"), "soccer_france_ligue_one")
        self.assertIsNone(toa_sport_key_for_sm_league_id("not-an-id"))
        self.assertIsNone(toa_sport_key_for_sm_league_id(999999))


if __name__ == "__main__":
    unittest.main()
