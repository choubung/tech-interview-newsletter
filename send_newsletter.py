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
제공된 원본 마크다운 기술 콘텐츠를 바탕으로, 노션(Notion) 워크스페이스처럼 정갈하고 압도적인 시각적 가독성을 가진 뉴스레터 본문을 작성해주세요.

[🎯 출력 형식 규격 - 최우선 필수 사항]
- 반드시 이메일 본문에 바로 삽입 가능한 순수 HTML 태그 형태로만 응답해주세요.
- ⚠️ 절대 답변 앞뒤에 마크다운 코드 블록 기호(```html 이나 ```)를 붙이지 마십시오.
- ⚠️ 전체를 감싸는 큰 <div> 태그는 절대 생성하지 마십시오.

[🎨 노션 스타일에 맞춘 텍스트 태그 규칙]
1. 💡 전구 이모티콘 및 제목 통제: 
   - 오직 본문의 '기술 개념 핵심 대제목(<h2> 태그)'에만 맨 앞에 '💡 ' 전구 이모티콘을 붙여주세요.
   - ⚠️ 대제목(<h2>)에는 '1.', '2.'와 같은 숫자를 절대 붙이지 마십시오. 오직 전구와 텍스트만 존재해야 합니다. (예: <h2>💡 배열의 메모리 특성</h2>)
   - ⚠️ 반대로, 대제목 아래의 '일반 세부 소제목(<h3> 태그)'에는 절대 이모티콘을 붙이지 말고, 대신 반드시 '1)', '2)'와 같은 형식으로 숫자를 붙여 정렬해 주세요. (예: <h3>1) 배열 회전 알고리즘</h3>)
2. 볼드(Bold) 제한: <strong> 태그는 문장 전체가 아닌, 오직 핵심적인 기술 개념 '키워드(단어)' 단독으로만 적용해야 합니다.
3. 🔷 파란색 하이라이트 (개념 정의): 기술 키워드에 대한 '본질적인 정의'에만 사용해야 하며, 문장 구조가 반드시 "[개념]은(는) ~이다" 또는 "~를 의미한다" 형태로 딱 떨어지는 '단 한 문장'에만 <span class="hl-blue">...</span> 태그를 씌워주세요. (문단당 최대 1개)
4. 🔶 노란색 하이라이트 (핵심 특징): 백엔드 실무 아키텍처 관점에서 '성능의 핵심적 트레이드오프(Trade-off)'나 치명적인 효율성/한계를 다루는 핵심 구절(15자 내외)에만 <span class="hl-yellow">...</span> 태그를 지정해주세요.
5. 💻 가독성을 위한 코드 블록 처리:
   - 본문에 소스 코드가 포함될 경우, 반드시 `<pre><code>코드내용</code></pre>` 태그로 감싸주세요. 절대로 마크다운 기호(```)를 본문에 날것으로 노출해서는 안 됩니다.
6. 🧮 점화식 및 수식 표기 기호 금지:
   - ⚠️ 마크다운 수식 기호인 $ 기호(예: $O(N)$)는 이메일에서 완전히 깨집니다. 절대 사용하지 마십시오.
   - 모든 시간 복잡도나 알고리즘 점화식은 일반 텍스트 포맷을 활용해 깔끔하게 풀어써주세요. (예: T(n) = T(n-1) + O(1) 또는 O(N log N))

[✍️ 컨텐츠 작성 가이드라인]
1. 제목: 주간지 감성을 살려 묵직하고 매력적인 헤드라인을 뽑아 <h2> 태그로 감싸주세요. (전구 이모티콘 포함, 넘버링 금지)
2. 서론 (인삿말/자아 표출 금지): 불필요한 수식어 없이 곧바로 오늘 다룰 키워드가 백엔드 환경에서 왜 중요한지 담백하고 묵직하게 <p> 태그로 시작해주세요.
3. 본문 심화 해설: 원본 마크다운의 알맹이를 흐리지 않게 풍부하게 보완하되, 위의 규칙들을 정확히 녹여서 작성해주세요. 특징을 나열할 때는 <ul>과 <li>를 적극 활용하세요.
4. 기술 면접 대비 예상 질문 & 모범 답안: 
   - 본문이 끝나면 구분선 없이 곧바로 <h2> 태그를 사용하여 "📡 기술 면접 대비 예상 질문 & 모범 답안" 섹션을 열어주세요. (⚠️ 전구 이모티콘 금지)
   - 질문과 답안은 반드시 하나의 세트처럼 <ul>과 <li> 구조로 묶여야 합니다. 
   - ⚠️ 특히 예상 질문(Q)뿐만 아니라 모범 답안(A)이 시작되는 문장 앞에도 누락 없이 정갈하게 대시(-) 기호 형태가 들어가도록 <li> 구조를 엄격하게 맞춰주세요.

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
    
    # 💡 노션 스타일 코드 블록 및 푸터가 추가된 최종 고정 CSS 템플릿
    notion_advanced_template = f"""
    <div style="font-size: 14.5px; line-height: 1.8; color: #37352f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', 'Malgun Gothic', sans-serif; max-width: 600px; margin: 0 auto; padding: 24px 16px;">
        <style>
            /* 대제목: 노션 H1 감성, 하단 은은한 경계선 고정 */
            h2 {{ 
                font-size: 19px; 
                color: #1a365d; 
                margin-top: 32px; 
                margin-bottom: 12px; 
                border-bottom: 1px solid #e1e4e6; 
                padding-bottom: 6px; 
                font-weight: 600; 
            }}
            /* 소제목 */
            h3 {{ 
                font-size: 16px; 
                color: #2c5282; 
                margin-top: 24px; 
                margin-bottom: 8px; 
                font-weight: 600; 
            }}
            p {{ margin-top: 0; margin-bottom: 12px; text-align: justify; }}
            blockquote {{ margin: 16px 0; padding: 10px 14px; background-color: #f1f3f5; border-left: 3px solid #4a5568; color: #4a5568; }}
            
            /* 본문 가독성을 위한 대시 리스트 스타일 */
            ul {{ margin-top: 0; margin-bottom: 12px; padding-left: 16px; list-style-type: none; }}
            li {{ margin-bottom: 6px; position: relative; }}
            li::before {{ content: "–"; position: absolute; left: -14px; color: #37352f; }}
            
            strong {{ color: #111111; font-weight: 600; }}
            hr {{ border: 0; border-top: 1px dashed #e1e4e6; margin: 28px 0; }}

            /* 🎨 노션 스타일 실시간 형광펜 하이라이트 속성 */
            .hl-blue {{ background-color: #e3f2fd; padding: 2px 4px; border-radius: 3px; color: #0d47a1; }}
            .hl-yellow {{ background-color: #fffde7; padding: 2px 4px; border-radius: 3px; color: #f57f17; }}

            /* 💻 노션 감성 프리미엄 코드 블록 스타일 */
            pre {{
                background-color: #f7f6f3;
                padding: 14px;
                border-radius: 6px;
                border-left: 4px solid #dfdfde;
                overflow-x: auto;
                margin: 16px 0;
            }}
            code {{
                font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
                font-size: 13px;
                color: #eb5757; /* 인라인 코드용 색상 */
                background-color: rgba(135,131,120,0.15);
                padding: 2px 4.5px;
                border-radius: 3px;
            }}
            pre code {{
                color: #37352f; /* 코드 블록 내부 텍스트 색상 복구 */
                background-color: transparent;
                padding: 0;
                border-radius: 0;
            }}

            /* 📑 푸터 스타일 */
            .newsletter-footer {{
                margin-top: 48px;
                padding-top: 16px;
                border-top: 1px solid #e1e4e6;
                font-size: 12px;
                color: #868685;
                text-align: center;
            }}
            .newsletter-footer a {{
                color: #2c5282;
                text-decoration: none;
                font-weight: 500;
            }}
            .newsletter-footer a:hover {{ text-decoration: underline; }}
        </style>
        {body}
        
        <div class="newsletter-footer">
            본 콘텐츠는 <a href="[https://github.com/gyoogle/tech-interview-for-developer](https://github.com/gyoogle/tech-interview-for-developer)" target="_blank">tech-interview-for-developer</a> 오픈소스 레포지토리를 기반으로 큐레이션되었습니다.
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
        
        # 1. 깃허브 액션즈가 터미널 인터랙티브(입력 대기) 모드로 빠지는 것을 원천 차단하는 환경 변수 설정
        os.environ["GIT_TERMINAL_PROMPT"] = "0"
        
        # 2. 유저 정보 세팅
        os.system('git config --global user.name "github-actions[bot]"')
        os.system('git config --global user.email "github-actions[bot]@users.noreply.github.com"')
        
        # 3. 변경사항 스테이징 및 커밋
        os.system('git add progress.json')
        # 변경사항이 없을 때 에러로 터지는 것을 방지하기 위해 || true 추가
        os.system('git commit -m "CHORE: Update daily newsletter progress" || true')
        
        # 4. 토큰을 이용한 원격 저장소 URL 구성 (안전한 push 규칙 적용)
        remote_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{GITHUB_REPOSITORY}.git"
        
        # 만약 인증이 실패하면 무한 대기하지 않고 즉시 0이 아닌 에러 코드를 뱉고 Fail-fast 하도록 설정
        result = os.system(f'git push {remote_url} HEAD:master')
        
        if result != 0:
            print("⚠️ [경고] Git Push에 실패했습니다. GitHub Actions Workflow의 Write 권한 설정을 확인하세요.")
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
