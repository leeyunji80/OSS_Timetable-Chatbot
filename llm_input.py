def parse_user_input(text):
    text = text.lower()
    processed_text = text.strip()

    result = {
        "요일": None,
        "시간": None
    }

    if "월요일" in processed_text:
        result["요일"] = "월요일"

    if "오전" in processed_text:
        result["시간"] = "오전"

    
    return result