from searchbible.health_check import HealthCheck
from searchbible.utils.BibleBooks import BibleBooks
from searchbible.utils.BibleVerseParser import BibleVerseParser
from searchbible.db.Bible import Bible
from searchbible import config
from packaging import version
from chromadb.config import Settings
import os, chromadb, re, argparse
from prompt_toolkit.styles import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from pathlib import Path

# set up basic configs
if not hasattr(config, "openaiApiKey"):
    HealthCheck.setBasicConfig()

thisFile = os.path.realpath(__file__)
config.packageFolder = os.path.dirname(thisFile)
abbrev = BibleBooks.abbrev["eng"]
config.divider = "--------------------"

historyFolder = os.path.join(HealthCheck.getFiles(), "history")
Path(historyFolder).mkdir(parents=True, exist_ok=True)
read_history = os.path.join(historyFolder, "read")
read_session = PromptSession(history=FileHistory(read_history))
read_suggestions = [i[0] for i in abbrev.values()]
read_completer = WordCompleter(read_suggestions, ignore_case=True)
search_book_history = os.path.join(historyFolder, "search_book")
search_book_session = PromptSession(history=FileHistory(search_book_history))
book_suggestions = ["ALL"] + [i[0] for i in abbrev.values()]
book_completer = WordCompleter(book_suggestions, ignore_case=True)
search_chapter_history = os.path.join(historyFolder, "search_chapter")
search_chapter_session = PromptSession(history=FileHistory(search_chapter_history))
search_literal_history = os.path.join(historyFolder, "search_literal")
search_literal_session = PromptSession(history=FileHistory(search_literal_history))
search_semantic_history = os.path.join(historyFolder, "search_semantic")
search_semantic_session = PromptSession(history=FileHistory(search_semantic_history))
search_regex_history = os.path.join(historyFolder, "search_regex")
search_regex_session = PromptSession(history=FileHistory(search_regex_history))

promptStyle = Style.from_dict({
    # User input (default text).
    "": config.terminalCommandEntryColor2,
    # Prompt.
    "indicator": config.terminalPromptIndicatorColor2,
})

def read(bible:str="NET") -> None:
    HealthCheck.print2("Search Bible AI")
    HealthCheck.print3("Developed by: Eliran Wong")
    HealthCheck.print3("Open source: https://github.com/eliranwong/searchbibleai")
    HealthCheck.print2(config.divider)
    HealthCheck.print("* enter a single reference to display a full chapter")
    HealthCheck.print("* enter multiple references to display verses")
    HealthCheck.print("* enter '.verses' or press 'Ctrl+F' to search verses")
    HealthCheck.print("* enter '.paragraphs' or press 'Ctrl+P' to search paragraphs")
    HealthCheck.print(f"* enter '{config.exit_entry}' or press 'Ctrl+Q' to exit current feature of quit this app")
    HealthCheck.print2(config.divider)

    parser = BibleVerseParser(config.parserStandarisation)
    while True:
        userInput = HealthCheck.simplePrompt(style=promptStyle, promptSession=read_session, completer=read_completer)
        if userInput == config.exit_entry:
            HealthCheck.print2("Closing ...")
            break
        elif userInput == ".verses":
            # ctrl+f to search verses
            search(bible=bible, paragraphs=False)
        elif userInput == ".paragraphs":
            # ctrl+p to search paragraphs
            search(bible=bible, paragraphs=True)
        elif userInput:
            refs = parser.extractAllReferences(userInput)
            if not refs:
                HealthCheck.print2("No reference is found!")
                return None

            isChapter = (len(refs) == 1 and len(refs[0]) == 3)
            HealthCheck.print2(config.divider)
            if isChapter:
                # check if it is a single reference; display a full chapter
                fullChapter, verses = Bible.getVerses(refs, bible)
                chapterTitle = False
                for _, book, chapter, verse, scripture in fullChapter:
                    if not chapterTitle:
                        book_abbr = abbrev[str(book)][0]
                        HealthCheck.print2(f"# {book_abbr} {chapter}")
                        chapterTitle = True
                    HealthCheck.print4(f"({verse}) {scripture.strip()}")
                # draw a whole chapter
                HealthCheck.print2(config.divider)
            else:
                verses = Bible.getVerses(refs, bible)
            # display all verses
            for _, book, chapter, verse, scripture in verses:
                book_abbr = abbrev[str(book)][0]
                HealthCheck.print4(f"({book_abbr} {chapter}:{verse}) {scripture.strip()}")
            HealthCheck.print2(config.divider)

# combined semantic searches, literal searches and regular expression searches
def search(bible:str="NET", paragraphs:bool=False) -> None:

    def getAndItems(query):
        splits = query.split("&&")
        return {"$and": [{"$contains": i} for i in splits]} if len(splits) > 1 else {"$contains": query}

    #dbpath
    dbpath = Bible.getDbPath(bible)
    if not dbpath:
        return None

    # client
    chroma_client = chromadb.PersistentClient(dbpath, Settings(anonymized_telemetry=False))
    # collection
    collection = chroma_client.get_or_create_collection(
        name="paragraphs" if paragraphs else "verses",
        metadata={"hnsw:space": "cosine"},
        embedding_function=HealthCheck.getEmbeddingFunction(embeddingModel="all-mpnet-base-v2"),
    )

    def getChapterRange(i):
        cc = []
        try:
            rangeStart, rangeEnd = [ii.strip() for ii in i.split("-")]
            rangeStart, rangeEnd = int(rangeStart), int(rangeEnd)
            if rangeEnd > rangeStart:
                for ii in range(rangeStart, rangeEnd):
                    cc.append(ii)
                cc.append(rangeEnd)
            else:
                cc.append(rangeStart)
        except:
            pass
        return cc

    # user input
    HealthCheck.print2(f"SEARCH {'PARAGRAPHS' if paragraphs else 'VERSES'}")
    HealthCheck.print2(config.divider)
    # search in books
    HealthCheck.print3("In books (use '||' for combo, '-' for range): e.g. Gen||Matt-John||Rev")
    books = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_book_session, completer=book_completer)
    if books.lower() == "all":
        books = ""
    books = BibleBooks.getBookCombo(books)
    if books:
        if paragraphs:
            books = {"book_start": {"$in": books}}
        else:
            books = {"book": {"$in": books}}
    else:
        books = {}
    # search in chapters
    HealthCheck.print3("In chapters (use '||' for combo, '-' for range): e.g. 2||4||6-8||10")
    chapters = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_chapter_session)
    if chapters := chapters.strip():
        splits = chapters.split("||")
        if len(splits) == 1:
            if "-" in chapters:
                cc = getChapterRange(chapters)
            else:
                try:
                    cc = [int(chapters)]
                except:
                    cc = []
        else:
            cc = []
            for i in splits:
                i = i.lower().strip()
                if "-" in i:
                    cc += getChapterRange(i)
                else:
                    try:
                        cc.append(int(i))
                    except:
                        pass
    else:
        cc = []
    if cc:
        if paragraphs:
            chapters = {"$or": [{"$and": [{"chapter_start": {"$lte": c}}, {"chapter_end": {"$gte": c}}]} for c in cc]} if len(cc) > 1 else {"$and": [{"chapter_start": {"$lte": cc[0]}}, {"chapter_end": {"$gte": cc[0]}}]}
        else:
            chapters = {"chapter": {"$in": cc}}
    else:
        chapters = {}

    # search for plain words
    HealthCheck.print3("Search for plain words ('||' denotes 'or'; '&amp;&amp;' denotes 'and'): e.g. Lord&amp;&amp;God||Jesus&amp;&amp;love")
    contains = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_literal_session)
    if contains.strip():
        splits = contains.split("||")
        contains = {"$or": [getAndItems(i) for i in splits]} if len(splits) > 1 else getAndItems(contains)
    else:
        contains = ""
    # search for meaning
    HealthCheck.print3("Search for meaning:")
    meaning = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_semantic_session)
    # search for regex
    HealthCheck.print3("Search for regular expression:")
    regex = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_regex_session)

    # formulate where filter
    if books and chapters:
        where = {"$and": [books, chapters]}
    elif books:
        where = books
    elif chapters:
        where = chapters
    else:
        where = None

    if meaning:
        # specify number of closest matches
        default_n_results = 10
        n_results = input("Number of closest matches: ")
        if n_results:
            try:
                n_results = int(n_results)
            except:
                n_results = default_n_results
        else:
            n_results = default_n_results
        # run query
        res = collection.query(
            query_texts=[meaning],
            n_results = n_results,
            where=where,
            where_document=contains if contains else None,
        )
    else:
        res = collection.get(
            where=where,
            where_document=contains if contains else None,
        )
    HealthCheck.print2(config.divider)
    print(f">>> Retrieved {'paragraphs' if paragraphs else 'verses'}: \n")

    if meaning:
        metadatas = res["metadatas"][0]
        documents = res["documents"][0]
    else:
        metadatas = res["metadatas"]
        documents = res["documents"]

    if paragraphs:
        verses = [(metadata["start"], metadata["book_start"], metadata["chapter_start"], metadata["verse_start"], metadata["chapter_end"], metadata["verse_end"], document) for metadata, document in zip(metadatas, documents)]
    else:
        verses = [(metadata["reference"], metadata["book"], metadata["chapter"], metadata["verse"], document) for metadata, document in zip(metadatas, documents)]
    
    if not meaning:
        # sorting for non-semantic search
        verses = sorted(verses, key=lambda x: version.parse(x[0]))

    if paragraphs:
        for _, book, chapter, verse, chapter_end, verse_end, scripture in verses:
            book_abbr = abbrev[str(book)][0]
            if not regex or (regex and re.search(regex, scripture, flags=re.I|re.M)):
                HealthCheck.print2(f"# {book_abbr} {chapter}:{verse}-{chapter_end}:{verse_end}")
                print(f"## {scripture.strip()}\n")
    else:
        for _, book, chapter, verse, scripture in verses:
            book_abbr = abbrev[str(book)][0]
            if not regex or (regex and re.search(regex, scripture, flags=re.IGNORECASE)):
                print(f"({book_abbr} {chapter}:{verse}) {scripture.strip()}")
    HealthCheck.print2(config.divider)

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="SearchBibleAI CLI options")
    # Add arguments
    parser.add_argument("default", nargs="?", default=None, help="Specify a bible module, e.g. KJV, NET, etc.")
    # Parse arguments
    args = parser.parse_args()
    # Get options
    bible = args.default.strip() if args.default and args.default.strip() else ""
    if not bible:
        bible = input("Enter a bible version (e.g. KJV, NET, etc.): ").strip()

    read(bible=bible if bible else "NET")
    # search verses
    #search(bible=bible if bible else "NET")
    # search paragraphs
    #search(bible=bible if bible else "NET", paragraphs=True)


if __name__ == '__main__':
    main()