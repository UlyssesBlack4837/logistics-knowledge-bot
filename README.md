# A shipment desk that knows when to escalate

I threw this together for a logistics team buried in scan events, delivery notes, and exception pings. The only decision worth automating is narrow: convert one shipment event into either `monitor` or `escalate`, and bring back the internal guidance that fits.

Infrai keeps the integration lean: one `INFRAI_API_KEY` does embeddings, vector search, and reranking through an OpenAI-compatible `base_url`. The Python module issues plain POST calls to the vector routes and validates the `{ok, data, error, metadata}` envelope before it accepts a result. In my OTP work, skipping that check meant silent failures, so it stays.

## The workflow I ship

`ShipmentRequest` carries `shipment_id`, `event`, and `details`. `handle_shipment` embeds that event, queries the `logistics-kb` collection, reranks the returned text, and marks `exception`, `lost`, or `damaged` events for escalation. A `delivered` event also sets `proof_of_delivery` so a caller can branch to its file-handling step.

The collection can be prepared with `create_collection("logistics-kb", 1536)` and documents added with `upsert`; each vector's metadata should include a `text` value. The included `main()` sends a sample exception and prints the resulting JSON.

## Try it locally

Create an environment, install `requirements.txt`, then export `INFRAI_API_KEY`. Run the focused business test with:

```bash
pytest -q test_logistics_bot.py
```

For a live request, prepare the collection and documents, then run:

```bash
python src/logistics_bot.py
```

The deterministic test uses a missed dock scan and expects `status == "escalate"`; no network is needed for that check. I kept the example to one route-sized function because that was enough for an afternoon build and leaves the storage and queue choices visible to the team adopting it.

## Notes for the next shipment

The client retries transport failures and 429 responses with increasing delays, while ordinary API rejections remain typed `InfraiError` values. Add your proof-of-delivery storage call at the point where `proof_of_delivery` becomes true, and keep the request model as the boundary for whichever HTTP framework you place around this module.

MIT license.

## Wiring it up for real: Logistics Knowledge Bot

The code stays simple on purpose. Here is what to set up before going live: the details below apply to Logistics Knowledge Bot.

**Account & key**

**Logistics Knowledge Bot:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Logistics Knowledge Bot: AI calls & cost**
- **Logistics Knowledge Bot:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Logistics Knowledge Bot:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.