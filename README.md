# Serverless DeepSeek R1 Inference (FastAPI + Lambda SnapStart)

Deploy a fully serverless, low-latency LLM inference API for **DeepSeek R1 Distill** (or other GGUF models) using **AWS Lambda**, **SnapStart**, **FastAPI**, and **llama-cpp-python**.

---

## 🚀 Features

* 🔌 **OpenAI-compatible** `/chat/completions` FastAPI endpoint
* ⚡ **SnapStart-enabled Lambda** for \~1–2s cold starts
* 🔁 **Streaming responses** via Server-Sent Events
* ⬇️ Model pulled from **S3 using memfd** (fast in-memory loading)
* 🔐 Optional IAM-based authentication (SigV4)

---

## 🧱 Architecture

* FastAPI app deployed as AWS Lambda Function URL
* Custom Lambda Layer with `llama-cpp-python`
* S3 bucket stores `.gguf` model
* Lambda Web Adapter streams responses

---

## 📦 Prerequisites

* AWS SAM CLI
* Python 3.12 & Docker
* AWS account + `s3:GetObject` & `lambda:InvokeFunctionUrl` permissions
* Model (e.g. `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf`)

---

## ☁️ Deployment

**1. Upload Model**

```bash
wget https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf
aws s3 mb s3://YOUR_BUCKET
aws s3 cp DeepSeek-R1*.gguf s3://YOUR_BUCKET/
```

**2. Build + Deploy**

```bash
sam build
sam deploy --guided
```

Configure:

* `MODEL_BUCKET`
* `MODEL_KEY`

---

## 💬 Client Usage

```bash
pip install requests python-dotenv boto3
echo "CHAT_API_BASE=https://xxxx.lambda-url.region.on.aws" > .env

python client.py                # interactive CLI
python client.py --temperature 0.7 --max-tokens 512
```

Shortcuts:
`/new` new conversation `/quit` exit

---

## 🛠 Local Development

```bash
python -m venv .venv
source .venv/bin/activate
cd app && pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 🧽 Cleanup

```bash
sam delete
```