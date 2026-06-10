import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import google.generativeai as genai

# ==========================================
# 1. 환경 변수 및 설정 로드
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")

# 💡 [리팩토링] 여러 수신자 이메일을 환경 변수에서 안전하게 파싱합니다.
# Secrets에 RECEIVER_EMAILS 이름으로 "메일1, 메일2" 형태로 등록하시면 됩니다.
RECEIVER_EMAILS_STR = os.environ.get("RECEIVER_EMAILS", "")
RECEIVER_EMAILS = [email.strip() for email in RECEIVER_EMAILS_STR.split(",") if email.strip()]

# 수신자 목록이 비어있을 때를 대비한 Fallback (기본 하드코딩값 유지)
if not RECEIVER_EMAILS:
    RECEIVER_EMAILS = ["doubuhanmo16@gmail.com"]

SENDER_EMAIL = "doubuhanmo16@gmail.com"

# Gemini API 초기화
genai.configure(api_key=GEMINI_API_KEY)

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
    """Gemini API를 사용하여 취준생 맞춤형 기술 뉴스레터를 생성합니다."""
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
    # 💡 [핵심 수정] 2026년 기준 가장 안정적이고 확실한 범용 프리 티어 모델코드로 변경합니다.
    # 대량 문맥 요약과 텍스트 생성에 최적화된 최신 가속화 엔진 명칭입니다.
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    response = model.generate_content(prompt)
    return response.text

def send_email_to_user(receiver, subject, body):
    """단일 수신자에게 메일을 발송합니다."""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Gmail SMTP 서버 연결
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
        print("🎉 축하합니다! 모든 커리큘럼 뉴스레터 발송이 완료되었습니다.")
        return

    target_item = curriculum[current_idx]
    topic_title = target_item["title"]
    repo_path = target_item["path"]
    
    print(f"📰 오늘의 주제 [{current_idx + 1}/{len(curriculum)}]: {topic_title}")
    
    try:
        # 1. 깃허브에서 원본 마크다운 다운로드
        raw_content = fetch_github_raw_content(repo_path)
        
        # 2. 제미나이를 통한 맞춤형 큐레이션 본문 생성
        print("🤖 Gemini가 뉴스레터를 작성하고 있습니다...")
        newsletter_body = generate_newsletter_with_gemini(topic_title, raw_content)
        
        # 3. 이메일 순차 발송 (하나가 실패해도 대포알이 멈추지 않도록 안전 루프 처리)
        email_subject = f"[Dev-Digest] 오늘 자 백엔드 기술 배달: {topic_title}"
        print(f"📬 총 {len(RECEIVER_EMAILS)}명의 구독자에게 발송을 시작합니다...")
        
        for email in RECEIVER_EMAILS:
            try:
                send_email_to_user(email, email_subject, newsletter_body)
                print(f"   ✅ 발송 성공: {email}")
            except Exception as mail_err:
                print(f"   ❌ 발송 실패: {email} (사유: {mail_err})")
        
        # 4. 진도 한 칸 전진 및 저장
        progress["current_index"] = current_idx + 1
        save_json_file(PROGRESS_FILE, progress)
        
        # 5. GitHub 레포지토리에 동기화 변경 사항 반영
        commit_and_push_progress()
        
    except Exception as e:
        print(f"❌ [에러 발생] 프로세스가 중단되었습니다: {e}")

if __name__ == "__main__":
    main()
