import streamlit as st
import json
import uuid
import os
import requests
import boto3

# === SECRETS FROM STREAMLIT ===
AZURE_TTS_URL = st.secrets["azure"]["AZURE_TTS_URL"]
AZURE_API_KEY = st.secrets["azure"]["AZURE_API_KEY"]

AWS_ACCESS_KEY = st.secrets["aws"]["AWS_ACCESS_KEY"]
AWS_SECRET_KEY = st.secrets["aws"]["AWS_SECRET_KEY"]
AWS_REGION = st.secrets["aws"]["AWS_REGION"]
AWS_BUCKET = st.secrets["aws"]["AWS_BUCKET"]
S3_PREFIX = st.secrets["aws"]["S3_PREFIX"]
CDN_BASE = st.secrets["aws"]["CDN_BASE"]

# === AVAILABLE VOICES ===
voice_options = {
    "1": "alloy",
    "2": "echo",
    "3": "fable",
    "4": "onyx",
    "5": "nova",
    "6": "shimmer"
}

# === STREAMLIT UI ===
st.title("🎙️ GPT-4o Text-to-Speech to S3")
uploaded_file = st.file_uploader("Upload JSON file", type=["json"])
voice_label = st.selectbox("Choose Voice", list(voice_options.values()))

# === TTS + UPLOAD ===
def synthesize_and_upload(paragraphs, voice):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name=AWS_REGION,
    )

    result = {}
    os.makedirs("temp", exist_ok=True)

    index = 2  # Start from slide2, s2paragraph1, audio_url2
    for text in paragraphs.values():
        st.write(f"🛠️ Processing: slide{index}")

        response = requests.post(
            AZURE_TTS_URL,
            headers={
                "Content-Type": "application/json",
                "api-key": AZURE_API_KEY
            },
            json={
                "model": "tts-1-hd",
                "input": text,
                "voice": voice
            }
        )
        response.raise_for_status()

        filename = f"tts_{uuid.uuid4().hex}.mp3"
        local_path = os.path.join("temp", filename)

        with open(local_path, "wb") as f:
            f.write(response.content)

        s3_key = f"{S3_PREFIX}{filename}"
        s3.upload_file(local_path, AWS_BUCKET, s3_key)
        cdn_url = f"{CDN_BASE}{s3_key}"

        # Build result dict
        slide_key = f"slide{index}"
        paragraph_key = f"s{index}paragraph1"
        audio_key = f"audio_url{index}"

        result[slide_key] = {
            paragraph_key: text,
            audio_key: cdn_url,
            "voice": voice
        }

        index += 1
        os.remove(local_path)

    return result

# === MAIN EXECUTION ===
if uploaded_file and voice_label:
    paragraphs = json.load(uploaded_file)
    st.success(f"✅ Loaded {len(paragraphs)} paragraphs")

    if st.button("🚀 Generate TTS + Upload to S3"):
        with st.spinner("Please wait..."):
            output = synthesize_and_upload(paragraphs, voice_label)

            st.success("✅ Done uploading to S3!")
            st.download_button(
                label="⬇️ Download Output JSON",
                data=json.dumps(output, indent=2, ensure_ascii=False),
                file_name="Output_data.json",
                mime="application/json"
            )
