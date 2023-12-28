from searchbible.health_check import HealthCheck
from searchbible.converter.bible import ConvertBible
from searchbible import config
from searchbible.utils.RefUtil import RefUtil
from chromadb.config import Settings
import chromadb, os
from packaging import version


class Bible:

    @staticmethod
    def getBibleList() -> list:
        bibles = os.path.join(config.storagedirectory, "bibles")
        return [i for i in os.listdir(bibles) if os.path.isdir(os.path.join(bibles, i)) and os.path.isfile(os.path.join(bibles, i, "chroma.sqlite3"))]

    @staticmethod
    def getUbaBibleList() -> list:
        return [i[:-6] for i in os.listdir(os.path.join(config.packageFolder, "data", "bibles")) if os.path.isfile(os.path.join(config.packageFolder, "data", "bibles", i)) and i.endswith(".bible")]

    @staticmethod
    def getDbPath(bible: str) -> str:
        def convertBible(bible: str):
            HealthCheck.print3(f"Converting bible: {bible} ...")
            ConvertBible.convert_bible(os.path.join(config.packageFolder, "data", "bibles", f"{bible}.bible"))
        installedBibles = Bible.getBibleList()
        dbpath = os.path.join(config.storagedirectory, "bibles", bible)
        if bible in installedBibles:
            config.mainText = bible
            return dbpath
        elif bible in Bible.getUbaBibleList():
            convertBible(bible)
            config.mainText = bible
            return dbpath
        else:
            bible = "NET"
            if not bible in installedBibles:
                convertBible(bible)
            config.mainText = "NET"
            return os.path.join(config.storagedirectory, "bibles", "NET")

    @staticmethod
    def getVerses(refs: list, bible: str = "NET") -> list:
        isChapter = (len(refs) == 1 and len(refs[0]) == 3)

        filters = RefUtil.getAllRefFilters(refs)
        if not filters:
            return []
        #dbpath
        dbpath = Bible.getDbPath(bible)
        if not dbpath:
            return []
        # client
        chroma_client = chromadb.PersistentClient(dbpath, Settings(anonymized_telemetry=False))
        # collection
        collection = chroma_client.get_or_create_collection(
            name="verses",
            metadata={"hnsw:space": "cosine"},
            embedding_function=HealthCheck.getEmbeddingFunction(embeddingModel="all-mpnet-base-v2"),
        )
        res = collection.get(where=filters["$or"][0] if isChapter else filters)
        # unpack data
        metadatas = res["metadatas"]
        documents = res["documents"]
        verses = [(metadata["reference"], metadata["book"], metadata["chapter"], metadata["verse"], document) for metadata, document in zip(metadatas, documents)]
        # sorting
        verses = sorted(verses, key=lambda x: version.parse(x[0]))

        # check if it is a single reference; get also all verses in the chapter
        if isChapter:
            config.mainB, config.mainC, config.mainV = refs[0]
            res0 = collection.get(where={"$and": [{"book": {"$eq": config.mainB}}, {"chapter": {"$eq": config.mainC}}]})
            metadatas = res0["metadatas"]
            documents = res0["documents"]
            chapter = [(metadata["reference"], metadata["book"], metadata["chapter"], metadata["verse"], document) for metadata, document in zip(metadatas, documents)]
            return [sorted(chapter, key=lambda x: version.parse(x[0])), verses]
        else:
            return verses