import apsw, uuid, os, chromadb, shutil
from chromadb.config import Settings
from searchbible import config
from searchbible.utils.AGBsubheadings import agbSubheadings
from searchbible.utils.AGBparagraphs_expanded import agbParagraphs
from searchbible.health_check import HealthCheck
from pathlib import Path
from prompt_toolkit.shortcuts import ProgressBar


class ConvertBible:
    """
    Convert UniqueBible App bible files (*.bible) into Chromadb format
    """

    @staticmethod
    def convert_bible(database: str) -> None:
        if not os.path.isfile(database) or not database.endswith(".bible"):
            print("Invalid file path given!")
            return None
        else:
            version = os.path.basename(database)[:-6]
        
        def getAllVerses():
            # get all verses from Unique Bible App bible file
            with apsw.Connection(database) as connection:
                cursor = connection.cursor()
                query = "SELECT * FROM Verses ORDER BY Book, Chapter, Verse"
                cursor.execute(query)
                allVerses = cursor.fetchall()
                return allVerses
            return ()

        # database path
        dbpath = os.path.join(config.storagedirectory, "bibles", version)
        if os.path.isdir(dbpath):
            # remove old database if it exists
            HealthCheck.print3(f"Removing old database: {dbpath}")
            shutil.rmtree(dbpath, ignore_errors=True)
        HealthCheck.print3(f"Creating database: {dbpath}")
        # create directory for chromadb files
        Path(dbpath).mkdir(parents=True, exist_ok=True)
        # keep all original data
        shutil.copy(database, os.path.join(dbpath, "chroma.sqlite3"))
        # client
        chroma_client = chromadb.PersistentClient(dbpath, Settings(anonymized_telemetry=False))
        # collection
        collectionVerse = chroma_client.get_or_create_collection(
            name="verses",
            metadata={"hnsw:space": "cosine"},
            embedding_function=HealthCheck.getEmbeddingFunction(embeddingModel="paraphrase-multilingual-mpnet-base-v2"),
        )
        collectionParagraph = chroma_client.get_or_create_collection(
            name="paragraphs",
            metadata={"hnsw:space": "cosine"},
            embedding_function=HealthCheck.getEmbeddingFunction(embeddingModel="paraphrase-multilingual-mpnet-base-v2"),
        )

        paragraphTitle = ""
        paragraphStart = ""
        paragraphStartB = ""
        paragraphStartC = ""
        paragraphStartV = ""
        paragraphEnd = ""
        paragraphEndB = ""
        paragraphEndC = ""
        paragraphEndV = ""
        paragraphContent = ""            

        with ProgressBar() as pb:
            for book, chapter, verse, scripture in pb(getAllVerses()):
                bcv = f"{book}.{chapter}.{verse}"

                metadata = {
                    "book": book,
                    "chapter": chapter,
                    "verse": verse,
                    "reference": bcv,
                }
                id = str(uuid.uuid4())
                collectionVerse.add(
                    documents = [scripture],
                    metadatas = [metadata],
                    ids = [id]
                )

                if bcv in agbSubheadings:
                    if paragraphStart and paragraphEnd:
                        # save previous paragraph
                        metadata = {
                            "title": paragraphTitle,
                            "start": paragraphStart,
                            "book_start": paragraphStartB,
                            "chapter_start": paragraphStartC,
                            "verse_start": paragraphStartV,
                            "end": paragraphEnd,
                            "book_end": paragraphEndB,
                            "chapter_end": paragraphEndC,
                            "verse_end": paragraphEndV,
                        }
                        id = str(uuid.uuid4())
                        collectionParagraph.add(
                            documents = [paragraphContent],
                            metadatas = [metadata],
                            ids = [id]
                        )
                    paragraphTitle = agbSubheadings.get(bcv)
                    paragraphStart = bcv
                    paragraphStartB = book
                    paragraphStartC = chapter
                    paragraphStartV = verse
                    paragraphContent = f"{paragraphTitle}\n{chapter}:{verse} {scripture}"
                else:
                    if (book, chapter, verse) in agbParagraphs:
                        paragraphContent += "\n"
                    paragraphContent += f"\n{chapter}:{verse} {scripture}"
                paragraphEnd = bcv
                paragraphEndB = book
                paragraphEndC = chapter
                paragraphEndV = verse

            # save the last paragraph
            metadata = {
                "title": paragraphTitle,
                "start": paragraphStart,
                "book_start": paragraphStartB,
                "chapter_start": paragraphStartC,
                "verse_start": paragraphStartV,
                "end": paragraphEnd,
                "book_end": paragraphEndB,
                "chapter_end": paragraphEndC,
                "verse_end": paragraphEndV,
            }
            id = str(uuid.uuid4())
            collectionParagraph.add(
                documents = [paragraphContent],
                metadatas = [metadata],
                ids = [id]
            )

        return None
