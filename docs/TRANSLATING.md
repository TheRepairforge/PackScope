# Translating PackScope

PackScope exists in English, French, German, Spanish, Japanese, Korean, Simplified Chinese,
Traditional Chinese and Vietnamese. English and French are written by the maintainer. The words
PackScope shares with the PocketOBI screen come from the firmware, whose Japanese was reviewed
and whose Chinese was written by native speakers. **Everything else in German, Spanish and the
Asian languages is a first draft that no native speaker has checked yet.** If you speak one of
them, your corrections are very welcome.

## The easy way

Open the review page for your language: https://therepairforge.github.io/translate/

It shows the main screens in your language and lists every string. Next to each one,
**Suggest a fix** opens a GitHub issue already filled in: you only type your version.

For a full pass, download the spreadsheet from the same page, fill the `your_suggestion`
column, and attach the file to a [translation issue](https://github.com/TheRepairforge/PackScope/issues/new?template=translation.yml).

PackScope has no character or length limit: accents and full words are welcome.

## Where the strings live

One JSON file per language in [`packscope/locales/`](../packscope/locales/). The Japanese,
Korean, Chinese and Vietnamese app-only text is kept in
[`tools/desk_strings_asia.py`](../tools/desk_strings_asia.py) and written into those files by
`tools/gen_locales_asia.py`. The shared
vocabulary (verdicts, field names) comes from the PocketOBI firmware, so a fix to one of those
words may also apply to the device: we take care of keeping the two in line.

## Credit

Tell us in the issue how you want to be thanked in the release notes, or leave it empty to
stay anonymous.
