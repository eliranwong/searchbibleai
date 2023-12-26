from searchbible.health_check import HealthCheck
from searchbible.converter.bible import ConvertBible
from searchbible import config
from searchbible.utils.RefUtil import RefUtil
from chromadb.config import Settings
import chromadb, os
from packaging import version


class Bible:

    @staticmethod
    def getDbPath(bible: str) -> str:
        #dbpath
        dbpath = os.path.join(HealthCheck.getFiles(), "bibles", bible)
        if os.path.isdir(dbpath):
            return dbpath
        elif bible in ("KJV", "NET"):
            HealthCheck.print3(f"Converting bible: {bible} ...")
            ConvertBible.convert_bible(os.path.join(config.packageFolder, "data", "bibles", f"{bible}.bible"))
            return dbpath
        else:
            HealthCheck.print3(f"Bible version not found: {bible}")
            return ""

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
            b, c, _ = refs[0]
            res0 = collection.get(where={"$and": [{"book": {"$eq": b}}, {"chapter": {"$eq": c}}]})
            metadatas = res0["metadatas"]
            documents = res0["documents"]
            chapter = [(metadata["reference"], metadata["book"], metadata["chapter"], metadata["verse"], document) for metadata, document in zip(metadatas, documents)]
            return [sorted(chapter, key=lambda x: version.parse(x[0])), verses]
        else:
            return verses