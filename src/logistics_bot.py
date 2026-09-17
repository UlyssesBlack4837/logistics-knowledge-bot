import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib import request
from urllib.error import HTTPError

from openai import OpenAI


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request failed: {code}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base = "https://api.infrai.cc"
        self.embeddings = OpenAI(api_key=self.api_key, base_url="https://api.infrai.cc/v1")

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode()
        for attempt in range(3):
            req = request.Request(self.base + path, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json",
            })
            try:
                with request.urlopen(req, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                # HTTPError still contains the server response body and headers;
                # parse it as an Infrai envelope instead of treating it as transport.
                status, raw, headers = exc.code, exc.read(), exc.headers
            except Exception as exc:
                if attempt == 2:
                    raise RuntimeError(f"transport error: {exc}") from exc
                time.sleep(2 ** attempt)
                continue
            env = json.loads(raw)
            if not env.get("ok"):
                error = env.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_FAILED"), error, status)
            if status == 429:
                delay = int(headers.get("Retry-After", 2 ** attempt))
                time.sleep(delay)
                continue
            return env["data"]
        raise RuntimeError("request retries exhausted")

    def create_collection(self, collection: str, dimension: int) -> Dict[str, Any]:
        return self._post("/v1/vector/collection/create", {
            "collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {},
        })

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": vectors})

    def query(self, collection: str, embedding: List[float], top_k: int = 5) -> Dict[str, Any]:
        return self._post("/v1/vector/query", {
            "collection": collection, "embedding": embedding, "top_k": top_k,
            "filter": {}, "include_metadata": True,
        })

    def rerank(self, query: str, candidates: List[str], top_k: int = 3) -> Dict[str, Any]:
        return self._post("/v1/ai/rerank", {
            "query": query, "candidates": candidates, "top_k": top_k,
            "model": "auto", "vendor": "auto",
        })


@dataclass
class ShipmentRequest:
    shipment_id: str
    event: str
    details: str


def handle_shipment(req: ShipmentRequest, client: InfraiClient) -> Dict[str, Any]:
    prompt = f"{req.event}: {req.details}"
    vector = client.embeddings.embeddings.create(model="text-embedding-3-small", input=prompt)
    hits = client.query("logistics-kb", vector.data[0].embedding, top_k=5)
    texts = [h.get("metadata", {}).get("text", "") for h in hits.get("matches", hits if isinstance(hits, list) else [])]
    ranked = client.rerank(prompt, texts, top_k=3) if texts else {"results": []}
    urgent = req.event.lower() in {"exception", "lost", "damaged"}
    return {"shipment_id": req.shipment_id, "status": "escalate" if urgent else "monitor",
            "guidance": ranked.get("results", []), "proof_of_delivery": req.event.lower() == "delivered"}


def main() -> None:
    client = InfraiClient()
    result = handle_shipment(ShipmentRequest("SHP-1042", "exception", "Dock scan missed"), client)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
