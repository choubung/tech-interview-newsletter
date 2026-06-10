import os
import json
import smtplib
import time
import sys 
import subprocess 
from email.mime.text import MIMEText          # 💡 누락되었던 MIME 임포트 주입
from email.mime.multipart import MIMEMultipart  # 💡 누락되었던 MIME 임포트 주입
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
    """Gemini API를 사용하여 뉴스레터를 생성합니다. (503 에러 대비 3회 지수 백오프 재시도 적용)"""
    prompt = f"""
당신은 백엔드 개발자 채용을 담당하는 기술 면접관이자 아키텍트입니다.
제공된 원본 마크다운 기술 콘텐츠를 바탕으로, 모바일(스마트폰) 메일 앱 화면에서도 가독성이 절대 깨지지 않는 노션 스타일의 뉴스레터를 작성해주세요.

[🎯 출력 형식 규격 - 최우선 필수 사항]
- 반드시 이메일 본문에 바로 삽입 가능한 순수 HTML 태그 형태로만 응답해주세요.
- ⚠️ 절대 답변 앞뒤에 마크다운 코드 블록 기호(```html 이나 ```)를 붙이지 마십시오. 첫 글자는 HTML 태그여야 합니다.
- ⚠️ 전체를 감싸는 큰 <div> 태그는 생성하지 마십시오.

[🎨 모바일 최적화 인라인 스타일 및 구조 규칙]
1. 💡 전구 이모티콘 및 제목 넘버링 통제 (+ 하단 구분선 필수):
   - 오직 '기술 개념 핵심 대제목(<h2> 태그)'에만 맨 앞에 '💡 ' 전구 이모티콘을 붙이고, 숫자는 절대 붙이지 마십시오. (예: <h2>💡 배열의 메모리 특성</h2>)
   - ⚠️ [중요] 대제목과 대제목 본문 사이의 명확한 경계를 위해, 모든 <h2> 태그가 끝나면 곧바로 하단에 은은한 점선 구분선인 `<hr>` 태그를 무조건 한 줄 삽입해 주세요. 이외의 공간에는 구분선을 쓰지 않습니다.
     (구조 예시: <h2>💡 대제목</h2><hr><p>대제목 본문 시작...</p>)
   - 대제목 하위의 '일반 세부 소제목(<h3> 태그)'에는 이모티콘과 하단 구분선을 절대 빼고, 대신 반드시 '1)', '2)' 형식의 숫자를 붙여주세요. (예: <h3>1) 배열 크기 계산의 이해</h3>)
2. 볼드(Bold) 제한: <strong> 태그는 문장 전체가 아닌, 오직 핵심적인 기술 개념 '키워드(단어)' 단독으로만 적용해야 합니다.
3. 🔷 파란색 하이라이트 (개념 정의):
   - 기술 키워드에 대한 본질적 정의 문장(단 한 문장)은 반드시 다음 태그를 정확히 사용하여 감싸주세요 (글자색 검정 차콜 유지, 굵기 보통 설정): 
     <span style="background-color: #e3f2fd; padding: 2px 4px; border-radius: 3px; font-weight: normal; color: #37352f;">정의문</span>
4. 🔶 노란색 하이라이트 (핵심 특징):
   - 실무 관점의 핵심 트레이드오프나 중요 성능 특징(15자 내외)은 반드시 다음 태그를 정확히 사용하여 감싸주세요 (글자색 검정 차콜 유지, 굵기 보통 설정): 
     <span style="background-color: #fffde7; padding: 2px 4px; border-radius: 3px; font-weight: normal; color: #37352f;">핵심특징</span>
5. 💻 실무 소스 코드 전용 상자 (필요한 경우에만 제한적 적용):
   - ⚠️ 원본 내용에 구체적인 소스 코드 예시(자바, C++ 등)가 포함되어 있고, 이를 보여주는 것이 개념 이해에 '필수적'이라고 판단될 때만 이 상자를 사용하십시오. 뻔한 설명문은 절대 코드 블록으로 만들지 마십시오.
   - 메일 앱에서 디자인이 절대 깨지지 않도록 반드시 아래 구조의 인라인 스타일 래퍼로 감싸서 출력하십시오. (마크다운 기호 ``` 사용 절대 금지)
   - 구조: <pre style="background-color: #f7f6f3; padding: 12px; border-radius: 6px; border-left: 4px solid #dfdfde; margin: 12px 0; overflow-x: auto; white-space: pre;"><code style="font-family: 'SFMono-Regular', Consolas, monospace; font-size: 12.5px; color: #37352f; line-height: 1.5;">코드 내용</code></pre>
6. 🧮 점화식 및 수학적 관계 증명 상자 (맥락적 제한 적용):
   - 원본 기술 내용 중 알고리즘의 시간 복잡도 유도 과정, 수학적 점화식, 또는 메모리 주소 계산 공식처럼 '텍스트로 그냥 나열하면 모바일 화면에서 줄바꿈이 깨져 가독성이 망가질 수 있는 수식 연산 내용'이 있을 때만 단독 줄로 이 박스를 생성하십시오.
   - ⚠️ 단순 복잡도 표기(예: O(1), O(N))는 일반 문장 안에 <strong>O(1)</strong> 형태로 담백하게 녹여내고, 이 전용 박스는 오직 '공식과 관계식'에만 적용해야 합니다. (마크다운 수식 기호 $ 사용 절대 금지)
   - 구조: <div style="background-color: rgba(135,131,120,0.08); padding: 8px 12px; border-radius: 4px; font-family: monospace; font-size: 13px; color: #eb5757; margin: 8px 0; font-weight: 600; white-space: nowrap; overflow-x: auto;">T(n) = T(n-1) + O(1) 등 공식 내용</div>
7. ➖ 들여쓰기 한도 제한:
   - 본문 나열 시 `<ul>` 내부의 `<ul>` 중첩은 딱 2단계(하위 1단계)까지만 허용합니다. 그 이상 들여쓰지 마십시오.

[✍️ 기술 면접 섹션 작성 규격 - 모바일 특화]
- 본문이 끝나면 곧바로 <h2> 태그로 "📡 기술 면접 대비 예상 질문 & 모범 답안" 섹션을 열어주세요. (⚠️ 이 제목은 전구 금지이며, 바로 아래에 똑같이 <hr> 구분선을 한 줄 넣어준 뒤 Q&A 내용을 시작해야 합니다.)
- ⚠️ 들여쓰기로 인한 모바일 가독성 저하를 막기 위해, 이 섹션에서는 <ul>과 <li> 태그, 그리고 대시(-) 기호를 절대 사용하지 마십시오.
- 대신, 아래와 같이 정갈한 패딩 블록 구조를 활용해 질문과 답안의 레이아웃 위계를 확실하게 찢어주세요.
- 구조 규칙:
  <div style="margin-bottom: 20px; padding: 4px 0;">
      <div style="font-weight: bold; color: #111111; margin-bottom: 6px;">Q. 질문 내용이 여기에 들어갑니다.</div>
      <div style="color: #555555; padding-left: 4px;">A. 모범 답안 기술 내용이 여기에 단정하게 배치됩니다.</div>
  </div>

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
                wait_time = 5 * (2 ** attempt)  
                print(f"⚠️ 구글 서버 부하 발생(503). {attempt + 1}번째 실패. {wait_time}초 대기 후 재시도...")
                time.sleep(wait_time)
                continue
            else:
                raise e

def send_email_to_user(receiver, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver
    msg['Subject'] = subject

    # 💡 마크다운 링크 찌꺼기가 제거된 클린 푸터 프레임
    notion_advanced_template = f"""
    <div style="font-size: 14.5px; line-height: 1.8; color: #37352f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px 12px;">
        <style>
            h2 {{ 
                font-size: 18.5px; 
                color: #1a365d; 
                margin-top: 28px; 
                margin-bottom: 12px; 
                border-bottom: 1px solid #e1e4e6; 
                padding-bottom: 6px; 
                font-weight: 600; 
            }}
            h3 {{ 
                font-size: 15.5px; 
                color: #2c5282; 
                margin-top: 22px; 
                margin-bottom: 8px; 
                font-weight: 600; 
            }}
            p {{ margin-top: 0; margin-bottom: 10px; text-align: justify; }}
            blockquote {{ margin: 16px 0; padding: 10px 14px; background-color: #f1f3f5; border-left: 3px solid #4a5568; color: #4a5568; font-size: 14px; }}
            ul {{ margin-top: 0; margin-bottom: 10px; padding-left: 14px; list-style-type: none; }}
            li {{ margin-bottom: 5px; position: relative; }}
            li::before {{ content: "–"; position: absolute; left: -12px; color: #37352f; }}
            ul ul {{ margin-top: 4px; margin-bottom: 4px; padding-left: 14px; }}
            strong {{ color: #111111; font-weight: 600; }}
        </style>
        {body}
        
        <div style="margin-top: 40px; padding-top: 16px; border-top: 1px solid #e1e4e6; font-size: 11.5px; color: #868685; text-align: center;">
            본 콘텐츠는 <a href="[https://github.com/gyoogle/tech-interview-for-developer](https://github.com/gyoogle/tech-interview-for-developer)" target="_blank" style="color: #2c5282; text-decoration: none; font-weight: 500;">tech-interview-for-developer</a> 오픈소스 레포지토리를 기반으로 큐레이션되었습니다.
        </div>
    </div>
    """

    msg.attach(MIMEText(notion_advanced_template, 'html', 'utf-8'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
    server.sendmail(SENDER_EMAIL, receiver, msg.as_string())
    server.quit()

def commit_and_push_progress():
    """GitHub Actions 환경에서 변경된 progress.json을 내 레포에 커밋 및 푸시합니다."""
    if GITHUB_TOKEN and GITHUB_REPOSITORY:
        print("▶ GitHub 저장소에 진도 파일 업데이트 중...")
        
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        
        os.system('git config --global user.name "github-actions[bot]"')
        os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
        
        os.system('git add progress.json')
        os.system('git commit -m "CHORE: Update daily newsletter progress" || true')
        
        remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
        
        # 💡 [핵심 수정 1] 당겨올 브랜치 이름을 master에서 main으로 변경
        print("▶ 원격 저장소 최신 상태 동기화(Pull) 중...")
        subprocess.run(['git', 'pull', '--rebase', remote_url, 'main'], capture_output=True)
        
        # 💡 [핵심 수정 2] 밀어넣을 타겟 브랜치를 HEAD:master에서 HEAD:main으로 변경
        result = subprocess.run(
            ['git', 'push', remote_url, 'HEAD:main'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️ [경고] Git Push에 실패했습니다.")
            print("================ [상세 에러 로그] ================")
            print(result.stderr)
            print("==================================================")
        else:
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

        # 💡 [테스트용 임시 코드] 제미나이 대신 고정된 텍스트를 강제로 꽂아 넣습니다.
        # newsletter_body = "<h2>🌊 깃허브 Push 및 이메일 발송 테스트 완료!</h2><p>이 메일이 무사히 도착하고, 깃허브 레포지토리의 progress.json 숫자가 2로 올라갔다면 모든 백엔드 파이프라인이 완벽하게 뚫린 것입니다.</p>"

        email_subject = f"[🌊 오늘의 CS 토픽] {topic_title}"

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
        sys.exit(1)

if __name__ == "__main__":
    main()
