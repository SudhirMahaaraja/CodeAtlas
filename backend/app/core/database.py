import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: MongoClient = None
    db = None
    use_fallback: bool = False
    _fallback_store: dict = {}

    @classmethod
    def connect(cls):
        """Initialize MongoDB client connection with fallback mechanisms."""
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URI}...")
            # Set a low timeout so it fails fast if not running locally
            cls.client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
            # Force connection check
            cls.client.admin.command('ping')
            cls.db = cls.client[settings.DATABASE_NAME]
            cls.use_fallback = False
            logger.info("Successfully connected to MongoDB!")
        except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
            logger.warning(f"MongoDB connection failed: {e}. Falling back to in-memory store.")
            cls.use_fallback = True
            cls._fallback_store = {}

    @classmethod
    def get_collection(cls, name: str):
        """Returns the collection or a mock fallback wrapper."""
        if cls.use_fallback:
            return FallbackCollection(cls._fallback_store, name)
        return cls.db[name]

class FallbackCollection:
    """Mock PyMongo collection using a simple in-memory dict."""
    def __init__(self, store: dict, name: str):
        self.store = store
        self.name = name
        if name not in self.store:
            self.store[name] = {}

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            import uuid
            doc["_id"] = str(uuid.uuid4())
        key = str(doc["_id"])
        # Store a copy
        self.store[self.name][key] = dict(doc)
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return InsertResult(key)

    def find_one(self, query: dict):
        # Handle simple query by _id
        if "_id" in query:
            return self.store[self.name].get(str(query["_id"]))
        for doc in self.store[self.name].values():
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                return doc
        return None

    def update_one(self, query: dict, update: dict):
        # Handle simple $set operations
        doc = self.find_one(query)
        if doc and "$set" in update:
            doc.update(update["$set"])
            self.store[self.name][str(doc["_id"])] = doc
        class UpdateResult:
            def __init__(self):
                self.modified_count = 1
        return UpdateResult()
