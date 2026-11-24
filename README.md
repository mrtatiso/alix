# alix

syvox + alias → a band80 that reads as another alias.

```
$ alix check maria
valid · ma·ria

$ echo holamundo | vox 2501…0097 | alix seal maria
12509162188663147248.27751441095915090144.63591052175226227273.05146632382007457312

$ alix show 1250…7312                              anyone sees
tawos

$ echo holamundo | vox 2501…0097 | alix open 1250…7312
maria
$ echo pedro | vox 2501…0097 | alix open 1250…7312
téhay
```

No dependencies. Its only data is `clean.tecy`. Nothing stored.

## Run

```
git clone https://github.com/mrtatiso/alix
cd alix
python3 alix.py check <alias>      can it be sealed, and as which syllables
python3 alix.py seal <alias>       the band80 to store    (syvox through stdin)
python3 alix.py open <band80>      the alias it hides     (syvox through stdin)
python3 alix.py show <band80>      the alias anyone sees
python3 alix.py sample [n]         n aliases read from random band80s
```

alix is not a pip package: `clean.tecy` must sit next to `alix.py`, so run it from the cloned folder. The syvox always comes through stdin, never as an argument, usually straight from [vox](https://github.com/mrtatiso/vox):

```
echo clave | vox <salt> | python3 alix.py seal maria
echo clave | vox <salt> | python3 alix.py open <band80>
```

### Python

```python
from alix import check, seal, open_, show

stored = seal(syvox, "maria")    # a band80
open_(syvox, stored)             # 'maria'
show(stored)                     # the alias anyone sees
```

## What it does

- **What is stored is a band80.** In a file it looks like any other band80: it does not even say how many syllables the alias has.
- **Any band80 reads as an alias.** 4 digits say how many syllables (1 to 4) and each syllable comes from 19 more digits, looked up in the syllables of `clean.tecy`. Each syllable takes a share of the numbers proportional to its count to the power 3/4: common syllables come out often, rare ones seldom.
- **open** adds the digits of the syvox to the stored band80, digit by digit, mod 10, as vox does, and reads the alias. **seal** does the opposite, choosing at random one of the many band80s that read as the alias. The same alias sealed twice gives two different band80s.
- **Any syvox works.** A wrong one opens into another alias, built the same way. alix never sees a key or a salt.
- **Every alias that comes out is proper:** 3 to 10 letters, at most one accent, no `rr` or `ñ` at the start, at most 2 consonants in a row, or 3 when the last two are a Spanish pair (alejandro, hombre, ancho), and a start like Spanish or English (tr, pl, ch, st, sh, th…). If 80 digits read as an alias that is not proper, alix reads again from a hash of those digits, until it gets one. So a wrong syvox never shows noise, and nothing tells it apart from the right one.
- **Only proper aliases made of 1 to 4 syllables of the table can be sealed.** `alix check` says if one can, and as which syllables.

## The table

`clean.tecy` is the table published in [clinex](https://github.com/mrtatiso/clinex), unmodified. alix uses only its syllables (kind `s`) and checks its sha256 when it starts: if the table is missing or different, it stops. Another table gives other aliases from the same band80s, so changing it is v2.

```
a2593fa55ce78bdea018fdf3b261d44b8131f35eda059bf063db3ab087ad2341  clean.tecy
```

## One syvox per alias

Give each sealed alias its own syvox, as anon does with one salt per line. A syvox used for two things lets whoever knows one of them learn something about the other.

## v1

| | |
|---|---|
| digits | shake_256(`alix1|` + the 80 digits of the syvox), bytes 0–249 → digit |
| syllables | first 4 digits: 0000–0999 → 1, 1000–5499 → 2, 5500–8999 → 3, 9000–9999 → 4 |
| syllable i | 19 digits starting at 4 + 19·i, as a number, mod the total weight |
| weight | isqrt(isqrt(count³)) for each syllable of `clean.tecy`, in file order |
| not proper | read again from shake_256(`alix1-again|` + the 80 digits) |
| table | `clean.tecy`, sha256 above |

These never change within v1. The tests include fixed answers that any implementation of v1, in any language, with the same table, must reproduce.

## Test

```
python3 -m unittest discover test
```

## Licence

MIT, see `LICENSE`.

## Verify

```
sha256sum alix.py clean.tecy
```

v1.0.0:

```
bd9eb93a883ae7960d6eab61b5a3b4fa5eb2bb9a6ef34723b81958920dc2b513  alix.py
a2593fa55ce78bdea018fdf3b261d44b8131f35eda059bf063db3ab087ad2341  clean.tecy
```
