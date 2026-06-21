try:
    import langchain
    print("[OK] langchain imported!")
except Exception as e:
    print(f"[FAIL] langchain import failed: {e}")

try:
    import google.generativeai
    print("[OK] google.generativeai imported!")
except Exception as e:
    print(f"[FAIL] google.generativeai import failed: {e}")

try:
    import chromadb
    print("[OK] chromadb imported!")
except Exception as e:
    print(f"[FAIL] chromadb import failed: {e}")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    print("[OK] sklearn imported!")
except Exception as e:
    print(f"[FAIL] sklearn import failed: {e}")
