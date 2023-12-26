# Search Bible AI

Integrate Unique Bible App resources with AI tools

Built upon our projects, the [UniqueBible App](https://github.com/eliranwong/UniqueBible) and [LetMeDoIt AI](https://github.com/eliranwong/letmedoit), SearchBible AI is our latest Bible app that aims to integrate our comprehensive Bible resources with the recent advancements in AI technology and tools.

# Installation / Upgrade

> pip install --upgrade searchbible

# Usage

> searchbible

To specify a bible version for searches, e.g. KJV:

> searchbible KJV

* enter a single reference to display a full chapter

* enter multiple references to display verses

* enter '.verses' or press 'Ctrl+F' to search verses

* enter '.paragraphs' or press 'Ctrl+P' to search paragraphs

* enter '{config.exit_entry}' or press 'Ctrl+Q' to exit current feature of quit the app

To convert an UniqueBible App bible file, with a given path, e.g.:

> searchbibleconverter -b "/temp/KJV.bible"

# Progress

1. Support conversion of UnqiueBible App bibles (done)

2. Build simple cli interface for reading single bible chapter (partial)

3. Build simple cli interface for searching verses (partial)

4. Build simple cli interface for searching paragraphs (partial)

5. Integrates ChatGPT and Gemini Pro features (pending)

6. Support more UnqiueBible App bible resources (pending)

7. Build a Qt-based graphical user interface, like we do in [UniqueBible App](https://github.com/eliranwong/UniqueBible) (pending)

# New Features that are not available in oiginal Unique Bible App

* bible modules vector database formats on top of SQLite format

* support searching individual paragraphs in addition to searching individual verses

* support semantic searches (i.e. search for meaning); both in verses and paragraphs

* combination of literal search, semantic search and regular expression search in a single search
