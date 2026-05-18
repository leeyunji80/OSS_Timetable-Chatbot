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
            "수업방식": "", "요일": "", "교시": "", "강의실": "", "담당교수": "", "강의 정원": "",
            "방법_강의(%)": "0", "방법_토의토론(%)": "0", "방법_실험실습(%)": "0", 
            "방법_현장학습(%)": "0", "방법_발표(%)": "0", "방법_기타(%)": "0",
            "평가_중간(%)": "0", "평가_기말(%)": "0", "평가_출석(%)": "0", 
            "평가_퀴즈(%)": "0", "평가_과제(%)": "0", "평가_기타(%)": "0"
        }

        for i, row in enumerate(all_rows):
            clean_row = [str(cell).replace(" ", "").replace("\n", "") for cell in row]
            row_str = "".join(clean_row)

            # 기본 정보 매칭
            if "개설연도" in row_str:
                data["개설 연도"] = row[1] if len(row) > 1 else ""
                for idx, cell in enumerate(clean_row):
                    if "개설학과" in cell and idx + 1 < len(row):
                        data["개설 학과"] = row[idx+1]
            
            if "수강대상" in row_str:
                for idx, cell in enumerate(clean_row):
                    if "수강대상" in cell and idx + 1 < len(row):
                        data["수강 대상"] = row[idx+1].strip()
                
                # 만약 위에서 못 찾았거나 보충이 필요할 때만 '학년' 단어를 검색
                if not data["수강 대상"] or "학년" not in data["수강 대상"]:
                    for cell in row: # combined_cells 대신 row 사용
                        cell_clean = str(cell).strip()
                        if "학년" in cell_clean and "수강대상" not in cell_clean:
                            data["수강 대상"] = cell_clean
                            break
                

            if "교과목번호" in row_str:
                data["교과목 번호"] = row[1] if len(row) > 1 else ""
                data["분반 번호"] = row[2] if len(row) > 2 else ""
                # '교과목명' 텍스트를 찾아서 그 다음 칸을 가져오도록 더 정밀하게 수정
                for idx, cell in enumerate(clean_row):
                    if "교과목명" in cell and idx + 1 < len(row):
                        data["교과목명"] = row[idx+1].strip()

            if "이수구분" in row_str:
                data["이수구분"] = row[1]
                for idx, cell in enumerate(clean_row):
                    if "학점" in cell and idx + 1 < len(row):
                        time_val = row[idx+1]
                        if "-" in time_val:
                            parts = time_val.split("-")
                            if len(parts) == 3:
                                data["학점"], data["이론"], data["실습"] = parts[0], parts[1], parts[2]
            
            if len(clean_row) > 0 and clean_row[0] == "수업방식":
                # 보통 '수업방식' 라벨 옆칸에 정보가 있음
                data["수업방식"] = row[1].strip() if len(row) > 1 else ""

           # 요일, 교시, 건물 정밀 분리 로직 적용
            if "강의시간" in row_str:
                raw_time_loc = ""
                for cell in row[1:]:
                    if cell and "[" in cell and "]" in cell: # 요일과 강의실 형식이 포함된 칸 찾기
                        raw_time_loc = cell
                        break
                
                if not raw_time_loc: # 못 찾았다면 기존 방식 유지
                    raw_time_loc = " ".join([c for c in row[1:] if "개설" not in c and "담당" not in c and c]).strip()
               
                matches = re.findall(r'([월화수목금토일])\s*([\d,\s]+)\[(.*?)\]', raw_time_loc)
                
                if matches:
                    days, periods, rooms = [], [], []
                    for m in matches:
                        days.append(m[0].strip())
                        periods.append(m[1].replace(" ", ""))
                        rooms.append(m[2].strip())
                    data["요일"], data["교시"], data["강의실"] = "|".join(days), "|".join(periods), "|".join(rooms)
                
                        
            if "담당교수" in row_str and not data["담당교수"]:
               for idx, cell in enumerate(clean_row):
                   if "담당교수" in cell and idx + 1 < len(row):
                      data["담당교수"] = row[idx+1].strip()
                      break
                   
            if "강의정원" in row_str:
                data["강의 정원"] = row[1]

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
        result = []

        # 바로 아래 1행만 읽기
        target_idx = current_idx + 1

        if target_idx >= len(all_rows):
            return ["0"] * 6

        row = all_rows[target_idx]
  
        for cell in row:

            cell_str = str(cell).strip()

            # 50%, -% 패턴만 추출
            matches = re.findall(r'(\d+|-)\s*%', cell_str)

            for m in matches:

                if m == "-":
                    result.append("0")
                else:
                  result.append(m)

        # 부족하면 0 채우기
        while len(result) < 6:
              result.append("0")

        return result[:6]
    
class LectureExporter:
    """3. 출력: 결과를 CSV로 저장"""
    def save(self, data_list, output_path):
        df = pd.DataFrame(data_list)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    def create_mapping_csv(self, lecture_df):

        mapping_df = lecture_df.copy()

        mapping_df["교양대분류"] = ""
        mapping_df["교양소분류"] = ""

        mapping_path = "liberal_arts.csv"

        if os.path.exists(mapping_path):
            return

        mapping_df = lecture_df.copy()

        mapping_df["교양대분류"] = ""
        mapping_df["교양소분류"] = ""

        mapping_df.to_csv(
        mapping_path,
        index=False,
        encoding='utf-8-sig'
    )

    def merge_data(self):

        lecture_df = pd.read_csv(
            "lecture_data.csv",
            dtype=str
        )

        mapping_df = pd.read_csv(
            "liberal_arts.csv",
            dtype=str
        )

        final_df = pd.merge(
            lecture_df,
            mapping_df[[
                "교과목 번호",
                "교양대분류",
                "교양소분류"
            ]],
            on="교과목 번호",
            how="left"
        )

        final_df.to_csv(
            "final_lecture_database.csv",
            index=False,
            encoding='utf-8-sig'
        )

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

    exporter.save(final_results, "lecture_data.csv")

    lecture_df = pd.DataFrame(final_results)

    exporter.create_mapping_csv(lecture_df)

    print("완료")

if __name__ == "__main__":
    main()