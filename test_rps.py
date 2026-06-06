import importlib.util
import json
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).with_name("RPS NEA MOCK.py")
SPEC = importlib.util.spec_from_file_location("rps_game", MODULE_PATH)
rps_game = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rps_game)


class PredictableRandom:
    def choice(self, choices):
        return choices[-1]

    def random(self):
        return 0.0


class GameEngineTests(unittest.TestCase):
    def setUp(self):
        self.game = rps_game.GameEngine(rng=PredictableRandom())

    def test_all_rule_outcomes(self):
        expected = {
            ("Rock", "Rock"): "Draw",
            ("Rock", "Paper"): "Loss",
            ("Rock", "Scissors"): "Win",
            ("Paper", "Rock"): "Win",
            ("Paper", "Paper"): "Draw",
            ("Paper", "Scissors"): "Loss",
            ("Scissors", "Rock"): "Loss",
            ("Scissors", "Paper"): "Win",
            ("Scissors", "Scissors"): "Draw",
        }
        for choices, outcome in expected.items():
            with self.subTest(choices=choices):
                self.assertEqual(self.game.determine_outcome(*choices), outcome)

    def test_best_of_three_finishes_at_two_decisive_wins(self):
        self.game.set_mode("Best of 3")
        self.game.play_round("Rock", "Scissors")
        self.game.play_round("Paper", "Paper")
        final_round = self.game.play_round("Scissors", "Paper")

        self.assertEqual(final_round.outcome, "Win")
        self.assertTrue(self.game.match_over)
        self.assertEqual(self.game.match_winner, "Player")
        self.assertEqual(self.game.player_match_score, 2)
        self.assertEqual(self.game.draws, 1)
        with self.assertRaises(RuntimeError):
            self.game.play_round("Rock", "Scissors")

    def test_new_match_retains_session_statistics(self):
        self.game.set_mode("Best of 3")
        self.game.play_round("Rock", "Scissors")
        self.game.new_match()

        self.assertEqual(self.game.wins, 1)
        self.assertEqual(self.game.player_match_score, 0)
        self.assertFalse(self.game.match_over)
        self.assertEqual(len(self.game.history), 1)

    def test_reset_session_clears_statistics_and_history(self):
        self.game.play_round("Rock", "Scissors")
        self.game.play_round("Paper", "Scissors")
        self.game.reset_session()

        self.assertEqual(self.game.total_rounds, 0)
        self.assertEqual(self.game.best_streak, 0)
        self.assertEqual(self.game.history, [])

    def test_adaptive_ai_counters_most_common_player_move(self):
        self.game.play_round("Rock", "Scissors")
        self.game.play_round("Rock", "Scissors")
        self.game.set_difficulty("Adaptive")

        self.assertEqual(self.game.choose_computer_move(), "Paper")

    def test_snapshot_is_json_serializable(self):
        self.game.play_round("Rock", "Scissors")
        payload = self.game.snapshot()

        serialized = json.dumps(payload)
        self.assertIn('"player_choice": "Rock"', serialized)
        self.assertEqual(payload["session"]["win_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
