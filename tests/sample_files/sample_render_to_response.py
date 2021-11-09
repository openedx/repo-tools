import logging
from django.shortcuts import render_to_response


def get_submissions_for_student_item(request, course_id, student_id, item_id):
    student_item_dict = dict(
        course_id=course_id,
        student_id=student_id,
        item_id=item_id,
    )
    context = dict(**student_item_dict)

    return render_to_response('submissions.html', context)
