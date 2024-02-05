import os, platform

mainFile = os.path.realpath(__file__)
packageFolder = os.path.dirname(mainFile)

# create config.py if it does not exist; in case user delete the file for some reasons
configFile = os.path.join(packageFolder, "config.py")
if not os.path.isfile(configFile):
    open(configFile, "a", encoding="utf-8").close()

try:
    from searchbible import config
except:
    # write off problematic config file
    open(configFile, "w", encoding="utf-8").close()
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
import chromadb, re, argparse, shutil, threading, asyncio, sys, traceback
from searchbible.chatgpt import ChatGPT
from searchbible.geminipro import GeminiPro
from searchbible.utils.BibleBooks import BibleBooks
from searchbible.utils.BibleVerseParser import BibleVerseParser
from searchbible.utils.prompts import Prompts
from searchbible.utils.prompt_dialogs import TerminalModeDialogs
from searchbible.utils.prompt_validator import NumberValidator
from searchbible.db.Bible import Bible
from searchbible.utils.AGBsubheadings import agbSubheadings
from searchbible.utils.AGBparagraphs_expanded import agbParagraphs
from searchbible.utils.bible_studies import bible_study_suggestions
from packaging import version
from chromadb.config import Settings
from prompt_toolkit.styles import Style
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter
from prompt_toolkit.shortcuts import set_title, clear_title
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.input import create_input
from prompt_toolkit.keys import Keys
from pathlib import Path

# Work with VLC player for bible audio playback
import vlc
# Create a VLC instance
vlc_instance = vlc.Instance()
# Create a media player
media_player = vlc_instance.media_player_new()

appName = "Search Bible AI"
abbrev = BibleBooks.abbrev["eng"]
kjvRefs, _ = BibleBooks().getAllKJVreferences()
config.currentVerses = []

actions = sorted([
    ".configs",
    ".audio",
    ".verses",
    ".paragraphs",
    ".bibles",
    ".chatgpt",
    ".geminipro",
    ".setdefaultchatbot",
    "[chat]",
    "[chatgpt]",
    "[geminipro]",
])

historyFolder = os.path.join(config.storagedirectory, "history")
Path(historyFolder).mkdir(parents=True, exist_ok=True)
read_history = os.path.join(historyFolder, "read")
read_session = PromptSession(history=FileHistory(read_history))
bible_study_suggestions = [f"{i}[chat]\n" for i in bible_study_suggestions]
config.read_suggestions = Bible.getBibleList() + [i[0] for i in abbrev.values()] + kjvRefs + bible_study_suggestions
read_completer = FuzzyCompleter(WordCompleter(config.read_suggestions + actions, ignore_case=True, sentence=True))
search_book_history = os.path.join(historyFolder, "search_book")
search_book_session = PromptSession(history=FileHistory(search_book_history))
book_suggestions = ["ALL"] + [i[0] for i in abbrev.values()]
book_completer = FuzzyCompleter(WordCompleter(book_suggestions, ignore_case=True))
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

def removeSpecialEntries(content):
    return re.sub("\[chatgpt\]|\[chat\]|\[geminipro\]", "", content)
config.removeSpecialEntries = removeSpecialEntries

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

def compareBibles(ref: str, paragraphs: bool=False) -> None:
    if config.compareBibles:
        for i in filter(lambda x: not x == config.mainText, config.compareBibleVersions):
            if data := Bible.getSingleItem(ref, i, paragraphs):
                *_, itemContent = data
                if paragraphs:
                    itemContent = re.sub("\\A.*?\n", "", itemContent.strip())
                    print(f"({i})\n{itemContent}\n")
                else:
                    itemContent = itemContent.strip()
                    config.currentVerses.append((i, ref, itemContent))
                    HealthCheck.print4(f"({i}) {itemContent}")

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
    HealthCheck.print("* press 'Ctrl+K' for more keyboard shortcuts")
    HealthCheck.print(f"* enter '{config.exit_entry}' or press 'Ctrl+Q' to exit current feature of quit this app")
    HealthCheck.print2(config.divider)

    def setDefaultChatbot():
        dialogs = TerminalModeDialogs(None)
        model = dialogs.getValidOptions(
            options=("chatgpt", "geminipro"),
            title="Default Chatbot",
            default=config.chatbot,
            text="Default chatbot is loaded when you include '[chat]' in your input.",
        )
        if model:
            config.chatbot = model
            print(f"Default chatbot: {model}")

    def selectBibleForComparison():
        dialogs = TerminalModeDialogs(None)
        options = Bible.getBibleList()
        versions = dialogs.getMultipleSelection(
            title="Bibles for Comparison",
            text="Select bible version(s):",
            options=options,
            default_values=config.compareBibleVersions,
        )
        if versions:
            config.compareBibleVersions = versions

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
    @this_key_bindings.add("c-g")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".chatgpt" if config.chatbot == "chatgpt" else ".geminipro"
        buffer.validate_and_handle()
    @this_key_bindings.add("escape", "g")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".geminipro" if config.chatbot == "chatgpt" else ".chatgpt"
        buffer.validate_and_handle()
    @this_key_bindings.add("c-p")
    def _(event):
        config.compareBibles = not config.compareBibles
        HealthCheck.print3(f"Bible Comparison: {'ON' if config.compareBibles else 'OFF'}")
        buffer = event.app.current_buffer
        buffer.text = getLastEntry(read_history)
        buffer.validate_and_handle()
    @this_key_bindings.add("escape", "p")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".bibles"
        buffer.validate_and_handle()
    @this_key_bindings.add("c-s")
    def _(event):
        config.chapterParagraphsAndSubheadings = not config.chapterParagraphsAndSubheadings
        HealthCheck.print3(f"Chapter Paragraphs and Subheadings: {'ON' if config.chapterParagraphsAndSubheadings else 'OFF'}")
        buffer = event.app.current_buffer
        buffer.text = ":"
        buffer.validate_and_handle()
    @this_key_bindings.add("c-y")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".audio"
        buffer.validate_and_handle()
    @this_key_bindings.add("escape", "c")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".configs"
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

        # default chatbot
        userInput = userInput.replace("[chat]", f"[{config.chatbot}]")

        if userInput == config.exit_entry:
            break
        elif userInput == ".configs":
            changeConfigs()
        elif userInput == ".verses":
            # ctrl+f to search verses
            search(bible=config.mainText, paragraphs=False)
        elif userInput == ".paragraphs":
            # ctrl+p to search paragraphs
            search(bible=config.mainText, paragraphs=True)
        elif userInput == ".bibles":
            selectBibleForComparison()
        elif userInput == ".setdefaultchatbot":
            setDefaultChatbot()
        elif "[chatgpt]" in userInput:
            default = ChatGPT(
                temperature=config.llmTemperature,
                max_output_tokens = config.chatGPTApiMaxTokens,
            ).run(userInput)
        elif userInput == ".chatgpt":
            default = ChatGPT(
                temperature=config.llmTemperature,
                max_output_tokens = config.chatGPTApiMaxTokens,
            ).run()
        elif "[geminipro]" in userInput:
            default = GeminiPro(
                temperature=config.llmTemperature,
                max_output_tokens = config.chatGPTApiMaxTokens,
            ).run(userInput)
        elif userInput == ".geminipro":
            default = GeminiPro(
                temperature=config.llmTemperature,
                max_output_tokens = config.chatGPTApiMaxTokens,
            ).run()
        elif userInput == ".audio":
            playBibleAudio()
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
            elif re.search("^[0-9]+?:[0-9]+?$", userInput):
                # change both chapter and verse in the same book
                userInput = f"{bookName} {userInput}"
            elif re.search("^[0-9]+?:$", userInput):
                # change chapter in the same book
                userInput = f"{bookName} {userInput[:-1]}:1"
            elif re.search("^:[0-9]+?$", userInput):
                # change verse in the same book
                userInput = f"{bookName} {config.mainC}:{userInput[1:]}"

            if refs := parser.extractAllReferences(userInput):
                # reset config.currentVerses
                config.currentVerses = []
                # verse reference(s) provided
                isChapter = (len(refs) == 1 and len(refs[0]) == 3)
                if isChapter:
                    # check if it is a single reference; display a full chapter
                    fullChapter, verses = Bible.getVerses(refs, config.mainText)
                    chapterTitle = False
                    for ref, book, chapter, verse, scripture in fullChapter:
                        if not chapterTitle:
                            book_abbr = abbrev[str(book)][0]
                            HealthCheck.print2(f"# {book_abbr} {chapter}")
                            chapterTitle = True
                        elif config.chapterParagraphsAndSubheadings and (book, chapter, verse) in agbParagraphs:
                            print("")
                        if config.chapterParagraphsAndSubheadings and f"{book}.{chapter}.{verse}" in agbSubheadings:
                            HealthCheck.print2(f"## {agbSubheadings[f'{book}.{chapter}.{verse}']}")
                        scripture = scripture.strip()
                        config.currentVerses.append((config.mainText, ref, scripture))
                        HealthCheck.print4(f"({verse}) {scripture}")
                        compareBibles(ref)
                    # draw a whole chapter
                    HealthCheck.print2(config.divider)
                else:
                    verses = Bible.getVerses(refs, config.mainText)
                # display all verses
                book_chapter = ""
                for ref, book, chapter, verse, scripture in verses:
                    this_book_chapter = f"{book}.{chapter}"
                    if not book_chapter:
                        book_chapter = this_book_chapter
                    elif not this_book_chapter == book_chapter:
                        HealthCheck.print2(config.divider)
                        book_chapter = this_book_chapter
                    book_abbr = abbrev[str(book)][0]
                    scripture = scripture.strip()
                    config.currentVerses.append((config.mainText, ref, scripture))
                    HealthCheck.print4(f"({book_abbr} {chapter}:{verse}) {scripture}")
                    compareBibles(ref)
                HealthCheck.print2(config.divider)
            else:
                search(bible=config.mainText, paragraphs=False, simpleSearch=userInput)
                HealthCheck.print2(config.divider)

# change configs
def changeConfigs():
    def loadConfig(configPath):
        with open(configPath, "r", encoding="utf-8") as fileObj:
            configs = fileObj.read()
        configs = "from searchbible import config\n" + re.sub("^([A-Za-z])", r"config.\1", configs, flags=re.M)
        exec(configs, globals())
    # file paths
    configFile = os.path.join(config.packageFolder, 'config.py')
    backupFile = os.path.join(config.storagedirectory, "config_backup.py")
    # backup configs
    HealthCheck.saveConfig()
    shutil.copy(configFile, backupFile)
    # open current configs with built-in text editor
    eTextEditor = f"{sys.executable} {os.path.join(config.packageFolder, 'eTextEdit.py')}"
    os.system(f"{eTextEditor} {configFile}")
    set_title("Search Bible AI")
    # re-load configs
    try:
        loadConfig(configFile)
        HealthCheck.print2("Changes loaded!")
    except:
        HealthCheck.print2("Failed to load your changes!")
        print(traceback.format_exc())
        try:
            HealthCheck.print2("Restoring backup ...")
            loadConfig(backupFile)
            shutil.copy(backupFile, configFile)
            HealthCheck.print2("Restored!")
        except:
            HealthCheck.print2("Failed to restore backup!")

# play bible audio
def playAudioFile(audioFile):
    media = vlc_instance.media_new(audioFile)
    media_player.set_media(media)
    media_player.play()
    media_player.set_rate(config.vlcSpeed)
    while config.playback and media_player.get_state() != vlc.State.Ended:
        continue

def startBibleAudioPlayback(playback_event):
    for version, ref, scripture in config.currentVerses:
        if config.playback and not playback_event.is_set():
            b, c, v = ref.split(".")
            audioFile = os.path.join(config.storagedirectory, "audio", version, "default", f"{b}_{c}", f"{version}_{b}_{c}_{v}.mp3")
            b = abbrev[str(b)][0]
            if os.path.isfile(audioFile):
                HealthCheck.print2(f"{version} - {b} {c}:{v}")
                HealthCheck.print(scripture)
                playAudioFile(audioFile)
        else:
            break
    if not playback_event.is_set():
        playback_event.set()

def closeMediaPlayer():
    media_player.stop()
    config.playback = False
    HealthCheck.print2("\nMedia player stopped!")

def keyToStopPlayback(playback_event):
    # allow users to stop the playback by pressing either ctrl+Q or ctrl+z
    async def readKeys() -> None:
        # create an input
        input = create_input()
        # capture key input
        def keys_ready():
            for key_press in input.read_keys():
                #print(key_press)
                if key_press.key in (Keys.ControlQ, Keys.ControlZ):
                    closeMediaPlayer()
                    playback_event.set()
        # loop when playback is in progress
        with input.raw_mode():
            with input.attach(keys_ready):
                while config.playback and not playback_event.is_set():
                    await asyncio.sleep(0.1)
    # run readKeys
    asyncio.run(readKeys())

def playBibleAudio():
    playback_event = threading.Event()
    playback_thread = threading.Thread(target=startBibleAudioPlayback, args=(playback_event,))
    config.playback = True
    playback_thread.start()
    keyToStopPlayback(playback_event)
    playback_thread.join()

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
        embedding_function=HealthCheck.getEmbeddingFunction(embeddingModel="paraphrase-multilingual-mpnet-base-v2"),
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
        meaning = HealthCheck.simplePrompt(style=promptStyle, promptSession=search_semantic_session, default=getLastEntry(search_semantic_history))
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
    if not simpleSearch:
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
        for ref, book, chapter, verse, chapter_end, verse_end, scripture in verses:
            book_abbr = abbrev[str(book)][0]
            if not regex or (regex and re.search(regex, scripture, flags=re.I|re.M)):
                HealthCheck.print2(f"# {book_abbr} {chapter}:{verse}-{chapter_end}:{verse_end}")
                scripture = re.sub(r"\A(.+?)$", r"<{0}>## \1</{0}>".format(config.terminalPromptIndicatorColor2), scripture, flags=re.M)
                scripture = re.sub("^([0-9]+?:[0-9]+?) ", r"<{0}>(\1)</{0}>".format(config.terminalPromptIndicatorColor2), scripture, flags=re.M)
                print_formatted_text(HTML(f"{scripture.strip()}\n"))
                compareBibles(ref, paragraphs=True)
    else:
        for ref, book, chapter, verse, scripture in verses:
            book_abbr = abbrev[str(book)][0]
            if not regex or (regex and re.search(regex, scripture, flags=re.IGNORECASE)):
                scripture = scripture.strip()
                config.currentVerses.append((config.mainText, ref, scripture))
                HealthCheck.print4(f"({book_abbr} {chapter}:{verse}) {scripture}")
                compareBibles(ref)
    
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

    # Release the media player
    media_player.release()
    # Release the VLC instance
    vlc_instance.release()


if __name__ == '__main__':
    main()