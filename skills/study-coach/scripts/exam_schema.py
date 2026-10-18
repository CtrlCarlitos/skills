QUESTION_TYPES = {"multiple_choice", "single_select", "true_false", "fill_in_blank", "matching", "open_response"}


def make_question(question_id, type, subject, topic, prompt, options=None, correct_answer=None, competency=None):
    if type not in QUESTION_TYPES:
        raise ValueError(f"unknown question type: {type!r}")

    return {
        "question_id": question_id,
        "type": type,
        "subject": subject,
        "topic": topic,
        "competency": competency,
        "prompt": prompt,
        "options": options,
        "correct_answer": correct_answer,
    }


def make_exam(exam_id, child_id, subject, topic, grade, questions):
    if not questions:
        raise ValueError("an exam must have at least one question")

    return {
        "exam_id": exam_id,
        "child_id": child_id,
        "subject": subject,
        "topic": topic,
        "grade": grade,
        "questions": questions,
    }
