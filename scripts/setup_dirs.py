import os

paths = [
    "backend/app/__init__.py",
    "backend/app/api/__init__.py",
    "backend/app/agents/__init__.py",
    "backend/app/agents/base/__init__.py",
    "backend/app/agents/fraud/__init__.py",
    "backend/app/agents/recovery/__init__.py",
    "backend/app/agents/growth/__init__.py",
    "backend/app/shield/__init__.py",
    "backend/app/tools/__init__.py",
    "backend/app/tools/fraud/__init__.py",
    "backend/app/tools/recovery/__init__.py",
    "backend/app/tools/growth/__init__.py",
    "backend/app/ml/__init__.py",
    "backend/app/ml/training/__init__.py",
    "backend/app/ml/inference/__init__.py",
    "backend/app/ml/features/__init__.py",
    "backend/app/rag/__init__.py",
    "backend/app/rag/ingestion/__init__.py",
    "backend/app/rag/retrieval/__init__.py",
    "backend/app/rag/embeddings/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/services/__init__.py",
    "backend/app/database/__init__.py",
    "backend/app/core/__init__.py",
    "backend/tests/__init__.py",
]

for p in paths:
    full_path = os.path.join("d:\\Projects\\AgentShield", p)
    dir_name = os.path.dirname(full_path)
    os.makedirs(dir_name, exist_ok=True)
    with open(full_path, "w") as f:
        f.write("# Package initialization\n")

print("Backend directories and init files created successfully.")
