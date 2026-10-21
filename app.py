import base64
import io
import json
import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent


def rows(data, required):
    import openpyxl
    book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        sheet = book.active
        iterator = sheet.iter_rows(values_only=True)
        headers = [str(v).strip() if v is not None else '' for v in next(iterator)]
        missing = set(required) - set(headers)
        if missing:
            raise ValueError('필수 열이 없습니다: ' + ', '.join(sorted(missing)))
        for values in iterator:
            if any(v is not None for v in values):
                yield dict(zip(headers, values))
    finally:
        book.close()


def text(value):
    return '' if value is None else str(value).strip()


def analyze(master, materials):
    mapping = defaultdict(set)
    for row in rows(master, ['FCID', '제조오더번호']):
        if text(row['제조오더번호']):
            mapping[text(row['제조오더번호'])].add(text(row['FCID']))
    orders = {}
    warnings = defaultdict(int)
    for row in rows(materials, ['제조오더번호', '이동잔량', '품목코드']):
        key = text(row['제조오더번호'])
        if not key:
            warnings['제조오더번호 누락 행'] += 1
            continue
        order = orders.setdefault(key, {'order': key, 'total': 0, 'items': [], 'invalid': 0})
        order['total'] += 1
        try:
            quantity = Decimal(text(row['이동잔량']).replace(',', ''))
            if not quantity.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            warnings['이동잔량 확인 필요 행'] += 1
            order['invalid'] += 1
            continue
        if quantity >= 1:
            order['items'].append({field: text(row.get(field)) for field in
                                   ['품목코드', '품목명', '규격', '이동잔량', '현재고', '투입단위']})
    eligible = []
    unshipped = sum(len(o['items']) for o in orders.values())
    for key, order in orders.items():
        ids = mapping.get(key, set())
        if len(ids) != 1 or '' in ids:
            warnings['FCID 매칭 누락·충돌 제조오더'] += 1
            continue
        if order['invalid']:
            continue
        if 0 < len(order['items']) * 100 <= order['total'] * 5:
            order['fcid'] = next(iter(ids))
            order['rate'] = len(order['items']) / order['total'] * 100
            eligible.append(order)
    eligible.sort(key=lambda o: (o['fcid'], o['order']))
    return {'orders': eligible, 'warnings': dict(warnings), 'summary': {
        'totalOrders': len(orders), 'unshippedRows': unshipped,
        'eligibleOrders': len(eligible), 'fcids': len({o['fcid'] for o in eligible})}}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        target = files.get(self.path)
        if not target:
            self.send_error(404)
            return
        data = (ROOT / 'static' / target[0]).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', target[1])
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != '/api/analyze':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 100 * 1024 * 1024:
                raise ValueError('파일 합계는 약 70MB 이하로 업로드해 주세요.')
            body = json.loads(self.rfile.read(length))
            result = analyze(base64.b64decode(body['master'], validate=True),
                             base64.b64decode(body['materials'], validate=True))
            status = 200
        except Exception as error:
            status = 400
            result = {'error': str(error) if isinstance(error, ValueError) else
                      '엑셀을 읽지 못했습니다. 올바른 PP610·PP620 파일인지 확인해 주세요.'}
        payload = json.dumps(result, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', '8000')))
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    print(f'자재통합관리 개발 서버 시작 (port {args.port})', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
