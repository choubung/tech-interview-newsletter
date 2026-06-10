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
당신은 백엔드 개발자 채용을 담당하는 기술 면접관이자 아키텍트입니다.
제공된 원본 마크다운 기술 콘텐츠를 바탕으로, 깊이 있고 전문성이 돋보이는 고품질 뉴스레터 본문을 작성해주세요.

[🎯 출력 형식 규격 - 최우선 필수 사항]
- 반드시 이메일 본문에 바로 삽입 가능한 순수 HTML 태그 형태로만 응답해주세요.
- ⚠️ 절대 답변 앞뒤에 마크다운 코드 블록 기호(```html 이나 ```)를 붙이지 마십시오. 첫 글자는 HTML 태그로 시작해야 합니다.
- ⚠️ 전체를 감싸는 큰 <div> 태그는 절대 생성하지 마십시오. 디자인 프레임은 외부에서 자동으로 주입될 것입니다.
- ⚠️ 태그 내부에 style="..." 같은 인라인 속성은 절대로 넣지 말고, 온전히 순수한 구조 태그(<h2>, <h3>, <p>, <blockquote>, <ul>, <li>, <strong>)로만 문장 구조를 잡아주세요.

[✍️ 컨텐츠 작성 가이드라인]
1. 제목: 뉴스레터 주간지 감성을 살려 가장 묵직하고 매력적인 헤드라인을 뽑아 <h2> 태그로 감싸주세요.
2. 서론 (인삿말/자아 표출 금지): 
   - "안녕하세요", "멘토입니다", "구독자 여러분" 같은 피상적인 인사말이나 수식어는 절대 사용하지 마십시오.
   - AI 특유의 응원 메시지나 마무리 감성 문구도 전면 배제해 주세요.
   - 글의 시작은 곧바로 <p> 태그를 사용하여, 오늘 다룰 키워드가 하드웨어(CPU 캐시 지역성, 메모리 구조) 관점이나 백엔드 실무 아키텍처 환경에서 왜 치명적으로 중요한지 기술적 본질과 묵직한 인사이트를 던지며 시작해주세요.
3. 본문 심화 해설: 
   - 원본 마크다운의 핵심 원리를 흐려지지 않게 풍부하게 보완하여 <p>와 <h3> 태그를 교차 사용해 설명해주세요.
   - 문단 중에서 가장 핵심이 되는 요약 명제나 강조할 핵심 관점은 딱 한 번 <blockquote> 태그를 사용해 격리해주세요.
   - 중요 기술 키워드는 <strong> 태그를 활용해주세요.
4. 기술 면접 대비 예상 질문 & 모범 답안: 
   - 문단 하단에 <hr> 태그를 넣어 구분선을 한 줄 치고, <h2> 태그로 "📡 기술 면접 대비 예상 질문 & 모범 답안" 섹션을 열어주세요.
   - <ul>과 <li> 태그를 활용하되, 각 질문은 <li><strong>Q. 질문 내용</strong><br>A. 모범 답안 내용</li> 구조로 묶어서 가독성을 극대화해주세요.

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
            if "503" in str(e) and attempt < max_retries - 1:
                print(f"⚠️ 구글 서버 부하 발생(503). {attempt + 1}번째 재시도 중... (5초 대기)")
                time.sleep(5)
                continue
            else:
                raise e

def send_email_to_user(receiver, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver
    msg['Subject'] = subject
    
    # 💡 노션(Notion) 감성의 깔끔하고 세련된 고정 CSS 템플릿 프레임
    notion_style_template = f"""
    <div style="font-size: 14.5px; line-height: 1.8; color: #37352f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px 16px;">
        <style>
            h2 {{ font-size: 20px; color: #1a365d; margin-top: 32px; margin-bottom: 12px; border-bottom: 1px solid #e1e4e6; padding-bottom: 6px; font-weight: 600; }}
            h3 {{ font-size: 16.5px; color: #2c5282; margin-top: 24px; margin-bottom: 8px; font-weight: 600; }}
            p {{ margin-top: 0; margin-bottom: 12px; text-align: justify; }}
            blockquote {{ margin: 16px 0; padding: 10px 14px; background-color: #f1f3f5; border-left: 3px solid #4a5568; color: #4a5568; font-style: normal; }}
            ul {{ margin-top: 0; margin-bottom: 12px; padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            strong {{ color: #111111; font-weight: 600; }}
            hr {{ border: 0; border-top: 1px dashed #e1e4e6; margin: 28px 0; }}
        </style>
        {body}
    </div>
    """
    
    msg.attach(MIMEText(notion_style_template, 'html', 'utf-8'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
    server.sendmail(SENDER_EMAIL, receiver, msg.as_string())
    server.quit()

# 💡 [복구 완료] 이전 리팩토링 단계에서 누락되었던 깃허브 커밋/푸시 함수를 다시 채워 넣었습니다.
def commit_and_push_progress():
    """GitHub Actions 환경에서 변경된 progress.json을 내 레포에 커밋 및 푸시합니다."""
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
