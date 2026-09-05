#!/usr/bin/env python3
"""담다 서버 — 웹앱 + YouTube API (python server.py 로 실행)"""
import json, os, sys, re, urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

YT_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/transcript':
            self._transcript()
        elif path == '/api/info':
            self._info()
        elif path == '/api/description':   # 하위호환
            self._info()
        else:
            super().do_GET()

    def _transcript(self):
        vid = (parse_qs(urlparse(self.path).query).get('v') or [''])[0]
        if not vid:
            return self._json(400, {'error': '비디오 ID가 없습니다'})
        try:
            from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
            try:
                entries = YouTubeTranscriptApi.get_transcript(vid, languages=['ko', 'ko-KR'])
            except NoTranscriptFound:
                entries = YouTubeTranscriptApi.get_transcript(vid, languages=['en', 'en-US'])
            text = ' '.join(e['text'].replace('\n', ' ') for e in entries if e.get('text'))
            print(f'  자막 OK: {vid} ({len(text)}자)')
            self._json(200, {'text': text})
        except ImportError:
            self._json(500, {'error': 'youtube-transcript-api 미설치'})
        except Exception as e:
            print(f'  자막 실패: {vid} — {e}')
            self._json(500, {'error': str(e)})

    def _info(self):
        vid = (parse_qs(urlparse(self.path).query).get('v') or [''])[0]
        if not vid:
            return self._json(400, {'error': '비디오 ID가 없습니다'})

        result = {}

        # ── 1. 영상 설명 ─────────────────────────────────────────
        try:
            req = urllib.request.Request(
                f'https://www.youtube.com/watch?v={vid}', headers=YT_HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', html)
            if m:
                result['description'] = (
                    m.group(1)
                    .replace('\\n', '\n')
                    .replace('\\"', '"')
                    .replace('\\\\', '\\')
                )
                print(f'  설명 OK: {vid} ({len(result["description"])}자)')
        except Exception as e:
            print(f'  설명 실패: {vid} — {e}')

        # ── 2. 댓글 (인기순 상위 / 고정댓글 우선) ────────────────
        try:
            from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
            dl = YoutubeCommentDownloader()
            url = f'https://www.youtube.com/watch?v={vid}'
            pinned, top = [], []
            for i, c in enumerate(dl.get_comments_from_url(url, sort_by=SORT_BY_POPULAR)):
                if i >= 40:
                    break
                text = c.get('text', '').strip()
                if not text:
                    continue
                # 첫 번째 댓글은 보통 고정댓글
                if i == 0 or c.get('heart'):
                    pinned.append(text)
                else:
                    top.append(text)
            result['pinned_comments'] = pinned
            result['top_comments'] = top[:10]
            print(f'  댓글 OK: {vid} (고정 {len(pinned)}개, 상위 {len(top)}개)')
        except ImportError:
            print(f'  댓글 스킵: youtube-comment-downloader 미설치')
        except Exception as e:
            print(f'  댓글 실패: {vid} — {e}')

        self._json(200, result)

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    try:
        import youtube_transcript_api
    except ImportError:
        print('설치 필요: pip install youtube-transcript-api')
        sys.exit(1)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    port = 8080
    print(f'담다 앱: http://localhost:{port}')
    print('종료: Ctrl+C\n')
    try:
        HTTPServer(('', port), Handler).serve_forever()
    except KeyboardInterrupt:
        print('\n서버 종료')
