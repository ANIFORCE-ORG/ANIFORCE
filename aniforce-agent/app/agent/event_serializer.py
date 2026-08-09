"""Serialize Agents SDK events and usage into stable Runtime payloads."""


def to_jsonable(value, depth: int = 0):
    if depth > 6:
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item, depth + 1) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return to_jsonable(value.model_dump(mode="json"), depth + 1)
    if hasattr(value, "dict"):
        return to_jsonable(value.dict(), depth + 1)
    if hasattr(value, "__dict__"):
        public_fields = {key: item for key, item in vars(value).items() if not key.startswith("_")}
        return to_jsonable(public_fields, depth + 1)
    return str(value)


def serialize_sdk_event(sdk_event) -> dict:
    payload = {
        "type": getattr(sdk_event, "type", "unknown"),
        "class": type(sdk_event).__name__,
    }
    for field in ("name", "data", "item"):
        value = getattr(sdk_event, field, None)
        if value is not None:
            payload[field] = to_jsonable(value) if field != "name" else value
    new_agent = getattr(sdk_event, "new_agent", None)
    if new_agent is not None:
        payload["new_agent"] = {"name": getattr(new_agent, "name", None)}
    return payload


def extract_usage(result) -> dict:
    context_wrapper = getattr(result, "context_wrapper", None)
    usage = getattr(context_wrapper, "usage", None)
    if not usage:
        return {}
    input_details = getattr(usage, "input_tokens_details", None)
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    output_tokens = getattr(usage, "output_tokens", 0) or 0
    return {
        "input": input_tokens,
        "output": output_tokens,
        "cacheRead": getattr(input_details, "cached_tokens", 0) or 0,
        "cacheWrite": 0,
        "totalTokens": getattr(usage, "total_tokens", 0) or (input_tokens + output_tokens),
    }
