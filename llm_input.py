def parse_user_input(text):
    text = text.lower()
    processed_text = text.strip()

    result = {
        "요일": None,
        "시간": None
    }

    days = [
        "월요일",
        "화요일",
        "수요일",
        "목요일",
        "금요일",
        ]

    for day in days:
        if day in processed_text:
            result["요일"] = day

    times = [
        "오전",
        "오후",
        "아침"]

    for time in times:
        if time in processed_text:
            result["시간"] = time

    
    
    return result


user_input = "월요일 오전 수업 피하고 싶어"
    
print(parse_user_input(user_input))
