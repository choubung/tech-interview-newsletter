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
# GitHub Secrets 및 환경 변수에서 비밀키 로드
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
# 내 레포에 진도를 업데이트할 때 쓸 토큰 (GitHub Actions 기본 토큰 또는 내 PAT 사용)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY") # 예: "유저명/레포명"

# 이메일 수신자 설정 (본인 Gmail 주소 입력)
RECEIVER_EMAIL = "doubuhanmo16@gmail.com" 
SENDER_EMAIL = "doubuhanmo16@gmail.com"

# Gemini API 설정
genai.configure(api_key=GEMINI_API_KEY)

PROGRESS_FILE = "progress.json"
CURRICULUM_FILE = "curriculum.json"

# ==========================================
# 2. 핵심 비즈니스 로직 함수
# ==========================================

def load_json_file(filename, default_value):
    """파일이 존재하면 읽고, 없으면 기본값을 반환합니다."""
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_value

def save_json_file(filename, data):
    """데이터를 JSON 파일로 로컬에 저장합니다."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_github_raw_content(repo_path):
    """Gyoogle 레포지토리에서 마크다운 원본 텍스트를 가져옵니다."""
    # Public 레포이므로 토큰 없이 Raw URL로 직접 접근 가능합니다.
    raw_url = f"https://raw.githubusercontent.com/gyoogle/tech-interview-for-developer/master/{repo_path}"
    response = requests.get(raw_url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"GitHub 파일을 읽어오는데 실패했습니다. URL: {raw_url} (Status: {response.status_code})")

def generate_newsletter_with_gemini(title, content):
    """Gemini API를 사용하여 취준생 맞춤형 기술 뉴스레터를 생성합니다."""
    # 소요 시간인 15분에 알맞게 풍부한 해설과 면접 최적화 프롬프트 작성
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
    # 뉴스레터의 풍부한 분량과 추론 성능을 위해 1.5 Pro 모델 사용 권장
    model = genai.GenerativeModel('gemini-1.5-pro')
    response = model.generate_content(prompt)
    return response.text

def send_email(subject, body):
    """Gmail SMTP를 사용하여 나에게 메일을 발송합니다."""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject

    # 마크다운 텍스트를 메일 본문에 붙여넣음 (HTML로 변환하여 보내면 더 예쁘지만 우선 기본 텍스트로 안정적 발송)
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        # Gmail SMTP 서버 연결 (587 포트, TLS 보안)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("▶ [성공] 뉴스레터 이메일 발송 완료!")
    except Exception as e:
        raise Exception(f"이메일 발송 중 오류가 발생했습니다: {str(e)}")

def commit_and_push_progress():
    """GitHub Actions 환경에서 변경된 progress.json을 내 레포에 커밋 및 푸시합니다."""
    # 로컬 테스트 환경이 아니라 GitHub Actions 자동화 환경일 때만 실행
    if GITHUB_TOKEN and GITHUB_REPOSITORY:
        print("▶ GitHub 저장소에 진도 파일 업데이트 중...")
        os.system('git config --global user.name "github-actions[bot]"')
        os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
        os.system('git add progress.json')
        os.system('git commit -m "CHORE: Update daily newsletter progress"')
        
        # 권한이 부여된 토큰을 이용해 원격 저장소에 푸시
        remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
        os.system(f'git push {remote_url} HEAD:master')
        print("▶ [성공] 진도 상태 Git Push 완료!")

# ==========================================
# 3. 메인 가동 프로세스
# ==========================================
def main():
    # 커리큘럼과 현재 진도 상태 가져오기
    curriculum = load_json_file(CURRICULUM_FILE, [])
    progress = load_json_file(PROGRESS_FILE, {"current_index": 0})
    
    current_idx = progress["current_index"]
    
    # 모든 커리큘럼을 다 읽었을 경우 종료
    if current_idx >= len(curriculum):
        print("🎉 축하합니다! 모든 커리큘럼 뉴스레터 발송이 완료되었습니다.")
        return

    # 오늘의 타겟 주제 선정
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
        
        # 3. 이메일 발송
        email_subject = f"[Dev-Digest] 오늘 자 백엔드 기술 배달: {topic_title}"
        send_email(email_subject, newsletter_body)
        
        # 4. 진도 한 칸 전진 및 저장
        progress["current_index"] = current_idx + 1
        save_json_file(PROGRESS_FILE, progress)
        
        # 5. GitHub 레포지토리에 동기화 변경 사항 반영
        commit_and_push_progress()
        
    except Exception as e:
        print(f"❌ [에러 발생] 프로세스가 중단되었습니다: {e}")

if __name__ == "__main__":
    main()
