import sys
import os
import traceback
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.copilot import vector_store

async def main():
    print("Initializing vector store...")
    try:
        vector_store.initialize_store()
        print("Vector store initialized successfully.")
        print(f"use_fallback: {vector_store.use_fallback}")
        print(f"documents: {len(vector_store.documents)}")
    except Exception as e:
        print("Error during initialize_store:")
        traceback.print_exc()
        return

    print("\nPerforming similarity search for 'cpu'...")
    try:
        results = vector_store.similarity_search("cpu")
        print(f"Search results: {results}")
    except Exception as e:
        print("Error during similarity_search:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
