from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()  # GEMINI_API_KEY 환경변수를 읽어요
resp = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="안녕이라고 한 줄로 답해줘",
)
print(resp.text)