import os, platform

mainFile = os.path.realpath(__file__)
packageFolder = os.path.dirname(mainFile)

# create config.py if it does not exist; in case user delete the file for some reasons
configFile = os.path.join(packageFolder, "config.py")
if not os.path.isfile(configFile):
    open(configFile, "a", encoding="utf-8").close()

from searchbible import config
from searchbible.health_check import HealthCheck

# share mainFile and packageFolder paths in config
config.mainFile = mainFile
config.packageFolder = packageFolder
#package = os.path.basename(config.packageFolder)
if os.getcwd() != config.packageFolder:
    os.chdir(config.packageFolder)

# check current platform
config.thisPlatform = platform.system()
# check if it is running with Android Termux
config.isTermux = True if os.path.isdir("/data/data/com.termux/files/home") else False
# check storage directory
HealthCheck.setSharedItems()
# set up configs
from searchbible.utils.configDefault import *
HealthCheck.check()

# Start of main application
from prompt_toolkit import print_formatted_text, HTML
import chromadb, re, argparse, shutil
from searchbible.utils.BibleBooks import BibleBooks
from searchbible.utils.BibleVerseParser import BibleVerseParser
from searchbible.utils.prompt_validator import NumberValidator
from searchbible.utils.prompts import Prompts
from searchbible.db.Bible import Bible
from searchbible.utils.AGBsubheadings import agbSubheadings
from searchbible.utils.AGBparagraphs_expanded import agbParagraphs
from packaging import version
from chromadb.config import Settings
from prompt_toolkit.styles import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import set_title, clear_title
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path


appName = "Search Bible AI"
abbrev = BibleBooks.abbrev["eng"]

historyFolder = os.path.join(config.storagedirectory, "history")
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
search_closest_match_history = os.path.join(historyFolder, "search_closest_match")
search_closest_match_session = PromptSession(history=FileHistory(search_closest_match_history))
search_regex_history = os.path.join(historyFolder, "search_regex")
search_regex_session = PromptSession(history=FileHistory(search_regex_history))

promptStyle = Style.from_dict({
    # User input (default text).
    "": config.terminalCommandEntryColor2,
    # Prompt.
    "indicator": config.terminalPromptIndicatorColor2,
})

def getLastEntry(logFile: str) -> str:
    def isEntry(line):
        line = line.strip()
        return (re.search("^\+[^\.].*?$", line) and not line[1:] in (config.exit_entry, config.cancel_entry))
    if os.path.isfile(logFile) and not os.path.getsize(logFile) == 0:
        with open(logFile, "r", encoding="utf-8") as fileObj:
            lines = tuple(filter(isEntry, fileObj.readlines()))
        if lines:
            return lines[-1][1:].strip()
    return ""

def read(default: str="") -> None:
    HealthCheck.print2("Search Bible AI")
    HealthCheck.print3("Developed by: Eliran Wong")
    HealthCheck.print3("Open source: https://github.com/eliranwong/searchbibleai")
    HealthCheck.print2(config.divider)
    HealthCheck.print("* enter a single reference to display a full chapter")
    HealthCheck.print("* enter multiple references to display verses")
    HealthCheck.print("* enter a bible version abbreviation, e.g. KJV, to switch version")
    HealthCheck.print("* enter a search query to perform a simple search")
    HealthCheck.print("* enter '.verses' or press 'Ctrl+F' to perform a detailed search for verses")
    HealthCheck.print("* enter '.paragraphs' or press 'Esc+F' to perform a detailed search for paragraphs")
    HealthCheck.print(f"* enter '{config.exit_entry}' or press 'Ctrl+Q' to exit current feature of quit this app")
    HealthCheck.print2(config.divider)

    if not default:
        default = getLastEntry(read_history)

    parser = BibleVerseParser(config.parserStandarisation)

    this_key_bindings = KeyBindings()
    @this_key_bindings.add("c-f")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".verses"
        buffer.validate_and_handle()
    @this_key_bindings.add("escape", "f")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".paragraphs"
        buffer.validate_and_handle()
    @this_key_bindings.add("c-p")
    def _(event):
        config.chapterParagraphsAndSubheadings = not config.chapterParagraphsAndSubheadings
        HealthCheck.print3(f"Chapter Paragraphs and Subheadings: {'ON' if config.chapterParagraphsAndSubheadings else 'OFF'}")
        buffer = event.app.current_buffer
        buffer.text = ":"
        buffer.validate_and_handle()

    prompts = Prompts(custom_key_bindings=this_key_bindings)

    while True:
        userInput = prompts.simplePrompt(
            style=config.promptStyle1,
            promptSession=read_session,
            completer=read_completer,
            default=default,
            accept_default=True if default else False,
            bottom_toolbar=" [ctrl+q] exit [ctrl+k] shortcut keys ",
        )
        default = ""
        if userInput == config.exit_entry:
            break
        elif userInput == ".verses":
            # ctrl+f to search verses
            search(bible=config.mainText, paragraphs=False)
        elif userInput == ".paragraphs":
            # ctrl+p to search paragraphs
            search(bible=config.mainText, paragraphs=True)
        elif userInput:
            HealthCheck.print2(config.divider)

            # transform aliases
            bookName = abbrev[str(config.mainB)][0]
            if userInput in Bible.getBibleList() + Bible.getUbaBibleList():
                # change bible version
                config.mainText = userInput
                userInput = f"{bookName} {config.mainC}:{config.mainV}"
            elif userInput == ":":
                # loaded previous selected verse
                userInput = f"{bookName} {config.mainC}:{config.mainV}"
            elif re.search("^[0-9]+?:$", userInput):
                # change chapter
                userInput = f"{bookName} {userInput[:-1]}:1"
            elif re.search("^:[0-9]+?$", userInput):
                # change verse
                userInput = f"{bookName} {config.mainC}:{userInput[1:]}"

            if refs := parser.extractAllReferences(userInput):
                # verse reference(s) provided
                isChapter = (len(refs) == 1 and len(refs[0]) == 3)
                if isChapter:
                    # check if it is a single reference; display a full chapter
                    fullChapter, verses = Bible.getVerses(refs, config.mainText)
                    chapterTitle = False
                    for _, book, chapter, verse, scripture in fullChapter:
                        if not chapterTitle:
                            book_abbr = abbrev[str(book)][0]
                            HealthCheck.print2(f"# {book_abbr} {chapter}")
                            chapterTitle = True
                        elif config.chapterParagraphsAndSubheadings and (book, chapter, verse) in agbParagraphs:
                            print("")
                        if config.chapterParagraphsAndSubheadings and f"{book}.{chapter}.{verse}" in agbSubheadings:
                            HealthCheck.print2(f"## {agbSubheadings[f'{book}.{chapter}.{verse}']}")
                        HealthCheck.print4(f"({verse}) {scripture.strip()}")
                    # draw a whole chapter
                    HealthCheck.print2(config.divider)
                else:
                    verses = Bible.getVerses(refs, config.mainText)
                # display all verses
                for _, book, chapter, verse, scripture in verses:
                    book_abbr = abbrev[str(book)][0]
                    HealthCheck.print4(f"({book_abbr} {chapter}:{verse}) {scripture.strip()}")
            else:
                search(bible=config.mainText, paragraphs=False, simpleSearch=userInput)

            HealthCheck.print2(config.divider)

# combined semantic searches, literal searches and regular expression searches
def search(bible:str="NET", paragraphs:bool=False, simpleSearch="") -> None:

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

    if simpleSearch:
        meaning = simpleSearch.replace("\n", " ")
        n_results = config.maxClosestMatches
        where = None
        contains = None
        regex = None
    else:
        # user input
        HealthCheck.print2(f"SEARCH {'PARAGRAPHS' if paragraphs else 'VERSES'}")
        HealthCheck.print2(config.divider)
        # search in books
        HealthCheck.print2("In books (use '||' for combo, '-' for range):")
        print("e.g. Gen||Matt-John||Rev")
        books = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_book_session, completer=book_completer, default=getLastEntry(search_book_history))
        if books.lower() == config.exit_entry:
            return
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
        HealthCheck.print2("In chapters (use '||' for combo, '-' for range):")
        print("e.g. 2||4||6-8||10")
        chapters = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_chapter_session, validator=NumberValidator(), default=getLastEntry(search_chapter_history))
        if chapters.lower() == config.exit_entry:
            return
        if chapters.lower() == "all":
            chapters = ""
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
        HealthCheck.print2("Search for plain words ('||' denotes 'or'; '&amp;&amp;' denotes 'and'):")
        print("e.g. Lord&amp;&amp;God||Jesus&amp;&amp;love")
        contains = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_literal_session, default=getLastEntry(search_literal_history))
        if contains.lower() == config.exit_entry:
            return
        if contains.strip():
            splits = contains.split("||")
            contains = {"$or": [getAndItems(i) for i in splits]} if len(splits) > 1 else getAndItems(contains)
        else:
            contains = ""
        # search for meaning
        HealthCheck.print2("Search for meaning:")
        meaning = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_semantic_session)
        if meaning.lower() == config.exit_entry:
            return
        if meaning:
            HealthCheck.print2("Maximum number of closest matches:")
            # specify number of closest matches
            default_n_results = config.maxClosestMatches
            n_results = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_closest_match_session, validator=NumberValidator(), default=str(default_n_results))
            if n_results.lower() == config.exit_entry:
                return
            if n_results and int(n_results) > 0:
                config.maxClosestMatches = int(n_results)
            else:
                config.maxClosestMatches = default_n_results
        # search for regex
        HealthCheck.print2("Search for regular expression:")
        regex = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_regex_session, default=getLastEntry(search_regex_history))
        if regex.lower() == config.exit_entry:
            return

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
        # run query
        res = collection.query(
            query_texts=[meaning],
            n_results = config.maxClosestMatches,
            where=where,
            where_document=contains if contains else None,
        )
    else:
        res = collection.get(
            where=where,
            where_document=contains if contains else None,
        )
    HealthCheck.print2(config.divider)
    HealthCheck.print2(f">>> Retrieved {'paragraphs' if paragraphs else 'verses'}:\n")

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
                scripture = re.sub(r"\A(.+?)$", r"<{0}>## \1</{0}>".format(config.terminalPromptIndicatorColor2), scripture, flags=re.M)
                scripture = re.sub("^([0-9]+?:[0-9]+?) ", r"<{0}>(\1)</{0}>".format(config.terminalPromptIndicatorColor2), scripture, flags=re.M)
                print_formatted_text(HTML(f"## {scripture.strip()}\n"))
    else:
        for _, book, chapter, verse, scripture in verses:
            book_abbr = abbrev[str(book)][0]
            if not regex or (regex and re.search(regex, scripture, flags=re.IGNORECASE)):
                HealthCheck.print4(f"({book_abbr} {chapter}:{verse}) {scripture.strip()}")
    
    if not simpleSearch:
        HealthCheck.print2(config.divider)

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="SearchBibleAI CLI options")
    # Add arguments
    parser.add_argument("default", nargs="?", default=None, help="Specify a bible module, e.g. KJV, NET, etc.")
    # Parse arguments
    args = parser.parse_args()
    # Get options
    default = args.default.strip() if args.default and args.default.strip() else ""

    # set terminal title
    set_title("Search Bible AI")
    # check log files; delete old lines if too many
    for i in (
        read_history,
        search_book_history,
        search_chapter_history,
        search_literal_history,
        search_semantic_history,
        search_closest_match_history,
        search_regex_history,
    ):
        HealthCheck.set_log_file_max_lines(i, 3000)
    # start with reading mode
    read(default=default)
    # back up config on closing
    HealthCheck.print2("Saving configurations ...")
    HealthCheck.saveConfig()
    shutil.copy(configFile, os.path.join(config.storagedirectory, "config_backup.py"))
    # clear terminal title
    HealthCheck.print2("Closing ...")
    clear_title()


if __name__ == '__main__':
    main()