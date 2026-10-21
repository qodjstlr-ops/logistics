import io
import unittest
import openpyxl
from app import analyze


def workbook(headers, values):
    book = openpyxl.Workbook()
    book.active.append(headers)
    for row in values:
        book.active.append(row)
    output = io.BytesIO()
    book.save(output)
    return output.getvalue()


class AnalysisTests(unittest.TestCase):
    def test_threshold_and_quantities(self):
        master = workbook(['FCID', '제조오더번호'], [['001', key] for key in ['A', 'B', 'C']])
        values = []
        for key, count in [('A', 20), ('B', 19)]:
            values += [[key, 1 if n == 0 else 0, 'PART'] for n in range(count)]
        values += [['C', n, 'PART'] for n in [0, -1, 0.9]]
        result = analyze(master, workbook(['제조오더번호', '이동잔량', '품목코드'], values))
        self.assertEqual([o['order'] for o in result['orders']], ['A'])
        self.assertEqual(result['orders'][0]['rate'], 5)
        self.assertEqual(result['orders'][0]['fcid'], '001')
        self.assertEqual(result['orders'][0]['items'][0]['품목코드'], 'PART')

    def test_conflicts_and_invalid_values(self):
        master = workbook(['FCID', '제조오더번호'], [['X', 'A'], ['Y', 'A'], ['X', 'B']])
        values = [['A', 1, 'P'], ['B', 'oops', 'P'], ['C', 1, 'P']]
        result = analyze(master, workbook(['제조오더번호', '이동잔량', '품목코드'], values))
        self.assertEqual(result['orders'], [])
        self.assertEqual(result['warnings']['FCID 매칭 누락·충돌 제조오더'], 2)
        self.assertEqual(result['warnings']['이동잔량 확인 필요 행'], 1)

    def test_missing_headers(self):
        with self.assertRaises(ValueError):
            analyze(workbook(['wrong'], [['x']]), b'')
