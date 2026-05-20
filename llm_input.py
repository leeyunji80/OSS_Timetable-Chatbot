def parse_single_input(text):

    result = {
        "요일": None,
        "시간": None,
        "조건": None
    }

    days = [
        "월요일",
        "화요일",
        "수요일",
        "목요일",
        "금요일"
    ]

    times = [
        "오전",
        "오후",
        "아침"
    ]

    conditions = {
        "피하고": "회피",
        "싫어": "회피",
        "듣고": "선호",
        "원해": "선호"
    }

    for day in days:
        if day in text:
            result["요일"] = day

    for time in times:
        if time in text:
            result["시간"] = time

    for keyword, value in conditions.items():
        if keyword in text:
            result["조건"] = value

    return result


def parse_user_input(text):

    split_text = text.split("고")

    results = []

    current_day = None

    for sentence in split_text:

        parsed_result = parse_single_input(sentence)

        if parsed_result["요일"] is not None:
            current_day = parsed_result["요일"]

        else:
            parsed_result["요일"] = current_day

        results.append(parsed_result)

    return results


user_input = "월요일 오전은 피하고 오후는 듣고 싶어"

print(parse_user_input(user_input))