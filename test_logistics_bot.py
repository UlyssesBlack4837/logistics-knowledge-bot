from src.logistics_bot import ShipmentRequest, handle_shipment


class FakeEmbeddings:
    class embeddings:
        @staticmethod
        def create(model, input):
            return type("R", (), {"data": [type("D", (), {"embedding": [0.1, 0.2]})()]})()


class FakeClient:
    embeddings = FakeEmbeddings()

    def query(self, collection, embedding, top_k):
        return {"matches": [{"metadata": {"text": "Escalate missing scans"}}]}

    def rerank(self, query, candidates, top_k):
        return {"results": candidates[:top_k]}


def test_exception_is_escalated():
    result = handle_shipment(ShipmentRequest("S1", "exception", "Missed dock scan"), FakeClient())
    assert result["status"] == "escalate"
    assert result["proof_of_delivery"] is False
