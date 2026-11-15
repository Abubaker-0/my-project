"""Sample campus calendar, courses, 30 students, and a teacher.

Skipped in production. Safe to run again: it stops once the first sample
admission number is present.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.academics import (
    AcademicYear,
    Batch,
    BatchTeacher,
    Course,
    NumberSequence,
    Room,
    Staff,
    Subject,
    Term,
)
from app.models.branch import Branch
from app.models.enrollment import Enrollment
from app.models.people import Guardian, Inquiry, InquiryFollowup, Student, StudentGuardian
from app.models.rbac import Role, UserRole
from app.models.user import User

logger = logging.getLogger(__name__)

TEACHER_EMAIL = "maya.iqbal@tuition.example"
TEACHER_PASSWORD = "Teacher@12345"

_FIRST = [
    "Amina",
    "Bilal",
    "Chloe",
    "Darius",
    "Elena",
    "Farid",
    "Grace",
    "Hassan",
    "Imani",
    "Jamal",
    "Kira",
    "Leo",
    "Maya",
    "Noah",
    "Omar",
    "Priya",
    "Quinn",
    "Ravi",
    "Sara",
    "Tariq",
    "Uma",
    "Victor",
    "Wafa",
    "Xavier",
    "Yara",
    "Zain",
    "Lina",
    "Hugo",
    "Nora",
    "Idris",
]
_LAST = [
    "Khan",
    "Rahman",
    "Silva",
    "Mensah",
    "Novak",
    "Haddad",
    "Okoye",
    "Diallo",
    "Berg",
    "Santos",
    "Ibrahim",
    "Costa",
    "Nguyen",
    "Park",
    "Ali",
    "Sharma",
    "Rossi",
    "Mehta",
    "Noor",
    "Farouk",
    "Singh",
    "Duarte",
    "Hassan",
    "Lopez",
    "Kim",
    "Abbas",
    "Cruz",
    "Meyer",
    "Blake",
    "Yusuf",
]


def seed_samples(session: Session, branch: Branch, admin: User) -> None:
    """Insert the demo academic records for the main campus."""
    if session.scalar(select(Student.id).where(Student.admission_no == "MAIN-2026-0001")):
        return
    year = AcademicYear(
        branch_id=branch.id,
        name="2026-2027",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
        created_by=admin.id,
        updated_by=admin.id,
    )
    session.add(year)
    session.flush()
    term = Term(
        branch_id=branch.id,
        academic_year_id=year.id,
        name="Term 1",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 9, 30),
        created_by=admin.id,
        updated_by=admin.id,
    )
    room_a = Room(
        branch_id=branch.id,
        name="Room A",
        capacity=24,
        status="active",
        created_by=admin.id,
        updated_by=admin.id,
    )
    room_b = Room(
        branch_id=branch.id,
        name="Room B",
        capacity=18,
        status="active",
        created_by=admin.id,
        updated_by=admin.id,
    )
    session.add_all([term, room_a, room_b])
    session.flush()

    subjects = {
        code: Subject(
            branch_id=branch.id,
            code=code,
            name=name,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        for code, name in (
            ("MATH", "Mathematics"),
            ("ENG", "English"),
            ("SCI", "Science"),
            ("ICT", "Information and Communication Technology"),
        )
    }
    session.add_all(subjects.values())
    session.flush()
    catalog = {
        "MATH": ("Grade 8 Mathematics", "Grade 8", 16),
        "ENG": ("Grade 9 English", "Grade 9", 16),
        "SCI": ("Grade 10 Science", "Grade 10", 20),
        "ICT": ("ICT Foundation", "Foundation", 12),
    }
    courses = {}
    for code, (name, level, weeks) in catalog.items():
        course = Course(
            branch_id=branch.id,
            subject_id=subjects[code].id,
            name=name,
            level=level,
            description=f"{name} for the 2026-2027 year.",
            duration_weeks=weeks,
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        courses[code] = course
        session.add(course)
    session.flush()
    batches = {
        "MATH": _batch(branch, courses["MATH"], term, room_a, "Math A", 12, admin.id),
        "ENG": _batch(branch, courses["ENG"], term, room_b, "English A", 20, admin.id),
        "SCI": _batch(branch, courses["SCI"], term, room_a, "Science A", 18, admin.id),
        "ICT": _batch(branch, courses["ICT"], term, room_b, "ICT A", 10, admin.id),
    }
    session.add_all(batches.values())
    session.flush()

    students = []
    for index in range(30):
        student = Student(
            branch_id=branch.id,
            admission_no=f"MAIN-2026-{index + 1:04d}",
            first_name=_FIRST[index],
            last_name=_LAST[index],
            dob=date(2012, 1, 1) + timedelta(days=index * 17),
            gender=("female", "male")[index % 2],
            school_name="Riverside School",
            grade_level=("Grade 8", "Grade 9", "Grade 10")[index % 3],
            status="active",
            admission_date=date(2026, 4, 1),
            created_by=admin.id,
            updated_by=admin.id,
        )
        session.add(student)
        session.flush()
        guardian = Guardian(
            branch_id=branch.id,
            full_name=f"{_FIRST[index]} {_LAST[index]} Sr",
            relationship_name="Parent",
            phone=f"555-010-{index + 1:04d}",
            email=f"guardian{index + 1:02d}@tuition.example",
            created_by=admin.id,
            updated_by=admin.id,
        )
        session.add(guardian)
        session.flush()
        session.add(
            StudentGuardian(
                student_id=student.id,
                guardian_id=guardian.id,
                is_primary=True,
                can_pay=True,
                can_view=True,
                created_by=admin.id,
            )
        )
        students.append(student)
    _seat(session, branch, batches["MATH"], students[0:12], "active", admin.id)
    _seat(session, branch, batches["MATH"], students[12:15], "waitlisted", admin.id)
    _seat(session, branch, batches["ENG"], students[15:30], "active", admin.id)
    _seat(session, branch, batches["SCI"], students[0:10], "active", admin.id)

    teacher = _teacher(session, branch, admin)
    staff = Staff(
        branch_id=branch.id,
        user_id=teacher.id,
        employee_no="MAIN-EMP-0001",
        designation="Teacher",
        status="active",
        created_by=admin.id,
        updated_by=admin.id,
    )
    session.add(staff)
    session.flush()
    session.add_all(
        [
            BatchTeacher(
                batch_id=batches["MATH"].id, staff_id=staff.id, role="primary", created_by=admin.id
            ),
            BatchTeacher(
                batch_id=batches["SCI"].id, staff_id=staff.id, role="primary", created_by=admin.id
            ),
        ]
    )
    session.add_all(
        [
            NumberSequence(
                branch_id=branch.id,
                doc_type="admission",
                prefix="MAIN-2026-",
                next_number=31,
                created_by=admin.id,
                updated_by=admin.id,
            ),
            NumberSequence(
                branch_id=branch.id,
                doc_type="employee",
                prefix="MAIN-EMP-",
                next_number=2,
                created_by=admin.id,
                updated_by=admin.id,
            ),
        ]
    )
    converted = Inquiry(
        branch_id=branch.id,
        name=students[0].full_name,
        phone="555-010-0001",
        email="lead.amina@tuition.example",
        course_interest_id=courses["MATH"].id,
        source="walk_in",
        status="converted",
        converted_student_id=students[0].id,
        notes="Converted during sample setup.",
        created_by=admin.id,
        updated_by=admin.id,
    )
    open_leads = [
        Inquiry(
            branch_id=branch.id,
            name="Sara Noor",
            phone="555-200-0001",
            email="sara.noor@tuition.example",
            course_interest_id=courses["MATH"].id,
            source="website",
            status="new",
            created_by=admin.id,
            updated_by=admin.id,
        ),
        Inquiry(
            branch_id=branch.id,
            name="Omar Farid",
            phone="555-200-0002",
            source="phone",
            status="contacted",
            course_interest_id=courses["ENG"].id,
            follow_up_date=date(2026, 4, 15),
            created_by=admin.id,
            updated_by=admin.id,
        ),
        Inquiry(
            branch_id=branch.id,
            name="Lina Cruz",
            phone="555-200-0003",
            source="referral",
            status="qualified",
            course_interest_id=courses["SCI"].id,
            created_by=admin.id,
            updated_by=admin.id,
        ),
        Inquiry(
            branch_id=branch.id,
            name="Noah Blake",
            phone="555-200-0004",
            source="walk_in",
            status="lost",
            notes="Chose another centre.",
            created_by=admin.id,
            updated_by=admin.id,
        ),
    ]
    session.add_all([converted, *open_leads])
    session.flush()
    session.add(
        InquiryFollowup(
            branch_id=branch.id,
            inquiry_id=open_leads[1].id,
            note="Called and confirmed interest in Grade 9 English.",
            next_date=date(2026, 4, 15),
            created_by=admin.id,
        )
    )
    logger.info("Seeded sample courses, 30 students, and teacher %s", TEACHER_EMAIL)


def _batch(branch, course, term, room, name, capacity, admin_id) -> Batch:
    return Batch(
        branch_id=branch.id,
        course_id=course.id,
        term_id=term.id,
        room_id=room.id,
        name=name,
        start_date=term.start_date,
        end_date=term.end_date,
        capacity=capacity,
        status="active",
        created_by=admin_id,
        updated_by=admin_id,
    )


def _seat(
    session: Session, branch, batch: Batch, students: list[Student], status: str, admin_id: int
) -> None:
    for position, student in enumerate(students, start=1):
        session.add(
            Enrollment(
                branch_id=branch.id,
                student_id=student.id,
                batch_id=batch.id,
                enrolled_on=date(2026, 4, 1),
                status=status,
                waitlist_position=position if status == "waitlisted" else None,
                created_by=admin_id,
                updated_by=admin_id,
            )
        )


def _teacher(session: Session, branch: Branch, admin: User) -> User:
    role = session.scalar(select(Role).where(Role.name == "teacher"))
    user = session.scalar(select(User).where(User.email == TEACHER_EMAIL))
    if user is None:
        user = User(
            email=TEACHER_EMAIL,
            full_name="Maya Iqbal",
            password_hash=hash_password(TEACHER_PASSWORD),
            status="active",
            created_by=admin.id,
            updated_by=admin.id,
        )
        session.add(user)
        session.flush()
    link = session.scalar(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
    )
    if link is None:
        session.add(
            UserRole(user_id=user.id, role_id=role.id, branch_id=branch.id, created_by=admin.id)
        )
        session.flush()
    return user
