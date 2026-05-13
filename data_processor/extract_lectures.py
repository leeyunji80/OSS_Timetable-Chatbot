import pdfplumber
import pandas as pd
import re
import os

class LecturePDFReader:
    """1. 입력: PDF 파일에서 표와 텍스트를 추출"""
    def get_raw_data(self, file_path):
        all_rows = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            # 데이터 클리닝
                            all_rows.append([str(cell).strip() if cell else "" for cell in row])
            return all_rows
        except Exception as e:
            print(f"파일 읽기 오류 ({file_path}): {e}")
            return []
        
class LectureParser:
    """2. 처리: 날것의 행 데이터에서 강의 정보 파싱"""
    def parse_rows(self, all_rows):
        data = {
            "개설 연도": "", "개설 학과": "", "수강 대상": "",
            "교과목 번호": "", "분반 번호": "",
            "교과목명": "", "이수구분": "", "학점": "0", "이론": "0", "실습": "0",
            "수업방식": "", "강의시간(원본)": "", "요일": "", "교시": "", "강의실": "", "담당교수": "", "강의 정원": "",
            "방법_강의(%)": "0", "방법_토의토론(%)": "0", "방법_실험실습(%)": "0", 
            "방법_현장학습(%)": "0", "방법_발표(%)": "0", "방법_기타(%)": "0",
            "평가_중간(%)": "0", "평가_기말(%)": "0", "평가_출석(%)": "0", 
            "평가_퀴즈(%)": "0", "평가_과제(%)": "0", "평가_기타(%)": "0"
        }

        for i, row in enumerate(all_rows):
            row_str = "".join(row).replace(" ", "").replace("\n", "")

            # 기본 정보 매칭
            if "개설연도" in row_str:
                data["개설 연도"] = row[1] if len(row) > 1 else ""
                data["개설 학과"] = row[4] if len(row) > 4 else ""
            
            if "수강대상" in row_str:
                combined_cells = row + (all_rows[i+1] if i + 1 < len(all_rows) else [])
                
                target_grade = ""
                for cell in combined_cells:
                    cell_clean = str(cell).strip()
                    # '학년'이라는 단어가 포함되어 있고, '선수과목'이나 '수강대상'이라는 단어는 제외
                    if "학년" in cell_clean and "수강대상" not in cell_clean:
                        target_grade = cell_clean
                        break
                
                # 만약 '학년'이라는 단어를 못 찾았다면, 차선책으로 숫자가 포함된 칸을 찾음
                if not target_grade:
                    for cell in combined_cells:
                        cell_clean = str(cell).strip()
                        if any(char.isdigit() for char in cell_clean) and "학년" in cell_clean:
                             target_grade = cell_clean
                             break
                
                data["수강 대상"] = target_grade

            if "교과목번호" in row_str:
                data["교과목 번호"] = row[1]
                data["분반 번호"] = row[2]
                data["교과목명"] = row[4]

            if "이수구분" in row_str:
                data["이수구분"] = row[1]
                time_val = row[4] if len(row) > 4 else ""
                if "-" in time_val:
                    parts = time_val.split("-")
                    if len(parts) == 3:
                        data["학점"], data["이론"], data["실습"] = parts[0], parts[1], parts[2]
            
            if "수업방식" in row_str: data["수업방식"] = row[1]

           # 요일, 교시, 건물 정밀 분리 로직 적용
            if "강의시간" in row_str:
                raw_time_loc = " ".join([c for c in row[1:] if "개설" not in c and "담당" not in c and c]).strip()
                data["강의시간(원본)"] = raw_time_loc # 원본도 만약을 위해 남겨둡니다

                matches = re.findall(r'([월화수목금토일])\s*([\d,\s]+)[\[\(](.*)[\]\)]', raw_time_loc)
                
                if matches:
                    days = []
                    periods = []
                    rooms = []
                    
                    for m in matches:
                        days.append(m[0].strip())
                        periods.append(m[1].replace(" ", ""))
                        clean_room = m[2].strip().replace("[", "").replace("]", "")
                        rooms.append(clean_room)
                        
                # 구분자 '|'를 사용하여 하나의 셀에 합쳐서 저장 (알고리즘에서 split('|')로 분리 가능)
                    data["요일"] = "|".join(days)
                    data["교시"] = "|".join(periods)
                    data["강의실"] = "|".join(rooms)
                else:
                    # 괄호가 없는 특수 케이스 처리
                    match_simple = re.findall(r'([월화수목금토일])\s*([\d,\s]+)', raw_time_loc)
                    if match_simple:
                        data["요일"] = "|".join([m[0].strip() for m in match_simple])
                        data["교시"] = "|".join([m[1].replace(" ", "") for m in match_simple])

            if "담당교수" in row_str: data["담당교수"] = row[4]
            if "강의정원" in row_str: data["강의 정원"] = row[1]

            # 수치 데이터 정밀 추출 (수업방법/평가방법)
            if "수업진행방법" in row_str:
                nums = self._extract_numbers(all_rows, i)
                keys = ["방법_강의(%)", "방법_토의토론(%)", "방법_실험실습(%)", "방법_현장학습(%)", "방법_발표(%)", "방법_기타(%)"]
                for k, v in zip(keys, nums): data[k] = v

            if "평가방법" in row_str:
                nums = self._extract_numbers(all_rows, i)
                keys = ["평가_중간(%)", "평가_기말(%)", "평가_출석(%)", "평가_퀴즈(%)", "평가_과제(%)", "평가_기타(%)"]
                for k, v in zip(keys, nums): data[k] = v

        return data

    def _extract_numbers(self, all_rows, current_idx):
        """제목 행 아래 2행까지 탐색하여 숫자만 추출"""
        combined_row = []
        for next_idx in range(1, 3):
            if current_idx + next_idx < len(all_rows):
                combined_row.extend(all_rows[current_idx + next_idx])
        return [re.sub(r'[^0-9]', '', n) for n in combined_row if re.sub(r'[^0-9]', '', n)][:6]
class LectureExporter:
    """3. 출력: 결과를 CSV로 저장"""
    def save(self, data_list, output_path):
        df = pd.DataFrame(data_list)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n✨ {len(data_list)}개의 강의 데이터가 {output_path}에 저장되었습니다.")
# --- 메인 실행부 ---
def main():
    # 객체 생성
    reader = LecturePDFReader()
    parser = LectureParser()
    exporter = LectureExporter()

    final_results = []
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]

    if not pdf_files:
        print("현재 폴더에 PDF 파일이 없습니다.")
        return

    for pdf in pdf_files:
        print(f"🚀 처리 중: {pdf}")
        raw_rows = reader.get_raw_data(pdf)
        parsed_data = parser.parse_rows(raw_rows)
        final_results.append(parsed_data)

    exporter.save(final_results, "lectures_database.csv")

if __name__ == "__main__":
    main()