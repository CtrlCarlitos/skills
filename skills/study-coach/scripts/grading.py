def is_self_gradable(question):
    return question["type"] != "open_response"


def grade_answer(question, given_answer):
    if question["type"] == "open_response":
        return None

    if question["type"] == "fill_in_blank":
        normalized_given = given_answer.strip().casefold() if isinstance(given_answer, str) else given_answer
        accepted = question["correct_answer"] or []
        return any(normalized_given == accepted_answer.strip().casefold() for accepted_answer in accepted)

    return given_answer == question["correct_answer"]


def score_exam(exam, answers):
    results = []
    for question in exam["questions"]:
        given_answer = answers.get(question["question_id"])
        results.append({
            "question_id": question["question_id"],
            "subject": question["subject"],
            "topic": question["topic"],
            "competency": question["competency"],
            "type": question["type"],
            "given_answer": given_answer,
            "correct": grade_answer(question, given_answer),
        })
    return results
