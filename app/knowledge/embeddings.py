import httpx
from app.config.settings import settings

async def embed_texts(texts: list[str]) -> list[list[float]]:
    provider=settings.EMBEDDING_PROVIDER.lower().strip(); model=settings.EMBEDDING_MODEL.strip()
    if not provider or not model: raise RuntimeError("Embedding provider/model is not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        if provider == "openai":
            if not settings.OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY is required")
            r=await client.post("https://api.openai.com/v1/embeddings",headers={"Authorization":f"Bearer {settings.OPENAI_API_KEY}"},json={"model":model,"input":texts}); r.raise_for_status()
            vectors=[x["embedding"] for x in r.json()["data"]]
        elif provider == "ollama":
            r=await client.post(settings.OLLAMA_URL.rstrip("/")+"/api/embed",json={"model":model,"input":texts}); r.raise_for_status()
            vectors=r.json().get("embeddings",[])
        else: raise ValueError("EMBEDDING_PROVIDER must be openai or ollama")
    dim=len(vectors[0]) if vectors else 0
    if settings.EMBEDDING_DIMENSION and dim != int(settings.EMBEDDING_DIMENSION): raise ValueError(f"Embedding dimension mismatch: configured {settings.EMBEDDING_DIMENSION}, received {dim}")
    if any(len(v)!=dim for v in vectors): raise ValueError("Embedding provider returned inconsistent vector dimensions")
    return vectors
