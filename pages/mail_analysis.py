# pages/mail_analysis.py - 피싱 메일 분석 페이지

import streamlit as st
import email
from email.header import decode_header
import re
import hashlib
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup
import plotly.graph_objects as go
import requests

# 페이지 설정
st.set_page_config(
    page_title="메일 분석 - 피싱 제로",
    page_icon="📧",
    layout="wide"
)

# API 서버 주소
API_BASE_URL = "http://127.0.0.1:8000"

# OpenCV 라이브러리 가용성 확인 (QR 코드 스캔용)
OPENCV_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    pass

# ----------------------------------------------------------------------
# 1. 분석에 필요한 상수 및 헬퍼 함수
# ----------------------------------------------------------------------

# 파일 시그니처 맵 (매직 넘버)
FILE_SIGNATURES = {
    'application/pdf': '25504446',          # %PDF
    'application/zip': '504b0304',          # PK.. (ZIP, DOCX, XLSX, PPTX 등)
    'application/x-msdownload': '4d5a',      # MZ (EXE, DLL)
    'application/x-ole-storage': 'd0cf11e0a1b11ae1', # OLE (구 버전 DOC, XLS, PPT, MSI 등)
    'application/rtf': '7b5c727466',      # {\rtf
    'application/vnd.rar': '526172211a07',  # Rar!
    'application/x-7z-compressed': '377abcaf271c', # 7z
    'image/jpeg': 'ffd8ffe0',
    'image/png': '89504e47',
    'image/gif': '47494638',
}

# 사회 공학적 피싱 키워드
SOCIAL_ENGINEERING_KEYWORDS = [
    '긴급', '경고', '계정', '잠금', '보안', '업데이트', '인증', '확인', '비밀번호',
    '만료', '로그인', '클릭', '즉시', '은행', '결제', '송장', '법적', '조치'
]

def decode_subject(header):
    """디코딩된 이메일 제목을 반환하는 헬퍼 함수"""
    if header is None:
        return ""
    decoded_parts = decode_header(header)
    subject = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            try:
                subject.append(part.decode(charset or 'utf-8', errors='ignore'))
            except (UnicodeDecodeError, LookupError):
                subject.append(part.decode('cp949', errors='ignore'))
        else:
            subject.append(part)
    return ''.join(subject)

def get_email_address(header_value):
    """헤더 값에서 이메일 주소만 추출하는 헬퍼 함수"""
    if header_value is None:
        return None
    match = re.search(r'<([^>]+)>', header_value)
    return match.group(1) if match else header_value

@st.cache_data(ttl=3600) # 1시간 동안 도메인 정보 캐시
def get_domain_info_from_api(domain_name):
    """FastAPI 서버로부터 도메인 Whois 정보를 가져옵니다."""
    if not domain_name:
        return None
    try:
        response = requests.get(f"{API_BASE_URL}/domain_info/{domain_name}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        # API 호출 실패 시 None 반환 (분석 중단을 막기 위함)
        return None

@st.cache_data(ttl=3600)
def get_vt_report_from_api(endpoint, resource):
    """FastAPI 서버로부터 VirusTotal 리포트를 가져옵니다."""
    if not resource: return None
    try:
        response = requests.get(f"{API_BASE_URL}/report/{endpoint}/{resource}", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 503:
            st.session_state.vt_key_missing = True
        return None

# ----------------------------------------------------------------------
# 2. 핵심 분석 로직
# ----------------------------------------------------------------------

def analyze_headers(msg, results):
    """이메일 헤더를 분석합니다."""
    # 기본 정보 추출
    from_addr = decode_subject(msg.get("From"))
    to_addr = decode_subject(msg.get("To"))
    subject = decode_subject(msg.get("Subject"))
    results['header'].append({'item': '발신자 (From)', 'value': from_addr, 'status': 'info'})
    results['header'].append({'item': '수신자 (To)', 'value': to_addr, 'status': 'info'})
    results['header'].append({'item': '제목 (Subject)', 'value': subject, 'status': 'info'})
    results['header'].append({'item': '메일 클라이언트 (X-Mailer)', 'value': msg.get("X-Mailer", "N/A"), 'status': 'info'})

    # From/Return-Path 불일치
    from_email = get_email_address(from_addr)
    return_path = get_email_address(msg.get("Return-Path"))
    if from_email and return_path and from_email != return_path:
        results['header'].append({'item': 'From/Return-Path 불일치', 'value': '발신자 주소와 반송 주소가 다릅니다.', 'status': 'warn'})
        results['riskScores']['header'] += 15

    # From/Reply-To 불일치
    reply_to = get_email_address(msg.get("Reply-To"))
    if from_email and reply_to and from_email != reply_to:
        results['header'].append({'item': 'From/Reply-To 불일치', 'value': '발신자 주소와 회신 주소가 다릅니다.', 'status': 'warn'})
        results['riskScores']['header'] += 15

    # Received 헤더 분석
    received_headers = msg.get_all("Received", [])
    if len(received_headers) > 5:
        results['header'].append({'item': '메일 서버 경로', 'value': f'경유 서버가 {len(received_headers)}개로 많습니다.', 'status': 'warn'})
        results['riskScores']['header'] += 10
    
    ip_regex = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    path_ips = [ip for h in received_headers for ip in re.findall(ip_regex, h)]
    if path_ips:
        results['header'].append({'item': '경유 IP 주소', 'value': ' → '.join(path_ips), 'status': 'info'})

    # 인증 결과 분석
    auth_results = msg.get("Authentication-Results", "")
    for auth_type in ['spf', 'dkim', 'dmarc']:
        match = re.search(rf'{auth_type}=(\w+)', auth_results)
        if match:
            status = match.group(1).lower()
            if status != 'pass':
                results['header'].append({'item': f'{auth_type.upper()} 인증', 'value': f'실패 ({status})', 'status': 'danger'})
                results['riskScores']['header'] += 20
            else:
                results['header'].append({'item': f'{auth_type.upper()} 인증', 'value': '성공 (pass)', 'status': 'safe'})
        else:
            results['header'].append({'item': f'{auth_type.upper()} 인증', 'value': '결과 없음', 'status': 'info'})

def analyze_html_body(html_content, results):
    """HTML 본문을 분석합니다."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # 사회 공학적 키워드 분석
    text_content = soup.get_text(separator=' ').lower()
    found_keywords = [kw for kw in SOCIAL_ENGINEERING_KEYWORDS if kw in text_content]
    if len(found_keywords) > 2:
        results['body'].append({'item': '사회 공학 키워드', 'value': f'의심 키워드 발견: {", ".join(found_keywords[:3])}...', 'status': 'warn'})
        results['riskScores']['body'] += 15

    # 링크 분석
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if text and href != text and text.replace(" ", "") not in href:
            results['body'].append({'item': '링크/텍스트 불일치', 'value': f'표시({text})와 실제 링크({href})가 다릅니다.', 'status': 'danger'})
            results['riskScores']['body'] += 25
        analyze_url(href, results)

    # 이미지 및 QR 코드 분석
    for img in soup.find_all('img', src=True):
        style = img.get('style', '')
        width = img.get('width', '')
        height = img.get('height', '')
        if 'width:1px' in style or 'height:1px' in style or (width == '1' and height == '1'):
            results['body'].append({'item': '추적 픽셀 의심', 'value': '1x1 크기의 숨겨진 이미지가 있습니다.', 'status': 'warn'})
            results['riskScores']['body'] += 10

    # 숨겨진 콘텐츠 분석
    hidden_elements = soup.select('[style*="display:none"], [style*="visibility:hidden"]')
    for el in hidden_elements:
        if el.get_text(strip=True):
            results['body'].append({'item': '숨겨진 콘텐츠', 'value': f'눈에 보이지 않는 텍스트/링크가 있습니다: <{el.name}>', 'status': 'warn'})
            results['riskScores']['body'] += 10

    # 스크립트 분석
    if soup.find_all('script'):
        results['body'].append({'item': 'Javascript 포함', 'value': '메일 본문에 스크립트가 포함되어 있습니다.', 'status': 'warn'})
        results['riskScores']['body'] += 15

def analyze_attachment(part, results):
    """첨부파일을 분석합니다."""
    filename = part.get_filename()
    if not filename:
        return

    # 기본 정보
    status, risk, details = 'info', 0, f'파일: {filename}'
    
    # 의심스러운 확장자
    suspicious_ext = ['.exe', '.vbs', '.scr', '.bat', '.com', '.pif', '.js', '.cmd', '.jar']
    if any(filename.lower().endswith(ext) for ext in suspicious_ext):
        status, risk, details = 'danger', 30, details + ' (실행 파일 의심)'

    # 이중 확장자
    if len(filename.split('.')) > 2:
        status = 'danger' if status == 'danger' else 'warn'
        risk = max(risk, 20)
        details += ' (이중 확장자 의심)'
    
    results['attachments'].append({'item': '첨부파일', 'value': details, 'status': status})
    results['riskScores']['attachments'] += risk

    # 파일 데이터 분석
    payload = part.get_payload(decode=True)
    if payload:
        # 파일 크기
        size_kb = len(payload) / 1024
        results['attachments'].append({'item': '파일 크기', 'value': f'{size_kb:.2f} KB', 'status': 'info'})

        # 파일 해시
        sha256_hash = hashlib.sha256(payload).hexdigest()
        results['attachments'].append({'item': '파일 해시 (SHA-256)', 'value': sha256_hash, 'status': 'info'})

        # MIME 타입 vs 시그니처 비교
        signature = payload[:8].hex()
        declared_content_type = part.get_content_type()
        
        # 간단한 MIME 타입 불일치 검사
        mismatch = False
        for mime_type, sig in FILE_SIGNATURES.items():
            if signature.startswith(sig):
                if declared_content_type != mime_type:
                    # 일부 특별한 경우 고려 (예: OOXML 파일들)
                    if not ('openxmlformats' in declared_content_type and mime_type == 'application/zip'):
                        mismatch = True
                break

        if mismatch:
            results['attachments'].append({'item': 'MIME 타입 불일치', 'value': '선언된 파일 형식과 실제 형식이 다를 수 있습니다.', 'status': 'danger'})
            results['riskScores']['attachments'] += 40

def analyze_url(url, results):
    """URL을 분석합니다."""
    if not url:
        return

    # URL에서 도메인 추출
    try:
        url_obj = urlparse(unquote(url))
        hostname = url_obj.hostname
        if not hostname:
            return
    except Exception:
        return

    # 이미 분석된 도메인인지 확인 (중복 방지)
    analyzed_domains = [item['value'].split(' - ')[0] for item in results['urls'] if 'Domain:' in item['value']]
    if hostname in analyzed_domains:
        return

    status, risk, issues = 'safe', 0, []

    # IP 주소 직접 사용
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', hostname):
        risk += 40
        issues.append('IP 주소 직접 사용')
    
    # HTTPS 미사용
    if url_obj.scheme != 'https':
        risk += 10
        issues.append('HTTPS 미사용')
    
    # Punycode
    if hostname.startswith('xn--'):
        risk += 30
        issues.append('Punycode 도메인')

    # 의심스러운 TLD
    suspicious_tlds = ['.guru', '.club', '.xyz', '.top', '.loan', '.work', '.click', '.link', '.biz', '.info']
    if any(hostname.endswith(tld) for tld in suspicious_tlds):
        risk += 20
        issues.append('의심스러운 TLD')

    # URL 내 이메일
    if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', url_obj.query):
        risk += 25
        issues.append('URL에 이메일 주소 포함')

    # 복잡한 경로
    if len([p for p in url_obj.path.split('/') if p]) > 3:
        risk += 15
        issues.append('복잡한 URL 경로 구조')
    
    # 의심스러운 파라미터
    suspicious_params = ['redirect', 'login', 'token', 'next', 'continue', 'return']
    if any(f'{p}=' in url_obj.query for p in suspicious_params):
        risk += 10
        issues.append('의심스러운 파라미터')

    if risk >= 40: status = 'danger'
    elif risk >= 15: status = 'warn'

    # 도메인만 표시하도록 수정
    details = f'Domain: {hostname}'
    if issues:
        details += f' - <span class="status-{status}">({", ".join(issues)})</span>'
    
    results['urls'].append({'item': 'URL 도메인', 'value': details, 'status': status})
    results['riskScores']['urls'] += risk


def get_domain_reputation_findings(hostnames):
    """도메인 평판 분석 결과를 리스트로 반환합니다."""
    findings = []
    scores = 0
    
    for hostname in hostnames:
        # 1. Whois 조회
        whois_report = get_domain_info_from_api(hostname)
        if whois_report and whois_report.get('days_since_creation', -1) >= 0:
            days = whois_report['days_since_creation']
            if days < 30:
                findings.append({
                    'item': f'도메인 신뢰도 - {hostname}', 
                    'value': f"생성된 지 {days}일밖에 되지 않은 신생 도메인입니다.", 
                    'status': 'danger'
                })
                scores += 30
            else:
                findings.append({
                    'item': f'도메인 정보 - {hostname}', 
                    'value': f"생성일: {whois_report.get('creation_date', 'N/A')[:10]}", 
                    'status': 'info'
                })
        
        # 2. VirusTotal 도메인 평판 조회
        vt_report = get_vt_report_from_api("domain", hostname)
        if vt_report and 'positives' in vt_report and 'total' in vt_report:
            positives = vt_report["positives"]
            total = vt_report["total"]
            
            if positives > 0:
                findings.append({
                    'item': f'VirusTotal 평판 - {hostname}', 
                    'value': f"악성/의심 탐지: {positives}/{total} 엔진에서 위험으로 분류", 
                    'status': 'danger'
                })
                scores += min(positives * 10, 50)  # 최대 50점까지만 추가
            elif total > 0:
                findings.append({
                    'item': f'VirusTotal 평판 - {hostname}', 
                    'value': f"검사 완료: {total}개 엔진에서 위험 요소 발견되지 않음", 
                    'status': 'safe'
                })
    
    return findings, scores

def get_file_reputation_findings(hashes):
    """파일 해시 평판 분석 결과를 리스트로 반환합니다."""
    findings = []
    scores = 0
    
    for file_hash in hashes:
        vt_report = get_vt_report_from_api("file", file_hash)
        if vt_report and 'positives' in vt_report and 'total' in vt_report:
            positives = vt_report["positives"]
            total = vt_report["total"]
            
            if positives > 0:
                findings.append({
                    'item': f'파일 평판 - {file_hash[:16]}...', 
                    'value': f"악성/의심 탐지: {positives}/{total} 엔진에서 위험으로 분류", 
                    'status': 'danger'
                })
                scores += min(positives * 10, 50)  # 최대 50점까지만 추가
            elif total > 0:
                findings.append({
                    'item': f'파일 평판 - {file_hash[:16]}...', 
                    'value': f"검사 완료: {total}개 엔진에서 위험 요소 발견되지 않음", 
                    'status': 'safe'
                })
    
    return findings, scores


def calculate_summary(results):
    """분석 결과를 종합하여 요약합니다."""
    total_score = sum(results['riskScores'].values())
    total_score = min(100, total_score)
    results['summary']['totalScore'] = total_score

    if total_score >= 70:
        results['summary']['level'] = '높음'
        results['summary']['message'] = '매우 위험한 피싱 이메일일 가능성이 높습니다. 즉시 삭제하세요.'
    elif total_score >= 40:
        results['summary']['level'] = '주의'
        results['summary']['message'] = '여러 위험 요소가 발견되었습니다. 링크 클릭 및 첨부파일 실행에 각별히 주의하세요.'
    elif total_score >= 10:
        results['summary']['level'] = '낮음'
        results['summary']['message'] = '일부 의심스러운 점이 있으나, 직접적인 위협은 낮아 보입니다. 주의해서 확인하세요.'
    else:
        results['summary']['level'] = '안전'
        results['summary']['message'] = '특별한 위협이 탐지되지 않았습니다.'

# ----------------------------------------------------------------------
# 3. Streamlit UI 구성
# ----------------------------------------------------------------------

# CSS 스타일 적용
st.markdown("""
<style>
    /* 전체 앱 배경 및 폰트 색상 */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Streamlit의 기본 흰색 배경을 가진 요소들을 투명하게 처리 */
    [data-testid="stAppViewContainer"] > .main {
        background-color: transparent;
    }
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    [data-testid="stToolbar"] {
        background-color: transparent;
    }

    /* 컨테이너 스타일 */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 1.5rem;
        border: 2px solid rgba(255, 255, 255, 0.2);
    }

    /* 위험도 표시 색상 */
    .status-safe { color: #4CAF50; }
    .status-warn { color: #FFC107; }
    .status-danger { color: #F44336; }
    .status-info { color: #4A90E2; }
    
    /* 파일 업로드 영역 스타일 */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1rem;
        border: 2px dashed rgba(255, 255, 255, 0.3);
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<div style="text-align: center;"><h1>📧 피싱 메일 분석</h1></div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; font-size: 1.2em; opacity: 0.9; margin-bottom: 2rem;">의심스러운 이메일 파일을 업로드하여 위험 요소를 정밀 분석해보세요</div>', unsafe_allow_html=True)

    if not OPENCV_AVAILABLE:
        st.warning("🔍 QR 코드 스캔을 위한 OpenCV 라이브러리를 찾을 수 없습니다. 'pip install opencv-python'으로 설치하시면 더 정확한 분석이 가능합니다.")

    # 파일 업로드 섹션
    st.markdown("### 📁 EML 파일 업로드")
    uploaded_file = st.file_uploader(
        "분석할 이메일 파일(.eml)을 선택하세요", 
        type=['eml'],
        help="Outlook, Thunderbird 등에서 저장한 .eml 파일을 업로드하세요"
    )

    if uploaded_file is not None:
        with st.spinner('📊 이메일을 정밀 분석 중입니다... (외부 API 조회로 인해 시간이 걸릴 수 있습니다)'):
            st.session_state.vt_key_missing = False

            eml_content = uploaded_file.getvalue().decode('utf-8', errors='ignore')
            
            msg = email.message_from_string(eml_content)
            results = {
                'header': [], 'body': [], 'attachments': [], 'urls': [],
                'riskScores': {'header': 0, 'body': 0, 'attachments': 0, 'urls': 0},
                'summary': {}
            }
            
            analyze_headers(msg, results)
            
            for part in msg.walk():
                if part.is_multipart(): continue
                if part.get_content_disposition() == 'attachment':
                    analyze_attachment(part, results)
                elif part.get_content_type() == 'text/html':
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    try: html_content = payload.decode(charset, errors='ignore')
                    except LookupError: html_content = payload.decode('cp949', errors='ignore')
                    analyze_html_body(html_content, results)

            # 고유 호스트네임 및 파일 해시 추출
            unique_hostnames = set()
            unique_hashes = set()

            # URL 분석에서 도메인 추출
            for url_item in results['urls']:
                if 'Domain:' in url_item['value']:
                    domain = url_item['value'].split('Domain: ')[1].split(' - ')[0]
                    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
                        unique_hostnames.add(domain)
            
            for att_item in results['attachments']:
                if att_item['item'] == '파일 해시 (SHA-256)':
                    unique_hashes.add(att_item['value'])

            # 외부 API 연동 분석 호출 및 결과 통합
            if unique_hostnames:
                domain_findings, domain_scores = get_domain_reputation_findings(unique_hostnames)
                results['urls'].extend(domain_findings)
                results['riskScores']['urls'] += domain_scores
            
            if unique_hashes:
                file_findings, file_scores = get_file_reputation_findings(unique_hashes)
                results['attachments'].extend(file_findings)
                results['riskScores']['attachments'] += file_scores

            calculate_summary(results)
            display_results(results)
            
            if st.session_state.vt_key_missing:
                st.warning("백엔드 서버에 VirusTotal API 키가 설정되지 않아 평판 조회를 건너뛰었습니다.")


def display_results(results):
    st.markdown("---")
    st.markdown("## 📊 분석 결과")

    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🎯 종합 위험도</h3>", unsafe_allow_html=True)
            
            # 파이 차트로 위험도 시각화
            fig = go.Figure(data=[go.Pie(
                labels=['헤더', '본문', '첨부파일', 'URL'],
                values=[
                    results['riskScores']['header'],
                    results['riskScores']['body'],
                    results['riskScores']['attachments'],
                    results['riskScores']['urls']
                ],
                hole=.4,
                marker_colors=['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
            )])
            fig.update_layout(
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                margin=dict(l=0, r=0, t=0, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>📋 분석 요약</h3>", unsafe_allow_html=True)
            summary = results['summary']
            level = summary['level']
            
            # 위험 등급에 따른 색상 설정
            if level == '높음': color = 'danger'
            elif level == '주의': color = 'warn'
            elif level == '낮음': color = 'info'
            else: color = 'safe'
            
            st.markdown(f"**종합 위험 점수: {summary['totalScore']} / 100**")
            st.markdown(f'**위험 등급: <span class="status-{color}">{level}</span>**', unsafe_allow_html=True)
            st.info(summary['message'])

    st.markdown("---")
    st.markdown("## 🔍 상세 분석 결과")

    # 상세 분석 결과를 탭으로 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📨 헤더 분석", "📄 본문 분석", "📎 첨부파일 분석", "🔗 URL 분석"])
    
    with tab1:
        display_section_results("헤더 분석", results['header'])
    
    with tab2:
        display_section_results("본문 분석", results['body'])
    
    with tab3:
        display_section_results("첨부파일 분석", results['attachments'])
    
    with tab4:
        display_section_results("URL 분석", results['urls'])


def display_section_results(section_name, section_results):
    """각 섹션의 분석 결과를 표시합니다."""
    if not section_results:
        st.info(f"{section_name}에서 검사할 항목이 없습니다.")
        return
    
    for item in section_results:
        icon = {'safe': '✅', 'warn': '⚠️', 'danger': '❌', 'info': 'ℹ️'}[item['status']]
        
        # 상태에 따른 컨테이너 스타일
        if item['status'] == 'danger':
            st.error(f"{icon} **{item['item']}**: {item['value']}")
        elif item['status'] == 'warn':
            st.warning(f"{icon} **{item['item']}**: {item['value']}")
        elif item['status'] == 'safe':
            st.success(f"{icon} **{item['item']}**: {item['value']}")
        else:
            st.info(f"{icon} **{item['item']}**: {item['value']}")

if __name__ == "__main__":
    main()