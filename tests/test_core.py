import unittest
from voiceover_check import compare, tokens


def timed(text):
    return [(w, float(i)) for i, w in enumerate(text.split())]


class Tokens(unittest.TestCase):
    def test_case_punctuation_and_hyphens(self):
        self.assertEqual(tokens("Well-known, Founders!"), ["well", "known", "founders"])

    def test_curly_apostrophes(self):
        self.assertEqual(tokens("Don’t"), tokens("don't"))

    def test_pronunciation_markup(self):
        self.assertEqual(tokens("in [Lagos](/lˈAɡɔs/) today"), ["in", "lagos", "today"])

    def test_accents_stay_in_the_word(self):
        self.assertEqual(tokens("Café"), ["café"])


class Numbers(unittest.TestCase):
    def test_spoken_and_written_match(self):
        for a, b in [("thirty nine", "39"), ("two thousand and sixteen", "2016"), ("twenty twenty six", "2026"),
                     ("two hundred and fifty", "250"), ("thirtieth", "30th"), ("twenty first", "21st"), ("nineteen ninety", "1990"),
                     ("sixty five percent", "65%"), ("two point one", "2.1"), ("one thousand", "1,000"),
                     ("thirty nine million dollars", "$39 million"), ("five hundred naira", "₦500"), ("two point one billion dollars", "$2.1 billion")]:
            self.assertEqual(tokens(a), tokens(b), a)

    def test_different_numbers_still_differ(self):
        self.assertNotEqual(tokens("thirty nine"), tokens("93"))
        self.assertNotEqual(tokens("two million"), tokens("2 billion"))


class Compare(unittest.TestCase):
    def test_perfect(self):
        score, flags = compare("We raised money.", timed("we raised money"))
        self.assertEqual((score, flags), (1.0, []))

    def test_extra(self):
        _, flags = compare("We raised money", timed("we really raised money"))
        self.assertEqual([(f.kind, f.heard, f.seconds) for f in flags], [("EXTRA", "really", 1.0)])

    def test_single_missing_word(self):
        _, flags = compare("We did not raise", timed("we did raise"))
        self.assertEqual([(f.kind, f.wrote) for f in flags], [("MISSING", "not")])

    def test_changed_number_word(self):
        _, flags = compare("two million users", timed("two billion users"))
        self.assertEqual([(f.kind, f.wrote, f.heard) for f in flags], [("CHANGED", "million", "billion")])

    def test_spacing_is_not_flagged(self):
        self.assertEqual(compare("our startup", timed("our start up"))[1], [])
        self.assertEqual(compare("founders cable dot com", timed("founderscable.com"))[1], [])

    def test_possessive_is_not_flagged(self):
        self.assertEqual(compare("customers", timed("customer's"))[1], [])

    def test_numbers_split_across_timed_words(self):
        self.assertEqual(compare("39 people", timed("thirty nine people"))[1], [])

    def test_number_split_by_speech_model(self):
        self.assertEqual(compare("2000 people", [("2", 0.0), (",000", 0.2), ("people", 0.5)])[1], [])
        self.assertEqual(compare("2000 people", [("2,", 0.0), ("000", 0.2), ("people", 0.5)])[1], [])
        self.assertEqual(compare("$2.1 billion", [("$2", 0.0), (".1", 0.2), ("billion", 0.5)])[1], [])

    def test_year_then_number_stays_apart(self):
        self.assertEqual(compare("in 2019 200 people", [("in", 0.0), ("2019,", 0.1), ("200", 0.2), ("people", 0.5)])[1], [])

    def test_empty_transcript_does_not_crash(self):
        _, flags = compare("hello there", [])
        self.assertEqual(flags[0].kind, "MISSING")


if __name__ == "__main__":
    unittest.main()
