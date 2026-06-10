import os
import json
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from google import genai

# ==========================================
# 1. 환경 변수 및 설정 로드
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

# 수신자 이메일 파싱
RECEIVER_EMAILS_STR = os.environ.get("RECEIVER_EMAILS", "")
RECEIVER_EMAILS = [email.strip() for email in RECEIVER_EMAILS_STR.split(",") if email.strip()]

if not RECEIVER_EMAILS:
    RECEIVER_EMAILS = ["doubuhanmo16@gmail.com"]

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "doubuhanmo16@gmail.com")

# 구글 제미나이 클라이언트 초기화
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
        raise Exception(f"GitHub 파일을 읽어오는데 실패했습니다. URL: {raw_url}")

def generate_newsletter_with_gemini(title, content):
    """Gemini API를 사용하여 뉴스레터를 생성합니다. (503 에러 대비 3회 재시도 포함)"""
    prompt = f"""
너는 백엔드 개발자 채용을 담당하는 기술 면접관이자, 친절한 멘토야.
취업 준비생이 읽기 좋은 풍부하고 깊이 있는 기술 뉴스레터를 작성해줘.

[🎯 출력 형식 규격 - 필수]
- 반드시 이메일 본문에 바로 삽입 가능한 순수 HTML 태그 형태로만 응답해줘.
- ⚠️ 절대 답변 앞뒤에 마크다운 코드 블록 기호(```html 이나 ```)를 붙이지 마. 
- 스타일을 넣고 싶다면 각 태그 내부에 inline style(예: style="color: #2b2b2b;")을 활용해줘.

[요구사항]
1. 제목: 주간/일간 뉴스레터 감성을 살려 <h2> 태그로 매력적인 기술 제목을 뽑아줘.
2. 서론: 오늘 다룰 키워드와 백엔드 개발에서의 중요성을 <p> 태그로 작성해줘.
3. 본문 요약 및 심화 해설: 원리를 친절하게 보완해서 풍부하게 설명하되, 중요 키워드는 <strong> 태그를 쓰고, 강조할 문장은 블록 인용구(<blockquote>) 태그를 써줘.
4. 기술 면접 대비 예상 질문 & 모범 답안: <ul>과 <li> 태그를 활용해 구조적이고 명쾌하게 정리해줘.

[원본 마크다운 제목]: {title}
[원본 마크다운 내용]:
{content}
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            # 503 에러가 감지되었고, 아직 재시도 횟수가 남았다면 5초 대기 후 루프 재개
            if "503" in str(e) and attempt < max_retries - 1:
                print(f"⚠️ 구글 서버 부하 발생(503). {attempt + 1}번째 재시도 중... (5초 대기)")
                time.sleep(5)
                continue
            else:
                # 3번 다 실패했거나 다른 치명적인 에러라면 예외를 밖으로 던짐
                raise e

def send_email_to_user(receiver, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'html', 'utf-8'))

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
    curriculum = load_json_file(CURRICULUM_FILE, [])
    progress = load_json_file(PROGRESS_FILE, {"current_index": 0})
    current_idx = progress["current_index"]
    
    if current_idx >= len(curriculum):
        print("🎉 모든 커리큘럼 뉴스레터 발송이 완료되었습니다.")
        return

    target_item = curriculum[current_idx]
    topic_title = target_item["title"]
    repo_path = target_item["path"]
    
    print(f"📰 오늘의 주제 [{current_idx + 1}/{len(curriculum)}]: {topic_title}")
    
    try:
        raw_content = fetch_github_raw_content(repo_path)
        
        print("🤖 Gemini가 뉴스레터를 작성하고 있습니다...")
        newsletter_body = generate_newsletter_with_gemini(topic_title, raw_content)
        
        email_subject = f"[Dev-Digest] 오늘 자 백엔드 기술 배달: {topic_title}"
        print(f"📬 총 {len(RECEIVER_EMAILS)}명의 구독자에게 발송을 시작합니다...")
        
        for email in RECEIVER_EMAILS:
            try:
                send_email_to_user(email, email_subject, newsletter_body)
                print(f"   ✅ 발송 성공: {email}")
            except Exception as mail_err:
                print(f"   ❌ 발송 실패: {email} (사유: {mail_err})")
        
        progress["current_index"] = current_idx + 1
        save_json_file(PROGRESS_FILE, progress)
        commit_and_push_progress()
        
    except Exception as e:
        print(f"❌ [에러 발생] 프로세스가 중단되었습니다: {e}")

if __name__ == "__main__":
    main()
