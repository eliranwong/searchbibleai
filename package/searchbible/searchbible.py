from searchbible.health_check import HealthCheck
from searchbible.converter.bible import ConvertBible
from searchbible.utils.BibleBooks import BibleBooks
from searchbible import config
from packaging import version as ver
from chromadb.config import Settings
import os, chromadb, re, argparse


# combined semantic and literal and regular expression searches

def searchVerses(version: str) -> None:

    def getAndItems(query):
        splits = query.split("&&")
        return {"$and": [{"$contains": i} for i in splits]} if len(splits) > 1 else {"$contains": query}

    #dbpath
    dbpath = os.path.join(HealthCheck.getFiles(), "bibles", version)
    if not os.path.isdir(dbpath):
        if version in ("KJV", "NET"):
            print(f"Converting {version} bible ...")
            ConvertBible.convert_bible(os.path.join("data", "bibles", f"{version}.bible"))
        else:
            HealthCheck.print3(f"Bible version not found: {version}")
            return None

    # client
    chroma_client = chromadb.PersistentClient(dbpath, Settings(anonymized_telemetry=False))
    # collection
    collection = chroma_client.get_or_create_collection(
        name="verses",
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

    while True:
        # user input
        HealthCheck.print2("SEARCH VERSES")
        print("--------------------")
        # search in books
        books = input("In books: ")
        books = BibleBooks.getBookCombo(books)
        if books:
            books = {"book_abbr": {"$in": books}}
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
        if chapters:
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
        print(">>> retrieved verses: \n")
        metadatas = res["metadatas"][0] if meaning else res["metadatas"]
        verses = [(i["book_abbr"], i["book"], i["chapter"], i["verse"], res["documents"][0][index] if meaning else res["documents"][index]) for index, i in enumerate(metadatas)]
        if not meaning:
            # sorting for non-semantic search
            verses = sorted(verses, key=lambda x: ver.parse(f"{x[1]}.{x[2]}.{x[3]}"))
        for book_abbr, _, chapter, verse, scripture in verses:
            if not regex or (regex and re.search(regex, scripture, flags=re.IGNORECASE)):
                print(f"({book_abbr} {chapter}:{verse}) {scripture.strip()}")
        print("--------------------")
    return None

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
    searchVerses(version=version if version else "NET")


if __name__ == '__main__':
    main()