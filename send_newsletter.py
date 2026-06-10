import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
# 💡 최신 공식 라이브러리 규격으로 import 변경
from google import genai

# ==========================================
# 1. 환경 변수 및 설정 로드
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

# 여러 수신자 이메일 파싱
RECEIVER_EMAILS_STR = os.environ.get("RECEIVER_EMAILS", "")
RECEIVER_EMAILS = [email.strip() for email in RECEIVER_EMAILS_STR.split(",") if email.strip()]

if not RECEIVER_EMAILS:
    RECEIVER_EMAILS = ["doubuhanmo16@gmail.com"]

SENDER_EMAIL = "doubuhanmo16@gmail.com"

# 💡 최신 google-genai 규격에 맞게 클라이언트 초기화
client = genai.Client(api_key=GEMINI_API_KEY)

PROGRESS_FILE = "progress.json"
CURRICULUM_FILE = "curriculum.json"

# ==========================================
# 2. 핵심 비즈니스 로직 함수
# ==========================================

def load_json_file(filename, default_value):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_value

def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_github_raw_content(repo_path):
    raw_url = f"https://raw.githubusercontent.com/gyoogle/tech-interview-for-developer/master/{repo_path}"
    response = requests.get(raw_url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"GitHub 파일을 읽어오는데 실패했습니다. URL: {raw_url} (Status: {response.status_code})")

def generate_newsletter_with_gemini(title, content):
    """최신 google-genai 라이브러리를 사용하여 뉴스레터를 생성합니다."""
    prompt = f"""
너는 백엔드 개발자 채용을 담당하는 기술 면접관이자, 친절한 멘토야.
취업 준비생이 등굣길이나 출근길에 15분 동안 몰입해서 읽기 좋은 풍부하고 깊이 있는 기술 뉴스레터를 작성해줘.

[요구사항]
1. 제목: 주간/일간 뉴스레터 감성을 살려 매력적인 기술 제목으로 뽑아줘.
2. 서론: 오늘 다룰 키워드와 이 지식이 백엔드 개발(특히 Java/Spring 생태계나 서버 아키텍처)에서 왜 중요한지 가볍게 환기하며 시작해줘.
3. 본문 요약 및 심화 해설: 제공된 마크다운 내용을 기반으로 하되, 단순히 요약만 하지 말고 자바 백엔드 개발자 관점에서 반드시 알아야 하는 실무 맥락이나 원리를 친절하게 보완해서 풍부하게 설명해줘. (텍스트 양이 15분 읽기에 적당하도록 상세하게 작성)
4. 기술 면접 대비 예상 질문 & 모범 답안: 
   - 해당 주제와 관련해 실제 백엔드 면접에서 단골로 나오는 '날카로운 면접 질문 2개'를 뽑아줘.
   - 각 질문에 대해 구조적이고 명쾌한 '모범 답안(10초 두괄식 요약 + 꼬리 질문 대비 상세 설명)'을 작성해줘.

[원본 마크다운 제목]: {title}
[원본 마크다운 내용]:
{content}
"""
    # 💡 최신 패키지에서 표준으로 사용하는 공식 모델명 'gemini-2.5-flash'를 사용합니다.
    # 추론 능력과 처리 속도가 대폭 개선된 최신 기본 모델입니다.
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

def send_email_to_user(receiver, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
    server.sendmail(SENDER_EMAIL, receiver, msg.as_string())
    server.quit()

def commit_and_push_progress():
    if GITHUB_TOKEN and GITHUB_REPOSITORY:
        print("▶ GitHub 저장소에 진도 파일 업데이트 중...")
        os.system('git config --global user.name "github-actions[bot]"')
        os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
        os.system('git add progress.json')
        os.system('git commit -m "CHORE: Update daily newsletter progress"')
        
        remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
        os.system(f'git push {remote_url} HEAD:master')
        print("▶ [성공] 진도 상태 Git Push 완료!")

# ==========================================
# 3. 메인 가동 프로세스
# ==========================================
def main():
    # 이 부분을 아래와 같이 정확하게 고쳐주세요!
    curriculum = load_json_file(CURRICULUM_FILE, [])
    progress = load_json_file(PROGRESS_FILE, {"current_index": 0})
    current_idx = progress["current_index"]
