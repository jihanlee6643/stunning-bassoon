import re
from urllib.parse import urlparse, parse_qs
import requests
import streamlit as st

st.set_page_config(page_title='YouTube Stats', page_icon='📺', layout='centered')
st.title('📺 YouTube Stats')
st.caption('유튜브 영상 링크를 입력하면 조회수와 좋아요 수를 확인할 수 있어요.')

def video_id_from_url(raw):
    raw = raw.strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', raw):
        return raw
    parsed = urlparse(raw)
    host = (parsed.hostname or '').lower()
    path = parsed.path.strip('/').split('/')
    if host in ('youtu.be', 'www.youtu.be') and path:
        candidate = path[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if parsed.path == '/watch':
            candidate = parse_qs(parsed.query).get('v', [''])[0]
        elif len(path) >= 2 and path[0] in ('shorts', 'live', 'embed'):
            candidate = path[1]
        else:
            return None
    else:
        return None
    return candidate if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate) else None

url = st.text_input('영상 링크', placeholder='https://www.youtube.com/watch?v=...')
if st.button('조회하기', type='primary', use_container_width=True):
    vid = video_id_from_url(url)
    if not vid:
        st.error('올바른 YouTube 영상 URL 또는 11자리 영상 ID를 입력해 주세요.')
    else:
        try:
            key = st.secrets['YOUTUBE_API_KEY']
        except (KeyError, FileNotFoundError):
            st.error('Streamlit Secrets에 YOUTUBE_API_KEY를 등록해 주세요.')
            st.stop()
        try:
            resp = requests.get('https://www.googleapis.com/youtube/v3/videos', params={
                'part': 'snippet,statistics', 'id': vid, 'key': key
            }, timeout=12)
            resp.raise_for_status()
            items = resp.json().get('items', [])
            if not items:
                st.warning('영상을 찾지 못했어요. 비공개 또는 삭제된 영상일 수 있어요.')
            else:
                info = items[0]
                snippet = info['snippet']
                stats = info.get('statistics', {})
                thumbnails = snippet.get('thumbnails', {})
                thumb = thumbnails.get('high') or thumbnails.get('medium') or thumbnails.get('default')
                if thumb:
                    st.image(thumb['url'], use_container_width=True)
                st.subheader(snippet['title'])
                st.caption(snippet.get('channelTitle', ''))
                cols = st.columns(3)
                for col, label, field in zip(cols, ['👁️ 조회수', '👍 좋아요', '💬 댓글'], ['viewCount', 'likeCount', 'commentCount']):
                    value = stats.get(field)
                    col.metric(label, f'{int(value):,}' if value is not None else '비공개/미제공')
                st.link_button('YouTube에서 보기', f'https://www.youtube.com/watch?v={vid}', use_container_width=True)
        except requests.HTTPError as e:
            status = e.response.status_code
            if status == 403:
                st.error('API 접근이 거부됐어요. YouTube Data API v3 활성화, API 키 제한, 할당량을 확인해 주세요.')
            elif status == 400:
                st.error('API 요청이 올바르지 않아요. 키 설정을 확인해 주세요.')
            else:
                st.error(f'YouTube API 요청 실패 (HTTP {status}).')
        except requests.RequestException:
            st.error('네트워크 오류가 발생했어요. 잠시 후 다시 시도해 주세요.')
