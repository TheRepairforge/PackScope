# Translating PackScope

PackScope exists in English, French, German and Spanish. English and French are written by the
maintainer; **German and Spanish are first drafts that no native speaker has checked yet.** If
you speak one of them, your corrections are very welcome.

## The easy way

Open the review page for your language: https://therepairforge.github.io/translate/

It shows the main screens in your language and lists every string. Next to each one,
**Suggest a fix** opens a GitHub issue already filled in: you only type your version.

For a full pass, download the spreadsheet from the same page, fill the `your_suggestion`
column, and attach the file to a [translation issue](https://github.com/TheRepairforge/PackScope/issues/new?template=translation.yml).

PackScope has no character or length limit: accents and full words are welcome.

## Where the strings live

One JSON file per language in [`packscope/locales/`](../packscope/locales/). The shared
vocabulary (verdicts, field names) comes from the PocketOBI firmware, so a fix to one of those
words may also apply to the device: we take care of keeping the two in line.

## Credit

Tell us in the issue how you want to be thanked in the release notes, or leave it empty to
stay anonymous.
