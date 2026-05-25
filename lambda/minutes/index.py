import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict

import boto3


REGION = os.environ.get("AWS_REGION", "us-east-1")
MINUTES_BUCKET = os.environ["MINUTES_BUCKET"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
ALLOWED_ORIGINS = json.loads(os.environ.get("ALLOWED_ORIGINS", '["*"]'))

s3_client = boto3.client("s3", region_name=REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=REGION)


PROMPTS = {
    "summary": "Create concise, structured meeting minutes.",
    "detailed": "Create detailed meeting minutes with decisions, constraints, owners, and follow-up items.",
    "executive": "Create an executive summary focused on decisions, impact, and required action.",
}


def cors_headers(origin: str = "") -> Dict[str, str]:
    allow_origin = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": allow_origin,
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
    }


def response(status_code: int, body: Dict[str, Any], origin: str = "") -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": cors_headers(origin),
        "body": json.dumps(body, ensure_ascii=False),
    }


def generate_minutes(title: str, transcript: str, style: str) -> str:
    instruction = PROMPTS.get(style, PROMPTS["summary"])
    prompt = f"""
{instruction}

Use this Markdown format:

# {title}

## Summary
## Decisions
## Action Items
## Open Questions

Transcript:
{transcript[:120000]}
"""
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2500,
        "messages": [{"role": "user", "content": prompt}],
    }
    result = bedrock_runtime.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(request_body),
    )
    payload = json.loads(result["body"].read())
    return "".join(block.get("text", "") for block in payload.get("content", [])).strip()


def save_minutes(minutes_id: str, payload: Dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=MINUTES_BUCKET,
        Key=f"minutes/{minutes_id}.json",
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
        ServerSideEncryption="AES256",
    )


def get_minutes(minutes_id: str) -> Dict[str, Any]:
    result = s3_client.get_object(Bucket=MINUTES_BUCKET, Key=f"minutes/{minutes_id}.json")
    return json.loads(result["Body"].read().decode("utf-8"))


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    origin = event.get("headers", {}).get("origin") or event.get("headers", {}).get("Origin", "")

    if event.get("httpMethod") == "OPTIONS":
        return response(200, {}, origin)

    try:
        if event.get("httpMethod") == "GET":
          minutes_id = event.get("pathParameters", {}).get("id")
          if not minutes_id:
              return response(400, {"error": "id is required"}, origin)
          return response(200, get_minutes(minutes_id), origin)

        body = json.loads(event.get("body") or "{}")
        title = str(body.get("title") or "Meeting Minutes").strip()
        transcript = str(body.get("transcript") or "").strip()
        style = str(body.get("style") or "summary").strip()
        if not transcript:
            return response(400, {"error": "transcript is required"}, origin)

        minutes_id = str(uuid.uuid4())
        minutes = generate_minutes(title, transcript, style)
        payload = {
            "id": minutes_id,
            "title": title,
            "style": style,
            "minutes": minutes,
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }
        save_minutes(minutes_id, payload)
        return response(200, payload, origin)
    except Exception as exc:
        return response(500, {"error": "minutes request failed", "detail": str(exc)}, origin)
