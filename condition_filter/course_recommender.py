import json
import pandas as pd


# ---------------------------------
# 파일 경로
# ---------------------------------

GRADUATION_RULE_PATH = (
    "graduation_rule/graduation.json"
)

CURRICULUM_MODEL_PATH = (
    "graduation_rule/standard_curriculum.csv"
)


# ---------------------------------
# 졸업요건 JSON 로드
# ---------------------------------

def load_graduation_rules(json_path):

    with open(
        json_path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ---------------------------------
# 표준이수모형 CSV 로드
# ---------------------------------

def load_curriculum_model(csv_path):

    return pd.read_csv(
        csv_path,
        encoding="utf-8-sig"
    )


# ---------------------------------
# 입학년도에 맞는 졸업요건 선택
# ---------------------------------

def get_graduation_rule(
    rules_data,
    admission_year
):

    for _, rule in rules_data["rule_sets"].items():

        applies = rule["applies_to"]

        if (
            applies["admission_year_from"]
            <= admission_year
            <= applies["admission_year_to"]
        ):

            return rule

    return None


# ---------------------------------
# 데이터 로드
# ---------------------------------

rules_data = load_graduation_rules(
    GRADUATION_RULE_PATH
)

curriculum_df = load_curriculum_model(
    CURRICULUM_MODEL_PATH
)


# ---------------------------------
# 테스트
# ---------------------------------

admission_year = 2025

graduation_rule = get_graduation_rule(
    rules_data,
    admission_year
)

print("\n선택된 졸업요건")
print(graduation_rule["name"])