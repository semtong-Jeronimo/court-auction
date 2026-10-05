import httpx
from bs4 import BeautifulSoup
from typing import Optional

BASE_URL = "https://www.courtauction.go.kr"

def register_auction_tools(mcp):
    """FastMCP 인스턴스에 대한민국 법원 법원경매 도구들을 등록하는 함수"""

    @mcp.tool()
    async def search_court_auction_items(
        keyword: str,
        court_name: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        대한민국 법원경매정보(courtauction.go.kr)에서 진행 중인 경매 물건을 검색합니다.
        
        Args:
            keyword: 검색어 (아파트명, 동/리 단위 지역명, 도로명 등 - 예: '반포', '자이', '역삼동')
            court_name: 특정 관할법원 (선택 사항, 예: '서울중앙지방법원', '수원지방법원')
            limit: 가져올 최대 물건 수 (기본 5건)
        """
        # 법원경매 기본 헤더 설정 (User-Agent 필수)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{BASE_URL}/pgi/index.do",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        search_url = f"{BASE_URL}/pgi/search/searchMaster.do"
        params = {
            "searchWord": keyword,
        }

        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, headers=headers) as client:
            try:
                # 1. 메인 세션 쿠키 획득 (초기 방문)
                await client.get(f"{BASE_URL}/pgi/index.do")

                # 2. 물건 검색 요청
                response = await client.get(search_url, params=params)
                if response.status_code != 200:
                    return f"법원경매 사이트 접속 실패 (HTTP {response.status_code})"

                # 3. HTML 파싱 (검색 결과 테이블 정제)
                soup = BeautifulSoup(response.text, "html.parser")
                rows = soup.select("table.Ltbl_list tbody tr")

                if not rows or "검색결과가 없습니다" in soup.text:
                    return f"'{keyword}'에 대한 법원경매 진행 물건 검색 결과가 없습니다."

                results = [f"=== 법원경매 물건 검색 결과 ('{keyword}', 상위 {limit}건) ===\n"]
                count = 0

                for tr in rows:
                    cols = tr.find_all("td")
                    if len(cols) < 5:
                        continue

                    # 사건번호 및 담당법원
                    case_info = cols[1].get_text(separator=" ", strip=True)
                    # 용도 및 소재지
                    usage_addr = cols[2].get_text(separator=" ", strip=True)
                    # 감정평가액 / 최저매각가격
                    price_info = cols[3].get_text(separator=" ", strip=True)
                    # 매각기일 및 진행상태
                    status_info = cols[4].get_text(separator=" ", strip=True)

                    results.append(
                        f"[{count + 1}] 사건/법원: {case_info}\n"
                        f" - 소재지/용도: {usage_addr}\n"
                        f" - 감정가/최저가: {price_info}\n"
                        f" - 매각기일/상태: {status_info}\n"
                    )
                    count += 1
                    if count >= limit:
                        break

                if count == 0:
                    return f"'{keyword}' 관련 상세 목록을 파싱하지 못했습니다. 검색어를 더 구체적인 동/단지명으로 시도해 보세요."

                return "\n".join(results)

            except Exception as e:
                return f"법원경매 조회 중 오류 발생: {str(e)}"