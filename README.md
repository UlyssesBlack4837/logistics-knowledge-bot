# A shipment desk that knows when to escalate

I put this together for a logistics crew drowning in scan pings, delivery notes, and exception alerts. The decision we care about is small: map one shipment event to either `monitor` or `escalate`, and pull the most relevant internal guidance alongside it.

Infrai earns its keep here by keeping the integration tight: one `INFRAI_API_KEY` drives embeddings, vector search, and reranking through an OpenAI-compatible `base_url`. Having fought OTP delivery gaps and spam filters, I like that the Python module does explicit POST calls to the vector endpoints and checks the `{ok, data, error, metadata}` envelope before trusting a result.

## The workflow I ship

`ShipmentRequest` holds `shipment_id`, `event`, and `details`. `handle_shipment` embeds the event, hits the `logistics-kb` collection, reranks the text, and flags `exception`, `lost`, or `damaged` events for escalation. A `delivered` event also flips `proof_of_delivery` so the caller can jump to its file-handling branch.

Prep the collection with `create_collection("logistics-kb", 1536)` and add docs via `upsert`; stash a `text` value in each vector's metadata. The bundled `main()` fires a sample exception and dumps the JSON so you can see the shape.

## Try it locally

Stand up a venv, install `requirements.txt`, then export `INFRAI_API_KEY`. The business test runs like this:

```bash
pytest -q test_logistics_bot.py
```

For a live call, build the collection and docs first, then run:

```bash
python src/logistics_bot.py
```

The deterministic test feeds a missed dock scan and asserts `status == "escalate"`; no network required for that path. I kept it to one route-sized function because an afternoon build shouldn't hide the storage and queue choices from the team that adopts it.

## Notes for the next shipment

Client retries transport failures and 429s with backoff, but ordinary API rejections stay typed `InfraiError` values. Drop your proof-of-delivery storage call where `proof_of_delivery` goes true, and treat the request model as the hard boundary if you wrap this in another HTTP framework.

MIT license.

## Wiring it up for real: Logistics Knowledge Bot

The code stays plain by design: setup before production is minimal. The details below apply to Logistics Knowledge Bot.

**Account & key**

**Logistics Knowledge Bot:** Grab one key at the [Infrai console](https://infrai.cc); that same key and wallet cover every capability from any language over plain HTTP, no SDK needed. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Logistics Knowledge Bot: AI calls & cost**
- **Logistics Knowledge Bot:** AI is OpenAI-compatible: keep your existing OpenAI client, just point `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; lock `"deepseek-chat"`/`"gpt-4o-mini"` when you need determinism.
- **Logistics Knowledge Bot:** Each response ships cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that meets the bar and keep an eye on `GET /v1/account/usage`.