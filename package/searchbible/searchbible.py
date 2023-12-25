from searchbible.health_check import HealthCheck
from searchbible.convertor.bible import ConvertBible
from searchbible import config
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

    meaning = ""
    while not meaning == ".quit":
        # user input
        meaning = input("Search for meaning: ")
        if meaning == ".quit":
            break
        books = input("In books: ")
        if books := books.strip():
            splits = books.split("||")
            books = {"$or": [{"book_abbr": i.strip()} for i in splits]} if len(splits) > 1 else {"book_abbr": books.strip()}
        contains = input("In verses that literally contain: ")
        if contains.strip():
            splits = contains.split("||")
            contains = {"$or": [getAndItems(i) for i in splits]} if len(splits) > 1 else getAndItems(contains)
        else:
            contains = ""
        regex = input("With regular expression: ")
        if meaning:
            res = collection.query(
                query_texts=[meaning],
                n_results = 10,
                where=books if books else None,
                where_document=contains if contains else None,
            )
        else:
            res = collection.get(
                where=books if books else None,
                where_document=contains if contains else None,
            )
        print("--------------------")
        print(">>> retrieved verses: \n")
        metadatas = res["metadatas"][0] if meaning else res["metadatas"]
        refs = [f'''{i["book_abbr"]} {i["chapter"]}:{i["verse"]}''' for i in metadatas]
        # results = filter(lambda scripture: re.search(regex, scripture, flags=re.IGNORECASE), zip(refs, res["documents"][0] if meaning else res["documents"]))
        for ref, scripture in zip(refs, res["documents"][0] if meaning else res["documents"]):
            if not regex or (regex and re.search(regex, scripture, flags=re.IGNORECASE)):
                print(f"({ref}) {scripture}")
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