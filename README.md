# Meeting Minutes Generator

A standalone AWS CDK sample that turns meeting transcripts into structured minutes using Amazon Bedrock, API Gateway, Lambda, and S3.

This public copy contains only generic prompts and placeholder configuration.

## Architecture

- API Gateway REST API
- Lambda minutes handler
- Amazon Bedrock model invocation
- S3 bucket for generated minutes
- Optional static HTML client in `frontend/index.html`

## Deploy

```bash
npm install
npm run build
npx cdk deploy
```

## API

`POST /minutes`

```json
{
  "title": "Weekly planning",
  "transcript": "Alice: ... Bob: ...",
  "style": "summary"
}
```

`GET /minutes/{id}` returns a generated minutes document saved in S3.

