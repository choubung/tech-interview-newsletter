import json
import requests
import sys
import time
from urllib.parse import quote

CURRICULUM_FILE = "curriculum.json"
REPO_BASE_URL = "https://raw.githubusercontent.com/gyoogle/tech-interview-for-developer/master/"

def load_curriculum():
    try:
        with open(CURRICULUM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ {CURRICULUM_FILE} 파일을 찾을 수 없습니다.")
        sys.exit(1)

def main():
    curriculum = load_curriculum()
    print(f"🔍 총 {len(curriculum)}개의 커리큘럼 경로 검증을 시작합니다...\n")

    failed_paths = []

    for i, item in enumerate(curriculum):
        title = item.get("title", "Unknown Title")
        path = item.get("path", "")
        
        # URL 인코딩 (띄어쓰기 등 처리)
        encoded_path = quote(path)
        url = f"{REPO_BASE_URL}{encoded_path}"

        try:
            # 💡 파일의 존재 여부만 빠르게 확인하기 위해 GET 요청을 보냅니다.
            # raw.githubusercontent 특성상 70여 개 연속 요청은 무리 없이 통과됩니다.
            response = requests.get(url)

            if response.status_code == 200:
                print(f"✅ [{i+1}/{len(curriculum)}] 정상: {title}")
            else:
                print(f"❌ [{i+1}/{len(curriculum)}] 에러({response.status_code}): {title}")
                print(f"   -> 끊어진 링크: {path}")
                failed_paths.append((title, path, response.status_code))
                
        except requests.RequestException as e:
            print(f"⚠️ [{i+1}/{len(curriculum)}] 네트워크 통신 에러: {title} ({e})")
            failed_paths.append((title, path, "Network Error"))
            
        # 깃허브 API 봇 차단을 방지하기 위한 미세 딜레이
        time.sleep(0.1)

    print("\n==================================================")
    if not failed_paths:
        print("🎉 모든 커리큘럼 경로가 정상입니다! (404 에러 없음)")
        sys.exit(0) # 💡 성공 코드 (0): 깃허브 액션즈 초록불
    else:
        print(f"🚨 치명적 경고: {len(failed_paths)}개의 경로가 유효하지 않습니다.")
        print("원본 레포지토리의 파일명이 변경되었는지 확인하고 curriculum.json을 수정하세요!\n")
        for title, path, err in failed_paths:
            print(f" - [{err}] {title}\n   (경로: {path})")
        print("==================================================")
        
        # 💡 실패 코드 (1): 깃허브 액션즈 빨간불 & 소유자에게 에러 메일 자동 발송 트리거
        sys.exit(1) 

if __name__ == "__main__":
    main()
