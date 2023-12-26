from searchbible.health_check import HealthCheck
from searchbible.converter.bible import ConvertBible
from searchbible.utils.BibleBooks import BibleBooks
from searchbible import config
from packaging import version as ver
from chromadb.config import Settings
import os, chromadb, re, argparse

thisFile = os.path.realpath(__file__)
packageFolder = os.path.dirname(thisFile)

# combined semantic and literal and regular expression searches

def search(version: str, paragraphs: bool = False) -> None:

    def getAndItems(query):
        splits = query.split("&&")
        return {"$and": [{"$contains": i} for i in splits]} if len(splits) > 1 else {"$contains": query}

    #dbpath
    dbpath = os.path.join(HealthCheck.getFiles(), "bibles", version)
    if not os.path.isdir(dbpath):
        if version in ("KJV", "NET"):
            HealthCheck.print3(f"Converting bible: {version} ...")
            ConvertBible.convert_bible(os.path.join(packageFolder, "data", "bibles", f"{version}.bible"))
        else:
            HealthCheck.print3(f"Bible version not found: {version}")
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

    abbrev = BibleBooks.abbrev["eng"]

    while True:
        # user input
        HealthCheck.print2(f"SEARCH {'PARAGRAPHS' if paragraphs else 'VERSES'}")
        print("--------------------")
        # search in books
        books = input("In books: ")
        books = BibleBooks.getBookCombo(books)
        if books:
            if paragraphs:
                books = {"book_start": {"$in": books}}
            else:
                books = {"book": {"$in": books}}
        else:
            books = {}
        # search in chapters
        chapters = input("In chapters: ")
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
        contains = input("Search for plain words: ")
        if contains.strip():
            splits = contains.split("||")
            contains = {"$or": [getAndItems(i) for i in splits]} if len(splits) > 1 else getAndItems(contains)
        else:
            contains = ""
        # search for meaning
        meaning = input("Search for meaning: ")
        # search for regex
        regex = input("Search for regular expression: ")

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
        print("--------------------")
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
            verses = sorted(verses, key=lambda x: ver.parse(x[0]))

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
        print("--------------------")

def main():
    # set up basic configs
    if not hasattr(config, "openaiApiKey"):
        HealthCheck.setBasicConfig()

    # Create the parser
    parser = argparse.ArgumentParser(description="SearchBibleAI CLI options")
    # Add arguments
    parser.add_argument("default", nargs="?", default=None, help="Specify a bible module, e.g. KJV, NET, etc.")
    # Parse arguments
    args = parser.parse_args()
    # Get options
    version = args.default.strip() if args.default and args.default.strip() else ""
    if not version:
        version = input("Enter a bible version (e.g. KJV, NET, etc.): ").strip()

    # search verses
    search(version=version if version else "NET")


if __name__ == '__main__':
    main()