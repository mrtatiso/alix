import os
import secrets
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import alix  # noqa: E402

SYVOX = "67137111632918228090.03198478452534193697.85614958450118272798.55305506750949179189"
BAND = "25018599682202377746.87783789576741058797.28832678037307446403.33471880386520197097"
NAMES = ["maria", "carlos", "ana", "juan", "valentina", "alejandro", "cuauhtemoc",
         "john", "michael", "sarah", "jessica", "robert", "william", "emily", "fernanda"]


def band():
    n = str(secrets.randbelow(10 ** 80)).zfill(80)
    return ".".join(n[i:i + 20] for i in range(0, 80, 20))


class TestCheck(unittest.TestCase):
    def test_names_are_valid(self):
        for n in NAMES:
            self.assertTrue(alix.check(n), n)
        self.assertEqual(alix.check("Maria"), ["ma", "ria"])

    def test_noise_is_invalid(self):
        for n in ("qqqq", "ab", "bcees", "rrosa", "ñame", "xqzt", "abcdefghijk"):
            self.assertIsNone(alix.check(n), n)

    def test_proper(self):
        for a in ("alejandro", "hombre", "ancho", "stella", "carlos"):
            self.assertTrue(alix.proper(a), a)
        for a in ("bcees", "rrosa", "ñame", "ab", "dádá", "toolongalias"):
            self.assertFalse(alix.proper(a), a)


class TestAlix(unittest.TestCase):
    def test_roundtrip(self):
        for n in NAMES:
            s = band()
            self.assertEqual(alix.open_(s, alix.seal(s, n)), n)

    def test_same_alias_twice_looks_different(self):
        self.assertNotEqual(alix.seal(SYVOX, "maria"), alix.seal(SYVOX, "maria"))

    def test_any_syvox_gives_a_proper_alias(self):
        stored = alix.seal(SYVOX, "maria")
        for _ in range(200):
            a = alix.open_(band(), stored)
            self.assertTrue(alix.proper(a), a)

    def test_show_is_a_proper_alias(self):
        for _ in range(50):
            self.assertTrue(alix.proper(alix.show(band())))

    def test_fixed_answers(self):
        # v1 must always give these: any implementation, any language, same table
        self.assertEqual(alix.show(BAND), "góver")
        self.assertEqual(alix.open_(SYVOX, BAND), "estant")

    def test_grouping_does_not_matter(self):
        flat = BAND.replace(".", "")
        self.assertEqual(alix.open_(SYVOX, flat), alix.open_(SYVOX, BAND))

    def test_bad_inputs(self):
        with self.assertRaises(ValueError):
            alix.seal(SYVOX, "qqqq")
        with self.assertRaises(ValueError):
            alix.open_("123", BAND)


class TestTable(unittest.TestCase):
    def _with_here(self, here):
        saved = alix.HERE, alix._SYL, alix._START, alix._INDEX, alix._TOTAL
        alix.HERE, alix._SYL = here, None
        try:
            with self.assertRaises(SystemExit):
                alix._load()
        finally:
            alix.HERE, alix._SYL, alix._START, alix._INDEX, alix._TOTAL = saved

    def test_missing_table_stops_alix(self):
        with tempfile.TemporaryDirectory() as d:
            self._with_here(d)

    def test_changed_table_stops_alix(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(os.path.join(alix.HERE, alix.TABLE), d)
            with open(os.path.join(d, alix.TABLE), "a", encoding="utf-8") as f:
                f.write("zz\t2\ts\n")
            self._with_here(d)


if __name__ == "__main__":
    unittest.main()
